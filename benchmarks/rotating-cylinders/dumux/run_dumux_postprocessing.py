import json
import zipfile
from argparse import ArgumentParser
from pathlib import Path

import meshio
import numpy as np


def run_dumux_postprocessing(
    dumux_output_dir: str,
    configuration: str,
    metrics_file: str,
    solution_file_zip: str,
) -> None:
    dumux_output_dir = Path(dumux_output_dir)

    # ---- read all VTU / PVTU files ----
    vtk_files = list(dumux_output_dir.glob("*.vtu")) + list(
        dumux_output_dir.glob("*.pvtu")
    )
    if not vtk_files:
        raise RuntimeError("No VTU/PVTU files found in DuMuX output directory")

    # Read first file for metrics (extend if needed)
    mesh = meshio.read(vtk_files[0])

    metrics = {}

    # ---- example metrics (adapt to benchmark definition) ----
    if "p" in mesh.cell_data_dict:
        p = mesh.cell_data_dict["p"]
        # flatten possible block structure
        p_vals = np.concatenate([np.asarray(v).ravel() for v in p.values()])
        metrics["min_pressure"] = float(np.min(p_vals))
        metrics["max_pressure"] = float(np.max(p_vals))
        metrics["mean_pressure"] = float(np.mean(p_vals))

    if "velocity_liq (m/s)" in mesh.cell_data_dict:
        v = mesh.cell_data_dict["velocity_liq (m/s)"]
        v_vals = np.concatenate([np.asarray(vv) for vv in v.values()])
        speed = np.linalg.norm(v_vals, axis=1)
        metrics["max_velocity_magnitude"] = float(np.max(speed))
        metrics["mean_velocity_magnitude"] = float(np.mean(speed))

    # ---- write metrics JSON ----
    with open(metrics_file, "w") as f:
        json.dump(metrics, f, indent=4)

    # ---- zip solution field data ----
    with zipfile.ZipFile(solution_file_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in vtk_files:
            zipf.write(file, arcname=file.name)

    # ---- cleanup: delete original VTU/PVTU files ----
    for ext in ["*.vtu", "*.pvtu", "*.pvd"]:
        for file in dumux_output_dir.glob(ext):
            file.unlink()


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Post-process DuMuX results into benchmark artifacts"
    )
    parser.add_argument(
        "--input_dumux_output_dir",
        required=True,
        help="Directory containing DuMuX VTU/PVTU files",
    )
    parser.add_argument(
        "--input_configuration",
        required=True,
        help="Configuration name",
    )
    parser.add_argument(
        "--output_metrics_file",
        required=True,
        help="Path to solution_metrics_{configuration}.json",
    )
    parser.add_argument(
        "--output_solution_file_zip",
        required=True,
        help="Path to solution_field_data_{configuration}.zip",
    )

    args = parser.parse_args()

    run_dumux_postprocessing(
        args.input_dumux_output_dir,
        args.input_configuration,
        args.output_metrics_file,
        args.output_solution_file_zip,
    )
