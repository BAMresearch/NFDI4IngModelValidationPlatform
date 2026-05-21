import os
from rdflib import Graph
import matplotlib.pyplot as plt
from collections import defaultdict
from typing import List, Tuple
import re
from rocrate_validator import services, models


class ProvenanceAnalyzer:
    """
    A class to analyze, validate, and visualize provenance data from RO-Crate metadata files.

    This class loads RO-Crate JSON-LD files, builds dynamic SPARQL queries to extract
    workflow metadata about methods, parameters, and metrics, and provides visualization
    capabilities. It also validates RO-Crate files against the RO-Crate 1.1 profile.

    Attributes:
        provenance_folderpath (str): The directory path containing the RO-Crate folder.
        provenance_filename (str): The name of the provenance file (default: 'ro-crate-metadata.json').
    """

    def __init__(
        self,
        provenance_folderpath: str = None,
        provenance_filename: str = "ro-crate-metadata.json",
    ):
        """
        Initialize the ProvenanceAnalyzer.

        Args:
            provenance_folderpath (str, optional): Path to the folder containing the RO-Crate.
                                                   Defaults to None.
            provenance_filename (str, optional): Name of the RO-Crate metadata file.
                                                 Defaults to "ro-crate-metadata.json".
        """
        self.provenance_folderpath = provenance_folderpath
        self.provenance_filename = provenance_filename

    def load_graph_from_file(self) -> Graph:
        """
        Loads the RO-Crate metadata file into an rdflib Graph object.

        Returns:
            rdflib.Graph: The loaded RDF graph containing the provenance data.

        Raises:
            Exception: If the file cannot be parsed as JSON-LD.
        """
        try:
            g = Graph()
            # The parse method handles file loading and format parsing
            g.parse(
                os.path.join(self.provenance_folderpath, self.provenance_filename),
                format="json-ld",
            )
            return g
        except Exception as e:
            print(f"Failed to parse {self.provenance_filename}: {e}")
            raise  # Re-raise to ensure error is handled

    def sanitize_variable_name(self, name: str) -> str:
        """
        Convert a string into a valid SPARQL variable name.

        Replaces invalid characters with underscores and ensures the variable
        name doesn't start with a digit.

        Args:
            name (str): The original string to convert.

        Returns:
            str: A sanitized variable name safe for use in SPARQL queries.
        """
        # Replace invalid chars with underscore
        var = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        # Ensure it doesn't start with a digit
        if re.match(r"^\d", var):
            var = "_" + var
        return var

    def _sparql_string_literal(self, value: str) -> str:
        """
        Escape a Python string for safe use as a SPARQL string literal.
        """
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def build_dynamic_rocrate_query(
        self,
        parameters,
        metrics,
        tools=None,
        named_graph=None,
        order_by=None,
        include_tool=False,
    ):
        """
        Generate a dynamic SPARQL query for the schema.org CreateAction structure
        used by the newer RO-Crate provenance output.

        The query extracts run parameters from:
            CreateAction -> schema:object -> PropertyValue -> schema:exampleOfWork

        and metrics from:
            CreateAction -> schema:result -> PropertyValue

        Args:
            parameters (list): Parameter names matched via schema:name.
            metrics (list): Metric names matched via schema:name.
            tools (list, optional): Tool name substrings to filter by. Matching is
                                   case-insensitive and uses schema:instrument.
            named_graph (str, optional): URI of a named graph to query within.
            order_by (str, optional): Parameter or metric name to order results by.
                                     Defaults to the first parameter, if available.
            include_tool (bool, optional): Include ?tool_name in SELECT even when
                                          no tool filter is provided.

        Returns:
            str: A complete SPARQL query string ready to execute.
        """

        all_names = parameters + metrics
        var_map = {name: self.sanitize_variable_name(name) for name in all_names}

        select_names = list(all_names)
        select_vars = " ".join(f"?{var_map[name]}" for name in select_names)
        should_query_tool = include_tool or bool(tools)
        if should_query_tool:
            select_vars = f"{select_vars} ?tool_name"

        action_links = [
            "?runAction a schema:CreateAction .",
            "?runAction schema:object ?configuration .",
            "?configuration a schema:PropertyValue .",
        ]

        parameter_blocks = []
        for name in parameters:
            safe_name = var_map[name]
            escaped_name = self._sparql_string_literal(name)
            parameter_blocks.append(
                f"""
                ?configuration schema:exampleOfWork ?param_{safe_name} .
                ?param_{safe_name} a <https://bioschemas.org/FormalParameter> ;
                    schema:name "{escaped_name}" ;
                    schema:defaultValue ?{safe_name} .
                """.strip()
            )

        metric_blocks = []
        for name in metrics:
            safe_name = var_map[name]
            escaped_name = self._sparql_string_literal(name)
            metric_blocks.append(
                f"""
                ?runAction schema:result ?metric_{safe_name} .
                ?metric_{safe_name} a schema:PropertyValue ;
                    schema:name "{escaped_name}" ;
                    schema:defaultValue ?{safe_name} .
                """.strip()
            )

        tool_block = ""
        if should_query_tool:
            tool_block = """
                ?runAction schema:instrument ?tool .
                ?tool a schema:SoftwareApplication ;
                    schema:name ?tool_name .
            """.strip()
            if tools:
                filter_cond = " || ".join(
                    f'CONTAINS(LCASE(STR(?tool_name)), "{self._sparql_string_literal(t.lower())}")'
                    for t in tools
                )
                tool_block += f"\nFILTER({filter_cond}) ."

        inner_query = "\n".join(
            block
            for block in (
                "\n".join(action_links),
                "\n".join(parameter_blocks),
                "\n".join(metric_blocks),
                tool_block,
            )
            if block
        )

        where_block = (
            f"GRAPH <{named_graph}> {{\n{inner_query}\n}}"
            if named_graph
            else inner_query
        )

        order_name = order_by or (parameters[0] if parameters else None)
        order_clause = ""
        if order_name:
            order_var = var_map.get(order_name, self.sanitize_variable_name(order_name))
            order_clause = f"\n        ORDER BY ?{order_var}"

        query = f"""
        PREFIX schema: <http://schema.org/>

        SELECT {select_vars}
        WHERE {{
            {where_block}
        }}{order_clause}
        """.strip()

        return query

    def build_dynamic_query(
        self,
        parameters,
        metrics,
        tools=None,
        named_graph=None,
        query_structure="legacy",
        order_by=None,
    ):
        """
        Generate a dynamic SPARQL query to extract m4i:Method instances with specified
        parameters and metrics.

        The query extracts methods along with their associated parameters (via m4i:hasParameter),
        metrics (via m4i:investigates), and the tools that implement them (via ssn:implementedBy).

        Args:
            parameters (list): List of parameter names to query (matched via rdfs:label).
            metrics (list): List of metric names to query (matched via rdfs:label).
            tools (list, optional): List of tool name substrings to filter results.
                                   Case-insensitive matching. Defaults to None.
            named_graph (str, optional): URI of a named graph to query within.
                                        If None, queries the default graph. Defaults to None.
            query_structure (str, optional): Query structure to generate. Use
                                            "legacy" for the existing m4i query or
                                            "rocrate" for the schema.org
                                            CreateAction query.
            order_by (str, optional): Parameter or metric name to order by when
                                     query_structure is "rocrate".

        Returns:
            str: A complete SPARQL query string ready to execute.
        """

        if query_structure in {"rocrate", "create_action", "schema"}:
            return self.build_dynamic_rocrate_query(
                parameters=parameters,
                metrics=metrics,
                tools=tools,
                named_graph=named_graph,
                order_by=order_by,
                include_tool=bool(tools),
            )

        all_names = parameters + metrics
        # Map original names to safe SPARQL variable names
        var_map = {name: self.sanitize_variable_name(name) for name in all_names}

        # Build SELECT variables
        select_vars = " ".join(f"?{var_map[name]}" for name in all_names)

        # Build method→parameter and method→metric links
        method_links = (
            "\n    ".join(
                f"?method m4i:hasParameter ?param_{var_map[p]} ." for p in parameters
            )
            + "\n"
            + "\n    ".join(
                f"?method m4i:investigates ?param_{var_map[m]} ." for m in metrics
            )
        )

        # Build parameter and metric blocks
        value_blocks = "\n".join(
            f'?param_{var_map[name]} a schema:PropertyValue ;\n rdfs:label "{name}" ;\n schema:value ?{var_map[name]} .\n'
            for name in all_names
        )

        # Tool block with optional filter
        tool_predicate = "ssn:implementedBy" if named_graph else "m4i:implementedByTool"
        tool_block = f"?method {tool_predicate} ?tool .\n?tool a schema:SoftwareApplication ;\n rdfs:label ?tool_name .\n"
        if tools:
            filter_cond = " || ".join(
                f'CONTAINS(LCASE(?tool_name), "{t.lower()}")' for t in tools
            )
            tool_block += f"\nFILTER({filter_cond}) .\n"

        # Build the inner query
        inner_query = f"""
        ?method a m4i:Method .
        {method_links}
        {value_blocks}
        {tool_block}
        """.strip()

        # Wrap in GRAPH if named_graph is provided
        where_block = (
            f"GRAPH <{named_graph}> {{\n{inner_query}\n}}"
            if named_graph
            else inner_query
        )

        # Final query
        query = f"""
        PREFIX schema: <http://schema.org/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX m4i: <http://w3id.org/nfdi4ing/metadata4ing#>
        PREFIX ssn: <http://www.w3.org/ns/ssn/>
        
        SELECT {select_vars} ?tool_name
        WHERE {{
            {where_block}
        }}
        """.strip()

        return query

    def run_query_on_graph(
        self, graph: Graph, query: str
    ) -> Tuple[List[str], List[List]]:
        """
        Executes a SPARQL query on the provided RDF graph.

        Args:
            graph (rdflib.Graph): The RDF graph to query.
            query (str): The SPARQL query string to execute.

        Returns:
            rdflib.plugins.sparql.processor.SPARQLResult: The query results object
                                                          from rdflib.
        """
        return graph.query(query)

    def plot_provenance_graph(
        self,
        data: List[List],
        x_axis_label: str,
        y_axis_label: str,
        x_axis_index: str,
        y_axis_index: str,
        group_by_index: str,
        title: str,
        output_file: str = None,
        figsize: Tuple[int, int] = (12, 5),
    ):
        """
        Generates a scatter/line plot from the extracted provenance data.

        The plot displays data points grouped by a specified column, with each group
        shown as a separate line series. The x-axis uses a logarithmic scale.

        Args:
            data (List[List]): The table data to plot, where each row is a list of values.
            x_axis_label (str): Label for the x-axis.
            y_axis_label (str): Label for the y-axis.
            x_axis_index (int or str): Index or key for the x-axis values in each row.
            y_axis_index (int or str): Index or key for the y-axis values in each row.
            group_by_index (int or str): Index or key for the grouping variable (used for legend).
            title (str): Title of the plot.
            output_file (str, optional): Path where the plot will be saved as an image.
                                        If None, displays the plot. Defaults to None.
            figsize (Tuple[int, int], optional): Figure dimensions (width, height).
                                                Defaults to (12, 5).
        """

        grouped_data = defaultdict(list)
        x_tick_set = set()

        for row in data:
            x = float(row[x_axis_index])
            y = float(row[y_axis_index])
            grouped_data[row[group_by_index]].append((x, y))
            x_tick_set.add(x)

        # Sort x-tick labels
        x_ticks = sorted(x_tick_set)

        plt.figure(figsize=figsize)
        for grouped_title, values in grouped_data.items():
            # Sort values by x-axis (element size) to ensure correct line plotting
            values.sort()
            x_vals, y_vals = zip(*values)
            plt.plot(x_vals, y_vals, marker="o", linestyle="-", label=grouped_title)

        plt.xlabel(x_axis_label)
        plt.ylabel(y_axis_label)
        plt.title(title)
        plt.grid(True)
        plt.legend()
        plt.xscale("log")

        # Set x-ticks to show original values
        plt.xticks(ticks=x_ticks, labels=[str(x) for x in x_ticks], rotation=45)
        plt.tight_layout()

        if output_file:
            plt.savefig(output_file)
            print(f"Plot saved to: {output_file}")
        else:
            plt.show()

    def validate_provenance(self):
        """
        Validates the RO-Crate against the RO-Crate 1.1 profile.

        Uses the rocrate-validator library to check if the RO-Crate metadata
        conforms to the RO-Crate 1.1 specification with required severity level.

        Raises:
            AssertionError: If the RO-Crate has validation issues, with details
                           about each issue's severity and message.

        Prints:
            Success message if the RO-Crate is valid.
        """
        settings = services.ValidationSettings(
            rocrate_uri=self.provenance_folderpath,
            profile_identifier="ro-crate-1.1",
            requirement_severity=models.Severity.REQUIRED,
        )

        result = services.validate(settings)

        assert not result.has_issues(), "RO-Crate is invalid!\n" + "\n".join(
            f"Detected issue of severity {issue.severity.name} with check "
            f'"{issue.check.identifier}": {issue.message}'
            for issue in result.get_issues()
        )

        print("RO-Crate is valid!")
