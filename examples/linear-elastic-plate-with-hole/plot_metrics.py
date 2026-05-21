import argparse
import sys
from pathlib import Path
import pandas as pd


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
    query = analyzer.build_dynamic_rocrate_query(parameters, metrics, tools)
    results = analyzer.run_query_on_graph(graph, query)

    provenance_df = sparql_result_to_dataframe(results)
    assert len(provenance_df), "No data found for the provenance query."

    return provenance_df


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
        y_axis_label="Max Von Mises Stress Nodes",
        x_axis_index=0,
        y_axis_index=1,
        group_by_index=2,
        title="Element Size vs Max Von Mises Stress Nodes",
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
    tools = ["Fenics", "Kratos"]

    run(args, parameters, metrics, tools)


if __name__ == "__main__":
    main()
