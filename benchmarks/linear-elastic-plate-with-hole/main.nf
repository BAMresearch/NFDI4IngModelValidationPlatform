
include { fenics_workflow } from './fenics/fenics.nf'
include { kratos_workflow } from './kratos/kratos.nf'

// params._ can be passed through the CLI.
params.jsonFile = file("workflow_config_nextflow.json")
params.workflow_config_file = new groovy.json.JsonSlurper().parseText(params.jsonFile.text)
params.result_dir = params.workflow_config_file.result_dir
params.configuration_to_parameter_file = params.workflow_config_file.configuration_to_parameter_file
params.configurations = params.workflow_config_file.configurations
params.tools = params.workflow_config_file.tools
params.benchmark = params.workflow_config_file.benchmark


process create_mesh {
    //publishDir "$result_dir/mesh/"
    publishDir "${params.result_dir}/mesh/"
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
    publishDir "${params.result_dir}/${tool}/"
    conda 'environment_postprocessing.yml'

    input:
    val configuration
    val parameter_file
    val mesh_file
    val solution_metrics
    val solution_field_data
    val benchmark
    val tool

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


def prepare_inputs_for_process_summary(input_process_run_simulation, output_process_run_simulation) {

    // A function to prepare inputs for the summary process from the outputs of a simulation process.
    
    //Each entry in the matched_channel defined below is a tuple: (configuration, parameter_file, mesh_file, solution_field_data, solution_metrics)
    def matched_channels = input_process_run_simulation.join(output_process_run_simulation)
    def input_summary_configuration = matched_channels.map{a,_b,_c,_d,_e -> a}.collect()
    def input_summary_parameter_file = matched_channels.map{_a,b,_c,_d,_e -> b }.collect()
    def input_summary_mesh = matched_channels.map{_a,_b,c,_d,_e -> c }.collect()
    def input_summary_solution_field = matched_channels.map{_a,_b,_c,d,_e -> d }.collect()
    def input_summary_metrics = matched_channels.map{_a,_b,_c,_d,e -> e }.collect()
    return [
        input_summary_configuration,
        input_summary_parameter_file,
        input_summary_mesh,
        input_summary_solution_field,
        input_summary_metrics
    ]
}

workflow {
    main:
    // Load JSON file into a map
    //def jsonFile = file("workflow_config.json")
    //def workflow_config_file = new groovy.json.JsonSlurper().parseText(jsonFile.text)
    //def configurations = workflow_config_file.configurations
    //def configurations_to_parameter_file = workflow_config_file.configuration_to_parameter_file
    //def benchmark = workflow_config_file.benchmark
    //def tools = workflow_config_file.tools
    //def result_dir = workflow_config_file.result_dir

    def parameter_files_path = []
    params.configurations.each { elem ->
        parameter_files_path.add(file(params.configuration_to_parameter_file[elem]))
    }
    //println parameter_files

    //def ch_mesh_files = Channel.fromList(mesh_files)
    def ch_parameter_files = Channel.fromList(parameter_files_path)
    def ch_configurations = Channel.fromList(params.configurations)
    def ch_mesh_python_script = Channel.value(file('create_mesh.py'))

    //Creating Mesh
    output_process_create_mesh = create_mesh(ch_mesh_python_script, ch_configurations, ch_parameter_files)

    input_process_run_simulation = ch_configurations.merge(ch_parameter_files).join(output_process_create_mesh)
    
    //Running Simulation

    def ch_benchmark = Channel.value(params.benchmark)

    input_summary_configuration = Channel.empty()
    input_summary_parameter_file = Channel.empty()
    input_summary_mesh = Channel.empty()
    input_summary_solution_field = Channel.empty()
    input_summary_metrics = Channel.empty()
    ch_tools = Channel.empty()


    if (params.tools.contains("fenics")) {

        fenics_workflow(input_process_run_simulation, params.result_dir)
        output_process_fenics_simulation = fenics_workflow.out

        (input_fenics_summary_configuration, input_fenics_summary_parameter_file, input_fenics_summary_mesh, input_fenics_summary_solution_field, input_fenics_summary_metrics) = prepare_inputs_for_process_summary(input_process_run_simulation, output_process_fenics_simulation)

        input_summary_configuration = input_summary_configuration.concat( input_fenics_summary_configuration )
        input_summary_parameter_file = input_summary_parameter_file.concat( input_fenics_summary_parameter_file )
        input_summary_mesh = input_summary_mesh.concat( input_fenics_summary_mesh )
        input_summary_solution_field = input_summary_solution_field.concat( input_fenics_summary_solution_field )
        input_summary_metrics = input_summary_metrics.concat( input_fenics_summary_metrics )
        ch_tools = ch_tools.concat(Channel.of("fenics"))
    
    }  
    if (params.tools.contains("kratos")) {

        kratos_workflow(input_process_run_simulation, params.result_dir)
        output_process_kratos_simulation = kratos_workflow.out

        (input_kratos_summary_configuration, input_kratos_summary_parameter_file, input_kratos_summary_mesh, input_kratos_summary_solution_field, input_kratos_summary_metrics) = prepare_inputs_for_process_summary(input_process_run_simulation, output_process_kratos_simulation)

        input_summary_configuration = input_summary_configuration.concat( input_kratos_summary_configuration )
        input_summary_parameter_file = input_summary_parameter_file.concat( input_kratos_summary_parameter_file )
        input_summary_mesh = input_summary_mesh.concat( input_kratos_summary_mesh )
        input_summary_solution_field = input_summary_solution_field.concat( input_kratos_summary_solution_field )
        input_summary_metrics = input_summary_metrics.concat( input_kratos_summary_metrics )
        ch_tools = ch_tools.concat(Channel.of("kratos"))

    } else {
        //throw new IllegalArgumentException("Unsupported tool(s): ${tools}. Supported tools are 'fenics' and 'kratos'.")
        error "Unsupported tool(s). Supported tools are 'fenics' and 'kratos'."
    }


    //Summarizing results
    summary(input_summary_configuration, input_summary_parameter_file, input_summary_mesh, input_summary_metrics,input_summary_solution_field, ch_benchmark, ch_tools)

}