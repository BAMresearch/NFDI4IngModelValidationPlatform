import json

with open("parameters.json", "r", encoding="utf-8") as file:
    parameters = json.load(file)

with open("./input_template.inp", "r") as infile:
    lines = infile.readlines()


replaceDict = {
    "_E_": parameters["young-modulus"]["value"],
    "_NU_": parameters["poisson-ratio"]["value"],
}

with open("input.inp", "w+") as outfile:
    for line in lines:
        for old, new in replaceDict.items():
            line = line.replace(old,str(new))
        outfile.write(line)
