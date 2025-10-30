# Comprehensive Workflow Creation Guide for Benchmark Problems

This guide outlines the algorithm and steps needed to create workflows for benchmark problems in the NFDI4IngModelValidationPlatform. The guide is based on the analysis of the `linear-elastic-plate-with-hole` benchmark implementation which demonstrates both workflow systems.

## Overview

The platform supports **dual workflow systems** to maximize compatibility and user preferences:

1. **Snakemake Workflow System**: Python-based workflow management with conda integration
2. **Nextflow Workflow System**: Container-native workflow management with enhanced provenance tracking

Both systems support:
- Multiple simulation tools (e.g., FEniCS, Kratos)
- Multiple parameter configurations per benchmark
- Automated mesh generation
- Standardized output formats
- Comprehensive provenance tracking and metadata collection
- Automated results summarization and visualization

## Benchmark Structure Requirements

Create a dedicated directory for your benchmark with the following structure:

```
your-benchmark-name/
├── README.md                        # Documentation
├── generate_config.py               # Configuration generator
├── workflow_config.json             # Generated workflow configuration
├── create_mesh.py                  # Mesh generation script
├── summarise_results.py            # Results aggregation script
├── parameter_extractor.py          # Provenance parameter extraction
├── plot_provenance.py              # Provenance visualization
├── plateWithHoleSolution.py        # Analytical solution (if applicable)
├── parameters_*.json               # Parameter files for each configuration
├── environment_mesh.yml            # Conda environment for meshing
├── environment_postprocessing.yml  # Conda environment for post-processing
│
├── # Snakemake Implementation
├── Snakefile                       # Main Snakemake workflow
│
├── # Nextflow Implementation  
├── main.nf                         # Main Nextflow workflow
├── nextflow.config                 # Nextflow configuration
│
└── tool1/                          # Directory for simulation tool 1
    ├── Snakefile                   # Tool-specific Snakemake workflow
    ├── tool1.nf                    # Tool-specific Nextflow workflow
    ├── environment_simulation.yml  # Tool-specific conda environment
    ├── run_tool1_simulation.py     # Main simulation script
    ├── create_tool1_input.py       # Input file preparation (if needed)
    ├── postprocess_results.py      # Post-processing script (if needed)
    └── template_files/             # Template configuration files
```

## Algorithm for Creating Dual-System Workflows

### Step 1: Define Parameter Files and Configuration

Create parameter files following the standardized JSON format:

```json
{
    "configuration": "unique_config_name",
    "geometry_parameters": {
        "radius": {"value": 0.33, "unit": "m"},
        "length": {"value": 1.0, "unit": "m"}
    },
    "material_properties": {
        "young-modulus": {"value": 210e9, "unit": "Pa"},
        "poisson-ratio": {"value": 0.3, "unit": ""}
    },
    "mesh_parameters": {
        "element-size": {"value": 0.1, "unit": "m"},
        "element-order": 1,
        "element-degree": 1
    },
    "solver_settings": {
        "quadrature-rule": "gauss",
        "quadrature-degree": 1
    },
    "loading_conditions": {
        "load": {"value": 100.0, "unit": "MPa"}
    }
}
```

### Step 2: Implement Configuration Generator

Create `generate_config.py` to automatically discover and validate configurations:

```python
import json
from pathlib import Path

def generate_workflow_config():
    # Discover parameter files
    files = list(Path(".").glob("parameters_*.json"))
    
    # Extract and validate configurations
    configurations = {}
    for file in files:
        with open(file, 'r') as f:
            data = json.load(f)
        config_name = data.get("configuration", file.stem.split("_")[1])
        configurations[file] = config_name
    
    # Check for duplicates
    config_values = list(configurations.values())
    duplicates = set([x for x in config_values if config_values.count(x) > 1])
    if duplicates:
        raise ValueError(f"Duplicate configurations: {duplicates}")
    
    # Create workflow configuration
    workflow_config = {
        "configuration_to_parameter_file": {v: str(k) for k, v in configurations.items()},
        "configurations": list(configurations.values()),
        "tools": ["fenics", "kratos"],  # Update with your tools
        "benchmark": "your-benchmark-name"
    }
    
    # Save configuration
    with open("workflow_config.json", "w") as f:
        json.dump(workflow_config, f, indent=4)
    
    return workflow_config

if __name__ == "__main__":
    generate_workflow_config()
```

