# A Guide to add a Benchmark Problem

The steps are as follows:

1. **Create a folder for the problem**

    Inside the `benchmarks` directory, create a folder for the problem e.g. `benchmarks/problem_name`.

2. **Add the simulation tool**

    - For each simulation tool used to solve the problem, create a corresponding subfolder inside the problem directory, e.g.

        ```
        benchmarks/problem_name/
        ├── tool_A
        ├── tool_B
        ```

    -   Inside each tool’s folder (e.g. tool_A/):
        - Write a script for running the simulation.
        - Write the I/O interface scripts needed to ensure a common I/O interface across the tools.
        - Create an environment.yml file listing out all the tool-specific software dependencies.
        - Develop a workflow script (Snakemake/Nextflow) connecting the I/O scripts, simulation code and environment.yml files.

3. **Define parameter configurations**

    For each parameter configuration run using simulation tools, create a JSON file in `benchmarks/problem/` specifying parameters related to the domain geometry, mesh information, and constitutive model parameters, cf. [parameter_1.json](https://github.com/BAMresearch/NFDI4IngModelValidationPlatform/blob/main/benchmarks/linear-elastic-plate-with-hole/parameters_1.json).

4. **Create a script for discovering the configurations**

    - Create the script `generate_config.py` in `benchmarks/problem/`.
    - The script should:
        - Discover all the configuration JSON files.
        - Extract configurations.
        - List the simulation tools for each configuration, cf. [generate_config.py](https://github.com/BAMresearch/NFDI4IngModelValidationPlatform/blob/main/benchmarks/linear-elastic-plate-with-hole/generate_config.py).

        **Note:** The simulation-tool-specific keywords are used by the main workflow to call the corresponding sub-workflows.

5. **Create the mesh generation script**

    **With mesh generation**

    - Create `create_mesh.py` inside `benchmarks/problem_name/` to define the domain geometry.
    - In the file, provide the interface for the user-adjustable inputs related to geometry, mesh and numerical solver. These inputs are passed to the script via `parameter_*.json`.
    - If required, include an environment file for the mesh generation script in the same directory.

    **Pre-existing meshes**

    - Ensure that the parameter JSON files and mesh files are named according to their configurations correctly.
    - Modify generate_config.py to include the key "configuration_to_mesh_file" listing all the meshes for different configurations.
    - In the main & sub-workflows:
        - For Snakemake:
            - Comment out the create_mesh rule in the main workflow.
            - Change in summary rule's input:

                ```
                mesh = expand("{mesh}", param=[configuration_to_mesh_file[c] for c in configurations])
                ```

            - Change in tool's sub-workflow input:

                ```
                mesh = lambda wildcards: configuration_to_mesh_file[wildcards.configuration]
                ```

        - For Nextflow:
            - Comment out the create_mesh process in the main workflow.
            - Create an input channel for the mesh files.

                ```
                def mesh_files_path = []
                params.configurations.each { elem -> mesh_files_path.add(file(params.configuration_to_mesh_file[elem])) }

                def ch_mesh_files = Channel.fromList(mesh_files_path)
                ```

            - Merge the configurations, parameters and mesh channels before running simulation.

                ```
                input_process_run_simulation = ch_configurations.merge(ch_parameter_files, ch_mesh_files)
                ```

6. **Develop the main workflow**

    - Place the main workflow in `benchmarks/problem/`.
    - Include rules for:
        - Running `create_mesh.py`.
        - Calling the simulation-tool-specific sub-workflows.
    - Additional rules can be added depending on the requirements, cf. [main.nf](https://github.com/BAMresearch/NFDI4IngModelValidationPlatform/blob/main/benchmarks/linear-elastic-plate-with-hole/main.nf).
