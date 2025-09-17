# Infinite linear elastic plate with hole

## Problem description

We consider the case of an infinite plate with a circular hole with radius $a$ in the center. The plate is subjected to uniform tensile load $p$ at infinity. The analytical solution for the stress field has been derived by Kirsch in 1898 [@Kirsch1898].
<!-- include an svg picture here-->
![Infinite linear elastic plate with hole](plate-with-hole.svg)

The solution is given in polar stress components of the Cauchy stress tensor $\boldsymbol \sigma$ at a point with polar coordinates $(r,\theta)\in\mathbb R_+ \times \mathbb R$. Assume that the infinite plate is loaded in $x$-direction with load $p$, then the polar stress components are given by

$$
    \begin{aligned}
        \sigma_{rr}(r,\theta) &= \frac{p}{2}\left(1-\frac{a^2}{r^2}\right)+\frac{p}{2}\left(1-\frac{a^2}{r^2}\right)\left(1-\frac{3a^2}{r^2}\right)\cos(2\theta)\\
        \sigma_{\theta\theta}(r,\theta) &=\frac{p}{2}\left(1+\frac{a^2}{r^2}\right) - \frac{p}{2}\left(1+\frac{3a^4}{r^4}\right)\cos(2\theta)\\
        \sigma_{r\theta}(r,\theta) &= -\frac{p}{2}\left(1-\frac{a^2}{r^2}\right)\left(1+\frac{3a^2}{r^2}\right)\sin(2\theta)
    \end{aligned}
$$

In order to write the stresses in a cartesian coordiante system, they need to be rotated by $\theta$, which results in

$$
    \begin{aligned}
        \sigma_{xx} (r,\theta) &=  \frac{3 a^{4} p \cos{\left(4 \theta \right)}}{2 r^{4}} - \frac{a^{2} p \left(1.5 \cos{\left(2 \theta \right)} + \cos{\left(4 \theta \right)}\right)}{r^{2}} + p \\
        \sigma_{yy} (r,\theta)&= - \frac{3 a^{4} p \cos{\left(4 \theta \right)}}{2 r^{4}} - \frac{a^{2} p \left(\frac{\cos{\left(2 \theta \right)}}{2} - \cos{\left(4 \theta \right)}\right)}{r^{2}}\\
        \sigma_{xy} (r,\theta) &= \frac{3 a^{4} p \sin{\left(4 \theta \right)}}{2 r^{4}} - \frac{a^{2} p \left(\frac{\sin{\left(2 \theta \right)}}{2} + \sin{\left(4 \theta \right)}\right)}{r^{2}}
    \end{aligned}
$$

with the full stress tensor solution given by

$$
\boldsymbol\sigma_\mathrm{analytical} (r,\theta)= \begin{bmatrix} \sigma_{xx}(r,\theta) & \sigma_{xy}(r,\theta)\\\ \sigma_{xy}(r,\theta) & \sigma_{yy}(r,\theta) \end{bmatrix}.
$$

or for a cartesion point $(x,y)\in \mathbb R_+^2$:

$$
\boldsymbol\sigma_\mathrm{analytical} (x,y)=\boldsymbol\sigma_\mathrm{analytical} \left(\sqrt{x^2 + y^2},\arccos\frac{x}{\sqrt{x^2+y^2}}\right). 
$$

In order to transform this into a practical benchmark, we consider a rectangular subdomain
of the infinite plate around the hole. The boundary conditions of the subdomain are determined
from the analytical solution. The example is further reduced by only simulating one quarter
of the rectangular domain with length $l$ and assuming symmetry conditions at the edges. Let 

$$
\Omega =[0,l]^2 \setminus \lbrace (x,y) \mid \sqrt{x^2+y^2}<a \rbrace
$$ 

be the domain of the benchmark example and

$$
\begin{aligned}
\Gamma_\mathrm{D_1} &= \lbrace (x,y)\in \partial\Omega | y=0\rbrace \\
\Gamma_\mathrm{D_2} &= \lbrace (x,y)\in \partial\Omega | x=0\rbrace \\
\Gamma_\mathrm{N} &= \lbrace (x,y)\in \partial\Omega | x=l \lor y=l \rbrace
\end{aligned}
$$

then the PDE with the displacement $\boldsymbol u$ as solution variable is given by

