import numpy as np
import sympy as sp

class PlateWithHoleSolution:
    def __init__(self, E: float, nu: float, radius: float, L:float, load:float) -> None:
        self.radius = radius
        self.L = L
        self.load = load
        self.E = E
        self.nu = nu

        # Use symbolic expressions from displacement_symbolic
        # to create fast lambdified functions for numerical evaluation
        ux_sym, uy_sym = self.displacement_symbolic()
        x, y = sp.symbols('x y')
        E, nu, a, T = sp.symbols('E nu a T')
        subs = {
            E: self.E,
            nu: self.nu,
            a: self.radius,
            T: self.load
        }
        ux_expr_num = ux_sym.subs(subs)
        uy_expr_num = uy_sym.subs(subs)
        self.ux_func = sp.lambdify((x, y), ux_expr_num, modules='numpy')
        self.uy_func = sp.lambdify((x, y), uy_expr_num, modules='numpy')

        # Symbolic stress expressions and lambdify
        sxx_sym, sxy_sym, syy_sym = self.stress_symbolic()
        x, y = sp.symbols('x y')
        E, nu, a, T = sp.symbols('E nu a T')
        subs = {
            E: self.E,
            nu: self.nu,
            a: self.radius,
            T: self.load
        }
        sxx_expr_num = sxx_sym.subs(subs)
        sxy_expr_num = sxy_sym.subs(subs)
        syy_expr_num = syy_sym.subs(subs)
        self.sxx_func = sp.lambdify((x, y), sxx_expr_num, modules='numpy')
        self.sxy_func = sp.lambdify((x, y), sxy_expr_num, modules='numpy')
        self.syy_func = sp.lambdify((x, y), syy_expr_num, modules='numpy')

    def displacement_symbolic(self):
        """
        Returns symbolic expressions for ux and uy in terms of x and y.
        """
        # Define symbols
        x, y = sp.symbols('x y')
        E, nu, a, T = sp.symbols('E nu a T')
        r = sp.sqrt(x**2 + y**2)
        theta = sp.atan2(y, x)
        Ta_8mu = T * a / (4 * E / (1.0 + nu))
        k = (3.0 - nu) / (1.0 + nu)

        ct = sp.cos(theta)
        c3t = sp.cos(3 * theta)
        st = sp.sin(theta)
        s3t = sp.sin(3 * theta)

        fac = 2 * (a / r)**3

        ux = Ta_8mu * (
            r / a * (k + 1.0) * ct + 2.0 * a / r * ((1.0 + k) * ct + c3t) - fac * c3t
        )

        uy = Ta_8mu * (
            (r / a) * (k - 3.0) * st + 2.0 * a / r * ((1.0 - k) * st + s3t) - fac * s3t
        )

        return ux, uy
    
    def stress_symbolic(self):
        """
        Returns symbolic expressions for sxx, sxy, syx, syy in terms of x and y.
        """
        x, y = sp.symbols('x y')
        E, nu, a, T = sp.symbols('E nu a T')
        r = sp.sqrt(x**2 + y**2)
        theta = sp.atan2(y, x)
        cos2t = sp.cos(2 * theta)
        cos4t = sp.cos(4 * theta)
        sin2t = sp.sin(2 * theta)
        sin4t = sp.sin(4 * theta)

        fac1 = (a * a) / (r * r)
        fac2 = 1.5 * fac1 * fac1

        sxx = T - T * fac1 * (1.5 * cos2t + cos4t) + T * fac2 * cos4t
        syy = -T * fac1 * (0.5 * cos2t - cos4t) - T * fac2 * cos4t
        sxy = -T * fac1 * (0.5 * sin2t + sin4t) + T * fac2 * sin4t

        return sxx, sxy, syy

    def displacement(self, x: np.ndarray) -> np.ndarray:
        """
        Evaluates the symbolic displacement expressions
        Accepts x of shape (2, N) or (3,N) (third dimension is omitted, but some tools always compute in 3D)
        and returns two 1D arrays. 
        The lambda functions are computed from the symbolic representation in the constructor
        """
        arr = np.asarray(x)
        if arr.ndim != 2 or arr.shape[0] not in (2, 3):
            raise ValueError(f"Input x must have shape (2, N) or (3, N), got {arr.shape}")
        # If 3D, ignore the third row
        ux_vals = self.ux_func(arr[0], arr[1])
        uy_vals = self.uy_func(arr[0], arr[1])
        result = ux_vals, uy_vals

        return result

    def displacement_symbolic_str(self, X_str: str, Y_str: str):
        """
        Returns string representations of the symbolic displacement functions
        with variable names x and y being replaced by X_str and Y_str.
        """
        # Get symbolic expressions
        ux, uy = self.displacement_symbolic()
        # Define symbols
        x, y = sp.symbols('x y')
        E, nu, a, T = sp.symbols('E nu a T')
        subs_vars = {x: sp.Symbol(X_str), y: sp.Symbol(Y_str)}
        subs_params = {E: self.E, nu: self.nu, a: self.radius, T: self.load}
        ux_sub = ux.subs(subs_vars).subs(subs_params)
        uy_sub = uy.subs(subs_vars).subs(subs_params)
        # Convert to string using sympy.sstr for single-line output with **
        ux_str = sp.sstr(ux_sub)
        uy_str = sp.sstr(uy_sub)
        return ux_str, uy_str
    
    def stress(self, x: np.ndarray) -> np.ndarray:
        """
        Evaluates the symbolic stress expressions.
        Accepts coordinates x of shape (2, N) or (3, N) (third dimension is omitted).
        Returns three 1D arrays: sxx, sxy, syy.
        """
        arr = np.asarray(x)
        if arr.ndim != 2 or arr.shape[0] not in (2, 3):
            raise ValueError(f"Input x must have shape (2, N) or (3, N), got {arr.shape}")
        sxx = self.sxx_func(arr[0], arr[1])
        sxy = self.sxy_func(arr[0], arr[1])
        syy = self.syy_func(arr[0], arr[1])
        return sxx, sxy, syy
