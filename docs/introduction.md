The platform uses a hierarchical workflow system that incorporates:

- Multiple simulation tools (e.g., FEniCS, Kratos) for solving a problem.
- Standardized I/O streams to the simulation tools.
- Multiple parameter configurations per benchmark.
- Automated mesh generation.

# Workflow

The workflow has a hierarchical structure. The common tasks like mesh generation and results' summary creation are done by the top-level workflow. The top-level workflow interacts with the sub-workflows which are tool-specific. The sub-workflows are responsible for running the scripts containing simulation code and pre/post-processing scripts necessary for processing the mesh files or the simulation output. 

The benchmark `linear-elastic-plate-with-hole` is implemented with nextflow and snakemake packages. For this benchmark, the structure of the snakemake workflow is exemplified below:

```
linear-elastic-plate-with-hole/Snakefile 
│
├── calls ──> fenics/Snakefile 
│   └── executes ──> run_fenics_simulation.py
│
└── calls ──> kratos/Snakefile 
    ├── executes ──> msh_to_mdpa.py
    ├── executes ──> create_kratos_input.py
    ├── executes ──> run_kratos_simulation.py
    └── executes ──> postprocess_results.py
```

# Terminologies

### Parameter JSON File

A `parameter_*.json` file defines all the user-adjustable parameters for mesh generation, material properties, boundary conditions, and solver settings for finite element simulations. Each parameter file represents a unique configuration of these parameters that will be processed by the workflow system.

Cf. `benchmarks/linear-elastic-plate-with-hole/parameters_1.json`

```json
{   
    "configuration": "1",    
}
```

The keyword `"configuration"` is a unique identifier for the provided parameter set. It is used in output file naming and workflow tracking and must be unique across all parameter files.

### Configuration Generator

`generate_config.py` file writes a configuration file for the workflow managers (snakemake or nextflow) extracting the configuration information from `parameter_*.json` files. The keywords for simulation tools to run the configurations on are also specified by the user in this file.

Cf. `benchmarks/linear-elastic-plate-with-hole/generate_config.py`


### Mesh Generation 
<!--[create_mesh.py](https://github.com/BAMresearch/NFDI4IngModelValidationPlatform/blob/main/benchmarks/linear-elastic-plate-with-hole/create_mesh.py) -->

The `create_mesh.py` file contains the code for mesh generation. In case the mesh(es) are already available, the file is not needed. In the `linear-elastic-plate-with-hole` example the file: 

1. receives inputs from `\parameter_*.json` and output `.msh` files.
2. Uses `pint` library for unit conversion.
3. Uses `gmsh` library for mesh generation.

Cf. `benchmarks/linear-elastic-plate-with-hole/create_mesh.py`

### Summarize File
`summarize_results.py` creates a JSON file containing the solution metrics and their corresponding parameter configurations after simulation runs of a benchmark.
 
Cf. `benchmarks/linear-elastic-plate-with-hole/summarize_results.py`


### Environment Files
The environment files are YML files which configures the environment for running a script. They contain a list of software libraries that build up an environment.
















