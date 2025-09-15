
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

    ch_tools = Channel.fromList(params.tools) 

    input_process_run_simulation_with_tool = ch_tools.combine(input_process_run_simulation)
    input_fenics_workflow = input_process_run_simulation_with_tool.filter{ it[0] == 'fenics' }.map{_w,x,y,z -> tuple(x,y,z)}
    input_kratos_workflow = input_process_run_simulation_with_tool.filter{ it[0] == 'kratos' }.map{_w,x,y,z -> tuple(x,y,z)}


    fenics_workflow(input_fenics_workflow, params.result_dir)
    output_fenics_workflow = fenics_workflow.out
    def (fenics_configurations,\
        fenics_parameter_files,\
        fenics_meshes,\
        fenics_solution_fields,\
        fenics_summary_metrics) = prepare_inputs_for_process_summary(input_fenics_workflow, output_fenics_workflow)


    kratos_workflow(input_kratos_workflow, params.result_dir)
    output_kratos_workflow = kratos_workflow.out
    def (kratos_configurations, \
        kratos_parameter_files, \
        kratos_meshes, \
        kratos_solution_fields, \
        kratos_summary_metrics) = prepare_inputs_for_process_summary(input_kratos_workflow, output_kratos_workflow)


    // channels are concatenated in the same order as they are passed to the .concat. The order should be consistent with the order of tools in ch_tools.
    input_summary_configuration = fenics_configurations.concat(kratos_configurations)
    input_summary_parameter_file = fenics_parameter_files.concat(kratos_parameter_files)
    input_summary_mesh = fenics_meshes.concat(kratos_meshes)
    input_summary_solution_field = fenics_solution_fields.concat(kratos_solution_fields)
    input_summary_metrics = fenics_summary_metrics.concat(kratos_summary_metrics)

    //Summarizing results
    def ch_benchmark = Channel.value(params.benchmark)
    def ch_summarise_python_script = Channel.value(file('summarise_results.py'))
    summary(ch_summarise_python_script, \
            input_summary_configuration, \
            input_summary_parameter_file, \
            input_summary_mesh, \
            input_summary_metrics, \
            input_summary_solution_field, \
            ch_benchmark, \
            ch_tools)

}

// Steps to perform to add a new simulation tool to the workflow:
// 1. Add the tool name to "tools" workflow_config.json (generated here using generate_config.py)
// 2. Include the tool-specific workflow script at the top of this file.
// 3. Create an input channel for the new tool (e.g. see the definition of input_fenics_workflow)
// 4. Invoke the new tool-specific workflow (similar to fenics_workflow) & using its output, prepare inputs for the summary process.
// 5. Concatenate the prepared inputs to form the final input channels for the summary process.