// Default parameter input
params.ip_files_script = Channel.value(file('create_input_files.py'))
params.run_sim_script = Channel.value(file('run_simulation.py'))
//params.summary_script = Channel.value(file('summary.py'))

// split process
process generate_input_files {
    publishDir "data/"
    conda 'environment.yml'

    input:
    path python_script
    val name
    path parameters_json

    output:
    tuple val(name), path("input_${name}.json"), path("mesh_${name}.msh"), path(parameters_json)

    script:
    """
    python3 $python_script $name $parameters_json 
    """
}

process run_simulation {

    publishDir "data/"
    conda 'environment.yml'

    input:
    path python_script
    tuple val(name), path(input_json), path(mesh_msh), path(parameters_json)

    output:
    tuple val(name), path("output_${name}.vtk"), path(input_json), path(mesh_msh), path(parameters_json)

    script:
    """
    python3 $python_script $name $input_json
    """
}

process summary {

    publishDir "data/"
    //conda 'environment.yml'

    input:
    //path python_script
    tuple val(name), path(output_vtk), path(input_json), path(mesh_msh), path(parameters_json)

    output:
    path("summary_${name}.json")

    script:
    """
    #!/usr/bin/env python
    import json
    import pyvista
    from xml.etree import ElementTree as ET
    from pathlib import Path
    import sys
    import os

    summary = {}
    summary["name"] = "$name"
    summary["parameters"] = "$parameters_json"
    summary["input"] = "$input_json"
    summary["mesh"] = "$mesh_msh"
    summary["output"] = "$output_vtk"

    # Load the mesh and output data
    max_mises_stress = 42.0

    tree = ET.parse(summary["output"])
    root = tree.getroot()
    pvtu_filenames = []
    path = Path(os.path.realpath(summary["output"])).parent
    for dataset in root.findall(".//DataSet"):
        pvtu_filenames.append(path / dataset.get("file"))
    meshes = [pyvista.read(pvtu_filename) for pvtu_filename in pvtu_filenames]
    for mesh in meshes:
        print("Mesh:", mesh)
        # Assuming the mesh has a 'von_mises_stress' array
        try:
            max_mises_stress = float(mesh["von_mises_stress"].max())
        except KeyError:
            print("von_mises_stress not found in mesh.")
    summary["max_mises_stress"] = max_mises_stress # Replace with actual computation
    with open(f"summary_{summary["name"]}.json", "w") as f:
        json.dump(summary, f, indent=4)

    """
}

// Workflow block
workflow {

    def ch_parameter_files = Channel.fromPath('parameters_*.json', checkIfExists: true)
    //ch_parameter_files.view()

    def parameters_files = files('parameters_*.json')
    def names = parameters_files.baseName.collect{it.split('_')[1]}
    //println names
    def ch_file_names = Channel.fromList(names)   

    output_gen_input_files = generate_input_files(params.ip_files_script, ch_file_names, ch_parameter_files)
    //output_gen_input_files.view()
    output_run_sim = run_simulation(params.run_sim_script, output_gen_input_files)
    //output_run_sim.view()
    summary(output_run_sim)
}