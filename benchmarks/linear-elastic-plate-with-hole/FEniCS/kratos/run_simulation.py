from __future__ import print_function, absolute_import, division  # makes KratosMultiphysics backward compatible with python 2.6 and 2.7
import json
import sys
from argparse import ArgumentParser

import gmsh
import meshio
import re
from pint import UnitRegistry
import numpy as np
import os

ureg = UnitRegistry()

import KratosMultiphysics
from KratosMultiphysics.StructuralMechanicsApplication.structural_mechanics_analysis import StructuralMechanicsAnalysis
import sys

import pyvista
from pathlib import Path

# Add parent directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from plateWithHoleSolution import PlateWithHoleSolution


def msh_to_mdpa(parameter_file: str, mesh_file: str, mdpa_file: str):
    """
    This function converts the GMSH mesh to a Kratos MDPA file format.
    Due to limitations in the meshio conversion, several modifications are made to
    the mdpa file:
    - The element types are replaced with SmallDisplacementElement2D3N and SmallDisplacementElement2D6N
       since meshio only converts to Triangle2D3 and Triangle2D6 which only describe the geometry but
       not the finite elements.
    - The Line2D elements are removed since they are not used in Kratos.
    - The gmsh:dim_tags are removed since they are not used in Kratos.
    - SubModelParts for the boundary conditions are created.

    At this point, we don't see a better way to do this conversion, so we use a lot of string manipulation.
    """

    ureg = UnitRegistry()
    with open(parameter_file) as f:
        parameters = json.load(f)
    radius = (
        ureg.Quantity(parameters["radius"]["value"], parameters["radius"]["unit"])
        .to_base_units()
        .magnitude
    )
    L = (
        ureg.Quantity(parameters["length"]["value"], parameters["length"]["unit"])
        .to_base_units()
        .magnitude
    )

    x0 = 0.0
    x1 = x0 + radius
    x2 = x0 + L
    y0 = 0.0
    y1 = y0 + radius
    y2 = y0 + L
    mesh = meshio.read(mesh_file)

    meshio.write(mdpa_file, mesh)

    with open(mdpa_file, "r") as f:
        # replace all occurences of Triangle with SmallStrainElement
        text = f.read()

        text = text.replace("Triangle2D3", "SmallDisplacementElement2D3N")
        text = text.replace("Triangle2D6", "SmallDisplacementElement2D6N")

        text = re.sub(r"Begin\s+Elements\s+Line2D[\n\s\d]*End\s+Elements", "", text)

        mesh_tags = np.array(
            re.findall(
                r"Begin\s+NodalData\s+gmsh:dim_tags[\s\n]*(.*)End\s+NodalData\s+gmsh:dim_tags",
                text,
                flags=re.DOTALL,
            )[0]
            .replace("np.int64", "")
            .replace("(", "")
            .replace(")", "")
            .split(),
            dtype=np.int32,
        ).reshape(-1, 3)

        text = re.sub(
            r"Begin\s+NodalData\s+gmsh:dim_tags[\s\n]*(.*)End\s+NodalData\s+gmsh:dim_tags",
            "",
            text,
            flags=re.DOTALL,
        )

    append = "\nBegin SubModelPart boundary_left\n"
    append += "    Begin SubModelPartNodes\n        "
    nodes = np.argwhere(np.isclose(mesh.points[:, 0], x0)).flatten() + 1
    append += "\n        ".join(map(str, nodes)) + "\n"
    append += "    End SubModelPartNodes\n"
    append += "End SubModelPart\n"

    text += append

    append = "\nBegin SubModelPart boundary_bottom\n"
    append += "    Begin SubModelPartNodes\n        "
    nodes = np.argwhere(np.isclose(mesh.points[:, 1], y0)).flatten() + 1
    append += "\n        ".join(map(str, nodes)) + "\n"
    append += "    End SubModelPartNodes\n"
    append += "End SubModelPart\n"

    text += append

    append = "\nBegin SubModelPart boundary_right\n"
    append += "    Begin SubModelPartNodes\n        "
    nodes = np.argwhere(np.isclose(mesh.points[:, 0], x2)).flatten() + 1
    append += "\n        ".join(map(str, nodes)) + "\n"
    append += "    End SubModelPartNodes\n"
    append += "End SubModelPart\n"

    text += append

    append = "\nBegin SubModelPart boundary_top\n"
    append += "    Begin SubModelPartNodes\n        "
    nodes = np.argwhere(np.isclose(mesh.points[:, 1], y2)).flatten() + 1
    append += "\n        ".join(map(str, nodes)) + "\n"
    append += "    End SubModelPartNodes\n"
    append += "End SubModelPart\n"

    text += append
    with open(mdpa_file, "w") as f:
        f.write(text)


