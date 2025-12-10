
include { fenics_workflow } from './fenics/fenics.nf'
include { kratos_workflow } from './kratos/kratos.nf'

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
    path python_script
    val configuration
    val parameter_file
    val mesh_file
    val solution_metrics
    val solution_field_data
    val benchmark
    val benchmark_uri
    val tool

    output:
    path("summary.json")
    
    script:
    """
    python3 $python_script \
        --input_configuration ${configuration.join(' ')} \
        --input_parameter_file ${parameter_file.join(' ')} \
        --input_mesh_file ${mesh_file.join(' ')} \
        --input_solution_metrics ${solution_metrics.join(' ')} \
        --input_solution_field_data ${solution_field_data.join(' ')} \
        --input_benchmark ${benchmark} \
        --input_benchmark_uri ${benchmark_uri} \
        --output_summary_json "summary.json"

    """
}

def prepare_inputs_for_process_summary(input_process_run_simulation, output_process_run_simulation) {

    // Input: channels of the input and the output of the simulation process
    // Output: a tuple of channels to be used as input for the summary process
    // Purpose: To prepare inputs for the summary process (invoked once per simulation tool) from the output of the simulation process (depending on the number of configurations, invoked multiple times per simulation tool).

    // Firstly, the join operation is performed between the input and output channels of the simulation process based on a matching key (configuration).

    // Secondly, the individual components (configuration, parameter_file, mesh_file, solution_field_data, solution_metrics) are extracted from the joined tuples and collected into separate lists. 
    // The collect() method outputs a channel with a single entry as the summary process runs once per simulation tool. This single entry is a list of all the configurations or parameter files or mesh files etc.
    
    def matched_channels = input_process_run_simulation.join(output_process_run_simulation) 

    def branched_channels = matched_channels.multiMap{ v, w, x, y, z ->
    configuration : v 
    parameter_file : w 
    mesh : x 
    solution_field : y  
    metrics : z }

    return [
        branched_channels.configuration.collect(),
        branched_channels.parameter_file.collect(),
        branched_channels.mesh.collect(),
        branched_channels.solution_field.collect(),
        branched_channels.metrics.collect()
    ]
}

workflow {
    main:

    def parameter_files_path = []
    params.configurations.each { elem ->
        parameter_files_path.add(file(params.configuration_to_parameter_file[elem]))
    }

    def ch_parameter_files = Channel.fromList(parameter_files_path)
    def ch_configurations = Channel.fromList(params.configurations)
    def ch_mesh_python_script = Channel.value(file('create_mesh.py'))

    //Creating Mesh

    output_process_create_mesh = create_mesh(ch_mesh_python_script, ch_configurations, ch_parameter_files)

    input_process_run_simulation = ch_configurations.merge(ch_parameter_files).join(output_process_create_mesh)

    //Running Simulation
    
    ch_tool = Channel.value(params.tool) 
    
    if (params.tool == "fenics") {
        fenics_workflow(input_process_run_simulation, params.result_dir)
        output_simulation_tool_workflow = fenics_workflow.out
        
    } 
    else if (params.tool == "kratos") {
        kratos_workflow(input_process_run_simulation, params.result_dir)
        output_simulation_tool_workflow = kratos_workflow.out
    }
    else {
        error "Unknown tool: ${params.tool}"
    }
    
    def (input_summary_configuration,\
    input_summary_parameter_file,\
    input_summary_mesh,\
    input_summary_solution_field,\
    input_summary_metrics) = prepare_inputs_for_process_summary(input_process_run_simulation, output_simulation_tool_workflow)


    //Summarizing results
    def ch_benchmark = Channel.value(params.benchmark)
    def ch_benchmark_uri = Channel.value(params.benchmark_uri)
    def ch_summarize_python_script = Channel.value(file('../common/summarize_results.py'))
    summary(ch_summarize_python_script, \
            input_summary_configuration, \
            input_summary_parameter_file, \
            input_summary_mesh, \
            input_summary_metrics, \
            input_summary_solution_field, \
            ch_benchmark, \
            ch_benchmark_uri, \
            ch_tool)/**/

}
/*
Steps to add a new simulation tool to the workflow:

1. Write the tool-specific workflow, scripts, environment file and store them in the benchmarks/linear-elastic-plate-with-hole/tool_name/.
2. Include the tool-specific workflow script at the top of this file.
3. Add an if-else statement for the new tool to be compared with the user input at CLI.

---------------------------------------------------------------------------------------------------------------------------------

Remark: Care should be taken to track the entries in the I/O channels, as the process output for a given configuration 
may not arrive in the same order as the inputs were sent. When reusing channel entries after process execution, outputs should 
be matched with their corresponding inputs using a common key.

Information on channel operations: https://www.nextflow.io/docs/latest/reference/operator.html
Information on channels: https://training.nextflow.io/2.2/basic_training/channels/
*/ 