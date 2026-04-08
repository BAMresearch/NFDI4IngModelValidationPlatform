from pathlib import Path
import zipfile
import json
import shutil
import subprocess

"""
The script performs the following steps:

1. Extracts the benchmark files from a zip archive (currently assuming that it is an RO-Crate of the benchmark).
2. Iterates through the parameter configuration files, checks the "element-size" value, and if it meets the specified condition (>= 0.025)
, it executes the Snakemake workflow for that configuration.

The results of each run (and the files used by it) are stored in the directory with the configuration name.
"""

####################################################################################################
####################################################################################################
# Benchmark Extraction
####################################################################################################
####################################################################################################

root_zipped_benchmark_dir = Path(__file__).resolve().parent.parent
root_unzipped_benchmark_dir = Path(__file__).resolve().parent

with zipfile.ZipFile(root_zipped_benchmark_dir / "linear-elastic-plate-with-hole.zip", 'r') as zip_ref:
    # Extract all files
    zip_ref.extractall(root_unzipped_benchmark_dir)
    
    
#Creates a directory to store the conda environments. The environments are shared across different parameter configurations.
#To avoid redundant creation of environments, this path will be passed to all snakemake files during execution.
        
shared_env_dir = root_unzipped_benchmark_dir / "conda_envs"
shared_env_dir.mkdir(parents=True, exist_ok=True)  

####################################################################################################
####################################################################################################
# Conditional execution of parameter configurations 
####################################################################################################
####################################################################################################
  
for file in root_unzipped_benchmark_dir.glob("parameters_*.json"):
    with open(file, "r") as f:
        data = json.load(f)
        if data.get("element-size").get("value") >= 0.025:
            
            # Create output directory for the configuration
            output_dir = root_unzipped_benchmark_dir / "results" / data.get("configuration")
            output_dir.mkdir(parents=True, exist_ok=True) 
            
            # Copy the selected parameter file to the output directory with a standardised name
            with open(output_dir / "parameters.json", "w") as outfile:
                json.dump(data, outfile, indent=2)

            # Copy files from benchmark_dir to output_dir, excluding non-matching parameter files.
            for item in root_unzipped_benchmark_dir.iterdir():
                if item.is_file():
                    if item.name.startswith("parameters_") and item.suffix == ".json":
                        continue
                    else:
                        shutil.copy(item, output_dir / item.name)
                            
            # Run the Snakemake workflow for the configuration
            subprocess.run(["snakemake", "--use-conda", "--force", "--cores", "all", "--conda-prefix", str(shared_env_dir)], check=True, cwd=output_dir)
            print("Workflow executed successfully.")
            
            # For the scenario where the snakemake workflow doesn't exist, one can directly run the simulation script using the subprocess module, e.g.:
            #subprocess.run(["python", "run_fenics_simulation.py" \
                            #"--input_parameter_file" "parameters.json" \
                            #"--input_mesh_file" "mesh.msh" \
                            #"--output_solution_file_zip" "solution_field_data.zip" \
                            #"--output_metrics_file" "solution_metrics.json"], check=True, cwd=output_dir)
                            
            #Assuming the mesh.msh and parameters.json files are present/copied to the output_dir.