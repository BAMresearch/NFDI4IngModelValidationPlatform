import os
import argparse
from rdflib import Graph
import matplotlib.pyplot as plt
from collections import defaultdict

def load_graphs(base_dir):
    """
    Walk through the base_dir and load all JSON-LD files into rdflib Graphs.
    """
    graph_list = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".jsonld"):
                file_path = os.path.join(root, file)
                try:
                    g = Graph()
                    g.parse(file_path, format='json-ld')
                    graph_list.append(g)
                    print(f"✅ Parsed: {file_path}")
                except Exception as e:
                    print(f"❌ Failed to parse {file_path}: {e}")
    print(f"\nTotal graphs loaded: {len(graph_list)}")
    return graph_list


def query_and_build_table(graph_list):
    """
    Run SPARQL query on graphs and build a table.
    Returns headers and table_data.
    """
    query = """
    PREFIX cr: <http://mlcommons.org/croissant/>
    PREFIX sio: <http://semanticscience.org/resource/>

    SELECT DISTINCT  ?value_element_size  ?value_max_von_mises_stress_gauss_points ?tool_name
    WHERE {
      ?processing_step_child m4i:investigates ?max_von_mises_stress_gauss_points ;
            m4i:hasParameter ?element_size ;
            m4i:hasParameter ?element_order ;
            m4i:hasParameter ?element_degree ;
            schema:isPartOf ?processing_step_parent .
    
      ?max_von_mises_stress_gauss_points a schema:PropertyValue ;
            rdfs:label "max_von_mises_stress_nodes" ;
            schema:value ?value_max_von_mises_stress_gauss_points .
            
      ?element_order a schema:PropertyValue ;
            rdfs:label "element_order" ;
            schema:value 1 .

      ?element_degree a schema:PropertyValue ;
            rdfs:label "element_degree" ;
            schema:value 1 .      

      ?element_size a schema:PropertyValue ;
            rdfs:label "element_size" ;
            schema:value ?value_element_size .
    
      ?processing_step_parent a schema:Action ;
            schema:object ?mesh_file .
    
      ?processing_step_mesh a schema:Action ;
            schema:result ?mesh_file ;
            schema:instrument ?tool .

      ?tool a schema:SoftwareApplication ;
            rdfs:label ?tool_name .
    }
    """

    headers = [
        "element-size",
        "max-mises-stress",
        "Tool Name"
    ]

    table_data = []

    for g in graph_list:
        results = g.query(query)
        for row in results:
            value_element_size = row.value_element_size
            value_max_von_mises_stress_gauss_points = row.value_max_von_mises_stress_gauss_points
            tool_name = row.tool_name
            table_data.append(
                [
                    value_element_size,
                    value_max_von_mises_stress_gauss_points,
                    tool_name,
                ]
            )

    # Sort by element-size
    sort_key = headers.index("element-size")
    table_data.sort(key=lambda x: x[sort_key])

    return headers, table_data


def plot_element_size_vs_stress(headers, table_data, output_file="element_size_vs_stress.pdf"):
    """Plots element-size vs max-mises-stress grouped by tool and saves as PDF."""

    idx_element_size = headers.index("element-size")
    idx_stress = headers.index("max-mises-stress")
    idx_tool = headers.index("Tool Name")

    grouped_data = defaultdict(list)
    x_tick_set = set()

    for row in table_data:
        tool = row[idx_tool]
        x = float(row[idx_element_size])
        y = float(row[idx_stress])
        grouped_data[tool].append((x, y))
        x_tick_set.add(x)

    # Sort x-tick labels
    x_ticks = sorted(x_tick_set)

    plt.figure(figsize=(12, 5))
    for tool, values in grouped_data.items():
        values.sort()
        x_vals, y_vals = zip(*values)
        plt.plot(x_vals, y_vals, marker='o', linestyle='-', label=tool)

    plt.xlabel("element-size")
    plt.ylabel("max-mises-stress")
    plt.title("element-size vs max-mises-stress by Tool\n(element-order = 1 , element-degree = 1)")
    plt.legend(title="Tool Name")
    plt.grid(True)

    # Use logarithmic scale for x-axis
    plt.xscale('log')

    # Set x-ticks to show original values
    plt.xticks(ticks=x_ticks, labels=[str(x) for x in x_ticks], rotation=45)
    plt.tight_layout()
    
    # Save to PDF instead of showing
    plt.savefig(output_file)
    print(f"Plot saved as {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process JSON-LD artifacts and display simulation results.")
    parser.add_argument("artifact_folder", type=str, help="Path to the folder containing unzipped artifacts")
    args = parser.parse_args()

    graphs = load_graphs(args.artifact_folder)
    headers, table_data = query_and_build_table(graphs)
    plot_element_size_vs_stress(headers, table_data, output_file="element_size_vs_stress.pdf")