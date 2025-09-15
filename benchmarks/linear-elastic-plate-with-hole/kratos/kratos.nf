params.tool = "kratos"

process mesh_to_mdpa {
    publishDir "${params.result_dir}/${params.tool}/"
    conda './kratos/environment_simulation.yml'
    
    input:
    path python_script
    tuple val(configuration), path(parameter_file), path(mesh_file) 
    
    output:
    tuple val(configuration), path("mesh_${configuration}.mdpa")
    
    script:
    """
    python3 ${python_script} \
        --input_parameter_file ${parameter_file} \
        --input_mesh_file ${mesh_file} \
        --output_mdpa_file mesh_${configuration}.mdpa
    """
}

process create_kratos_input_and_run_simulation {

    // The process combines the creation of the Kratos input file (json) and the execution of the simulation. Initially, these were two separate processes. 
    // The combination was necessary because the create_kratos_input.py specifies the location of the mesh file and the output location of the simulation results in 
    // the json file. In the case of Nextflow, these locations are related to the process's sub-directory (inside the work directory). Executing the simulation as a 
    // separate process results in a failure to find the mesh file and write the output files unless the paths (in the json file) are explicitly provided as an input 
    // to the process. 
    // This is not an issue in the case of Snakemake, as the working directory doesn't automatically change between different rules.

    publishDir "${params.result_dir}/${params.tool}/"
    conda './kratos/environment_simulation.yml'
    
    input:
    path script_create_kratos_input
    path script_run_kratos
    tuple val(configuration), path(parameters), path(mdpa)
    path kratos_input_template
    path kratos_material_template
    
    output:
    tuple val(configuration), path("ProjectParameters_${configuration}.json"), path("MaterialParameters_${configuration}.json"), path("${configuration}/Structure_0_1.vtk")
    
    script:
    """
    python3 ${script_create_kratos_input} \
        --input_parameter_file ${parameters} \
        --input_mdpa_file ${mdpa} \
        --input_kratos_input_template ${kratos_input_template} \
        --input_material_template ${kratos_material_template} \
        --output_kratos_inputfile ProjectParameters_${configuration}.json \
        --output_kratos_materialfile MaterialParameters_${configuration}.json

    python3 ${script_run_kratos} \
        --input_parameter_file ${parameters} \
        --input_kratos_inputfile "ProjectParameters_${configuration}.json" \
        --input_kratos_materialfile "MaterialParameters_${configuration}.json"
    """
}

process postprocess_kratos_results {
    publishDir "${params.result_dir}/${params.tool}/"
    conda './kratos/environment_simulation.yml'
    
    input:
    path python_script
    tuple val(configuration), path(parameter_file), path(result_vtk)
    
    output:
    tuple val(configuration), path("solution_field_data_${configuration}.zip"), path("solution_metrics_${configuration}.json")
    
    script:
    """
    python3 ${python_script} \
        --input_parameter_file ${parameter_file} \
        --input_result_vtk ${result_vtk} \
        --output_solution_file_zip solution_field_data_${configuration}.zip \
        --output_metrics_file solution_metrics_${configuration}.json
    """
}

workflow kratos_workflow {
    take:
    mesh_data // tuple(configuration, parameters, mesh)  //change the name
    result_dir
    
    main:
    params.result_dir = result_dir

    // Define script paths
    msh_to_mdpa_script = Channel.value(file('kratos/msh_to_mdpa.py'))
    create_input_script = Channel.value(file('kratos/create_kratos_input.py'))
    run_sim_script = Channel.value(file('kratos/run_kratos_simulation.py'))
    postprocess_script = Channel.value(file('kratos/postprocess_results.py'))
    
    // Template files
    kratos_input_template = Channel.value(file('kratos/input_template.json'))
    kratos_material_template = Channel.value(file('kratos/StructuralMaterials_template.json'))
    
    // Process pipeline
    output_process_mesh_to_mdpa = mesh_to_mdpa(msh_to_mdpa_script, mesh_data)
    
    input_process_create_kratos_input = mesh_data.join(output_process_mesh_to_mdpa).map { tuple(it[0], it[1], it[3]) }

    //input_process_create_kratos_input.view()
    output_create_kratos_input_and_run_simulation = create_kratos_input_and_run_simulation(
        create_input_script,
        run_sim_script,
        input_process_create_kratos_input,
        kratos_input_template,
        kratos_material_template
    )
  
    input_process_postprocess_kratos_results = mesh_data.join(output_create_kratos_input_and_run_simulation).map { tuple(it[0], it[1], it[5]) }


    output_process_postprocess_kratos_results = postprocess_kratos_results(postprocess_script,input_process_postprocess_kratos_results)
    
    emit:
    output_process_postprocess_kratos_results
}

