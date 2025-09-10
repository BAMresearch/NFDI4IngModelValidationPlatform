# generate_config.py
import json

from pathlib import Path
from os.path import join

files = list(Path(".").glob("parameters_*.json"))

# extract the configuration from the parameter files
# by reading in the json files and extracting the "configuration" value
# configuration stores the appendix in the output files)"
# in theory, you could make that identical so parameters_1.json with configuration "1" 
# would produce summary_1.json
import json
import copy
def get_configuration(file):
    with open(file, 'r') as f:
        data = json.load(f)
    # Check if "configuration" key exists, otherwise use the file name
    if "configuration" in data:
        return data["configuration"]
    # Fallback to using the file name if "configuration" is not present
    # Assuming the file name is in the format "parameters_<configuration>.json"
    if file.stem.startswith("parameters_"):
        return file.stem.split("_")[1]
    # If no configuration is found, raise an error
    raise ValueError(f"Configuration key not found for file: {file}")

# Create a dictionary of configurations (key is the name of the parameter file)
# configurations: {Path("parameters_1.json"): "1", ...}
configurations = {file: get_configuration(file) for file in files if file.is_file()}

# Check for duplicate configuration values (the configurations should be unique)
config_values = list(configurations.values())
duplicates = set([x for x in config_values if config_values.count(x) > 1])
if duplicates:
    raise ValueError(f"Duplicate configuration values found in parameter files: {', '.join(duplicates)}")

# Reverse mapping for easy lookup by configuration name
configuration_to_parameter_file = {v: str(k) for k, v in configurations.items()}

benchmark = "linear-elastic-plate-with-hole"

# results are stored in snakemake_results/linear-elastic-plate-with-hole/fenics
result_dir_snakemake = join("snakemake_results", benchmark)
result_dir_nextflow = join("nextflow_results", benchmark)

# Template for workflow config
workflow_config_template = {
    "result_dir": None,  # to be set
    "configuration_to_parameter_file": configuration_to_parameter_file,
    "configurations": list(configurations.values()),
    "tools": ["fenics", "kratos"],
    "benchmark": benchmark
}

# Create configs by copying the template and setting result_dir

workflow_config_snakemake = copy.deepcopy(workflow_config_template)
workflow_config_snakemake["result_dir"] = result_dir_snakemake

workflow_config_nextflow = copy.deepcopy(workflow_config_template)
workflow_config_nextflow["result_dir"] = result_dir_nextflow

# Write both configs to separate files
with open("workflow_config_snakemake.json", "w") as f:
    json.dump(workflow_config_snakemake, f, indent=4)
with open("workflow_config_nextflow.json", "w") as f:
    json.dump(workflow_config_nextflow, f, indent=4)