### Step 3: Implement Mesh Generation

Create `create_mesh.py` with standardized interface:

```python
import json
import gmsh
from argparse import ArgumentParser
from pint import UnitRegistry

def create_mesh(parameter_file: str, mesh_file: str):
    ureg = UnitRegistry()
    
    # Load parameters
    with open(parameter_file) as f:
        parameters = json.load(f)
    
    configuration = parameters["configuration"]
    
    # Extract geometry parameters with unit conversion
    length = ureg.Quantity(
        parameters["length"]["value"], 
        parameters["length"]["unit"]
    ).to_base_units().magnitude
    
    radius = ureg.Quantity(
        parameters["radius"]["value"], 
        parameters["radius"]["unit"]
    ).to_base_units().magnitude
    
    element_size = ureg.Quantity(
        parameters["element-size"]["value"], 
        parameters["element-size"]["unit"]
    ).to_base_units().magnitude
    
    # Initialize gmsh and create mesh
    gmsh.initialize()
    gmsh.model.add(configuration)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", element_size)
    
    # Create geometry (implementation specific to your problem)
    # ... geometry creation code ...
    
    # Generate mesh
    gmsh.model.mesh.generate(2)
    gmsh.write(mesh_file)
    gmsh.finalize()

if __name__ == "__main__":
    parser = ArgumentParser(description="Generate mesh for benchmark problem")
    parser.add_argument("--input_parameter_file", required=True)
    parser.add_argument("--output_mesh_file", required=True)
    args = parser.parse_args()
    
    create_mesh(args.input_parameter_file, args.output_mesh_file)
```

### Step 4: Create Snakemake Workflow System

#### Main Snakefile

```snakemake
import json
configfile: "workflow_config.json"

result_dir = "snakemake_results/" + config["benchmark"]
configuration_to_parameter_file = config["configuration_to_parameter_file"]
configurations = config["configurations"]
tools = config["tools"]
benchmark = config["benchmark"]

rule all:
    input:
        expand(f"{result_dir}/{{tool}}/summary.json", tool=tools),

rule create_mesh:
    input:
        script = "create_mesh.py",
        parameters = lambda wildcards: configuration_to_parameter_file[wildcards.configuration],
    output:
        mesh = f"{result_dir}/mesh/mesh_{{configuration}}.msh",
    conda: "environment_mesh.yml"
    shell:
        """
        python3 {input.script} --input_parameter_file {input.parameters} --output_mesh_file {output.mesh}
        """

# Include tool-specific rules
for tool in tools:
    include: f"{tool}/Snakefile"

rule summary:
    input:
        script = "summarise_results.py",
        parameters = expand("{param}", param=[configuration_to_parameter_file[c] for c in configurations]),
        mesh = expand(f"{result_dir}/mesh/mesh_{{configuration}}.msh", configuration=configurations),
        metrics = lambda wildcards: expand(
            f"{result_dir}/{{tool}}/solution_metrics_{{configuration}}.json",
            tool=[wildcards.tool], configuration=configurations
        ),
        solution_field_data = lambda wildcards: expand(
            f"{result_dir}/{{tool}}/solution_field_data_{{configuration}}.zip",
            tool=[wildcards.tool], configuration=configurations
        ),
    output:
        summary_json = f"{result_dir}/{{tool}}/summary.json",
    conda: "environment_postprocessing.yml",
    shell:
        """
        python3 {input.script} \
            --input_configuration {configurations} \
            --input_parameter_file {input.parameters} \
            --input_mesh_file {input.mesh} \
            --input_solution_metrics {input.metrics} \
            --input_solution_field_data {input.solution_field_data} \
            --input_benchmark {benchmark} \
            --output_summary_json {output.summary_json}
        """
```

#### Tool-Specific Snakefile (e.g., tool1/Snakefile)

