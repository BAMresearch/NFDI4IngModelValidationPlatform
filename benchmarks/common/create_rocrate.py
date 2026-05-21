from __future__ import annotations

import argparse
import json
import uuid
import zipfile
from importlib import resources
from pathlib import Path
from typing import Any, TypedDict

from rdflib import Graph
from rocrate.rocrate import ROCrate
from provenance import ProvenanceAnalyzer
import semantic_benchmark

DEFAULT_BENCHMARK_FILE = (
    "/Users/mahdi/Documents/GitHub/NFDI4IngModelValidationPlatform/examples/"
    "linear-elastic-plate-with-hole/benchmark.json"
)
DEFAULT_SIMULATION_RESULT_PATH = (
    "/Users/mahdi/Downloads/fenics_provenance_linear-elastic-plate-with-hole"
)
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
    index: int
    config: semantic_benchmark.ParameterSet
    config_id: str
    processing_step_id: str


class RunResultEntry(TypedDict):
    run_name: str
    result_ids: list[dict[str, str]]


def _iter_subfolders(input_path: Path) -> list[Path]:
    return [entry for entry in sorted(input_path.iterdir()) if entry.is_dir()]


def _collect_subcrates(subfolders: list[Path]) -> list[Path]:
    subcrates: list[Path] = []
    for subfolder in subfolders:
        subcrates.extend(sorted(subfolder.glob(f"*-{subfolder.name}.zip")))
    return subcrates


def _unzip_subcrates_at_root(subcrates: list[Path]) -> None:
    for subcrate in subcrates:
        with zipfile.ZipFile(subcrate, "r") as archive:
            archive.extractall(subcrate.parent)


def _add_subcrates_to_main(
    crate: ROCrate, subcrates: list[Path], input_path: Path
) -> None:
    for subcrate in subcrates:
        crate.add_file(
            source=str(subcrate),
            dest_path=str(subcrate.relative_to(input_path)),
            properties={},
        )


def _create_action_object_ids(
    input_path: Path, subfolders: list[Path]
) -> dict[str, str]:
    object_ids: dict[str, str] = {}
    for subfolder in subfolders:
        subcrate = next(iter(sorted(subfolder.glob(f"*-{subfolder.name}.zip"))), None)
        if subcrate is None:
            continue
        object_ids[subfolder.name] = str(subcrate.relative_to(input_path))
    return object_ids


def _formal_parameter_key(part: semantic_benchmark.ParameterEntry) -> tuple[Any, ...]:
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


def _add_configuration_nodes(
    crate: ROCrate,
    benchmark_object: semantic_benchmark.SemanticBenchmark,
) -> list[ConfigurationEntry]:
    if not benchmark_object.processing_steps:
        raise ValueError("Benchmark has no processing steps.")

    formal_param_registry: dict[tuple[Any, ...], str] = {}
    configuration_entries: list[ConfigurationEntry] = []

    for processing_step in benchmark_object.processing_steps:
        for index, config in enumerate(processing_step.configurations, start=1):
            config_id = f"#{uuid.uuid4()}"
            formal_parameter_ids: list[dict[str, str]] = []

            for part in config.parts:
                key = _formal_parameter_key(part)
                part_id = formal_param_registry.get(key)

                if part_id is None:
                    part_id = f"#{uuid.uuid4()}"
                    formal_param_registry[key] = part_id
                    crate.add_jsonld(_formal_parameter_payload(part_id, part))

                formal_parameter_ids.append({"@id": part_id})

            crate.add_jsonld(
                {
                    "@id": config_id,
                    "@type": "PropertyValue",
                    "name": config.label,
                    "exampleOfWork": formal_parameter_ids,
                }
            )
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
    for candidate in ("parameter.json", "parameters.json"):
        path = run_folder / candidate
        if path.exists() and path.is_file():
            return path
    return None


def _load_run_parameters(run_folder: Path) -> dict[str, Any]:
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
    if path not in cache:
        with path.open("r", encoding="utf-8") as handle:
            cache[path] = json.load(handle)
    return cache[path]


def _extract_evaluated_value(
    run_folder: Path,
    metric: semantic_benchmark.NumericalVariable,
    json_cache: dict[Path, Any],
) -> tuple[Any, Path | None]:
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


def _add_evaluates_nodes(
    crate: ROCrate,
    benchmark_object: semantic_benchmark.SemanticBenchmark,
    subfolders: list[Path],
) -> list[RunResultEntry]:
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

            result_id = f"#{uuid.uuid4()}"
            node: dict[str, Any] = {
                "@id": result_id,
                "@type": "PropertyValue",
                "name": metric.label,
                "defaultValue": value,
            }
            if metric.unit:
                node["additionalType"] = metric.unit

            crate.add_jsonld(node)
            run_metric_results.append({"@id": result_id})

        run_results.append(
            {"run_name": run_folder.name, "result_ids": run_metric_results}
        )

    return run_results


