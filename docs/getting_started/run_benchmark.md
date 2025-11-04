# Running a Benchmark

This guide provides step-by-step instructions for running a benchmark workflow, using both Snakemake and Nextflow. The benchmark `linear-elastic-plate-with-hole` is used to demonstrate the steps.

## Initial Steps

- **Create the benchmark environment**

   ```bash
   # From repository root
   mamba env create -n model-validation -f environment_benchmarks.yml
   conda activate model-validation
   ```

- **Configuration Generation**

    Before running either workflow systems, generate the configuration files:

    ```bash
    # Navigate to benchmark directory
    cd benchmarks/linear-elastic-plate-with-hole/

    # Generate workflow configuration
    python generate_config.py
    ```

    This script creates a `workflow_config.json` that defines what configurations are computed (in the standard case one for each parameter_*.json) and what tools are used.

## Snakemake workflow

1. **Running Snakemake Workflow**

    You can run all tools and configurations via the command line:

    ```bash
    snakemake --use-conda --cores all
    ```

    To run only a specific tool or specific configuration (e.g. for testing), edit `generate_config.py` or use:

    ```bash
    snakemake --use-conda --cores all --config tools=fenics
    ```

    After running the workflow, the results are stored in the `linear-elastic-plate-with-hole/snakemake_results/`.

2. **Collect Provenance**

    Use the reporter plugin ([metadata4ing](https://github.com/izus-fokus/snakemake-report-plugin-metadata4ing)) to generate a RO-Crate file which stores the provenance report. Call snakemake again (make sure the plugin is added to the environment):

    ```bash
    snakemake --use-conda --force --cores all \
      --reporter metadata4ing \
      --report-metadata4ing-paramscript ./common/parameter_extractor.py \
      --report-metadata4ing-filename snakemake_provenance
    ```

    The provenance data from the reporter is stored as a .zip file in the benchmark directory. The `filename` is user-defined (in this case `snakemake_provenance`) and the `paramscript` is a custom script that helps supports the reporter to extract information from the provenance data.

3. **Post-Processing the provenance data**

    - **Unzip the reporter output**

        Unzip the provenance data from the reporter for post-processing.

        ```bash
        unzip snakemake_provenance -d snakemake_provenance
        ```

    - **Setup Post-Processing Environment**

        Set up the environment for post-processing the results.

        ```bash
        mamba env create -n postprocessing -f environment_postprocessing.yml
        conda activate postprocessing
        ```

    - **Generate Analysis Plots**

        To generate a plot, run:

        ```bash
        python plot_metrics.py --artifact_folder ./snakemake_provenance
        ```

        The command generates `element_size_vs_stress.pdf` file, that plots the maximum Von-Mises stress as reported by simulation tool(s) over the changing mesh element size.

## Nextflow workflow

1. **Running Nextflow Workflow & Provenance**

    You can run all tools and configurations via the command line:

    ```bash
    nextflow run main.nf -params-file workflow_config.json -c ../common/nextflow.config -plugins nf-prov@1.4.0
    ```

    The command runs the provenance reporter simultaneously with the workflow. All the output files including provenance report (RO-Crate) from the workflow are stored in `linear-elastic-plate-with-hole/nextflow_results/`.
