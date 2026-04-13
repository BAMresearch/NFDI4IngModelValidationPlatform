import json
import pyvista
from pathlib import Path
import zipfile
from argparse import ArgumentParser
import numpy as np
from pint import UnitRegistry
import sys
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytical_solution import AnalyticalSolution

def postprocess_results(input_parameter_file, input_result_vtk, output_metrics_file, output_solution_file_zip):
    ureg = UnitRegistry()
    with open(input_parameter_file) as f:
        parameters = json.load(f)
    config = parameters["configuration"]

    mesh = pyvista.read(str(input_result_vtk))
    if not isinstance(mesh, pyvista.DataSet):
        raise TypeError(f"Expected a pyvista.DataSet, got {type(mesh).__name__}")
    mesh = cast(pyvista.DataSet, mesh)

    E = (
        ureg.Quantity(
            parameters["young-modulus"]["value"], parameters["young-modulus"]["unit"]
        )
        .to_base_units()
        .magnitude
    )
    nu = (
        ureg.Quantity(
            parameters["poisson-ratio"]["value"], parameters["poisson-ratio"]["unit"]
        )
        .to_base_units()
        .magnitude
    )
    radius = (
        ureg.Quantity(parameters["radius"]["value"], parameters["radius"]["unit"])
        .to_base_units()
        .magnitude
    )
    L = (
        ureg.Quantity(parameters["length"]["value"], parameters["length"]["unit"])
        .to_base_units()
        .magnitude
    )
    load = (
        ureg.Quantity(parameters["load"]["value"], parameters["load"]["unit"])
        .to_base_units()
        .magnitude
    )

    displacement_evaluation_point = parameters["displacement-evaluation-point"]
    displacement_evaluation_x = (
        ureg.Quantity(
            displacement_evaluation_point["x"]["value"],
            displacement_evaluation_point["x"]["unit"],
        )
        .to_base_units()
        .magnitude
    )
    displacement_evaluation_y = (
        ureg.Quantity(
            displacement_evaluation_point["y"]["value"],
            displacement_evaluation_point["y"]["unit"],
        )
        .to_base_units()
        .magnitude
    )

    analytical_solution = AnalyticalSolution(
        E=E,
        nu=nu,
        radius=radius,
        L=L,
        load=load,
    )
    # Compute maximum von Mises stress at nodes and Gauss points.
    max_von_mises_stress_nodes = float(np.max(mesh.point_data["VON_MISES_STRESS"]))

    max_von_mises_stress_gauss_points = max_von_mises_stress_nodes
    for key, values in mesh.cell_data.items():
        if "VON_MISES_STRESS" in key:
            max_von_mises_stress_gauss_points = float(np.max(values))
            break
    
    # Compute L2 error of displacement field compared to analytical solution.
    coords = np.asarray(mesh.points)
    displacement = np.asarray(mesh.point_data["DISPLACEMENT"])[:, :2]
    u_ref_x, u_ref_y = analytical_solution.displacement(coords[:, :2].T)
    u_ref = np.column_stack((np.asarray(u_ref_x), np.asarray(u_ref_y)))
    err_sq_node = np.sum((displacement - u_ref) ** 2, axis=1)

    cell_sizes = mesh.compute_cell_sizes(length=False, area=True, volume=False)
    cell_areas = np.asarray(cell_sizes.cell_data["Area"])
    l2_error_sq = 0.0
    for i in range(mesh.n_cells):
        point_ids = mesh.get_cell(i).point_ids
        if len(point_ids) == 0:
            continue
        l2_error_sq += float(np.mean(err_sq_node[point_ids]) * cell_areas[i])
    l2_error_displacement = float(np.sqrt(l2_error_sq))

    # Compute reaction forces on the left boundary (x=0) by summing the reaction forces at the nodes on that boundary.
    tolerance = 1e-10 * max(1.0, L)
    left_boundary_mask = np.isclose(coords[:, 0], 0.0, atol=tolerance)
    reaction = np.asarray(mesh.point_data.get("REACTION", np.zeros((mesh.n_points, 3))))
    reaction_force_left_boundary_x = float(np.sum(reaction[left_boundary_mask, 0]))
    reaction_force_left_boundary_y = float(np.sum(reaction[left_boundary_mask, 1]))

    probe_points = pyvista.PolyData(
        np.array([[displacement_evaluation_x, displacement_evaluation_y, 0.0]], dtype=float)
    )
    sampled = probe_points.sample(mesh)
    displacement_sampled = sampled.point_data.get("DISPLACEMENT")
    if displacement_sampled is None:
        closest_id = mesh.find_closest_point([displacement_evaluation_x, displacement_evaluation_y, 0.0])
        displacement_x_at_evaluation_point = float(displacement[closest_id, 0])
    else:
        displacement_x_at_evaluation_point = float(displacement_sampled[0, 0])

    metrics = {
        "max_von_mises_stress_nodes": max_von_mises_stress_nodes,
        "max_von_mises_stress_gauss_points": max_von_mises_stress_gauss_points,
        "l2_error_displacement": l2_error_displacement,
        "reaction_force_left_boundary_x": reaction_force_left_boundary_x,
        "reaction_force_left_boundary_y": reaction_force_left_boundary_y,
        f"displacement_x_at_evaluation_point (x={displacement_evaluation_x}, y={displacement_evaluation_y})": displacement_x_at_evaluation_point,
    }
    with open(output_metrics_file, "w") as f:
        json.dump(metrics, f, indent=4)
        
    files_to_store = [str(input_result_vtk)]

    with zipfile.ZipFile(output_solution_file_zip, "w") as zipf:
        for filepath in files_to_store:
            zipf.write(filepath, arcname=f"result_{config}.vtk")

if __name__ == "__main__":
    parser = ArgumentParser(
        description="Postprocess Kratos results and write metrics and zipped solution."
    )
    parser.add_argument(
        "--input_parameter_file",
        required=True,
        help="JSON file containing simulation parameters (input)",
    )
    parser.add_argument(
        "--input_result_vtk",
        required=True,
        help="Path to the Kratos result VTK file (input)",
    )
    parser.add_argument(
        "--output_solution_file_zip",
        required=True,
        help="Path to the zipped solution files (output)",
    )
    parser.add_argument(
        "--output_metrics_file",
        required=True,
        help="Path to the output metrics JSON file (output)",
    )
    args, _ = parser.parse_known_args()

    postprocess_results(
        args.input_parameter_file,
        args.input_result_vtk,
        args.output_metrics_file,
        args.output_solution_file_zip
    )
