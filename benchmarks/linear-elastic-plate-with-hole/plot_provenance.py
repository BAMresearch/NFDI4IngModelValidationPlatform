import argparse
import sys
from pathlib import Path
from generate_config import workflow_config
import json
import os
import pandas as pd
import numpy as np


def parse_args():
    """
    Parse command-line arguments for the provenance processing script.

    Returns:
        argparse.Namespace: Parsed arguments containing:
            - provenance_folderpath: Path to the folder with RO-Crate data
            - provenance_filename: Name of the RO-Crate metadata file
            - output_file: Path for the final visualization output
    """
    parser = argparse.ArgumentParser(
        description="Process ro-crate-metadata.json artifacts and display simulation results."
    )
    parser.add_argument(
        "--provenance_folderpath",
        type=str,
        required=True,
        help="Path to the folder containing provenance data",
    )
    parser.add_argument(
        "--provenance_filename",
        type=str,
        default="ro-crate-metadata.json",
        help="File name for the provenance graph",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        required=True,
        help="Final visualization file",
    )
    return parser.parse_args()


def sparql_result_to_dataframe(results):
    """
    Convert SPARQL query results into a pandas DataFrame.

    Extracts variable bindings from each result row using asdict() and converts
    RDF values to Python native types using toPython().

    Args:
        results (rdflib.plugins.sparql.processor.SPARQLResult): SPARQL query results
                                                                from rdflib.

    Returns:
        pd.DataFrame: DataFrame where each row represents a query result and columns
                     correspond to SPARQL variables.
    """
    rows = []

    for row in results:
        row_dict = {k: v.toPython() for k, v in row.asdict().items()}
        rows.append(row_dict)

    return pd.DataFrame(rows)


def apply_custom_filters(data: pd.DataFrame) -> pd.DataFrame:
    """
    Filter provenance data to include only first-order linear elements.

    Filters rows where element_degree = 1 and element_order = 1, then removes
    these filtering columns from the result.

    Args:
        data (pd.DataFrame): Input DataFrame containing element_degree and
                            element_order columns.

    Returns:
        pd.DataFrame: Filtered DataFrame with element_degree and element_order
                     columns removed and index reset.
    """
    filtered_df = data[(data["element_degree"] == 1) & (data["element_order"] == 1)]

    return filtered_df.drop(columns=["element_degree", "element_order"]).reset_index(
        drop=True
    )


def summary_file_to_dataframe(analyzer, summary_path, parameters, metrics):
    """
    Load benchmark data from a summary.json file into a DataFrame.

    Handles both dictionary-style parameter/metric values (with 'value' key) and
    direct scalar values. Converts parameter names from underscore to hyphen format
    for JSON lookup.

    Args:
        summary_path (str): Path to the summary.json file.
        parameters (list): List of parameter names to extract.
        metrics (list): List of metric names to extract.

    Returns:
        pd.DataFrame: DataFrame with columns for each parameter and metric.
    """
    with open(summary_path, "r") as f:
        data = json.load(f)

    records = []
    for entry in data:
        record = {}

        for p in parameters:
            param_value = entry["parameters"][p]
            sanitized_param_name = analyzer.sanitize_variable_name(p)
            if isinstance(param_value, dict):
                record[sanitized_param_name] = param_value.get("value")
            else:
                record[sanitized_param_name] = param_value

        for m in metrics:
            metric_value = entry["metrics"][m]
            sanitized_metric_name = analyzer.sanitize_variable_name(m)
            if isinstance(metric_value, dict):
                record[sanitized_metric_name] = metric_value.get("value")
            else:
                record[sanitized_metric_name] = metric_value

        records.append(record)

    return pd.DataFrame(records)


