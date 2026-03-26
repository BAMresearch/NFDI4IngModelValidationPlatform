import json
import argparse
from pathlib import Path

def generate_grid_files(grid_template_path, grid_dir, base_cells0, base_cells1, num_files):
    grid_dir.mkdir(parents=True, exist_ok=True)

    if not grid_template_path.exists():
        print(f"Error: {grid_template_path} not found.")
        return []

    with open(grid_template_path, "r") as f:
        grid_template = json.load(f)

    generated_configs = []

    for i in range(num_files):
        scale = 2 ** i
        c0 = base_cells0 * scale
        c1 = base_cells1 * scale
        config_id = f"{c0}_{c1}"
        
        current_grid = json.loads(json.dumps(grid_template))
        current_grid["Grid"]["Cells0"] = f"{c0} {c0}"
        current_grid["Grid"]["Cells1"] = c1
        
        grid_file_path = grid_dir / f"grid_{config_id}.json"
        with open(grid_file_path, "w") as f:
            json.dump(current_grid, f, indent=4)
        
        generated_configs.append((config_id, current_grid))
        print(f"Generated Grid JSON: {grid_file_path}")
        
    return generated_configs


def write_dumux_inputs_json(grid_template, dumux_template, grid_out, input_out):
    problem_name_base = "/dumux/shared/dumux/test_rotatingcylinders"
    base_cells0, base_cells1 = 10, 80
    num_files = 3

    if not dumux_template.exists():
        print(f"Error: dumux template not found at {dumux_template}")
        return

    with open(dumux_template, "r") as f:
        dumux_config = json.load(f)

    grid_configs = generate_grid_files(
        grid_template, grid_out, base_cells0, base_cells1, num_files
    )

    input_out.mkdir(parents=True, exist_ok=True)

    for config_id, grid_data in grid_configs:
        full_config = json.loads(json.dumps(dumux_config))

        full_config["Problem"]["Name"] = f"{problem_name_base}_{config_id}"
        full_config.update(grid_data)

        output_file = input_out / f"params_{config_id}.json"

        with open(output_file, "w") as f:
            json.dump(full_config, f, indent=4)

        print(f"Generated JSON Input: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate DuMuX JSON input files from templates."
    )

    parser.add_argument("--grid_template", type=str, required=True)
    parser.add_argument("--dumux_template", type=str, required=True)
    parser.add_argument("--grid_dir", type=str, default="./dumux/grid_files")
    parser.add_argument("--input_dir", type=str, default="./dumux/dumux_input_files")

    args = parser.parse_args()

    write_dumux_inputs_json(
        grid_template=Path(args.grid_template).resolve(),
        dumux_template=Path(args.dumux_template).resolve(),
        grid_out=Path(args.grid_dir).resolve(),
        input_out=Path(args.input_dir).resolve()
    )