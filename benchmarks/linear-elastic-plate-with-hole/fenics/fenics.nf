process run_simulation {
    publishDir "results/fenics/simulation/"
    conda './fenics/environment_simulation.yml' 

    input:
    path python_script
    tuple val(configuration), path(parameter_file), path(mesh_file)
    //path ch_mesh_files

    output:
    tuple val(configuration), path("solution_field_data_${configuration}.zip"), path("solution_metrics_${configuration}.json")

    script:
    """
    python3 $python_script --input_parameter_file $parameter_file --input_mesh_file $mesh_file --output_solution_file_zip "solution_field_data_${configuration}.zip" --output_metrics_file "solution_metrics_${configuration}.json"
    """
}