def compare_dataframes(df1: pd.DataFrame, df2: pd.DataFrame):
    """
    Compare two DataFrames for identical content regardless of row order.

    Sorts both DataFrames by all columns, then checks for equality. If differences
    are found, prints rows that appear in one DataFrame but not the other.

    Args:
        df1 (pd.DataFrame): First DataFrame to compare.
        df2 (pd.DataFrame): Second DataFrame to compare.

    Returns:
        bool: True if DataFrames contain identical data, False otherwise.

    Raises:
        ValueError: If the DataFrames have different columns.

    Prints:
        Rows that are present in one DataFrame but missing in the other,
        when differences are detected.
    """
    cols1 = sorted(df1.columns)
    cols2 = sorted(df2.columns)

    if cols1 != cols2:
        raise ValueError("DataFrames have different columns.")

    df1_sorted = df1[cols1].sort_values(by=cols1).reset_index(drop=True)
    df2_sorted = df2[cols2].sort_values(by=cols2).reset_index(drop=True)

    are_equal = df1_sorted.equals(df2_sorted)

    if are_equal:
        return True

    missing_in_df2 = pd.concat([df1_sorted, df2_sorted, df2_sorted]).drop_duplicates(
        keep=False
    )

    missing_in_df1 = pd.concat([df2_sorted, df1_sorted, df1_sorted]).drop_duplicates(
        keep=False
    )

    print("Rows in df1 but not in df2:")
    print(missing_in_df2 if not missing_in_df2.empty else "None")

    print("\nRows in df2 but not in df1:")
    print(missing_in_df1 if not missing_in_df1.empty else "None")

    return False


def load_and_query_graph(analyzer, parameters, metrics, tools):
    """
    Load the RO-Crate graph and execute a SPARQL query to extract provenance data.

    Args:
        analyzer (ProvenanceAnalyzer): Initialized analyzer instance.
        parameters (list): List of parameter names to query.
        metrics (list): List of metric names to query.
        tools (list): List of tool names to filter by.

    Returns:
        pd.DataFrame: DataFrame containing the query results.

    Raises:
        AssertionError: If the query returns no data.
    """
    graph = analyzer.load_graph_from_file()
    query = analyzer.build_dynamic_query(parameters, metrics, tools)
    results = analyzer.run_query_on_graph(graph, query)

    provenance_df = sparql_result_to_dataframe(results)
    assert len(provenance_df), "No data found for the provenance query."

    return provenance_df


def validate_provenance_data_summary_file(
    analyzer, provenance_df, parameters, metrics, tools, provenance_folderpath
):
    """
    Validate provenance query results against ground truth data from summary.json files.

    For each tool, loads the corresponding summary.json file and compares its data
    against the filtered provenance query results for that tool.

    Args:
        provenance_df (pd.DataFrame): DataFrame containing all provenance query results.
        parameters (list): List of parameter names used in the comparison.
        metrics (list): List of metric names used in the comparison.
        tools (list): List of tool names to validate.
        provenance_folderpath (str): Base path to the provenance folder containing
                                     summary.json files.

    Raises:
        AssertionError: If data mismatch is found between summary.json and provenance
                       data for any tool.
    """
    for tool in tools:
        summary_path = os.path.join(
            provenance_folderpath,
            "snakemake_results",
            "linear-elastic-plate-with-hole",
            tool,
            "summary.json",
        )
        summary_df = summary_file_to_dataframe(
            analyzer, summary_path, parameters, metrics
        )

        filtered_df = provenance_df[
            provenance_df["tool_name"].str.contains(tool, case=False, na=False)
        ].drop(columns=["tool_name"])

        assert compare_dataframes(
            summary_df, filtered_df
        ), f"Data mismatch for tool '{tool}'. See above for details."


