
include { run_simulation } from './fenics/fenics.nf'


process create_mesh {
    //publishDir "$result_dir/mesh/"
    publishDir "results/mesh/"
    conda 'environment_mesh.yml'

    input:
    path python_script
    val configuration
    path parameter_file
    //path result_dir
    

    output:
    // val(configuration) works as matching key with the input channel in the workflow
    tuple val(configuration), path("mesh_${configuration}.msh")

    script:
    """ 
    python3 $python_script --input_parameter_file $parameter_file --output_mesh_file "mesh_${configuration}.msh"
    """
}

//process summary{
//    publishDir "results/"
//    conda 'environment_postprocessing.yml'
//
//    input:
//    tuple val configuration
//    path parameter_file
//    path mesh_file
//    path solution_field_data
//    path solution_metrics
//    val benchmark
//
//    output:
//    path("summary.json")
//
//    script:
//    """
//    #!/usr/bin/env python
//    import json
//    from pathlib import Path
//
//    parameter_files = [str(i) for i in "$configuration"]
//
//    """
//}

workflow {
    main:
    // Load JSON file into a map
    def jsonFile = file("workflow_config.json")
    def workflow_config_file = new groovy.json.JsonSlurper().parseText(jsonFile.text)
    def configurations = workflow_config_file.configurations
    def configurations_to_parameter_file = workflow_config_file.configuration_to_parameter_file
    def result_dir = workflow_config_file.result_dir

    //println configurations
    //println configurations_to_parameter_file

    def parameter_files_path = []
    configurations.each { elem ->
        parameter_files_path.add(file(configurations_to_parameter_file[elem]))
    }
    //println parameter_files

    //def ch_mesh_files = Channel.fromList(mesh_files)
    def ch_parameter_files = Channel.fromList(parameter_files_path)
    def ch_configurations = Channel.fromList(configurations)
    def ch_mesh_python_script = Channel.value(file('create_mesh.py'))
    def ch_result_dir = Channel.value(file(result_dir))

    //Creating Mesh
    output_process_create_mesh = create_mesh(ch_mesh_python_script, ch_configurations, ch_parameter_files)//, ch_result_dir)

    
    input_process_run_simulation = ch_configurations.merge(ch_parameter_files).join(output_process_create_mesh)
    
    def ch_sim_python_script = Channel.value(file('./fenics/run_fenics_simulation.py'))

    //Running Simulation
    output_process_run_simulation = run_simulation(ch_sim_python_script, input_process_run_simulation)


    input_summary_mesh = output_process_create_mesh.map{a,b -> b }.view()
    input_summary_soultion_field = output_process_run_simulation.map{a,b,c -> b }
    input_summary_metrics = output_process_run_simulation.map{a,b,c -> c } 



    ////mesh_file.collect().view()
    //
    //def benchmark = workflow_config_file.benchmark
    //def ch_benchmark = Channel.value(benchmark)
    //summary(config.collect(), param_file.collect(), mesh_file.collect(), solution_field_data.collect(), solution_metrics.collect(), ch_benchmark)
    ////ch_configurations.view()
    ////ch_parameter_files.view()
    ////ch_mesh_files.view()


}