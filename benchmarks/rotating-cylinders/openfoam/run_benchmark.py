import json
import shutil
import subprocess
import zipfile
import os
from pathlib import Path

root_dir = Path(__file__).resolve().parent
zip_path = root_dir.parent / "rotating-cylinders.zip"
benchmark_dir = root_dir / "rotating-cylinders"
snakefile_path = root_dir / "Snakefile"
reporter_config_path = root_dir / "metadata4ing.config"

# Extraction
if zip_path.exists():
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(benchmark_dir)
    print(f"Successfully extracted benchmark to: {benchmark_dir}")
else:
    print(f"Error: Could not find {zip_path} at {root_dir.parent}")
    exit(1)

# Iterate through all parameter files
for param_file in benchmark_dir.glob("parameters_*.json"):
    with open(param_file, "r") as f:
        data = json.load(f)
        config_name = data.get("configuration")

        if not config_name:
            print(f"Skipping {param_file.name}: No configuration name found.")
            continue

        # Create output directory for the configuration
        output_dir = root_dir / "results" / config_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy the selected parameter file to the output directory with a standardised name
        with open(output_dir / "parameters.json", "w") as outfile:
            json.dump(data, outfile, indent=2)

        # Copy OpenFOAM template files to the output directory
        for item in ["0", "system", "constant", "Allrun", "Allclean", "plot"]:
            src = root_dir / item
            dst = output_dir / item
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            elif src.is_file():
                shutil.copy(src, dst)

        # Copy any additional files from the zip extract dir (excluding parameter files)
        for item in benchmark_dir.iterdir():
            if item.is_file():
                if item.name.startswith("parameters_") and item.suffix == ".json":
                    continue
                else:
                    shutil.copy(item, output_dir / item.name)

        # Run the Snakemake workflow for the configuration
        subprocess.run([
            "snakemake",
            "-s", str(snakefile_path),
            "--use-singularity",
            "--cores", "all",
            "--resources", "serial_run=1",
            "--force"
        ], check=True, cwd=output_dir)
        
        # Run the Snakemake reporter for the configuration
        subprocess.run([
            "snakemake",
            "-s", str(snakefile_path),
            "--use-singularity",
            "--cores", "all",
            "--resources", "serial_run=1",
            "--force",
            "--reporter", "metadata4ing",
            "--report-metadata4ing-filename", f"openfoam_rocrate_{config_name}.zip",
            "--report-metadata4ing-name", "NFDI4Ing Provenance", \
            "--report-metadata4ing-description", "Benchmark for rotating cylinders", \
            "--report-metadata4ing-license", "https://opensource.org/licenses/MIT", \
            "--report-metadata4ing-profile", "provenance-run-crate-0.5", \
        ], check=True, cwd=output_dir)
        
        print(f"Workflow executed successfully for {config_name}.")

print("\nAll configurations processed.")

# --- CLEANUP SECTION ---
print("\nStarting cleanup...")

for param_file in benchmark_dir.glob("parameters_*.json"):
    try:
        os.remove(param_file)
        print(f"Deleted: {param_file.name}")
    except Exception as e:
        print(f"Error deleting {param_file.name}: {e}")

print("Cleanup complete.")
