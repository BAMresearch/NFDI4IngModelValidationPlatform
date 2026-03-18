import json
import argparse
from pathlib import Path

def generate_grid_files(grid_template_path, grid_dir, base_cells0, base_cells1, num_files):
    """
    Generates standalone grid JSON files and returns data for merging.
    """
    # Ensure the output directory exists
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
        
        # Write individual grid JSON files to grid_dir
        grid_file_path = grid_dir / f"grid_{config_id}.json"
        with open(grid_file_path, "w") as f:
            json.dump(current_grid, f, indent=4)
        
        generated_configs.append((config_id, current_grid))
        print(f"Generated Grid JSON: {grid_file_path}")
        
    return generated_configs
            
def dict_to_dumux_format(data):
    """
    Converts a nested dictionary into DuMuX .input format.
    Handles underscore-to-dot conversion for sections and recursive nesting.
    """
    lines = []

    def process_section(section_name, content):
        # Convert underscores to dots for DuMuX section naming convention
        formatted_section = section_name.replace("_", ".")
        lines.append(f"[{formatted_section}]")
        
        sub_sections = {}
        
        for key, value in content.items():
            if isinstance(value, dict):
                # Store nested dicts to process as [Section.SubSection] later
                sub_sections[f"{formatted_section}.{key}"] = value
            else:
                # Format values (handle lists as space-separated, bools as lowercase)
                if isinstance(value, list):
                    val_str = " ".join(map(str, value))
                elif isinstance(value, bool):
                    val_str = str(value).lower()
                else:
                    val_str = str(value)
                lines.append(f"{key} = {val_str}")
        
        lines.append("") # Newline after section
        
        # Recursively process nested dictionaries
        for sub_name, sub_content in sub_sections.items():
            process_section(sub_name, sub_content)

    for section, params in data.items():
        process_section(section, params)
        
    return "\n".join(lines)

def write_dumux_inputs(grid_template, dumux_template, grid_out, input_out):
    # Configuration constants
    problem_name_base = "/dumux/shared/dumux/test_rotatingcylinders"
    base_cells0, base_cells1 = 10, 80
    num_files = 3

    # 1. Load the dumux Template
    if not dumux_template.exists():
        print(f"Error: dumux template not found at {dumux_template}")
        return

    with open(dumux_template, "r") as f:
        dumux_config = json.load(f)

    # 2. Get Grid Data and generate grid files
    grid_configs = generate_grid_files(grid_template, grid_out, base_cells0, base_cells1, num_files)

    # 3. Merge and Generate .input files
    input_out.mkdir(parents=True, exist_ok=True)
    for config_id, grid_data in grid_configs:
        full_config = json.loads(json.dumps(dumux_config))
        full_config["Problem"]["Name"] = f"{problem_name_base}_{config_id}"
        full_config.update(grid_data)

        dumux_content = dict_to_dumux_format(full_config)
        input_filename = input_out / f"params_{config_id}.input"
        
        with open(input_filename, "w") as f:
            f.write(dumux_content)
        
        print(f"Generated DuMuX Input: {input_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate DuMuX input files from JSON templates.")
    
    # Define arguments
    parser.add_argument("--grid_template", type=str, required=True, help="Path to grid_template.json")
    parser.add_argument("--dumux_template", type=str, required=True, help="Path to dumux_config.json")
    parser.add_argument("--grid_dir", type=str, default="./dumux/grid_files", help="Output directory for grid JSONs")
    parser.add_argument("--input_dir", type=str, default="./dumux/input_files", help="Output directory for .input files")

    args = parser.parse_args()

    # Execute with absolute paths
    write_dumux_inputs(
        grid_template=Path(args.grid_template).resolve(),
        dumux_template=Path(args.dumux_template).resolve(),
        grid_out=Path(args.grid_dir).resolve(),
        input_out=Path(args.input_dir).resolve()
    )