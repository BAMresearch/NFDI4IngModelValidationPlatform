import json

from analytical_solution import AnalyticalSolution

with open("parameters.json", "r", encoding="utf-8") as file:
    parameters = json.load(file)

assert parameters["young-modulus"]["unit"] == "Pa"
assert parameters["poisson-ratio"]["unit"] == ""
assert parameters["radius"]["unit"] == "m"
assert parameters["length"]["unit"] == "m"
assert parameters["load"]["unit"] == "MPa"

E = parameters["young-modulus"]["value"]
nu = parameters["poisson-ratio"]["value"]
R = parameters["radius"]["value"]
L = parameters["length"]["value"]
load = parameters["load"]["value"] * 1e6 # convert to Pa

solutionSymbolic = AnalyticalSolution(E, nu, R, L, load)

def replaceMathFunctions(expression):
    expression = expression.replace("sqrt", "np.sqrt")
    expression = expression.replace("sin", "np.sin")
    expression = expression.replace("cos", "np.cos")
    expression = expression.replace("atan2", "np.atan2")
    return expression

with open("boundaryFields.inp", "w+") as f:
    f.write("*analyticalField, name=ux, type=scalarExpression" + "\n")
    expression = solutionSymbolic.displacement_symbolic_str("x", "y")[0]
    expression = replaceMathFunctions(expression)
    f.write(
        '"f(x,y,z)"="' + expression + '"\n'
    )
    f.write("*analyticalField, name=uy, type=scalarExpression" + "\n")
    expression = solutionSymbolic.displacement_symbolic_str("x", "y")[1]
    expression = replaceMathFunctions(expression)
    f.write(
        '"f(x,y,z)"="' + expression + '"\n'
    )