```snakemake
import json
import os

tool = "tool1"
result_dir = "snakemake_results/" + config["benchmark"]
configuration_to_parameter_file = config["configuration_to_parameter_file"]
configurations = config["configurations"]

rule run_tool1_simulation:
    input:
        script = "{tool}/run_tool1_simulation.py",
        parameters = lambda wildcards: configuration_to_parameter_file[wildcards.configuration],
        mesh = f"{result_dir}/mesh/mesh_{{configuration}}.msh",
    output:
        zip = f"{result_dir}/{{tool}}/solution_field_data_{{configuration}}.zip",
        metrics = f"{result_dir}/{{tool}}/solution_metrics_{{configuration}}.json",
    conda: "environment_simulation.yml",
    shell:
        """
        python3 {input.script} \
            --input_parameter_file {input.parameters} \
            --input_mesh_file {input.mesh} \
            --output_solution_file_zip {output.zip} \
            --output_metrics_file {output.metrics}
        """
```

### Step 5: Create Nextflow Workflow System

#### Main Nextflow Workflow (main.nf)

```nextflow
include { tool1_workflow } from './tool1/tool1.nf'
include { tool2_workflow } from './tool2/tool2.nf'

process create_mesh {
    publishDir "${params.result_dir}/mesh/"
    conda 'environment_mesh.yml'

    input:
    path python_script
    val configuration
    path parameter_file

    output:
    tuple val(configuration), path("mesh_${configuration}.msh")

    script:
    """ 
    python3 $python_script --input_parameter_file $parameter_file --output_mesh_file "mesh_${configuration}.msh"
    """
}

process summary {
    publishDir "${params.result_dir}/${tool}/"
    conda 'environment_postprocessing.yml'

    input:
    path python_script
    val configuration
    val parameter_file
    val mesh_file
    val solution_metrics
    val solution_field_data
    val benchmark
    val tool

    output:
    path("summary.json")
    
    script:
    """
    python3 $python_script \
        --input_configuration ${configuration.join(' ')} \
        --input_parameter_file ${parameter_file.join(' ')} \
        --input_mesh_file ${mesh_file.join(' ')} \
        --input_solution_metrics ${solution_metrics.join(' ')} \
        --input_solution_field_data ${solution_field_data.join(' ')} \
        --input_benchmark ${benchmark} \
        --output_summary_json "summary.json"
    """
}

def prepare_inputs_for_process_summary(input_process, output_process) {
    def matched_channels = input_process.join(output_process) 
    def branched_channels = matched_channels.multiMap{ v, w, x, y, z ->
        configuration : v 
        parameter_file : w 
        mesh : x 
        solution_field : y  
        metrics : z 
    }
    return [
        branched_channels.configuration.collect(),
        branched_channels.parameter_file.collect(),
        branched_channels.mesh.collect(),
        branched_channels.solution_field.collect(),
        branched_channels.metrics.collect()
    ]
}

workflow {
    main:
    // Setup input channels
    def parameter_files_path = []
    params.configurations.each { elem ->
        parameter_files_path.add(file(params.configuration_to_parameter_file[elem]))
    }
    
    def ch_parameter_files = Channel.fromList(parameter_files_path)
    def ch_configurations = Channel.fromList(params.configurations)
    def ch_mesh_python_script = Channel.value(file('create_mesh.py'))
    
    // Create meshes
    output_process_create_mesh = create_mesh(ch_mesh_python_script, ch_configurations, ch_parameter_files)
    input_process_run_simulation = ch_configurations.merge(ch_parameter_files).join(output_process_create_mesh)
    
    // Run simulations for each tool
    ch_tools = Channel.fromList(params.tools)
    input_process_run_simulation_with_tool = ch_tools.combine(input_process_run_simulation)
    
    // Filter inputs for each tool
    input_tool1_workflow = input_process_run_simulation_with_tool.filter{ it[0] == 'tool1' }.map{_w,x,y,z -> tuple(x,y,z)}
    input_tool2_workflow = input_process_run_simulation_with_tool.filter{ it[0] == 'tool2' }.map{_w,x,y,z -> tuple(x,y,z)}
    
    // Execute tool workflows
    tool1_workflow(input_tool1_workflow, params.result_dir)
    output_tool1_workflow = tool1_workflow.out
    def (tool1_configurations, tool1_parameter_files, tool1_meshes, tool1_solution_fields, tool1_summary_metrics) = 
        prepare_inputs_for_process_summary(input_tool1_workflow, output_tool1_workflow)
    
    tool2_workflow(input_tool2_workflow, params.result_dir)
    output_tool2_workflow = tool2_workflow.out
    def (tool2_configurations, tool2_parameter_files, tool2_meshes, tool2_solution_fields, tool2_summary_metrics) = 
        prepare_inputs_for_process_summary(input_tool2_workflow, output_tool2_workflow)
    
    // Combine results for summary
    input_summary_configuration = tool1_configurations.concat(tool2_configurations)
    input_summary_parameter_file = tool1_parameter_files.concat(tool2_parameter_files)
    input_summary_mesh = tool1_meshes.concat(tool2_meshes)
    input_summary_solution_field = tool1_solution_fields.concat(tool2_solution_fields)
    input_summary_metrics = tool1_summary_metrics.concat(tool2_summary_metrics)
    
    // Generate summaries
    def ch_benchmark = Channel.value(params.benchmark)
    def ch_summarise_python_script = Channel.value(file('summarise_results.py'))
    summary(ch_summarise_python_script,
            input_summary_configuration,
            input_summary_parameter_file,
            input_summary_mesh,
            input_summary_metrics,
            input_summary_solution_field,
            ch_benchmark,
            ch_tools)
}
```

