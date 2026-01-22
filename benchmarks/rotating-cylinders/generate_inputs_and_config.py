import json
from pathlib import Path

# Paths
TEMPLATE_FILE = "params.template"
JSON_OUTPUT_FILE = "rotating-cylinders_config.json"

def generate_input(cells0, cells1, problem_name, output_file, output_file_name):
    template = Path(TEMPLATE_FILE).read_text()
    content = template.format(
        cells0_x=cells0,
        cells0_y=cells0,
        cells1=cells1,
        problem_name=problem_name
    )
    # Ensure the parent directory exists
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    # Write file
    Path(output_file).write_text(content)
    print(f"Written: {output_file_name}")

if __name__ == "__main__":
    base_cells0 = 10
    base_cells1 = 80
    num_files = 3
    name_prefix = "/dumux/shared/dumux/test_rotatingcylinders"

    # Lists to collect JSON entries
    configurations = []
    configuration_to_parameter_file = {}
    configuration_to_solution_vtu_files = {}

    for i in range(num_files):
        cells0 = base_cells0 * (2 ** i)
        cells1 = base_cells1 * (2 ** i)
        config_name = f"{cells0}_{cells1}"
        problem_name = f"{name_prefix}_{cells0}_{cells1}"
        input_file_name = f"params_{cells0}_{cells1}.input"
        input_file = f"./dumux/input_files/{input_file_name}"

        # Generate input file
        generate_input(cells0, cells1, problem_name, input_file, input_file_name)

        # Update JSON lists/dicts
        configurations.append(config_name)
        configuration_to_parameter_file[config_name] = input_file_name
        configuration_to_solution_vtu_files[config_name] = [
            f"dumux/test_rotatingcylinders_{cells0}_{cells1}-00000.vtu",
            f"dumux/test_rotatingcylinders_{cells0}_{cells1}-00001.vtu"
        ]

    # Read template
template_path = Path("config_template.json")
benchmark_json = json.loads(template_path.read_text())

# Update only the dynamic parts
benchmark_json["configurations"] = configurations
benchmark_json["configuration_to_parameter_file"] = configuration_to_parameter_file
benchmark_json["configuration_to_solution_vtu_files"] = configuration_to_solution_vtu_files

# Write final JSON
with open(JSON_OUTPUT_FILE, "w") as f:
    json.dump(benchmark_json, f, indent=4)
print(f"Benchmark JSON written to {JSON_OUTPUT_FILE}")
