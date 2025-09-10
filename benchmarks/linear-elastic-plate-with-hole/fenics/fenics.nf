params.tool = "fenics"

process run_simulation {
    publishDir "${params.result_dir}/${params.tool}/"
    conda './fenics/environment_simulation.yml' 

    input:
    path python_script
    tuple val(configuration), path(parameter_file), path(mesh_file)


    output:
    tuple val(configuration), path("solution_field_data_${configuration}.zip"), path("solution_metrics_${configuration}.json")

    script:
    """
    python3 $python_script --input_parameter_file $parameter_file --input_mesh_file $mesh_file --output_solution_file_zip "solution_field_data_${configuration}.zip" --output_metrics_file "solution_metrics_${configuration}.json"
    """
}

workflow fenics_workflow {
    
    take: 
    mesh_data // tuple(configuration, parameters, mesh) 
    result_dir

    main:
    params.result_dir = result_dir
    run_sim_script = Channel.value(file('fenics/run_fenics_simulation.py'))
    output_process_run_simulation = run_simulation( run_sim_script, mesh_data )

    emit:
    output_process_run_simulation

}