#### Nextflow Configuration (nextflow.config)

```nextflow-config
conda {
   enabled = true
}

params.result_dir = "nextflow_results/${params.benchmark}"

prov {
   formats {
      dag {
         file = "${params.result_dir}/nf_prov_dag.html"
         overwrite = true
      }
      legacy {
         file = "${params.result_dir}/nf_prov_legacy.json"
         overwrite = true
      }
      wrroc {
         agent {
            name = 'Your Name'
            orcid = 'https://orcid.org/0000-0000-0000-0000'
         }
         file = "${params.result_dir}/ro-crate-metadata.json"
         license = 'https://spdx.org/licenses/MIT'
         overwrite = true
      }
   }
}
```

#### Tool-Specific Nextflow Workflow (tool1/tool1.nf)

```nextflow
params.tool = "tool1"

process run_simulation {
    publishDir "${params.result_dir}/${params.tool}/"
    conda './tool1/environment_simulation.yml' 

    input:
    path python_script
    tuple val(configuration), path(parameter_file), path(mesh_file)

    output:
    tuple val(configuration), path("solution_field_data_${configuration}.zip"), path("solution_metrics_${configuration}.json")

    script:
    """
    python3 $python_script \
        --input_parameter_file $parameter_file \
        --input_mesh_file $mesh_file \
        --output_solution_file_zip "solution_field_data_${configuration}.zip" \
        --output_metrics_file "solution_metrics_${configuration}.json"
    """
}

workflow tool1_workflow {
    take: 
    mesh_data // tuple(configuration, parameters, mesh) 
    result_dir

    main:
    params.result_dir = result_dir
    run_sim_script = Channel.value(file('tool1/run_tool1_simulation.py'))
    output_process_run_simulation = run_simulation(run_sim_script, mesh_data)

    emit:
    output_process_run_simulation
}
```

### Step 6: Implement Simulation Scripts

Each tool needs a standardized simulation script:

