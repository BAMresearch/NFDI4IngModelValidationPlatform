import json
import zipfile
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Setup paths
root_dir = Path(__file__).resolve().parent
results_base_dir = root_dir / "rotating-cylinders" / "results"

data = []

if not results_base_dir.exists():
    print(f"Error: Base directory {results_base_dir} does not exist.")
    exit(1)

# Iterate through every configuration folder
for conf_dir in results_base_dir.iterdir():
    if conf_dir.is_dir():
        zip_path = conf_dir / "test_rotatingcylinders.zip"
        
        # 1. Extraction: Unzip everything in the folder
        if zip_path.exists():
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(conf_dir)
                print(f"Extracted zip for: {conf_dir.name}")
            except zipfile.BadZipFile:
                print(f"Error: {zip_path.name} is corrupt.")
        
        # 2. Data Collection: Look for the newly extracted JSON
        metrics_path = conf_dir / "solution_metrics.json"
        if metrics_path.exists():
            try:
                with open(metrics_path, 'r') as f:
                    metrics = json.load(f)
                
                data.append({
                    "conf": conf_dir.name,
                    # "pressure_error": metrics.get("l2_error_pressure_rel"),
                    "velocity_error": metrics.get("l2_error_velocity_rel")
                })
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading metrics in {conf_dir.name}: {e}")

# 3. Processing and Plotting
if not data:
    print("No metrics found. Ensure the zip files contain solution_metrics.json.")
    exit(1)

df = pd.DataFrame(data)

# Sort numerically if folder names are numbers, otherwise alphabetical
try:
    df['conf_sort'] = pd.to_numeric(df['conf'])
    df = df.sort_values('conf_sort')
except ValueError:
    df = df.sort_values('conf')

plt.figure(figsize=(10, 6))
# plt.plot(df['conf'], df['pressure_error'], marker='o', label='$L^2$ Rel. Pressure Error')
plt.plot(df['conf'], df['velocity_error'], marker='s', label='Relative $L^2$ Error for Velocity')

plt.yscale('log')
plt.xlabel('Configuration')
plt.ylabel('Relative Error')
plt.title('Convergence Summary')
plt.legend()
plt.grid(True, which="both", ls="-", alpha=0.3)
plt.xticks(rotation=45)
plt.tight_layout()

# 4. Save the plot specifically into the results directory
plot_output = results_base_dir / "solution_metrics_plot.png"
plt.savefig(plot_output)

print(f"\nSummary plot saved to: {plot_output}")