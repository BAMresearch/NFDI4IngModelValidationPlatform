import json
import argparse
import meshio

def create_dumux_summary(configurations, parameter_files, solution_vtu_files, benchmark, benchmark_uri, summary_json):
    summaries = []
    for cfg, param_file, vtu_file in zip(configurations, parameter_files, solution_vtu_files):
        summary = {
            "benchmark": benchmark,
            "benchmark_uri": benchmark_uri,
            "configuration": cfg
        }
        # Load parameters
        with open(param_file) as f:
            summary["parameters"] = json.load(f)

        summary["solution_vtu"] = vtu_file

        # Extract field summaries
        vtu = meshio.read(vtu_file)
        field_summaries = {}
        for key, data in vtu.point_data.items():
            field_summaries[key] = {
                "min": float(data.min()),
                "max": float(data.max()),
                "mean": float(data.mean())
            }
        summary["solution_fields_summary"] = field_summaries

        summaries.append(summary)

    with open(summary_json, "w") as f:
        json.dump(summaries, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_configuration", nargs="+", required=True)
    parser.add_argument("--input_parameter_file", nargs="+", required=True)
    parser.add_argument("--input_solution_vtu", nargs="+", required=True)
    parser.add_argument("--input_benchmark", required=True)
    parser.add_argument("--input_benchmark_uri", required=True)
    parser.add_argument("--output_summary_json", required=True)
    args = parser.parse_args()

    create_dumux_summary(
        args.input_configuration,
        args.input_parameter_file,
        args.input_solution_vtu,
        args.input_benchmark,
        args.input_benchmark_uri,
        args.output_summary_json
    )
