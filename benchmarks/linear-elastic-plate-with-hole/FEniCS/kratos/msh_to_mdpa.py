import json
import meshio
import re
import numpy as np
from pint import UnitRegistry
from argparse import ArgumentParser

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

if __name__ == "__main__":
    parser = ArgumentParser(
        description="Convert GMSH mesh to Kratos MDPA format."
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
        "--output_mdpa_file",
        required=True,
        help="Path to the MDPA file (output)",
    )
    args, _ = parser.parse_known_args()
    msh_to_mdpa(args.input_parameter_file, args.input_mesh_file, args.output_mdpa_file)