def create_kratos_input(
    parameter_file: str,
    mdpa_file: str,
    kratos_input_template_file: str,
    kratos_material_template_file: str,
    kratos_input_file: str,
    kratos_material_file: str,
):
    """
    This function reads the input template file and the material template
    file and replaces the placeholders with the actual values.
    """

    # Load parameters
    with open(parameter_file) as f:
        parameters = json.load(f)

    E = (
        ureg.Quantity(
            parameters["young-modulus"]["value"], parameters["young-modulus"]["unit"]
        )
        .to_base_units()
        .magnitude
    )
    nu = (
        ureg.Quantity(
            parameters["poisson-ratio"]["value"], parameters["poisson-ratio"]["unit"]
        )
        .to_base_units()
        .magnitude
    )
    radius = (
        ureg.Quantity(parameters["radius"]["value"], parameters["radius"]["unit"])
        .to_base_units()
        .magnitude
    )
    L = (
        ureg.Quantity(parameters["length"]["value"], parameters["length"]["unit"])
        .to_base_units()
        .magnitude
    )
    load = (
        ureg.Quantity(parameters["load"]["value"], parameters["load"]["unit"])
        .to_base_units()
        .magnitude
    )

    analytical_solution = PlateWithHoleSolution(
        E=E,
        nu=nu,
        radius=radius,
        L=L,
        load=load,
    )

    bc = analytical_solution.displacement_symbolic_str("X", "Y")
    
    with open(kratos_material_template_file) as f:
        material_string = f.read()

    material_string = material_string.replace(r'"{{YOUNG_MODULUS}}"', str(E))
    material_string = material_string.replace(r'"{{POISSON_RATIO}}"', str(nu))

    with open(kratos_material_file, "w") as f:
        f.write(material_string)

    with open(kratos_input_template_file) as f:
        project_parameters_string = f.read()
    #remove the file extension .mdpa
    project_parameters_string = project_parameters_string.replace(
        r"{{MESH_FILE}}", os.path.splitext(mdpa_file)[0]
    )
    project_parameters_string = project_parameters_string.replace(
        r"{{MATERIAL_FILE}}", kratos_material_file
    )
    project_parameters_string = project_parameters_string.replace(
        r"{{BOUNDARY_RIGHT_DISPLACEMENT_X}}", str(bc[0])
    )
    project_parameters_string = project_parameters_string.replace(
        r"{{BOUNDARY_RIGHT_DISPLACEMENT_Y}}", str(bc[1])
    )
    project_parameters_string = project_parameters_string.replace(
        r"{{BOUNDARY_TOP_DISPLACEMENT_X}}", str(bc[0])
    )
    project_parameters_string = project_parameters_string.replace(
        r"{{BOUNDARY_TOP_DISPLACEMENT_Y}}", str(bc[1])
    )
    # Replace output path with a subdirectory named after the configuration
    config = parameters["configuration"]
    output_dir = os.path.join(os.path.dirname(os.path.abspath(kratos_input_file)), str(config))
    os.makedirs(output_dir, exist_ok=True)
    project_parameters_string = project_parameters_string.replace(r"{{OUTPUT_PATH}}", output_dir)

    with open(kratos_input_file, "w") as f:
        f.write(project_parameters_string)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Run FEniCS simulation for a plate with a hole.\n"
        "Inputs: --input_parameter_file, --input_mesh_file\n"
        "Outputs: --output_solution_file_hdf5, --output_metrics_file"
    )
    parser.add_argument(
        "--input_parameter_file",
        required=True,
        help="JSON file containing simulation parameters (input)",
    )
    parser.add_argument(
        "--input_mesh_file", required=True, help="Path to the mesh file (input)"
    )
    parser.add_argument(
        "--input_kratos_input_template",
        required=True,
        help="Path to the kratos input template file (input)",
    )
    parser.add_argument(
        "--input_material_template",
        required=True,
        help="Path to the kratos material template file (input)",
    )
    parser.add_argument(
        "--output_mdpa_file",
        required=True,
        help="Path to the MDPA file (output)",
    )
    parser.add_argument(
        "--output_kratos_inputfile",
        required=True,
        help="Path to the kratos input file (output)",
    )
    parser.add_argument(
        "--output_kratos_materialfile",
        required=True,
        help="Path to the kratos material file (output)",
    )
    parser.add_argument(
        "--output_solution_file_zip",
        required=True,
        help="Path to the zipped solution files (output)",
    )
    parser.add_argument(
        "--output_metrics_file",
        required=True,
        help="Path to the output metrics JSON file (output)",
    )
    args, _ = parser.parse_known_args()

    msh_to_mdpa(args.input_parameter_file, args.input_mesh_file, args.output_mdpa_file)

    create_kratos_input(
        parameter_file=args.input_parameter_file,
        mdpa_file=args.output_mdpa_file,
        kratos_input_template_file=args.input_kratos_input_template,  # <-- fixed argument name
        kratos_material_template_file=args.input_material_template,
        kratos_input_file=args.output_kratos_inputfile,
        kratos_material_file=args.output_kratos_materialfile,
    )

    """
    For user-scripting it is intended that a new class is derived
    from StructuralMechanicsAnalysis to do modifications
    """
    with open(args.output_kratos_inputfile, "r") as kratos_input:
        parameters = KratosMultiphysics.Parameters(kratos_input.read())

    model = KratosMultiphysics.Model()
    simulation = StructuralMechanicsAnalysis(model, parameters)
    simulation.Run()

    # Continue here Load the result mesh and output data
   # Load parameters
    with open(args.input_parameter_file) as f:
        parameters = json.load(f)
    config = parameters["configuration"]
    output_dir = Path(os.path.dirname(os.path.abspath(args.output_kratos_inputfile))) / str(config)
    mesh = pyvista.read(str(output_dir / "Structure_0_1.vtk"))
    max_von_mises_stress = float(mesh["VON_MISES_STRESS"].max())
    print("Max Von Mises Stress:", max_von_mises_stress)
    metrics = {
        "max_von_mises_stress_nodes": max_von_mises_stress
    }
    with open(args.output_metrics_file, "w") as f:
        json.dump(metrics, f, indent=4)
        
    files_to_store = [str(output_dir / "Structure_0_1.vtk")]

    import zipfile
    with zipfile.ZipFile(args.output_solution_file_zip, "w") as zipf:
        for filepath in files_to_store:
            zipf.write(filepath, arcname=f"result_{config}.vtk")