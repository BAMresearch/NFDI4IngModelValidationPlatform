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
            parameters["young_modulus[Pa]"], "Pa"
        )
        .to_base_units()
        .magnitude
    )
    nu = (
        ureg.Quantity(
            parameters["poisson_ratio"], ""
        )
        .to_base_units()
        .magnitude
    )
    radius = (
        ureg.Quantity(parameters["radius[m]"], "m")
        .to_base_units()
        .magnitude
    )
    L = (
        ureg.Quantity(parameters["length[m]"], "m")
        .to_base_units()
        .magnitude
    )
    load = (
        ureg.Quantity(parameters["load[MPa]"], "MPa")
        .to_base_units()
        .magnitude
    )

    displacement_evaluation_point = parameters["displacement_evaluation_point[m]"]
    displacement_evaluation_x = (
        ureg.Quantity(
            displacement_evaluation_point[0],
            "m",
        )
        .to_base_units()
        .magnitude
    )
    displacement_evaluation_y = (
        ureg.Quantity(
            displacement_evaluation_point[1],
            "m",
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
    # Compute maximum von Mises stress at Gauss points.
    max_von_mises_stress_gauss_points = 0
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
    # Note: Kratos REACTION variable represents force exerted BY structure ON constraint, 
    # so we negate to get the standard FEA convention (constraint force ON structure).
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

    # Compute nodal displacement error (Euclidean norm of error vector at each node)
    nodal_displacement_error = np.linalg.norm(displacement - u_ref, axis=1)
    max_displacement_error_nodes = float(np.max(nodal_displacement_error))
    
    # Compute the number of dofs
    num_dofs = int(mesh.n_points * 2)

    metrics = {
        "number_of_dofs[-]": num_dofs,
        "max_von_mises_stress[Pa]": max_von_mises_stress_gauss_points,
        "l2_error_displacement[m]": l2_error_displacement,
        "max_displacement_error[m]": max_displacement_error_nodes,
        "reaction_force_left_boundary_x[N]": reaction_force_left_boundary_x,
        "reaction_force_left_boundary_y[N]": reaction_force_left_boundary_y,
        f"displacement_x_at_evaluation_point (x={displacement_evaluation_x}, y={displacement_evaluation_y})[m]": displacement_x_at_evaluation_point,
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
