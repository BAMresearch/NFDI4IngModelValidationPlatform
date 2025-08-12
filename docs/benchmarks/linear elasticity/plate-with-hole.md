# Infinite linear elastic plate with hole

We consider the case of an infinite plate with a circular hole in the center. The plate is subjected to uniform tensile load $p$ at infinity. The analytical solution for the stress field has been derived by Kirsch in 1898 [@Kirsch1898].
<!-- include an svg picture here-->
![Infinite linear elastic plate with hole](plate-with-hole.svg)

The solution is given in polar coordinates. Assume that the infinite plate is loaded in $x$-direction with load $p$, then at
a point  with polar coordinates $(r,\theta)\in\mathbb R_+ \times \mathbb R$, the polar stress components are given by

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
\boldsymbol\sigma_\mathrm{analytical} (r,\theta)= \begin{bmatrix} \sigma_{xx} & \sigma_{xy}\\ \sigma_{xy} & \sigma_{yy} \end{bmatrix}.
$$

or for a cartesion point $(x,y)$:

$$
\boldsymbol\sigma_\mathrm{analytical} (x,y)=\boldsymbol\sigma_\mathrm{analytical} \left(\sqrt{x^2 + y^2},\arccos\frac{x}{\sqrt{x^2+y^2}}\right) 
$$

In order to transform this into a practical benchmark, we consider a rectangular subdomain
of the infinite plate around the hole. The boundary conditions of the subdomain are determined
from the analytical solution. The example is further reduced by only simulating one quarter
of the rectangular domain and assuming symmetry conditions at the edges. Let $\Omega =[0,l]^2 \setminus \left \lbrace (x,y) \mid \sqrt{x^2+y^2}<a \right \rbrace$ be the domain of the benchmark example, then the PDE is given by

$$
    \begin{aligned}
\mathrm{div}\boldsymbol{\sigma}(\boldsymbol{\varepsilon}(\boldsymbol{u})) &= 0 &\quad \text{ on } \Omega & \\
\boldsymbol{\varepsilon}(\boldsymbol u) &= \frac{1}{2}\left(\nabla \boldsymbol u + (\nabla\boldsymbol u)^\top\right) &&\text{Infinitesimal strain}\\
\boldsymbol{\sigma}(\boldsymbol{\varepsilon}) &= \frac{E}{1-\nu^2}\left((1-\nu)\boldsymbol{\varepsilon} + \nu \mathrm{tr}\boldsymbol{\varepsilon}\boldsymbol I_2\right) && \text{Plane stress law}\\
\boldsymbol u_y &=0 & \text{ on } \lbrace (x,y)\in \partial\Omega | y=0\rbrace& \text{ Dirichlet BC}\\
\boldsymbol u_x &=0 & \text{ on } \lbrace (x,y)\in \partial\Omega | x=0\rbrace& \text{ Dirichlet BC}\\
\boldsymbol t &= \boldsymbol{\sigma}_\mathrm{analytical} \cdot \boldsymbol n&\text{ on }\lbrace (x,y)\in \partial\Omega | x=l \lor y=l \rbrace& \text{ Neumann BC}
\end{aligned}
$$

The weak form is

$$
\int_{\Omega} \boldsymbol\varepsilon(\delta\boldsymbol{u}) : \boldsymbol{\sigma} \mathrm{d}{\boldsymbol{x}} =
    \int_{\Gamma_{\mathrm{N}}} {\boldsymbol{t}}\cdot\delta\boldsymbol{u}\mathrm{d}{\boldsymbol{s}}
$$

with a test function $\delta \boldsymbol u$ 