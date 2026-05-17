import json
import sys

import numpy as np
import pyvista as pv

with open("parameters.json", "r", encoding="utf-8") as file:
    parameters = json.load(file)

caseFile = sys.argv[1]
outFile = sys.argv[2]

reader = pv.EnSightReader(caseFile)
reader.set_active_time_set(1)
reader.set_active_time_point(len(reader.time_values) - 1)

mesh = reader.read()["all"]

voigtStress = mesh["stress"]
stressMises = np.sqrt(
    voigtStress[:, 0] ** 2
    + voigtStress[:, 1] ** 2
    + voigtStress[:, 2] ** 2
    - voigtStress[:, 1] * voigtStress[:, 2]
    - voigtStress[:, 0] * voigtStress[:, 2]
    - voigtStress[:, 0] * voigtStress[:, 1]
    + 3 * (voigtStress[:, 3] ** 2 + voigtStress[:, 4] ** 2 + voigtStress[:, 5] ** 2)
)

x = parameters["displacement-evaluation-point"]["x"]["value"]
y = parameters["displacement-evaluation-point"]["y"]["value"]

point = pv.PointSet([x, y, 0])

sampled = point.sample(mesh)

metrics = {
    # "max_von_mises_stress_nodes": "",
    "max_von_mises_stress_gauss_points": float(stressMises.max()),
    f"displacement_x_at_evaluation_point (x=f'{x:.2f}', y=f'{y:.2f}')": float(
        sampled["displacement"][0][0]
    ),
}

with open(outFile, "w+") as f:
    f.write(json.dumps(metrics, indent=4))
    # f.write()