```python
import json
import numpy as np
from argparse import ArgumentParser
from pathlib import Path
from pint import UnitRegistry

def run_simulation(parameter_file: str, mesh_file: str, 
                  solution_file_zip: str, metrics_file: str) -> None:
    ureg = UnitRegistry()
    
    # Load parameters
    with open(parameter_file) as f:
        parameters = json.load(f)
    
    # Extract parameters with unit conversion
    E = ureg.Quantity(parameters["young-modulus"]["value"], 
                     parameters["young-modulus"]["unit"]).to_base_units().magnitude
    nu = ureg.Quantity(parameters["poisson-ratio"]["value"], 
                      parameters["poisson-ratio"]["unit"]).to_base_units().magnitude
    
    # Load mesh and run simulation
    # ... tool-specific simulation code ...
    
    # Calculate metrics
    max_stress = float(np.max(stress_field))
    max_displacement = float(np.max(displacement_field))
    
    # Save metrics
    metrics = {
        "max_von_mises_stress_nodes": max_stress,
        "max_displacement": max_displacement,
        "total_elements": int(num_elements),
        "total_nodes": int(num_nodes),
        "solver_iterations": int(iterations),
        "computation_time": float(computation_time)
    }
    
    with open(metrics_file, "w") as f:
        json.dump(metrics, f, indent=4)
    
    # Save solution field data as ZIP
    import zipfile
    with zipfile.ZipFile(solution_file_zip, 'w') as zf:
        # Add VTK files, displacement fields, stress fields, etc.
        for file_path in solution_files:
            zf.write(file_path, Path(file_path).name)

if __name__ == "__main__":
    parser = ArgumentParser(description="Run simulation with specified tool")
    parser.add_argument("--input_parameter_file", required=True)
    parser.add_argument("--input_mesh_file", required=True)
    parser.add_argument("--output_solution_file_zip", required=True)
    parser.add_argument("--output_metrics_file", required=True)
    args = parser.parse_args()
    
    run_simulation(args.input_parameter_file, args.input_mesh_file,
                   args.output_solution_file_zip, args.output_metrics_file)
```

### Step 7: Implement Results Summarization

Create `summarise_results.py`:

```python
from argparse import ArgumentParser
import json

def create_summary(configurations: list[str],
                   parameter_files: list[str],
                   mesh_files: list[str],
                   solution_metrics: list[str],
                   solution_field_data: list[str],
                   benchmark: str,
                   summary_json: str) -> None:
    
    all_summaries = []
    for idx, config in enumerate(configurations):
        summary = {}
        summary["benchmark"] = benchmark
        summary["configuration"] = config
        
        # Load parameters
        with open(parameter_files[idx], "r") as param_file:
            summary["parameters"] = json.load(param_file)
        
        # Load metrics
        with open(solution_metrics[idx], "r") as metrics_file:
            summary["metrics"] = json.load(metrics_file)
        
        summary["mesh"] = f"{config}/mesh"
        summary["solution_field_data"] = f"solution_field_data_{config}.zip"
        all_summaries.append(summary)
    
    # Save consolidated summary
    with open(summary_json, "w") as f:
        json.dump(all_summaries, f, indent=4)

if __name__ == "__main__":
    parser = ArgumentParser(description="Generate summary statistics")
    parser.add_argument("--input_configuration", nargs="+", type=str, required=True)
    parser.add_argument("--input_parameter_file", nargs="+", type=str, required=True)
    parser.add_argument("--input_mesh_file", nargs="+", type=str, required=True)
    parser.add_argument("--input_solution_metrics", nargs="+", type=str, required=True)
    parser.add_argument("--input_solution_field_data", nargs="+", type=str, required=True)
    parser.add_argument("--input_benchmark", required=True, type=str)
    parser.add_argument("--output_summary_json", required=True, type=str)
    args = parser.parse_args()
    
    create_summary(
        args.input_configuration,
        args.input_parameter_file,
        args.input_mesh_file,
        args.input_solution_metrics,
        args.input_solution_field_data,
        args.input_benchmark,
        args.output_summary_json
    )
```

### Step 8: Create Provenance and Visualization Tools

#### Parameter Extractor for Metadata (parameter_extractor.py)

```python
import json
import os
from snakemake_report_plugin_metadata4ing.interfaces import ParameterExtractorInterface

class ParameterExtractor(ParameterExtractorInterface):
    def extract_params(self, rule_name: str, file_path: str) -> dict:
        results = {}
        file_name = os.path.basename(file_path)
        
        # Extract parameters from parameter files
        if file_name.startswith("parameters_") and file_name.endswith(".json"):
            if rule_name.startswith("postprocess_") or rule_name.startswith("run_"):
                results.setdefault(rule_name, {}).setdefault("has parameter", [])
                with open(file_path) as f:
                    data = json.load(f)
                for key, val in data.items():
                    if isinstance(val, dict) and "value" in val:
                        results[rule_name]["has parameter"].append({key: {
                            "value": val["value"],
                            "unit": val.get("unit", None),
                            "json-path": f"/{key}/value",
                            "data-type": self._get_type(val["value"]),
                        }})
                    else:
                        results[rule_name]["has parameter"].append({key: {
                            "value": val,
                            "unit": None,
                            "json-path": f"/{key}",
                            "data-type": self._get_type(val),
                        }})
        
        # Extract results from solution metrics
        elif file_name.startswith("solution_") and file_name.endswith(".json"):
            if rule_name.startswith("postprocess_") or rule_name.startswith("run_"):
                results.setdefault(rule_name, {}).setdefault("investigates", [])
                with open(file_path) as f:
                    data = json.load(f)
                for key, val in data.items():
                    results[rule_name]["investigates"].append({key: {
                        "value": val,
                        "unit": None,
                        "json-path": f"/{key}",
                        "data-type": "schema:Float",
                    }})
        
        return results

    def _get_type(self, val):
        if isinstance(val, float):
            return "schema:Float"
        elif isinstance(val, int):
            return "schema:Integer"
        elif isinstance(val, str):
            return "schema:Text"
        return None
```

