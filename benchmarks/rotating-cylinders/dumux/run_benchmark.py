import json
import shutil
import subprocess
import zipfile
import os
from pathlib import Path

# We look one level up for the zip and stay in the current folder for extraction.
root_dir = Path(__file__).resolve().parent
zip_path = root_dir.parent / "rotating-cylinders.zip"
benchmark_dir = root_dir / "rotating-cylinders"
snakefile_path = root_dir / "Snakefile"

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
        output_dir = benchmark_dir / "results" / data.get("configuration")
        output_dir.mkdir(parents=True, exist_ok=True) 
        
        # Copy the selected parameter file to the output directory with a standardised name
        with open(output_dir / "parameters.json", "w") as outfile:
            json.dump(data, outfile, indent=2)

        # Copy files from benchmark_dir to output_dir, excluding non-matching parameter files.
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
            "--singularity-args", f"--bind {benchmark_dir}:/dumux/shared",
            "--config", f'conf_name="{config_name}"',
            "--force"
        ], check=True, cwd=output_dir)
        
        # Run the Snakemake reporter for the configuration
        subprocess.run([
            "snakemake",
            "-s", str(snakefile_path),
            "--use-singularity",
            "--cores", "all",
            "--resources", "serial_run=1",
            "--singularity-args", f"--bind {benchmark_dir}:/dumux/shared",
            "--config", f'conf_name="{config_name}"',
            "--reporter", "metadata4ing",
            "--report-metadata4ing-config", "metadata4ing.config",
            "--report-metadata4ing-filename", f"dumux_rocrate_{config_name}.zip",
            "--force"
        ], check=True, cwd=output_dir)
        
        print(f"Workflow executed successfully for {config_name}.")
        
print("\nAll configurations processed.")

# --- CLEANUP SECTION ---
print("\nStarting cleanup...")

# Find all JSON files starting with 'parameters_' in the benchmark directory
for param_file in benchmark_dir.glob("parameters_*.json"):
    try:
        os.remove(param_file)
        print(f"Deleted: {param_file.name}")
    except Exception as e:
        print(f"Error deleting {param_file.name}: {e}")

print("Cleanup complete.")