$$
\begin{aligned}
\mathrm{div}\boldsymbol{\sigma}(\boldsymbol{\varepsilon}(\boldsymbol{u})) &= 0 &\quad \text{ on } \Omega & \\
\boldsymbol{\varepsilon}(\boldsymbol u) &= \frac{1}{2}\left(\nabla \boldsymbol u + (\nabla\boldsymbol u)^\top\right) &&\text{Infinitesimal strain}\\
\boldsymbol{\sigma}(\boldsymbol{\varepsilon}) &= \frac{E}{1-\nu^2}\left((1-\nu)\boldsymbol{\varepsilon} + \nu \mathrm{tr}\boldsymbol{\varepsilon}\boldsymbol I_2\right) && \text{Plane stress law}\\
\boldsymbol u_y &=0 & \text{ on } \Gamma_\mathrm{D_1}& \text{ Dirichlet BC}\\
\boldsymbol u_x &=0 & \text{ on } \Gamma_\mathrm{D_2}& \text{ Dirichlet BC}\\
\boldsymbol t &= \tilde{\boldsymbol{t}} & \text{ on } \Gamma_\mathrm{N} & \text{ Neumann BC}\\
\end{aligned}
$$

with the material parameters $E,\nu$ -- the Youngs modulus and Poisson ratio. The traction $\boldsymbol t$ is the Cauchy stress tensor multiplied by the normal vector on the boundary $\boldsymbol \sigma \cdot \boldsymbol n$. Prescribing a value $\tilde{\boldsymbol t}$ on a subset of the boundary $\partial\Omega$ is referred to as a Neumann boundary condition in computational mechanics. In this specific example, 

$$
\tilde{\boldsymbol t} =\boldsymbol\sigma_\mathrm{analytical} \cdot \boldsymbol{n}.
$$

## Weak formulation and numerical solution

In the weak formulation of the problem, we want to find $\boldsymbol u$ such that

$$
B(\boldsymbol u,\boldsymbol v) = f(\boldsymbol{v}) \quad \forall \boldsymbol v 
$$

with a test function $\boldsymbol{v}$ and 

$$
\begin{aligned}
B(\boldsymbol u,\boldsymbol v) &= \int_{\Omega} \boldsymbol\varepsilon(\boldsymbol{v}) : \boldsymbol{\sigma}(\boldsymbol{\varepsilon}(\boldsymbol{u})) \mathrm{d}{\boldsymbol{x}} \\
    f(\boldsymbol v)&=\int_{\Gamma_{\mathrm{N}}} {\boldsymbol{t}}\cdot\boldsymbol{v}\mathrm{d}{\boldsymbol{s}}.
\end{aligned}
$$


In order to solve the weak formulation, the finite-element method (FEM) can be used. This method discretizes the domain $\Omega$ into so called finite elements that can for example be triangles or quadrilaterals in 2D. On these elements, ansatz functions are defined such that they are continous on the boundaries between elements. These functions form a basis for the solution space for an approximate solution $\boldsymbol{u}_h$ of the problem.

## Comparison of approximate solution with analytical solution

The approxiamte solution and the analytical solution can be compared with the $L_2$ norm which is defined as

$$
\Vert \boldsymbol{u}\Vert_{L_2} = \sqrt{\int_\Omega \Vert\boldsymbol{u}(\boldsymbol{x})\Vert_2^2 \mathrm d \boldsymbol x}
$$

and the error in the $L_2$ norm

$$
e_{L_2} = \Vert \boldsymbol{u}-\boldsymbol{u}_h\Vert_{L_2}.
$$

Alternatively, the sup norm can be used which is defined as

$$
\Vert \boldsymbol{u}\Vert_{\inf} = \sup_{\boldsymbol x} \Vert \boldsymbol{u}(\boldsymbol{x}) \Vert
$$

and the error in the sup norm

$$
e_{\inf} = \Vert \boldsymbol{u}-\boldsymbol{u}_h\Vert_{\inf}.
$$


With these metrices, we can perform a convergence analysis for different approximations $\boldsymbol{u}_h$ which differ in the element size $h$. Plotting the error over the used element-size in a log-log plot lets us determine the convergence order of the approximation.

## Table of parameters

| Parameter    | Description                     |
| ------------ | ------------------------------  |
| $a$[m]   | Radius of the hole.             |
| $l$[m]   | Length of the benchmark domain. |
| $E$[Pa]  | Youngs modulus.                 |
| $\nu$[-]  | Poisson ratio.                  |
| $p$[Pa]  | Load at infinity.               |

