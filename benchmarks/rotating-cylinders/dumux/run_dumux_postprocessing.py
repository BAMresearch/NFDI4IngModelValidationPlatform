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

    # ---- Targeted Discovery ----
    # Only find files that belong to THIS configuration to avoid race conditions
    # DuMuX files usually look like: test_rotatingcylinders_10_80-00001.vtu
    vtk_files = list(dumux_output_dir.glob(f"*{configuration}*.vtu")) + \
                list(dumux_output_dir.glob(f"*{configuration}*.pvtu"))
    
    pvd_files = list(dumux_output_dir.glob(f"*{configuration}*.pvd"))

    if not vtk_files:
        raise RuntimeError(f"No VTU/PVTU files found for configuration: {configuration}")

    # Sort files to ensure we process the last timestep (usually the highest index)
    vtk_files.sort()
    
    # Read the last VTU file for metrics (represents the final state)
    mesh = meshio.read(vtk_files[-1])

    metrics = {}

    # ---- Example metrics (keep your original logic) ----
    if "p" in mesh.cell_data_dict:
        p = mesh.cell_data_dict["p"]
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

    # ---- Write metrics JSON ----
    metrics_path = Path(metrics_file)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=4)

    # ---- Zip solution field data ----
    # We include VTUs and the PVD specifically for this configuration
    with zipfile.ZipFile(solution_file_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in vtk_files + pvd_files:
            zipf.write(file, arcname=file.name)

    # ---- Targeted Cleanup ----
    # Only delete files we just zipped. This allows other concurrent 
    # configurations to finish safely.
    for file in vtk_files + pvd_files:
        try:
            file.unlink()
        except FileNotFoundError:
            pass # Already removed or handled


if __name__ == "__main__":
    parser = ArgumentParser(description="Post-process DuMuX results")
    parser.add_argument("--input_dumux_output_dir", required=True)
    parser.add_argument("--input_configuration", required=True)
    parser.add_argument("--output_metrics_file", required=True)
    parser.add_argument("--output_solution_file_zip", required=True)

    args = parser.parse_args()

    run_dumux_postprocessing(
        args.input_dumux_output_dir,
        args.input_configuration,
        args.output_metrics_file,
        args.output_solution_file_zip,
    )