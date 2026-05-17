import meshio
import numpy as np

mesh = meshio.read("mesh.msh")

# Keep only 2D cells
cells = []
cell_data = {
    "abaqus:element_type": []
}

for cell_block in mesh.cells:
    if cell_block.type == "triangle":
        cells.append(cell_block)
        cell_data["abaqus:element_type"].append(
            ["CPS3"] * len(cell_block.data)
        )

    elif cell_block.type == "quad":
        cells.append(cell_block)
        cell_data["abaqus:element_type"].append(
            ["CPS4"] * len(cell_block.data)
        )

# Use first and second coordinates only
pts2d = mesh.points[:, :2]
c1 = pts2d[:, 0]
c2 = pts2d[:, 1]

# Bounds
c1min, c1max = float(c1.min()), float(c1.max())
c2min, c2max = float(c2.min()), float(c2.max())

# Tolerances (relative to span, with a tiny absolute floor)
c1tol = max(1e-12, 1e-8 * max(1.0, c1max - c1min))
c2tol = max(1e-12, 1e-8 * max(1.0, c2max - c2min))

# Indices for node sets
i_c1min = np.where(np.isclose(c1, c1min, atol=c1tol))[0]
i_c1max = np.where(np.isclose(c1, c1max, atol=c1tol))[0]
i_c2min = np.where(np.isclose(c2, c2min, atol=c2tol))[0]
i_c2max = np.where(np.isclose(c2, c2max, atol=c2tol))[0]

point_sets = {
    "X_MIN": i_c1min.astype(np.int32),
    "X_MAX": i_c1max.astype(np.int32),
    "Y_MIN": i_c2min.astype(np.int32),
    "Y_MAX": i_c2max.astype(np.int32),
}

mesh2d = meshio.Mesh(
    points=pts2d,
    cells=cells,
    cell_data=cell_data,
    point_sets=point_sets,
)



meshio.write("mesh.inp", mesh2d)


