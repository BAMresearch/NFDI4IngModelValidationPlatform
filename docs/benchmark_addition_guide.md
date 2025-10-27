# A Guide to add a Benchmark Problem

The platform uses a hierarchical workflow system that incorporates:

- Multiple simulation tools (e.g., FEniCS, Kratos) for solving a problem.
- Standardized I/O streams to the simulation tools.
- Multiple parameter configurations per benchmark.
- Automated mesh generation.
<!-- Provenance tracking and metadata collection -->

This guide outlines the algorithm needed to add a benchmark problem.

1. **Create a folder for the problem** 
    
    Inside the `benchmarks` directory, create a folder for the problem e.g. `benchmarks/problem_name`.

2. **Add the simulation tool**
    -   For each simulation tool used to solve the problem, create a corresponding subfolder inside the problem directory, e.g.

        ```
        benchmarks/problem_name/
        ├── tool_A
        ├── tool_B
        ```

    -   Inside each tool’s folder (e.g. tool_A/):
        - Write a script for running the simulation.
        - Write the I/O interface scripts needed to ensure a common I/O interface across the tools.
        - Create an environment.yml file listing out all the tool-specific software dependencies.
        - Develop a workflow script connecting the I/O scripts, simulation code and environment.yml files.

3. **Create the mesh generation script**
    - Write `create_mesh.py` inside `benchmarks/problem_name/` to define the domain geometry.
    - Provide user-modifiable inputs via a JSON input interface, cf. `benchmarks/linear-elastic-plate-with-hole/create_mesh.py`.
    - If required, include an environment file for the mesh generation script in the same directory.

4. **Define parameter configurations**
    
    For each parameter configuration run using simulation tools, create a JSON file in `benchmarks/problem/` specifying parameters related to the domain geometry, mesh information, and constitutive model parameters, cf. `benchmarks/linear-elastic-plate-with-hole/parameters_*.json`.

5. **Create a script for discovering the configurations**
    - Create the script `generate_config.py` in `benchmarks/problem/`.
    - The script should:
        - Discover all the configuration JSON files.
        - Extract configurations.
        - List the simulation tools for each configuration, cf. `benchmarks/linear-elastic-plate-with-hole/generate_config.py`.
        
        **Note:** The simulation-tool-specific keywords are used by the main workflow to call the corresponding sub-workflows.

6. **Develop the main workflow**
    - Place the main workflow in `benchmarks/problem/`.
    - Include rules for:
        - Running `create_mesh.py`.
        - Calling the simulation-tool-specific sub-workflows.
    - Additional rules can be added depending on the requirements, cf. `benchmarks/linear-elastic-plate-with-hole/Snakefile`.
