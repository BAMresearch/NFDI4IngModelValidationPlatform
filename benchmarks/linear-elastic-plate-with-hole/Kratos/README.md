# Infinite plate with hole benchmark in Kratos

This directory contains:

* `Snakefile`: A snakefile to run the benchmark.
* `MainKratos.py`: The main script to run the benchmark.
* `create_input_files.py`: A script to create the input files for the benchmark.
* `input_template.json`: A template for the Kratos input file. It contains placeholder values that will be replaced by the `create_input_files.py` script.
* `StructuralMaterials_template.json`: A template for the structural materials file. It contains placeholder values that will be replaced by the `create_input_files.py` script.
* `environment.yml`: A conda environment file to create the environment needed to run the benchmark.
* `parameters_*.json`: A set of parameters files for the benchmark. Each file will create a new instance of the benchmark with different parameters.