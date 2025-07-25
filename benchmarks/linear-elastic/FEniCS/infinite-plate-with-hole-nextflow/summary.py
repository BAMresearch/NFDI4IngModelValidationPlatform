import json
import pyvista
from xml.etree import ElementTree as ET
from pathlib import Path
import sys
import os

summary = {}
summary["name"] = sys.argv[1]
summary["parameters"] = sys.argv[5]
summary["input"] = sys.argv[3]
summary["mesh"] = sys.argv[4]
summary["output"] = sys.argv[2]

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