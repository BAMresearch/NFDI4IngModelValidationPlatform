from argparse import ArgumentParser
import json

def create_summary(configurations: list[str],
                   parameter_files: list[str],
                   mesh_files: list[str],
                   solution_metrics: list[str],
                   solution_field_data: list[str],
                   benchmark: str,
                   summary_json: str) -> None:
    
    all_summaries = []
    for idx, config in enumerate(configurations):
        print(idx, config)
        summary = {}
        summary["benchmark"] = benchmark
        print(solution_metrics[idx])
        with open(parameter_files[idx], "r") as param_file:
            summary["parameters"] = json.load(param_file)
        summary["mesh"] = f"{config}/mesh"
        with open(solution_metrics[idx], "r") as metrics_file:
            summary["metrics"] = json.load(metrics_file)
        summary["configuration"] = config
        all_summaries.append(summary)
    with open(summary_json, "w") as f:
        json.dump(all_summaries, f, indent=4)
        

if __name__ == "__main__":
    parser = ArgumentParser(
        description="Generate summary statistics for simulation runs over different configurations.\n"
        "Inputs: --configuration, --input_parameter_file, --input_mesh_file, --input_solution_metrics, --input_solution_field_data, --input_benchmark, --input_tool\n"
        "Outputs: --output_summary_json,"
    )
    parser.add_argument("--input_configuration", nargs="+", type=str, required=True, help="Configuration names (input)")
    parser.add_argument("--input_parameter_file", nargs="+", type=str, required=True, help="Path to the JSON file containing simulation parameters (input)")
    parser.add_argument("--input_mesh_file", nargs="+", type=str, required=True, help="Path to the mesh file (input)")
    parser.add_argument("--input_solution_metrics", nargs="+", type=str, required=True, help="Path to the metrics JSON file (input)")
    parser.add_argument("--input_solution_field_data", nargs="+", type=str, required=True, help="Path to the zipped solution files (input)")
    parser.add_argument("--input_benchmark", required=True, type=str, help="Name of the benchmark (input)")
    parser.add_argument("--output_summary_json", required=True, type=str, help="Path to the summary JSON file (output)")
    args = parser.parse_args()
    create_summary(
        args.input_configuration,
        args.input_parameter_file,
        args.input_mesh_file,
        args.input_solution_metrics,
        args.input_solution_field_data,
        args.input_benchmark,
        args.output_summary_json
    )
