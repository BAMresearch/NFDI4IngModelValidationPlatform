"""Create an aggregate RO-Crate from per-configuration benchmark provenance crates."""

from __future__ import annotations

import argparse
import json
import uuid
import zipfile
from pathlib import Path
from typing import Any, TypedDict

from rocrate.rocrate import ROCrate
import semantic_benchmark

DEFAULT_BENCHMARK_FILE = (
    "/Users/mahdi/Documents/GitHub/NFDI4IngModelValidationPlatform/examples/"
    "linear-elastic-plate-with-hole/benchmark.json"
)
DEFAULT_SIMULATION_RESULT_PATH = (
    "/Users/mahdi/Downloads/kratos_provenance_linear-elastic-plate-with-hole"
)
DEFAULT_ROCRATE_FILENAME = "RoCrate.zip"
DEFAULT_SOFTWARE_NAME = "FENICS"
RUN_PARAMETER_FILENAMES = ("parameter.json", "parameters.json")
SNAKEMAKE_FILE_NAME = "Snakefile"
M4I_HAS_KIND_OF_QUANTITY = "http://w3id.org/nfdi4ing/metadata4ing#hasKindOfQuantity"
ROCRATE_CONFORMS_TO = [
    {"@id": "https://w3id.org/ro/crate/1.1"},
    {"@id": "https://w3id.org/workflowhub/workflow-ro-crate/1.0"},
]
ROOT_DATASET_CONFORMS_TO = [
    {"@id": "https://w3id.org/ro/wfrun/process/0.4"},
    {"@id": "https://w3id.org/ro/wfrun/workflow/0.4"},
    {"@id": "https://w3id.org/ro/wfrun/provenance/0.4"},
    {"@id": "https://w3id.org/workflowhub/workflow-ro-crate/1.0"},
]
PROFILE_CREATIVE_WORKS = (
    {
        "@id": "https://w3id.org/ro/wfrun/process/0.4",
        "@type": "CreativeWork",
        "name": "Process Run Crate",
        "version": "0.4",
    },
    {
        "@id": "https://w3id.org/ro/wfrun/workflow/0.4",
        "@type": "CreativeWork",
        "name": "Workflow Run Crate",
        "version": "0.4",
    },
    {
        "@id": "https://w3id.org/ro/wfrun/provenance/0.4",
        "@type": "CreativeWork",
        "name": "Provenance Run Crate",
        "version": "0.4",
    },
    {
        "@id": "https://w3id.org/workflowhub/workflow-ro-crate/1.0",
        "@type": "CreativeWork",
        "name": "Workflow RO-Crate",
        "version": "1.0",
    },
)


class ConfigurationEntry(TypedDict):
    """Metadata needed to connect a benchmark configuration to a run action."""

    index: int
    config: semantic_benchmark.ParameterSet
    config_id: str
    processing_step_id: str


class RunResultEntry(TypedDict):
    """Metric result node ids collected for one simulation result folder."""

    run_name: str
    result_ids: list[dict[str, str]]


def _new_jsonld_id() -> str:
    """Create a local JSON-LD fragment identifier.

    Returns:
        A string id in the form ``#<uuid>`` for generated crate nodes.
    """
    return f"#{uuid.uuid4()}"


def _iter_subfolders(input_path: Path) -> list[Path]:
    """List direct run folders in a simulation result directory.

    Args:
        input_path: Directory containing one child folder per simulation run.

    Returns:
        Sorted direct child paths that are directories.
    """
    return [entry for entry in sorted(input_path.iterdir()) if entry.is_dir()]


def _subcrate_pattern(subfolder: Path) -> str:
    """Build the metadata4ing zip filename pattern for a run folder.

    Args:
        subfolder: Run folder whose name is encoded in the subcrate filename.

    Returns:
        Glob pattern matching zip files named ``*-<run-folder-name>.zip``.
    """
    return f"*-{subfolder.name}.zip"


def _first_subcrate(subfolder: Path) -> Path | None:
    """Find the first metadata4ing subcrate zip in a run folder.

    Args:
        subfolder: Run folder to search.

    Returns:
        The first matching zip path, or ``None`` when no subcrate exists.
    """
    return next(iter(sorted(subfolder.glob(_subcrate_pattern(subfolder)))), None)


