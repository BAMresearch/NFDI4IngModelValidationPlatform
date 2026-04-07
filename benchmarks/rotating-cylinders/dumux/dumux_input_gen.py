import json
import argparse
from pathlib import Path

def generate_grid_files(grid_template_path, grid_dir, base_cells0, base_cells1, num_files, prob_data):
    grid_dir.mkdir(parents=True, exist_ok=True)

    if not grid_template_path.exists():
        print(f"Error: {grid_template_path} not found.")
        return []

    with open(grid_template_path, "r") as f:
        grid_template = json.load(f)

    # Extract geometry from problem file
    r_in = prob_data["geometry"]["radius_inner"]
    r_out = prob_data["geometry"]["radius_outer"]
    r_mid = (r_in + r_out) / 2.0
    ang = prob_data["geometry"]["angle_range"]

    generated_configs = []

    for i in range(num_files):
        scale = 2 ** i
        c0 = base_cells0 * scale
        c1 = base_cells1 * scale
        config_id = f"{c0}_{c1}"
        
        current_grid = json.loads(json.dumps(grid_template))
        
        # Inject tool-specific resolution
        current_grid["Grid"]["Cells0"] = f"{c0} {c0}"
        current_grid["Grid"]["Cells1"] = c1
        
        # Inject problem-specific geometry
        current_grid["Grid"]["Radial0"] = f"{r_in} {r_mid} {r_out}"
        current_grid["Grid"]["Angular1"] = f"{ang[0]}.0 {ang[1]}.0"
        
        grid_file_path = grid_dir / f"grid_{config_id}.json"
        with open(grid_file_path, "w") as f:
            json.dump(current_grid, f, indent=4)
        
        generated_configs.append((config_id, current_grid))
        print(f"Generated Grid JSON: {grid_file_path}")
        
    return generated_configs


def write_dumux_inputs_json(grid_template, dumux_template, grid_out, input_out, prob_path):
    problem_name_base = "/dumux/shared/dumux/test_rotatingcylinders"
    base_cells0, base_cells1 = 10, 80
    num_files = 3

    # 1. Load Problem Specific Params (from parent/current folder)
    if not prob_path.exists():
        print(f"Error: problem file not found at {prob_path}")
        return

    with open(prob_path, "r") as f:
        prob_data = json.load(f)

    # 2. Load Tool Template
    if not dumux_template.exists():
        print(f"Error: dumux template not found at {dumux_template}")
        return

    with open(dumux_template, "r") as f:
        dumux_config = json.load(f)

    # 3. Generate Grids (Injected with problem geometry)
    grid_configs = generate_grid_files(
        grid_template, grid_out, base_cells0, base_cells1, num_files, prob_data
    )

    input_out.mkdir(parents=True, exist_ok=True)

    # 4. Generate Final Params
    for config_id, grid_data in grid_configs:
        full_config = json.loads(json.dumps(dumux_config))

        # Merge problem-specific physics and identity
        if "Problem" not in full_config: full_config["Problem"] = {}
        full_config["Problem"]["Name"] = f"{problem_name_base}_{config_id}"
        full_config["Problem"]["Omega1"] = prob_data["physics"]["omega_inner"]
        full_config["Problem"]["Omega2"] = prob_data["physics"]["omega_outer"]

        # Merge fluid properties
        full_config["Component"] = {
            "LiquidDensity": prob_data["physics"]["LiquidDensity"],
            "LiquidDynamicViscosity": prob_data["physics"]["LiquidDynamicViscosity"]
        }

        # Merge grid data
        full_config.update(grid_data)

        output_file = input_out / f"params_{config_id}.json"
        with open(output_file, "w") as f:
            json.dump(full_config, f, indent=4)

        print(f"Generated JSON Input: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate DuMuX JSON input files.")

    parser.add_argument("--grid_template", type=str,  default="./dumux/grid_files/grid_template.json")
    parser.add_argument("--dumux_template", type=str, default="./dumux/dumux_input_files/dumux_config.json")
    parser.add_argument("--grid_dir", type=str, default="./dumux/grid_files")
    parser.add_argument("--input_dir", type=str, default="./dumux/dumux_input_files")

    args = parser.parse_args()

    # Locate problem file in the same directory as this script
    script_dir = Path(__file__).parent.parent.resolve()
    problem_file = script_dir / "param_rot_cylin.json"

    write_dumux_inputs_json(
        grid_template=Path(args.grid_template).resolve(),
        dumux_template=Path(args.dumux_template).resolve(),
        grid_out=Path(args.grid_dir).resolve(),
        input_out=Path(args.input_dir).resolve(),
        prob_path=problem_file
    )