import json
import os

kratos_input_template = "input_template.json"
kratos_material_template = "StructuralMaterials_template.json"

rule all:
    input:
        "solution_metrics.json",
        "solution_field_data.zip"

rule mesh_to_mdpa:
    input:
        parameters = "parameters.json",
        mesh = "mesh.msh",
        script = "msh_to_mdpa.py",
    output:
        mdpa = "mesh.mdpa",
    conda:
        "environment_simulation.yml",
    shell:
        """
        python3 {input.script} \
            --input_parameter_file {input.parameters} \
            --input_mesh_file {input.mesh} \
            --output_mdpa_file {output.mdpa}
        """

rule create_kratos_input_and_run_simulation:
    input:
        parameters = "parameters.json",
        mdpa = "mesh.mdpa",
        kratos_input_template = kratos_input_template,
        kratos_material_template = kratos_material_template,
        script_create_kratos_input = "create_kratos_input.py",
        script_run_kratos_simulation = "run_simulation.py",
    output:
        kratos_inputfile = "ProjectParameters.json",
        kratos_materialfile = "MaterialParameters.json",
        result_vtk = "vtk/Structure_0_1.vtk",
    conda:
        "environment_simulation.yml",
    shell:
        """
        python3 {input.script_create_kratos_input} \
            --input_parameter_file {input.parameters} \
            --input_mdpa_file {input.mdpa} \
            --input_kratos_input_template {input.kratos_input_template} \
            --input_material_template {input.kratos_material_template} \
            --output_kratos_inputfile {output.kratos_inputfile} \
            --output_kratos_materialfile {output.kratos_materialfile}

        python3 {input.script_run_kratos_simulation} \
            --input_parameter_file {input.parameters} \
            --input_kratos_inputfile {output.kratos_inputfile} \
            --input_kratos_materialfile {output.kratos_materialfile} \
        """

rule postprocess_kratos_results:
    input:
        parameters = "parameters.json",
        result_vtk = "vtk/Structure_0_1.vtk",
        script = "postprocess_results.py",
    output:
        zip = "solution_field_data.zip",
        metrics = "solution_metrics.json",
    conda:
        "environment_simulation.yml",
    shell:
        """
        python3 {input.script} \
            --input_parameter_file {input.parameters} \
            --input_result_vtk {input.result_vtk} \
            --output_solution_file_zip {output.zip} \
            --output_metrics_file {output.metrics}
        """