def validate_provenance_data_csv_file(analyzer, provenance_df, tools, float_precision=6, tol=1e+6):
    """
    Validate that the provided provenance DataFrame contains all rows from reference CSV files for the given tools.

    The CSV file is treated as the ground truth. It may contain extra columns, but only
    the columns that also exist in the input DataFrame are checked.

    Float values are rounded to avoid minor numerical differences.

    Args:
        analyzer: ProvenanceAnalyzer: Initialized analyzer instance.
        provenance_df (pd.DataFrame): The DataFrame containing provenance data to validate.
        tools (list of str): List of tool names. For each tool, a CSV file `<tool>.csv`
                             must exist in the `tests` folder next to this script.
        float_precision (int, optional): Decimal places for rounding float values.
                                         Defaults to 6.

    Raises:
        AssertionError: If any CSV row (considering only overlapping columns) is missing in `provenance_df`.
    """

    stress_cols = {"max_von_mises_stress_nodes", "max_von_mises_stress_gauss_points"}

    for tool in tools:
        df_subset = provenance_df[
            provenance_df["tool_name"].str.lower().str.startswith(tool.lower())
        ].copy()

        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", f"{tool}.csv")
        df_csv = pd.read_csv(csv_path)

        df_csv.columns = [analyzer.sanitize_variable_name(c) for c in df_csv.columns]

        common_cols = df_csv.columns.intersection(df_subset.columns)
        df_subset = df_subset[common_cols].reset_index(drop=True)
        df_csv = df_csv[common_cols].reset_index(drop=True)

        # Round all floats to avoid minor precision issues
        for col in df_csv.select_dtypes(include=["float", "float64", "float32"]).columns:
            df_csv[col] = df_csv[col].round(float_precision)

        for i, row_csv in df_csv.iterrows():
            best_mismatch = None
            best_mismatch_count = float("inf")
            matched = False

            for j, row_df in df_subset.iterrows():
                mismatches = []

                for col in common_cols:
                    v_csv = row_csv[col]
                    v_df = row_df[col]

                    if pd.api.types.is_numeric_dtype(df_subset[col]):
                        if col in stress_cols:
                            if not np.isclose(v_csv, v_df, atol=tol, rtol=0):
                                mismatches.append((col, v_csv, v_df))
                        else:
                            if v_csv != v_df:
                                mismatches.append((col, v_csv, v_df))
                    else:
                        # Non-numeric columns: exact match
                        if v_csv != v_df:
                            mismatches.append((col, v_csv, v_df))

                if not mismatches:
                    matched = True
                    break

                if len(mismatches) < best_mismatch_count:
                    best_mismatch = j, mismatches
                    best_mismatch_count = len(mismatches)

            if not matched:
                _, mismatches_best = best_mismatch
                for col, v_csv, v_df in mismatches_best:
                    print(f"Column `{col}` → CSV: {v_csv} | DataFrame: {v_df}")

                raise AssertionError(
                    f"\n[{tool}] CSV row {i} not matched in DataFrame within tolerance {tol} "
                    f"on columns {list(common_cols)}:\n{row_csv.to_dict()}"
                )


def plot_results(analyzer, final_df, output_file):
    """
    Generate a visualization plot of the provenance results.

    Creates a scatter/line plot showing the relationship between element size
    and maximum von Mises stress, grouped by tool name.

    Args:
        analyzer (ProvenanceAnalyzer): Initialized analyzer instance.
        final_df (pd.DataFrame): DataFrame containing filtered data to plot.
                                Expected columns: element_size, max_von_mises_stress_nodes,
                                tool_name (in that order).
        output_file (str): Path where the plot image will be saved.
    """
    analyzer.plot_provenance_graph(
        data=final_df.values.tolist(),
        x_axis_label="Element Size",
        y_axis_label="Max Von Mises Stress",
        x_axis_index=0,
        y_axis_index=1,
        group_by_index=2,
        title="Element Size vs Max Von Mises Stress",
        output_file=output_file,
    )


def run(args, parameters, metrics, tools):
    """
    Execute the complete provenance analysis workflow.

    Performs the following steps:
    1. Initialize the ProvenanceAnalyzer
    2. Load and query the provenance graph
    3. Validate query results against summary.json ground truth data
    4. Apply custom filters to the data
    5. Generate visualization plot

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
        parameters (list): List of parameter names to extract.
        metrics (list): List of metric names to extract.
        tools (list): List of tool names to process.
    """
    root_dir = Path(__file__).parent.parent.parent

    sys.path.insert(0, str(root_dir))
    from benchmarks.common.provenance import ProvenanceAnalyzer

    analyzer = ProvenanceAnalyzer(
        provenance_folderpath=args.provenance_folderpath,
        provenance_filename=args.provenance_filename,
    )

    provenance_df = load_and_query_graph(analyzer, parameters, metrics, tools)

    validate_provenance_data_summary_file(
        analyzer, provenance_df, parameters, metrics, tools, args.provenance_folderpath
    )

    validate_provenance_data_csv_file(analyzer, provenance_df, tools)

    final_df = apply_custom_filters(provenance_df)

    plot_results(analyzer, final_df, args.output_file)


def main():
    """
    Main entry point for the provenance analysis script.

    Parses command-line arguments, defines the parameters and metrics to extract,
    retrieves tool names from the workflow configuration, and executes the analysis
    workflow.
    """
    args = parse_args()

    parameters = ["element-size", "element-order", "element-degree"]
    metrics = ["max_von_mises_stress_nodes"]
    tools = workflow_config["tools"]

    run(args, parameters, metrics, tools)


if __name__ == "__main__":
    main()
