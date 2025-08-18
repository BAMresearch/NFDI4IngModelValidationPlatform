import json
import sys
from argparse import ArgumentParser

from pathlib import Path
import dolfinx as df
import basix.ufl
import numpy as np
import ufl
from dolfinx.fem.petsc import LinearProblem
from petsc4py.PETSc import ScalarType
from mpi4py import MPI
from pint import UnitRegistry

# Add parent directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from plateWithHoleSolution import PlateWithHoleSolution


def run_simulation(
    parameter_file: str, mesh_file: str, solution_file_zip: str, metrics_file: str
) -> None:
    ureg = UnitRegistry()
    with open(parameter_file) as f:
        parameters = json.load(f)

    mesh, cell_tags, facet_tags = df.io.gmshio.read_from_msh(
        mesh_file,
        comm=MPI.COMM_WORLD,
        gdim=2,
    )

    V = df.fem.functionspace(mesh, ("CG", parameters["element-degree"], (2,)))

    tags_left = facet_tags.find(1)
    tags_bottom = facet_tags.find(2)
    tags_right = facet_tags.find(3)
    tags_top = facet_tags.find(4)

    # Boundary conditions
    dofs_left = df.fem.locate_dofs_topological(V.sub(0), 1, tags_left)
    dofs_bottom = df.fem.locate_dofs_topological(V.sub(1), 1, tags_bottom)
    dofs_right = df.fem.locate_dofs_topological(V, 1, tags_right)
    dofs_top = df.fem.locate_dofs_topological(V, 1, tags_top)

    bc_left = df.fem.dirichletbc(0.0, dofs_left, V.sub(0))
    bc_bottom = df.fem.dirichletbc(0.0, dofs_bottom, V.sub(1))

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

    solution = PlateWithHoleSolution(
        E=E,
        nu=nu,
        radius=radius,
        L=L,
        load=load,
    )

    def eps(v):
        return ufl.sym(ufl.grad(v))

    def sigma(v):
        # plane stress
        epsilon = eps(v)
        return (
            E
            / (1.0 - nu**2)
            * ((1.0 - nu) * epsilon + nu * ufl.tr(epsilon) * ufl.Identity(2))
        )

    def as_tensor(v):
        return ufl.as_matrix([[v[0], v[2]], [v[2], v[1]]])

    dx = ufl.Measure(
        "dx",
        metadata={
            "quadrature_degree": parameters["quadrature-degree"],
            "quadrature_scheme": parameters["quadrature-rule"],
        },
    )
    ds = ufl.Measure(
        "ds",
        domain=mesh,
        subdomain_data=facet_tags,
    )
    stress_space = df.fem.functionspace(
        mesh, ("CG", parameters["element-degree"], (2, 2))
    )
    stress_function = df.fem.Function(stress_space)

    u = df.fem.Function(V, name="u")
    u_prescribed = df.fem.Function(V, name="u_prescribed")
    u_prescribed.interpolate(lambda x: solution.displacement(x))
    u_prescribed.x.scatter_forward()

    u_ = ufl.TestFunction(V)
    v_ = ufl.TrialFunction(V)
    a = df.fem.form(ufl.inner(sigma(u_), eps(v_)) * dx)

    # set rhs to zero
    f = df.fem.form(ufl.inner(df.fem.Constant(mesh, np.array([0.0, 0.0])), u_) * ufl.ds)

    bc_right = df.fem.dirichletbc(u_prescribed, dofs_right)
    bc_top = df.fem.dirichletbc(u_prescribed, dofs_top)
    solver = LinearProblem(
        a,
        f,
        bcs=[bc_left, bc_bottom, bc_right, bc_top],
        u=u,
        petsc_options={
            "ksp_type": "gmres",
            "ksp_rtol": 1e-14,
            "ksp_atol": 1e-14,
        },
    )
    solver.solve()

    def project(
        v: df.fem.Function | ufl.core.expr.Expr,
        V: df.fem.FunctionSpace,
        dx: ufl.Measure = ufl.dx,
    ) -> df.fem.Function:
        """
        Calculates an approximation of `v` on the space `V`

        Args:
            v: The expression that we want to evaluate.
            V: The function space on which we want to evaluate.
            dx: The measure that is used for the integration. This is important, if
            either `V` is a quadrature space or `v` is a ufl expression containing a quadrature space.

        Returns:
            A function if `u` is None, otherwise `None`.

        """
        dv = ufl.TrialFunction(V)
        v_ = ufl.TestFunction(V)
        a_proj = ufl.inner(dv, v_) * dx
        b_proj = ufl.inner(v, v_) * dx

        solver = LinearProblem(a_proj, b_proj)
        uh = solver.solve()
        return uh

    plot_space_stress = df.fem.functionspace(
        mesh, ("DG", parameters["element-degree"] - 1, (2, 2))
    )
    plot_space_mises = df.fem.functionspace(
        mesh, ("DG", parameters["element-degree"] - 1, (1,))
    )
    stress_nodes_red = project(sigma(u), plot_space_stress, dx)
    stress_nodes_red.name = "stress"

    def mises_stress(u):
        stress = sigma(u)
        p = ufl.tr(stress) / 3.0
        s = stress - p * ufl.Identity(2)
        return ufl.as_vector([(3.0 / 2.0) ** 0.5 * (ufl.inner(s, s) + p * p) ** 0.5])

    mises_stress_nodes = project(mises_stress(u), plot_space_mises, dx)
    mises_stress_nodes.name = "von_mises_stress"

    # Write each function to its own VTK file on all ranks
    output_dir = Path(solution_file_zip).parent
    with df.io.VTKFile(
        MPI.COMM_WORLD,
        str(output_dir / f"solution_field_data_displacements_{parameters['configuration']}.vtk"),
        "w",
    ) as vtk:
        vtk.write_function(u, 0.0)
    with df.io.VTKFile(
        MPI.COMM_WORLD,
        str(output_dir / f"solution_field_data_stress_{parameters['configuration']}.vtk"),
        "w",
    ) as vtk:
        vtk.write_function(stress_nodes_red, 0.0)
    with df.io.VTKFile(
        MPI.COMM_WORLD,
        str(output_dir / f"solution_field_data_mises_stress_{parameters['configuration']}.vtk"),
        "w",
    ) as vtk:
        vtk.write_function(mises_stress_nodes, 0.0)

    # extract maximum von Mises stress
    max_mises_stress_nodes = np.max(mises_stress_nodes.x.array)

    # Compute von Mises stress at quadrature (Gauss) points and extract maximum (global across MPI)
    quad_element = basix.ufl.quadrature_element(
        mesh.topology.cell_name(),
        value_shape=(1,),
        degree=parameters["quadrature-degree"],
    )

    Q_mises = df.fem.functionspace(mesh, quad_element)
    mises_qp = df.fem.Function(Q_mises, name="von_mises_stress_qp")
    expr_qp = df.fem.Expression(mises_stress(u), Q_mises.element.interpolation_points())
    mises_qp.interpolate(expr_qp)
    max_mises_stress_gauss_points = MPI.COMM_WORLD.allreduce(
        np.max(mises_qp.x.array), op=MPI.MAX
    )
    # Save metrics
    metrics = {
        "max_von_mises_stress_nodes": max_mises_stress_nodes,
        "max_von_mises_stress_gauss_points": max_mises_stress_gauss_points,
    }

    if MPI.COMM_WORLD.rank == 0:
        with open(metrics_file, "w") as f:
            json.dump(metrics, f, indent=4)
        # store all .pvd, .vtu, and .vtk files for this configuration in the zip file
        import zipfile

        config = parameters["configuration"]
        file_patterns = [
            str(output_dir / f"solution_field_data_displacements_{config}*.pvd"),
            str(output_dir / f"solution_field_data_stress_{config}*.vtu"),
            str(output_dir / f"solution_field_data_mises_stress_{config}*.vtk"),
        ]
        files_to_store = []
        for pattern in file_patterns:
            files_to_store.extend(Path().glob(pattern))
        with zipfile.ZipFile(solution_file_zip, "w") as zipf:
            for filepath in files_to_store:
                zipf.write(filepath, arcname=filepath.name)


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
    run_simulation(
        args.input_parameter_file,
        args.input_mesh_file,
        args.output_solution_file_zip,
        args.output_metrics_file,
    )