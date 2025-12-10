#!/usr/bin/env python3
"""
Script to generate a Snakefile for simulation tools in the benchmark workflow.

This script creates a standardized Snakefile that follows the expected output format
for integration with the main benchmark workflow.
"""

import argparse
import os
from pathlib import Path


def generate_snakefile(tool_name: str, environment_file: str, simulation_script: str, output_path: str = None):
    """
    Generate a Snakefile for a simulation tool.
    
    Args:
        tool_name: Name of the simulation tool (e.g., 'fenics', 'kratos')
        environment_file: Path to the conda environment YAML file (relative to tool directory)
        simulation_script: Path to the simulation Python script (relative to tool directory)
        output_path: Optional path where to save the Snakefile. If None, saves to {tool_name}/Snakefile
    """
    
    # Template for the Snakefile
    
    snakefile_template = f'''import json
import os

tool = "{tool_name}"
result_dir = "snakemake_results/" + config["benchmark"] 
configuration_to_parameter_file = config["configuration_to_parameter_file"]
configurations = config["configurations"]


rule run_{tool_name}_simulation:
    input: 
        script = "{{tool}}/{simulation_script}",
        parameters = lambda wildcards: configuration_to_parameter_file[wildcards.configuration],
        mesh = f"{{result_dir}}/mesh/mesh_{{{{configuration}}}}.msh",
    output:
        zip = f"{{result_dir}}/{{{{tool}}}}/solution_field_data_{{{{configuration}}}}.zip",
        metrics = f"{{result_dir}}/{{{{tool}}}}/solution_metrics_{{{{configuration}}}}.json",
    conda:
        "{environment_file}",
    shell:
        """
        python3 {{input.script}} --input_parameter_file {{input.parameters}} --input_mesh_file {{input.mesh}} --output_solution_file_zip {{output.zip}} --output_metrics_file {{output.metrics}}
        """
    '''
    
    # Determine output path
    if output_path is None:
        output_path = f"../linear-elastic-plate-with-hole/{tool_name}/Snakefile"
    
    # Write the Snakefile
    with open(output_path, 'w') as f:
        f.write(snakefile_template)
    
    print(f"Snakefile generated successfully: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Generate a simulation-tool-specific Snakefile for running the simulation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=
    """
    !IMPORTANT!:The scripts to be stored inside the tool's sub-directory in the benchmark folder. E.g., benchmarks/linear-elastic-plate-with-hole/tool_name/
    
    Execution example for fenics:
    python generate_tool_snakefile.py --tool fenics --env environment_simulation.yml --script run_fenics_simulation.py

    The simulation script must accept these command-line arguments:
      --input_parameter_file: JSON file with simulation parameters
      --input_mesh_file: Input mesh file (.msh format)
      --output_solution_file_zip: Output ZIP file containing solution visualization files (VTK)
      --output_metrics_file: Output JSON file with computed metrics

    """
    )
    
    parser.add_argument(
        '--tool',
        type=str,
        required=True,
        help='Name of the simulation tool (e.g., fenics, kratos, abaqus)'
    )
    
    parser.add_argument(
        '--environment_file',
        type=str,
        required=True,
        help='Conda environment YAML file name'
    )
    
    parser.add_argument(
        '--simulation_script',
        type=str,
        required=True,
        help='Simulation script name'
    )
    
    args = parser.parse_args()
    
    generate_snakefile(
        tool_name=args.tool,
        environment_file=args.environment_file,
        simulation_script=args.simulation_script
    )

if __name__ == "__main__":
    main()


