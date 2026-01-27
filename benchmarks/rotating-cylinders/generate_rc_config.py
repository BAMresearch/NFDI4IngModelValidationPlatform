import json
from pathlib import Path

def write_benchmark_config():
    base_cells0, base_cells1 = 10, 80
    num_files = 3
    
    configurations = []
    config_to_param = {}
    config_to_vtu = {}

    for i in range(num_files):
        cells0 = base_cells0 * (2 ** i)
        cells1 = base_cells1 * (2 ** i)
        config_name = f"{cells0}_{cells1}"
        
        configurations.append(config_name)
        config_to_param[config_name] = f"params_{config_name}.input"
        config_to_vtu[config_name] = [
            f"dumux/test_rotatingcylinders_{config_name}-00000.vtu",
            f"dumux/test_rotatingcylinders_{config_name}-00001.vtu"
        ]

    # Your hardcoded dictionary
    benchmark_json = {
        "benchmark": "rotating-cylinders",
        "benchmark_uri": "https://www.openfoam.com/documentation/guides/latest/doc/verification-validation-rotating-cylinders-2d.html",
        "tools": ["dumux"],
        "configurations": configurations,
        "configuration_to_parameter_file": config_to_param,
        "configuration_to_solution_vtu_files": config_to_vtu,
        "container_image": "git.iws.uni-stuttgart.de:4567/benchmarks/rotating-cylinders:3.0"
    }

    with open("rotating-cylinders_config.json", "w") as f:
        json.dump(benchmark_json, f, indent=4)
    print("rotating-cylinders_config.json generated.")

if __name__ == "__main__":
    write_benchmark_config()