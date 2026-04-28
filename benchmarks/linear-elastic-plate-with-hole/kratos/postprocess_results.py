import json
import pyvista
from pathlib import Path
import zipfile
from argparse import ArgumentParser

def postprocess_results(input_parameter_file, input_result_vtk, output_metrics_file, output_solution_file_zip):
    with open(input_parameter_file) as f:
        parameters = json.load(f)
    config = parameters["configuration"]

    mesh = pyvista.read(str(input_result_vtk))
    max_von_mises_stress = float(mesh["VON_MISES_STRESS"].max())
    print("Max Von Mises Stress:", max_von_mises_stress)
    metrics = {
        "max_von_mises_stress_nodes": max_von_mises_stress
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