#### Provenance Visualization (plot_provenance.py)

```python
import os
import argparse
from rdflib import Graph
import matplotlib.pyplot as plt
from collections import defaultdict
from generate_config import workflow_config

def load_graphs(base_dir):
    """Load all JSON-LD files into rdflib Graphs."""
    graph_list = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".jsonld"):
                file_path = os.path.join(root, file)
                try:
                    g = Graph()
                    g.parse(file_path, format='json-ld')
                    graph_list.append(g)
                    print(f"✅ Parsed: {file_path}")
                except Exception as e:
                    print(f"❌ Failed to parse {file_path}: {e}")
    return graph_list

def query_and_build_table(graph_list):
    """Run SPARQL queries on graphs and build visualization data."""
    tools = workflow_config["tools"]
    filter_conditions = " || ".join(
        f'CONTAINS(LCASE(?tool_name), "{tool.lower()}")' for tool in tools
    )
    
    query = f"""
    PREFIX schema: <http://schema.org/>
    PREFIX m4i: <http://example.org/m4i/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT DISTINCT ?value_element_size ?value_max_stress ?tool_name
    WHERE {{
      ?processing_step a schema:Action ;
            m4i:hasParameter ?element_size ;
            m4i:investigates ?max_stress ;
            schema:instrument ?tool .
    
      ?max_stress a schema:PropertyValue ;
            rdfs:label "max_von_mises_stress_nodes" ;
            schema:value ?value_max_stress .

      ?element_size a schema:PropertyValue ;
            rdfs:label "element_size" ;
            schema:value ?value_element_size .

      ?tool a schema:SoftwareApplication ;
            rdfs:label ?tool_name .
            
      FILTER ({filter_conditions})
    }}
    """

    table_data = []
    for g in graph_list:
        results = g.query(query)
        for row in results:
            table_data.append([
                float(row.value_element_size),
                float(row.value_max_stress),
                str(row.tool_name)
            ])

    return table_data

def plot_convergence_study(table_data, output_file="convergence_study.pdf"):
    """Plot element size vs stress convergence by tool."""
    grouped_data = defaultdict(list)
    
    for row in table_data:
        element_size, max_stress, tool = row
        grouped_data[tool].append((element_size, max_stress))
    
    plt.figure(figsize=(12, 8))
    for tool, values in grouped_data.items():
        values.sort()
        x_vals, y_vals = zip(*values)
        plt.plot(x_vals, y_vals, marker='o', linestyle='-', linewidth=2, label=tool)

    plt.xlabel("Element Size")
    plt.ylabel("Maximum von Mises Stress")
    plt.title("Mesh Convergence Study: Element Size vs Maximum Stress")
    plt.legend(title="Simulation Tool")
    plt.grid(True, alpha=0.3)
    plt.xscale('log')
    plt.tight_layout()
    plt.savefig(output_file)
    print(f"Convergence plot saved as {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize provenance data")
    parser.add_argument("artifact_folder", type=str, help="Path to artifacts folder")
    args = parser.parse_args()

    graphs = load_graphs(args.artifact_folder)
    table_data = query_and_build_table(graphs)
    plot_convergence_study(table_data)
```

### Step 9: Create Environment Files

#### Mesh Generation Environment (environment_mesh.yml)