def _collect_subcrates(subfolders: list[Path]) -> list[Path]:
    """Collect metadata4ing subcrate zip files from run folders.

    Args:
        subfolders: Run folders to search.

    Returns:
        Sorted matching subcrate zip paths from all run folders.
    """
    subcrates: list[Path] = []
    for subfolder in subfolders:
        subcrates.extend(sorted(subfolder.glob(_subcrate_pattern(subfolder))))
    return subcrates


def _unzip_subcrates_at_root(subcrates: list[Path]) -> None:
    """Extract each subcrate zip into its containing run folder.

    Args:
        subcrates: Zip files to extract.

    Returns:
        None. The function writes extracted files to each zip file's parent folder.
    """
    for subcrate in subcrates:
        with zipfile.ZipFile(subcrate, "r") as archive:
            archive.extractall(subcrate.parent)


def _add_subcrates_to_main(
    crate: ROCrate, subcrates: list[Path], input_path: Path
) -> None:
    """Add subcrate zip files as data files in the aggregate crate.

    Args:
        crate: Aggregate RO-Crate being built.
        subcrates: Zip files to add to the crate.
        input_path: Root simulation result directory used for relative crate paths.

    Returns:
        None. The function mutates ``crate``.
    """
    for subcrate in subcrates:
        crate.add_file(
            source=str(subcrate),
            dest_path=str(subcrate.relative_to(input_path)),
            properties={},
        )


def _create_action_object_ids(
    input_path: Path, subfolders: list[Path]
) -> dict[str, str]:
    """Map run folder names to relative subcrate object ids.

    Args:
        input_path: Root simulation result directory.
        subfolders: Run folders to inspect.

    Returns:
        Mapping from run folder name to the subcrate zip path relative to
        ``input_path``. Folders without a matching subcrate are omitted.
    """
    object_ids: dict[str, str] = {}
    for subfolder in subfolders:
        subcrate = _first_subcrate(subfolder)
        if subcrate is None:
            continue
        object_ids[subfolder.name] = str(subcrate.relative_to(input_path))
    return object_ids


def _formal_parameter_key(part: semantic_benchmark.ParameterEntry) -> tuple[Any, ...]:
    """Build a stable de-duplication key for a benchmark parameter.

    Args:
        part: Benchmark parameter or variable entry.

    Returns:
        Tuple containing the fields that define a unique FormalParameter node.
    """
    return (
        type(part).__name__,
        part.label,
        getattr(part, "unit", None),
        getattr(part, "numerical_value", None),
        getattr(part, "string_value", None),
        getattr(part, "quantity_kind", None),
    )


def _formal_parameter_payload(
    part_id: str, part: semantic_benchmark.ParameterEntry
) -> dict[str, Any]:
    """Create a JSON-LD FormalParameter payload.

    Args:
        part_id: JSON-LD id assigned to the FormalParameter.
        part: Benchmark parameter or variable entry to serialize.

    Returns:
        JSON-LD dictionary ready to add to the RO-Crate.
    """
    payload: dict[str, Any] = {
        "@id": part_id,
        "@type": "FormalParameter",
        "name": part.label,
    }

    unit = getattr(part, "unit", None)
    payload["additionalType"] = ""

    if unit is not None:
        payload["m4i:hasKindOfQuantity"] = {"@id": unit}

    if isinstance(part, semantic_benchmark.NumericalParameter):
        payload["defaultValue"] = part.numerical_value
    elif isinstance(part, semantic_benchmark.TextParameter):
        payload["defaultValue"] = part.string_value
    elif (
        isinstance(part, semantic_benchmark.NumericalVariable)
        and part.quantity_kind is not None
    ):
        payload["valueReference"] = part.quantity_kind

    return payload


def _add_formal_parameter(
    crate: ROCrate,
    part: semantic_benchmark.ParameterEntry,
    formal_param_registry: dict[tuple[Any, ...], str],
) -> dict[str, str]:
    """Add a FormalParameter node once and return its id reference.

    Args:
        crate: Aggregate RO-Crate being built.
        part: Benchmark parameter or variable entry to add.
        formal_param_registry: Registry mapping parameter keys to existing ids.

    Returns:
        JSON-LD id reference of the form ``{"@id": "<id>"}``.
    """
    key = _formal_parameter_key(part)
    part_id = formal_param_registry.get(key)

    if part_id is None:
        part_id = _new_jsonld_id()
        formal_param_registry[key] = part_id
        crate.add_jsonld(_formal_parameter_payload(part_id, part))

    return {"@id": part_id}


