
include { run_simulation } from './fenics/fenics.nf'


process create_mesh {
    //publishDir "$result_dir/mesh/"
    publishDir "results/mesh/"
    conda 'environment_mesh.yml'

    input:
    path python_script
    val configuration
    path parameter_file

    output:
    // val(configuration) works as matching key with the input channel in the workflow
    tuple val(configuration), path("mesh_${configuration}.msh")

    script:
    """ 
    python3 $python_script --input_parameter_file $parameter_file --output_mesh_file "mesh_${configuration}.msh"
    """
}

process summary{
    publishDir "results/"
    conda 'environment_postprocessing.yml'

    input:
    val configuration
    val parameter_file
    val mesh_file
    val solution_metrics
    val solution_field_data
    val benchmark

    output:
    path("summary.json")

    script:
    """
    #!/usr/bin/env python
    import json
    from pathlib import Path
    
    configurations = "${configuration.join(' ')}".split(' ')
    parameter_files = "${parameter_file.join(' ')}".split(' ')
    mesh_files = "${mesh_file.join(' ')}".split(' ')
    solution_field_data = "${solution_field_data.join(' ')}".split(' ')
    solution_metrics = "${solution_metrics.join(' ')}".split(' ')
    benchmark = "${benchmark}"
    all_summaries = []
    for idx, config in enumerate(configurations):
        print(idx, config)
        summary = {}
        summary["benchmark"] = benchmark
        print(solution_metrics[idx])
        with open(parameter_files[idx], "r") as param_file:
            summary["parameters"] = json.load(param_file)
        summary["mesh"] = f"{config}/mesh"
        with open(solution_metrics[idx], "r") as metrics_file:
            summary["metrics"] = json.load(metrics_file)
        summary["configuration"] = config
        all_summaries.append(summary)
    with open("summary.json", "w") as f:
        json.dump(all_summaries, f, indent=4)

    """
}

workflow {
    main:
    // Load JSON file into a map
    def jsonFile = file("workflow_config.json")
    def workflow_config_file = new groovy.json.JsonSlurper().parseText(jsonFile.text)
    def configurations = workflow_config_file.configurations
    def configurations_to_parameter_file = workflow_config_file.configuration_to_parameter_file
    //def result_dir = workflow_config_file.result_dir

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

    //Creating Mesh
    output_process_create_mesh = create_mesh(ch_mesh_python_script, ch_configurations, ch_parameter_files)

    input_process_run_simulation = ch_configurations.merge(ch_parameter_files).join(output_process_create_mesh)
    
    def ch_sim_python_script = Channel.value(file('./fenics/run_fenics_simulation.py'))

    //Running Simulation
    output_process_run_simulation = run_simulation(ch_sim_python_script, input_process_run_simulation)

    //Each entry in the channel defined below is a tuple: (configuration, parameter_file, mesh_file, solution_field_data, solution_metrics)
    matched_channels = input_process_run_simulation.join(output_process_run_simulation)

    input_summary_configuration = matched_channels.map{a,b,c,d,e -> a}
    input_summary_parameter_file = matched_channels.map{a,b,c,d,e -> b }
    input_summary_mesh = matched_channels.map{a,b,c,d,e -> c }
    input_summary_solution_field = matched_channels.map{a,b,c,d,e -> d }
    input_summary_metrics = matched_channels.map{a,b,c,d,e -> e }

    def benchmark = workflow_config_file.benchmark
    def ch_benchmark = Channel.value(benchmark)

    //Summarizing results
    summary(input_summary_configuration.collect(), input_summary_parameter_file.collect(), input_summary_mesh.collect(), input_summary_metrics.collect(),input_summary_solution_field.collect(), ch_benchmark)


    ////mesh_file.collect().view()
    //
    //summary(config.collect(), param_file.collect(), mesh_file.collect(), solution_field_data.collect(), solution_metrics.collect(), ch_benchmark)
    ////ch_configurations.view()
    ////ch_parameter_files.view()
    ////ch_mesh_files.view()


}