```yaml
name: mesh-generation
channels:
  - conda-forge
channel_priority: strict
dependencies:
  - python=3.12
  - pint
  - python-gmsh
```

#### Tool-Specific Simulation Environment (tool1/environment_simulation.yml)

```yaml
name: tool1_simulation
channels:
  - conda-forge
channel_priority: strict
dependencies:
  - python=3.12
  - tool1-specific-packages  # e.g., fenics-dolfinx, kratos, etc.
  - libadios2=2.10.1
  - petsc4py
  - pint
  - python-gmsh
  - sympy
  - numpy
  - scipy
```

#### Post-processing Environment (environment_postprocessing.yml)

```yaml
name: postprocessing
channels:
  - conda-forge
channel_priority: strict
dependencies:
  - python=3.12
  - matplotlib
  - pandas
  - pint
  - rdflib
  - numpy
```

### Step 10: Create Documentation

Create a comprehensive `README.md`:

```markdown
# Your Benchmark Name

## Problem Definition

[Describe the mathematical formulation, boundary conditions, and expected results]

## Dual Workflow System

This benchmark supports both Snakemake and Nextflow workflow systems:

### Snakemake Execution

1. Generate configuration:
   ```bash
   python generate_config.py
   ```

2. Run benchmark:
   ```bash
   snakemake --use-conda --cores all
   ```

3. Generate provenance report:
   ```bash
   snakemake --use-conda --cores all --reporter metadata4ing
   ```

### Nextflow Execution

1. Generate configuration:
   ```bash
   python generate_config.py
   ```

2. Run benchmark:
   ```bash
   nextflow run main.nf -c workflow_config.json
   ```

3. View provenance data in generated HTML and JSON files

## Output Structure

- **Snakemake**: Results in `snakemake_results/`
- **Nextflow**: Results in `nextflow_results/`

Both generate:
- Mesh files
- Solution field data (ZIP archives with VTK files)
- Metrics (JSON files with numerical results)
- Summary files (aggregated results)
- Provenance data (metadata and lineage)

## Adding New Simulation Tools

1. Create `new_tool/` directory
2. Implement `new_tool/Snakefile` and `new_tool/new_tool.nf`
3. Create `new_tool/environment_simulation.yml`
4. Implement simulation scripts with standardized interfaces
5. Update `generate_config.py` to include the new tool
6. Test with both workflow systems
```

## Workflow Execution Comparison

| Feature | Snakemake | Nextflow |
|---------|-----------|----------|
| **Configuration** | `workflow_config.json` | `workflow_config.json` + `nextflow.config` |
| **Execution** | `snakemake --use-conda --cores all` | `nextflow run main.nf -c workflow_config.json` |
| **Provenance** | metadata4ing plugin | Built-in WRROC format |
| **Results Location** | `snakemake_results/` | `nextflow_results/` |
| **Parallelization** | Rule-based DAG | Process-based dataflow |
| **Environment Management** | Conda integration | Conda + container support |

## Standardized Interfaces Summary

### Command-Line Arguments
- **Mesh generation**: `--input_parameter_file`, `--output_mesh_file`
- **Simulation**: `--input_parameter_file`, `--input_mesh_file`, `--output_solution_file_zip`, `--output_metrics_file`
- **Summarization**: Multiple inputs for aggregating all configurations

### File Formats
- **Parameters**: JSON with explicit units
- **Metrics**: JSON with numerical results
- **Solution data**: ZIP archives with visualization files
- **Summary**: JSON aggregating all configurations

### Output Requirements
Both workflow systems produce identical output formats, ensuring results can be compared directly regardless of the execution engine used.

## Best Practices for Dual-System Workflows

1. **Maintain Interface Consistency**: Both systems use identical Python scripts with standardized command-line interfaces
2. **Synchronize Tool Lists**: Keep tool lists consistent between `generate_config.py` and both workflow definitions
3. **Test Both Systems**: Validate that both Snakemake and Nextflow produce identical results
4. **Document Differences**: Clearly document any system-specific features or limitations
5. **Provenance Compatibility**: Ensure provenance data from both systems can be analyzed together
6. **Environment Consistency**: Use identical conda environments for both systems

This dual-system approach maximizes user choice while maintaining result reproducibility and comparability across different workflow management preferences.