def _add_configuration_node(
    crate: ROCrate,
    config: semantic_benchmark.ParameterSet,
    config_id: str,
    formal_parameter_ids: list[dict[str, str]],
) -> None:
    """Add one benchmark configuration as a PropertyValue node.

    Args:
        crate: Aggregate RO-Crate being built.
        config: Benchmark configuration to serialize.
        config_id: JSON-LD id assigned to this configuration node.
        formal_parameter_ids: FormalParameter references included in the configuration.

    Returns:
        None. The function mutates ``crate``.
    """
    crate.add_jsonld(
        {
            "@id": config_id,
            "@type": "PropertyValue",
            "name": config.label,
            "exampleOfWork": formal_parameter_ids,
        }
    )


def _add_configuration_nodes(
    crate: ROCrate,
    benchmark_object: semantic_benchmark.SemanticBenchmark,
) -> list[ConfigurationEntry]:
    """Add benchmark configuration nodes to the aggregate crate.

    Args:
        crate: Aggregate RO-Crate being built.
        benchmark_object: Parsed benchmark description containing processing steps
            and parameter sets.

    Returns:
        Metadata entries connecting each benchmark configuration to its generated
        JSON-LD id and processing step.

    Raises:
        ValueError: If the benchmark does not define processing steps.
    """
    if not benchmark_object.processing_steps:
        raise ValueError("Benchmark has no processing steps.")

    formal_param_registry: dict[tuple[Any, ...], str] = {}
    configuration_entries: list[ConfigurationEntry] = []

    for processing_step in benchmark_object.processing_steps:
        for index, config in enumerate(processing_step.configurations, start=1):
            config_id = _new_jsonld_id()
            formal_parameter_ids: list[dict[str, str]] = []

            for part in config.parts:
                formal_parameter_ids.append(
                    _add_formal_parameter(crate, part, formal_param_registry)
                )

            _add_configuration_node(crate, config, config_id, formal_parameter_ids)
            configuration_entries.append(
                {
                    "index": index,
                    "config": config,
                    "config_id": config_id,
                    "processing_step_id": processing_step.id,
                }
            )

    return configuration_entries


