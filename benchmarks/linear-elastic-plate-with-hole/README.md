# Infinite plate with hole benchmark in FEniCSx

## Problem Definition

See the [documentation](../../docs/benchmarks/linear%20elasticity/index.md) for a detailed problem definition and mathematical formulation.

## Running the Benchmark

1. **Generate Configuration Files**

   Before running the benchmark, generate the configuration files using:
   ```bash
   python generate_config.py
   ```
   This script creates a workflow_config.json that defines what configurations are computed (in the starndard case one for each parameter_file_*.json) and what tools are used.

2. **Run the Benchmark**

   The benchmark is managed via Snakemake. You can run all tools or specify a subset (e.g., only fenics) by editing the generated config or passing parameters via the command line:
   ```bash
   snakemake --use-conda --cores all
   ```
   To run only a specific tool or specific configuration (e.g. for testing), update the config file or use:
   ```bash
   snakemake --use-conda --cores all --config tools=fenics
   ```

3. **Collect Provenance**

   After running, provenance data is collected automatically and stored in .snakemake. If you want to use the reporter plugin ([metadata4ing](https://github.com/izus-fokus/snakemake-report-plugin-metadata4ing)) to generate an ROCrate, call snakemake again (make sure the plugin is added to the environment):
   ```bash
   snakemake --use-conda --cores all --reporter metadata4ing
   ```
   Output and provenance files are stored in the `snakemake_results/` directory and as zipped archives.

## Hierarchical Structure of Snakefiles

The workflow is organized hierarchically:
- The main `Snakefile` orchestrates the benchmark and includes sub-workflows for each tool.
- Each tool (e.g., fenics) has its own rules and output structure.

### Inputs

Each tool's rule must accept:
- A parameter/configuration file (e.g., `parameters_*.json`) specifying geometry, material properties, boundary conditions, and solver settings.
- A mesh file (*.msh from gmsh) generated with the rule generate_mesh.

### Outputs

Each tool's rule must produce:
- **Solution field results**: This zip-file should include all the data used to plot the output like strains, stresses or displacements of the solution field.
- **Metrics file**: JSON-File summarizing key metrics (e.g., max Mises stress at Gauss points or maximum mises stress obtained when projecting to the nodes).
- All output files should be placed in the designated results directory (e.g., `snakemake_results/{benchmark}/{tool}/solution_field_data_{configuration}.zip`). `snakemake_results/` is generated from the level where snakemake is executed, but this directory is then zipped.

To add another simulation tool:
  - Create a new subdirectory for the tool.
  - Create a new Snakefile with at least one rule that produces the outputs (metrics and solution fields)
  - Ensure the rule accepts the standardized parameter file and mesh/input files.
  - Update the main `Snakefile` to include the new tool's rules.