import json
import sys

import dolfinx as df
import numpy as np
import ufl
from dolfinx.fem.petsc import LinearProblem
from mpi4py import MPI
from pint import UnitRegistry


class PlateWithHoleSolution:
    def __init__(self, E, nu, radius, L, load):
        self.radius = radius
        self.L = L
        self.load = load
        self.E = E
        self.nu = nu

    def polar(self, x):
        r = np.hypot(x[0], x[1])
        theta = np.atan2(x[1], x[0])
        return r, theta

    def displacement(self, x):
        r, theta = self.polar(x)
        a = self.radius

        T = self.load
        Ta_8mu = T * a / (4 * self.E / (1.0 + 1.0 * self.nu))
        k = (3.0 - self.nu) / (1.0 + self.nu)

        ct = np.cos(theta)
        c3t = np.cos(3 * theta)
        st = np.sin(theta)
        s3t = np.sin(3 * theta)

        fac = 2 * np.pow(a / r, 3)

        ux = Ta_8mu * (
            r / a * (k + 1.0) * ct + 2.0 * a / r * ((1.0 + k) * ct + c3t) - fac * c3t
        )

        uy = Ta_8mu * (
            (r / a) * (k - 3.0) * st + 2.0 * a / r * ((1.0 - k) * st + s3t) - fac * s3t
        )

        return ux, uy

    def stress(self, x):
        r, theta = self.polar(x)
        T = self.load
        a = self.radius
        cos2t = np.cos(2 * theta)
        cos4t = np.cos(4 * theta)
        sin2t = np.sin(2 * theta)
        sin4t = np.sin(4 * theta)

        fac1 = (a * a) / (r * r)
        fac2 = 1.5 * fac1 * fac1

        sxx = T - T * fac1 * (1.5 * cos2t + cos4t) + T * fac2 * cos4t
        syy = -T * fac1 * (0.5 * cos2t - cos4t) - T * fac2 * cos4t
        sxy = -T * fac1 * (0.5 * sin2t + sin4t) + T * fac2 * sin4t

        return sxx, sxy, sxy, syy


ureg = UnitRegistry()

name = sys.argv[1]
parameter_file = sys.argv[2]

with open(parameter_file) as f:
    parameters = json.load(f)

mesh, cell_tags, facet_tags = df.io.gmshio.read_from_msh(
    parameters["mesh-file"],
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
stress_space = df.fem.functionspace(mesh, ("CG", parameters["element-degree"], (2, 2)))
stress_function = df.fem.Function(stress_space)
#stress_function.interpolate(lambda x: solution.stress(x))
#stress_function.x.scatter_forward()

u = df.fem.Function(V, name="u")
u_prescribed = df.fem.Function(V, name="u_prescribed")
u_prescribed.interpolate(lambda x: solution.displacement(x))
u_prescribed.x.scatter_forward()


u_ = ufl.TestFunction(V)
v_ = ufl.TrialFunction(V)
a = df.fem.form(ufl.inner(sigma(u_), eps(v_)) * dx)


f = df.fem.form(ufl.inner(ufl.dot(stress_function, ufl.FacetNormal(mesh)), u_) * ufl.ds)
#f = df.fem.form(ufl.inner(ufl.Constant(mesh, ((0.0),(0.0))), u_) * ufl.ds)

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
) -> None | df.fem.Function:
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

#space_type = "CG" if parameters["element-degree"] > 1 else "DG"
plot_space = df.fem.functionspace(mesh, ("DG", parameters["element-degree"]-1, (2,2)))
plot_space_mises = df.fem.functionspace(mesh, ("DG", parameters["element-degree"]-1, (1,)))
stress_nodes_red = project(sigma(u), plot_space, dx)
stress_nodes_red.name = "stress"

def mises_stress(u):
    stress = sigma(u)
    p = ufl.tr(stress) / 3.0
    s = stress - p * ufl.Identity(2)
    return ufl.as_vector([(3.0 / 2.0)**0.5 * (ufl.inner(s, s) + p*p)**0.5,])
print("mises_stress(u) = ", mises_stress(u).ufl_shape)
mises_stress_nodes = project(mises_stress(u), plot_space_mises, dx)
mises_stress_nodes.name = "von_mises_stress"
#stress_nodes = df.fem.Function(stress_space, name="stress")
#stress_nodes.interpolate(stress_nodes_red)

with df.io.VTKFile(MPI.COMM_WORLD, f"data/output_{name}.vtk", "w") as vtk:
    vtk.write_function([u], 0.0)
    vtk.write_function([stress_nodes_red, mises_stress_nodes
                        ], 0.0)