def _normalize_value(value: Any) -> str | None:
    """Normalize a value for configuration matching.

    Args:
        value: Raw identifier value from benchmark metadata, parameters, or folder
            names.

    Returns:
        Normalized string value, or ``None`` for missing or empty values.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return f"{float(value):.15g}"
    text = str(value).strip()
    if not text:
        return None
    try:
        return f"{float(text):.15g}"
    except ValueError:
        return text.lower()


def _run_parameters_file(run_folder: Path) -> Path | None:
    """Find the parameter file for a run folder.

    Args:
        run_folder: Simulation run folder to inspect.

    Returns:
        Path to ``parameter.json`` or ``parameters.json`` if present, otherwise
        ``None``.
    """
    for candidate in RUN_PARAMETER_FILENAMES:
        path = run_folder / candidate
        if path.exists() and path.is_file():
            return path
    return None


def _load_run_parameters(run_folder: Path) -> dict[str, Any]:
    """Load run parameters from a result folder.

    Args:
        run_folder: Simulation run folder containing a parameter JSON file.

    Returns:
        Parsed JSON object when the file exists and contains a dictionary;
        otherwise an empty dictionary.
    """
    parameters_file = _run_parameters_file(run_folder)
    if parameters_file is None:
        return {}
    try:
        with parameters_file.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _configuration_id_for_run(
    run_folder: Path,
    run_parameters: dict[str, Any],
    configuration_entries: list[ConfigurationEntry],
) -> str | None:
    """Resolve the generated configuration node id for a run.

    Args:
        run_folder: Simulation run folder being matched.
        run_parameters: Parameters loaded from the run folder.
        configuration_entries: Generated benchmark configuration entries for a
            processing step.

    Returns:
        Matching configuration JSON-LD id, or ``None`` if no match is found.
    """
    by_identifier: dict[str, str] = {}

    for entry in configuration_entries:
        config_id = entry["config_id"]
        config = entry["config"]

        identifier_key = _normalize_value(config.identifier)
        if identifier_key:
            by_identifier[identifier_key] = config_id

    run_config_value = run_parameters.get("configuration")

    candidates = [
        _normalize_value(run_config_value),
        _normalize_value(run_folder.name),
    ]

    for candidate in candidates:
        if candidate and candidate in by_identifier:
            return by_identifier[candidate]

    return None


def _json_path_value(payload: Any, json_path: str) -> Any:
    """Read a value from nested JSON data using a slash-separated path.

    Args:
        payload: Parsed JSON-compatible data structure.
        json_path: Slash-separated path, for example ``/metrics/stress``.

    Returns:
        Value found at the path, or ``None`` if any path segment is missing or
        incompatible with the current data type.
    """
    current = payload
    for token in (part for part in json_path.strip().strip("/").split("/") if part):
        if isinstance(current, dict):
            if token not in current:
                return None
            current = current[token]
            continue
        if isinstance(current, list):
            if not token.isdigit():
                return None
            index = int(token)
            if index < 0 or index >= len(current):
                return None
            current = current[index]
            continue
        return None
    return current


def _load_json(path: Path, cache: dict[Path, Any]) -> Any:
    """Load and cache a JSON document.

    Args:
        path: JSON file to load.
        cache: Mutable cache keyed by file path.

    Returns:
        Parsed JSON payload from the cache or file.
    """
    if path not in cache:
        with path.open("r", encoding="utf-8") as handle:
            cache[path] = json.load(handle)
    return cache[path]


def _extract_evaluated_value(
    run_folder: Path,
    metric: semantic_benchmark.NumericalVariable,
    json_cache: dict[Path, Any],
) -> tuple[Any, Path | None]:
    """Extract one evaluated metric value from a run folder.

    Args:
        run_folder: Simulation run folder containing result files.
        metric: Benchmark metric definition with field mapping information.
        json_cache: Cache for JSON result files read during this run.

    Returns:
        Tuple ``(value, source_file)``. ``value`` is ``None`` when the metric
        cannot be extracted. ``source_file`` is the expected/read file path when
        available, otherwise ``None``.
    """
    field_mapping = metric.field_mapping
    if (
        not field_mapping
        or not field_mapping.json_path
        or not field_mapping.file_object_label
    ):
        return None, None

    source_file = run_folder / field_mapping.file_object_label
    if not source_file.exists() or not source_file.is_file():
        return None, source_file

    try:
        payload = _load_json(source_file, json_cache)
    except (OSError, json.JSONDecodeError):
        return None, source_file

    return _json_path_value(payload, field_mapping.json_path), source_file


def _metric_result_payload(
    result_id: str,
    metric: semantic_benchmark.NumericalVariable,
    value: Any,
) -> dict[str, Any]:
    """Create a JSON-LD payload for an evaluated metric result.

    Args:
        result_id: JSON-LD id assigned to the metric result node.
        metric: Benchmark metric definition.
        value: Extracted metric value.

    Returns:
        JSON-LD dictionary ready to add to the RO-Crate.
    """
    payload: dict[str, Any] = {
        "@id": result_id,
        "@type": "PropertyValue",
        "name": metric.label,
        "defaultValue": value,
    }
    if metric.unit:
        payload["additionalType"] = metric.unit
    return payload


def _add_evaluates_nodes(
    crate: ROCrate,
    benchmark_object: semantic_benchmark.SemanticBenchmark,
    subfolders: list[Path],
) -> list[RunResultEntry]:
    """Add metric result nodes for all run folders.

    Args:
        crate: Aggregate RO-Crate being built.
        benchmark_object: Parsed benchmark description containing evaluated metrics.
        subfolders: Simulation run folders to inspect.

    Returns:
        One entry per run folder with JSON-LD references to metric result nodes.
        Runs without extracted metrics are included with an empty result list.
    """
    run_results: list[RunResultEntry] = []
    if not benchmark_object.evaluates:
        return run_results

    for run_folder in subfolders:
        json_cache: dict[Path, Any] = {}
        run_metric_results: list[dict[str, str]] = []
        for metric in benchmark_object.evaluates:
            value, _ = _extract_evaluated_value(run_folder, metric, json_cache)
            if value is None:
                continue

            result_id = _new_jsonld_id()
            crate.add_jsonld(_metric_result_payload(result_id, metric, value))
            run_metric_results.append({"@id": result_id})

        run_results.append(
            {"run_name": run_folder.name, "result_ids": run_metric_results}
        )

    return run_results


def _run_results_by_name(
    run_results: list[RunResultEntry],
) -> dict[str, list[dict[str, str]]]:
    """Index metric result references by run folder name.

    Args:
        run_results: Metric result entries returned by ``_add_evaluates_nodes``.

    Returns:
        Mapping from run folder name to metric result JSON-LD id references.
    """
    return {entry["run_name"]: entry["result_ids"] for entry in run_results}


def _configuration_entries_for_step(
    configuration_entries: list[ConfigurationEntry],
    processing_step: semantic_benchmark.ProcessingStep,
) -> list[ConfigurationEntry]:
    """Filter generated configuration entries by processing step.

    Args:
        configuration_entries: All generated configuration entries.
        processing_step: Benchmark processing step used for filtering.

    Returns:
        Configuration entries whose ``processing_step_id`` matches the step id.
    """
    return [
        entry
        for entry in configuration_entries
        if entry["processing_step_id"] == processing_step.id
    ]


def _add_run_actions(
    crate: ROCrate,
    subfolders: list[Path],
    object_ids_by_run: dict[str, str],
    processing_steps: list[semantic_benchmark.ProcessingStep],
    configuration_entries: list[ConfigurationEntry],
    run_results_by_name: dict[str, list[dict[str, str]]],
    software_id: str,
) -> None:
    """Add run action nodes connecting runs, configurations, and results.

    Args:
        crate: Aggregate RO-Crate being built.
        subfolders: Simulation run folders.
        object_ids_by_run: Mapping from run folder name to subcrate object id.
        processing_steps: Benchmark processing steps to represent as actions.
        configuration_entries: Generated configuration metadata entries.
        run_results_by_name: Mapping from run folder name to result references.
        software_id: JSON-LD id of the software application instrument.

    Returns:
        None. The function mutates ``crate`` by adding ``CreateAction`` nodes.
    """
    for run_folder in subfolders:
        run_name = run_folder.name
        run_object_id = object_ids_by_run.get(run_name)
        if not run_object_id:
            continue

        run_parameters = _load_run_parameters(run_folder)
        result_ids = run_results_by_name.get(run_name, [])

        for processing_step in processing_steps:
            step_configuration_entries = _configuration_entries_for_step(
                configuration_entries, processing_step
            )
            config_id = _configuration_id_for_run(
                run_folder, run_parameters, step_configuration_entries
            )

            step_name = processing_step.label or processing_step.id
            run_action: dict[str, Any] = {
                "@id": _new_jsonld_id(),
                "@type": "CreateAction",
                "name": f"{step_name} {run_name}",
                "object": [{"@id": run_object_id}],
                "instrument": {"@id": software_id},
            }
            if config_id:
                run_action["object"].append({"@id": config_id})
            if result_ids:
                run_action["result"] = result_ids
            crate.add_jsonld(run_action)


def _configure_crate_metadata(crate: ROCrate, snakemake_id: str) -> None:
    """Set crate-level metadata, profiles, license, and main workflow entity.

    Args:
        crate: Aggregate RO-Crate being built.
        snakemake_id: JSON-LD id/path of the main workflow file.

    Returns:
        None. The function mutates crate metadata and root dataset properties.
    """
    crate.metadata.extra_terms = {"m4i:hasKindOfQuantity": M4I_HAS_KIND_OF_QUANTITY}
    crate.mainEntity = {"@id": snakemake_id}
    crate.license = "https://opensource.org/licenses/MIT"
    crate.name = "NFDI4Ing Provenance"
    crate.description = "Benchmark for linear-elastic plate with a hole"
    crate.metadata["conformsTo"] = ROCRATE_CONFORMS_TO
    crate.root_dataset.append_to("conformsTo", ROOT_DATASET_CONFORMS_TO)


def _add_profile_creative_works(crate: ROCrate) -> None:
    """Add CreativeWork descriptions for crate profile documents.

    Args:
        crate: Aggregate RO-Crate being built.

    Returns:
        None. The function mutates ``crate``.
    """
    for creative_work in PROFILE_CREATIVE_WORKS:
        crate.add_jsonld(creative_work)


def _add_software_node(crate: ROCrate, software_id: str, software_name: str) -> None:
    """Add the software application node used as the action instrument.

    Args:
        crate: Aggregate RO-Crate being built.
        software_id: JSON-LD id assigned to the software node.
        software_name: Human-readable software name.

    Returns:
        None. The function mutates ``crate``.
    """
    crate.add_jsonld(
        {"@id": software_id, "@type": "SoftwareApplication", "name": software_name}
    )


def _add_workflow_node(
    crate: ROCrate,
    subcrates: list[Path],
    software_id: str,
    workflow_filename: str = SNAKEMAKE_FILE_NAME,
) -> None:
    """Add the Snakemake workflow file to the aggregate crate.

    Args:
        crate: Aggregate RO-Crate being built.
        subcrates: Collected subcrate zip files; the first subcrate's parent is
            used to locate the workflow file.
        software_id: JSON-LD id of the software application linked as ``hasPart``.
        workflow_filename: Workflow filename to add from the run folder.

    Returns:
        None. The function mutates ``crate``.
    """
    crate.add_workflow(
        source=str(subcrates[0].parent / workflow_filename),
        lang="snakemake",
        properties={"hasPart": {"@id": software_id}},
    )


def create_main_ro(
    path: str,
    benchmark_object: semantic_benchmark.SemanticBenchmark,
    rocrate_filename: str = DEFAULT_ROCRATE_FILENAME,
    software_name: str = DEFAULT_SOFTWARE_NAME,
) -> None:
    """Create and write an aggregate RO-Crate for a benchmark result directory.

    Args:
        path: Directory containing one subfolder per simulation run.
        benchmark_object: Parsed benchmark description used to create configuration
            and metric nodes.
        rocrate_filename: Output zip filename/path for the aggregate crate.
        software_name: Software name recorded as the run action instrument.

    Returns:
        None. The function writes the aggregate RO-Crate zip to
        ``rocrate_filename``.

    Raises:
        NotADirectoryError: If ``path`` is not a directory.
        ValueError: If no matching subcrate zip files are found.
    """
    crate = ROCrate(version="1.1")
    input_path = Path(path)

    if not input_path.is_dir():
        raise NotADirectoryError(f"{path} is not a valid directory")

    subfolders = _iter_subfolders(input_path)
    subcrates = _collect_subcrates(subfolders)
    _unzip_subcrates_at_root(subcrates)

    if not subcrates:
        raise ValueError(
            "No .zip files found inside subfolders of the specified directory"
        )

    _add_subcrates_to_main(crate, subcrates, input_path)

    object_ids_by_run = _create_action_object_ids(input_path, subfolders)
    configuration_entries = _add_configuration_nodes(crate, benchmark_object)
    run_results = _add_evaluates_nodes(crate, benchmark_object, subfolders)
    run_results_by_name = _run_results_by_name(run_results)

    snakemake_id = SNAKEMAKE_FILE_NAME
    software_id = str(uuid.uuid4())

    _add_run_actions(
        crate=crate,
        subfolders=subfolders,
        object_ids_by_run=object_ids_by_run,
        processing_steps=benchmark_object.processing_steps,
        configuration_entries=configuration_entries,
        run_results_by_name=run_results_by_name,
        software_id=software_id,
    )
    _configure_crate_metadata(crate, snakemake_id)

    _add_software_node(crate, software_id, software_name)
    _add_profile_creative_works(crate)
    _add_workflow_node(crate, subcrates, software_id)
    crate.write_zip(rocrate_filename)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for aggregate RO-Crate creation.

    Returns:
        Parsed command-line arguments with benchmark file, simulation result path,
        output RO-Crate filename, and software name.
    """
    parser = argparse.ArgumentParser(
        description="Create a benchmark provenance RO-Crate from simulation results."
    )
    parser.add_argument(
        "--benchmark-file",
        default=DEFAULT_BENCHMARK_FILE,
        help="Path to benchmark JSON-LD file",
    )
    parser.add_argument(
        "--simulation-result-path",
        default=DEFAULT_SIMULATION_RESULT_PATH,
        help="Path containing simulation result subfolders with RoCrate zip files",
    )
    parser.add_argument(
        "--rocrate-filename",
        default=DEFAULT_ROCRATE_FILENAME,
        help="Filename for the generated RO-Crate zip file",
    )
    parser.add_argument(
        "--software-name",
        default=DEFAULT_SOFTWARE_NAME,
        help="Name of the software application recorded in the generated RO-Crate",
    )

    return parser.parse_args()


def main() -> None:
    """Run the command-line entry point.

    Returns:
        None. The function loads the benchmark description and writes the
        aggregate RO-Crate requested by the CLI arguments.
    """
    args = parse_args()
    benchmark_object = semantic_benchmark.BenchmarkLoader(args.benchmark_file).load()
    create_main_ro(
        args.simulation_result_path,
        benchmark_object,
        rocrate_filename=args.rocrate_filename,
        software_name=args.software_name,
    )


if __name__ == "__main__":
    main()
