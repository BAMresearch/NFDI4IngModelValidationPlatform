# Infinite linear elastic plate with hole

We consider the case of an infinite plate with a circular hole in the center. The plate is subjected to uniform tensile load at infinity. The analytical solution for the stress field has been derived by Kirsch in 1898 [@Kirsch1898].
<!-- include an svg picture here-->
![Infinite linear elastic plate with hole](plate-with-hole.svg)

The solution is given in polar coordinates. Assume that the infinite plate is loaded in $x$-direction, then at
a point  with polar coordinates $(r,\theta)\in\mathbb R_+ \times \mathbb R$, the polar stress components are given by

\[
    \begin{aligned}
        \sigma_r &= \frac{p}{2}\left(1-\frac{a^2}{r^2}\right)+\frac{p}{2}\left(1-\frac{a^2}{r^2}\right)\left(1-\frac{3a^2}{r^2}\right)\cos(2\theta)\\
        \sigma_\theta &=\frac{p}{2}\left(1+\frac{a^2}{r^2}\right) - \frac{p}{2}\left(1+\frac{3a^4}{r^4}\right)\cos(2\theta)\\
        \sigma_{r\theta} &= -\frac{p}{2}\left(1-\frac{a^2}{r^2}\right)\left(1+\frac{3a^2}{r^2}\right)\sin(2\theta)
    \end{aligned}
\]
In order to transform this into a practical benchmark, we consider a rectangular subdomain
of the infinite plate around the hole. The boundary conditions of the subdomain are determined
from the analytical solution. The example is further reduced by only simulating one quarter
of the rectangular domain and assuming symmetry conditions at the edges. Let $\Omega =[0,l]^2 \setminus\left\{(x,y) \mid \sqrt{x^2+y^2}<a \right\}$ be the domain of the benchmark example, then the PDE is given by

\[
    \begin{aligned}
\mathrm{div}\boldsymbol{\sigma}(\boldsymbol{\varepsilon}(\boldsymbol{u})) &= 0 &\quad \boldsymbol u \in \Omega & \\
\boldsymbol{\varepsilon}(\boldsymbol u) &= \frac{1}{2}\left(\nabla \boldsymbol u + (\nabla\boldsymbol u)^\top\right) &&\text{Infinitesimal strain}\\
\boldsymbol{\sigma}(\boldsymbol{\varepsilon}) &= \frac{E}{1-\nu^2}\left((1-\nu)\boldsymbol{\varepsilon} + \nu \mathrm{tr}\boldsymbol{\varepsilon}\boldsymbol I_2\right) && \text{Plane stress law}\\
\boldsymbol u_y &=0 & y=0& \text{Dirichlet BC}\\
\boldsymbol u_x &=0 & x=0& \text{Dirichlet BC}\\
boldsymbol{n}
\end{aligned}
\]