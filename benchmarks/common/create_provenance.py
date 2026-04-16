from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from rocrate.rocrate import ROCrate

import semantic_benchmark


def _iter_subfolders(input_path: Path) -> list[Path]:
    return [entry for entry in sorted(input_path.iterdir()) if entry.is_dir()]


def _collect_subcrates(subfolders: list[Path]) -> list[Path]:
    subcrates: list[Path] = []
    for subfolder in subfolders:
        subcrates.extend(sorted(subfolder.glob("SubCrate.zip")))
    return subcrates


def _add_subcrates_to_main(crate: ROCrate, subcrates: list[Path], input_path: Path) -> None:
    for subcrate in subcrates:
        crate.add_file(
            source=str(subcrate),
            dest_path=str(subcrate.relative_to(input_path)),
            properties={},
        )


def _add_create_action_objects(crate: ROCrate, subfolders: list[Path]) -> list[dict[str, str]]:
    object_ids: list[dict[str, str]] = []
    for subfolder in subfolders:
        object_id = f"#{uuid.uuid4()}"
        crate.add_jsonld({"@id": object_id, "@type": "PropertyValue", "name": subfolder.name})
        object_ids.append({"@id": object_id})
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


def _formal_parameter_payload(part_id: str, part: semantic_benchmark.ParameterEntry) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "@id": part_id,
        "@type": "FormalParameter",
        "name": part.label,
    }

    unit = getattr(part, "unit", None)
    if unit is not None:
        payload["additionalType"] = unit

    if isinstance(part, semantic_benchmark.NumericalParameter):
        payload["defaultValue"] = part.numerical_value
    elif isinstance(part, semantic_benchmark.TextParameter):
        payload["defaultValue"] = part.string_value
    elif isinstance(part, semantic_benchmark.NumericalVariable):
        if part.quantity_kind is not None:
            payload["valueReference"] = part.quantity_kind

    return payload


def _add_configuration_nodes(
    crate: ROCrate,
    benchmark_object: semantic_benchmark.BenchmarkSemantic,
) -> None:
    if not benchmark_object.processing_steps:
        raise ValueError("Benchmark has no processing steps.")

    formal_param_registry: dict[tuple[Any, ...], str] = {}

    for config in benchmark_object.processing_steps[0].configurations:
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


def create_main_ro(path: str, benchmark_object: semantic_benchmark.BenchmarkSemantic) -> None:
    crate = ROCrate(version="1.1")
    input_path = Path(path)

    if not input_path.is_dir():
        raise NotADirectoryError(f"{path} is not a valid directory")

    subfolders = _iter_subfolders(input_path)
    subcrates = _collect_subcrates(subfolders)

    if not subcrates:
        raise ValueError("No .zip files found inside subfolders of the specified directory")

    _add_subcrates_to_main(crate, subcrates, input_path)
    object_ids = _add_create_action_objects(crate, subfolders)
    _add_configuration_nodes(crate, benchmark_object)

    crate.add_jsonld(
        {
            "@id": f"#{uuid.uuid4()}",
            "@type": "CreateAction",
            "name": "Simulation Run",
            "object": object_ids,
        }
    )

    crate.write_zip("RO.zip")


def merge_all_rocrates_as_subcrates(
    input_folder: str,
    output_zip: str,
    parent_name: str = "Merged RO-Crate",
    parent_description: str = "This RO-Crate contains multiple nested RO-Crates as subcrates.",
) -> None:
    """
    Merge all zipped RO-Crates in a folder into a single RO-Crate
    using the Subcrate mechanism.
    """
    input_path = Path(input_folder)
    if not input_path.is_dir():
        raise NotADirectoryError(f"{input_folder} is not a valid directory")

    merged = ROCrate()
    merged.name = parent_name
    merged.description = parent_description

    zip_files = sorted(input_path.glob("*.zip"))
    if not zip_files:
        raise ValueError("No .zip files found in the specified folder")

    for zip_path in zip_files:
        subcrate_name = zip_path.stem
        print(f"Adding subcrate: {zip_path.name} -> {subcrate_name}/")
        merged.add_subcrate(source=str(zip_path), dest_path=subcrate_name)

    merged.write_zip(output_zip)
    print(f"Merged RO-Crate written to: {output_zip}")
    print(f"Total subcrates added: {len(zip_files)}")


def _print_benchmark_summary(benchmark_object: semantic_benchmark.BenchmarkSemantic) -> None:
    for step in benchmark_object.processing_steps:
        print(f"Processing Step: {step.label}")
        for config in step.configurations:
            print(f"  Configuration: {config.label}")
            for part in config.parts:
                if isinstance(part, semantic_benchmark.NumericalParameter):
                    print(
                        f"    Numerical Parameter: {part.label} = {part.numerical_value} {part.unit}"
                    )
                elif isinstance(part, semantic_benchmark.TextParameter):
                    print(f"    Text Parameter: {part.label} = {part.string_value}")

        for tool in step.employed_tools:
            print(f"  Employed Tool: {tool.label}")


def main() -> None:
    benchmark_file = "/Users/mahdi/Documents/GitHub/NFDI4IngModelValidationPlatform/examples/linear-elastic-plate-with-hole/benchmark.json"
    simulation_result_path = "/Users/mahdi/Documents/GitHub/NFDI4IngModelValidationPlatform/examples/linear-elastic-plate-with-hole/fenics/results"

    benchmark_object = semantic_benchmark.BenchmarkLoader(benchmark_file).load()
    _print_benchmark_summary(benchmark_object)
    create_main_ro(simulation_result_path, benchmark_object)


if __name__ == "__main__":
    main()