def _run_results_by_name(
    run_results: list[RunResultEntry],
) -> dict[str, list[dict[str, str]]]:
    return {entry["run_name"]: entry["result_ids"] for entry in run_results}


def _configuration_entries_for_step(
    configuration_entries: list[ConfigurationEntry],
    processing_step: semantic_benchmark.ProcessingStep,
) -> list[ConfigurationEntry]:
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
                "@id": f"#{uuid.uuid4()}",
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
    crate.metadata.extra_terms = {"m4i:hasKindOfQuantity": M4I_HAS_KIND_OF_QUANTITY}
    crate.mainEntity = {"@id": snakemake_id}
    crate.license = "https://opensource.org/licenses/MIT"
    crate.name = "NFDI4Ing Provenance"
    crate.description = "Benchmark for linear-elastic plate with a hole"
    crate.metadata["conformsTo"] = ROCRATE_CONFORMS_TO
    crate.root_dataset.append_to("conformsTo", ROOT_DATASET_CONFORMS_TO)


def _add_profile_creative_works(crate: ROCrate) -> None:
    for creative_work in PROFILE_CREATIVE_WORKS:
        crate.add_jsonld(creative_work)


def unzip_rocrate(ro_zip_path: str = "RO.zip", extract_dir: str = "RO") -> Path:
    zip_path = Path(ro_zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(f"RO-Crate zip not found: {zip_path}")

    output_dir = Path(extract_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(output_dir)
    return output_dir


def create_main_ro(
    path: str, benchmark_object: semantic_benchmark.SemanticBenchmark
) -> None:
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

    snakemake_id = "Snakefile"
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

    crate.add_jsonld(
        {"@id": software_id, "@type": "SoftwareApplication", "name": "FENICS"}
    )
    _add_profile_creative_works(crate)

    crate.add_workflow(
        source=str(subcrates[0].parent / "Snakefile"),
        lang="snakemake",
        properties={"hasPart": {"@id": software_id}},
    )
    crate.write_zip("RoCrate.Zip")


def run_sparql_query(graph: Graph) -> None:
    query = """
    PREFIX schema: <http://schema.org/>

    SELECT ?elementSize ?maxVonMisesStressNodes ?l2ErrorDisplacement
    WHERE {
      ?runAction a schema:CreateAction ;
                 schema:object ?object ;
                 schema:result ?metric1 ;
                 schema:result ?metric2 .
    
      ?object a schema:PropertyValue ;
              schema:exampleOfWork ?param .
    
      ?param a <https://bioschemas.org/FormalParameter> ;
             schema:name "element-size" ;
             schema:defaultValue ?elementSize .
    
      ?metric1 a schema:PropertyValue ;
              schema:name "max_von_mises_stress_nodes" ;
              schema:defaultValue ?maxVonMisesStressNodes .
              
      ?metric2 a schema:PropertyValue ;
              schema:name "l2_error_displacement" ;
              schema:defaultValue ?l2ErrorDisplacement .
    }
    ORDER BY ?elementSize
    """
    results = graph.query(query)
    variables = [str(var) for var in results.vars]
    if variables:
        print(" | ".join(variables))
        print("-" * max(3, len(" | ".join(variables))))
    row_count = 0
    for row in results:
        values = [str(value) if value is not None else "" for value in row]
        print(" | ".join(values))
        row_count += 1
    print(f"\nRows: {row_count}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create RO-Crate and run SPARQL queries on ro-crate-metadata.json"
    )
    parser.add_argument(
        "--benchmark-file",
        default=DEFAULT_BENCHMARK_FILE,
        help="Path to benchmark JSON-LD file",
    )
    parser.add_argument(
        "--simulation-result-path",
        default=DEFAULT_SIMULATION_RESULT_PATH,
        help="Path containing run folders and SubCrate.zip files",
    )
    parser.add_argument(
        "--ro-zip", default="RoCrate.Zip", help="Path to RO-Crate zip file"
    )
    parser.add_argument(
        "--extract-dir",
        default="RO",
        help="Directory where RoCrate.Zip should be extracted",
    )
    args = parser.parse_args()

    benchmark_object = semantic_benchmark.BenchmarkLoader(args.benchmark_file).load()
    create_main_ro(args.simulation_result_path, benchmark_object)

    extracted_dir = unzip_rocrate(args.ro_zip, args.extract_dir)

    proveance = ProvenanceAnalyzer(provenance_folderpath=extracted_dir)
    query = proveance.build_dynamic_rocrate_query(
        parameters=["element-size"],
        metrics=["max_von_mises_stress_nodes", "max_von_mises_stress_gauss_points"],
    )
    proveance.plot_provenance_graph()
    print(query)


if __name__ == "__main__":
    main()
