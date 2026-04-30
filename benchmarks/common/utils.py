from pathlib import Path
from rocrate.rocrate import ROCrate
import semantic_benchmark
import uuid

def create_main_ro(path: str, benchmark_object: semantic_benchmark.SemanticBenchmark):
    crate = ROCrate()
    input_path = Path(path)

    if not input_path.is_dir():
        raise NotADirectoryError(f"{path} is not a valid directory")

    subCrates = []
    
    for subfolder in sorted(input_path.iterdir()):
        if subfolder.is_dir():
            subCrates.extend(sorted(subfolder.glob("SubCrate.zip")))

    if not subCrates:
        raise ValueError("No .zip files found inside subfolders of the specified directory")

    for subCrate in subCrates:
        crate.add_file(
            source=str(subCrate),
            dest_path=str(subCrate.relative_to(input_path)),
            properties={}
        )
    
    object_ids = []

    for subfolder in sorted(input_path.iterdir()):
        if subfolder.is_dir():
            obj_id = f"#{uuid.uuid4()}"
            crate.add_jsonld({
                "@id": obj_id,
                "@type": "PropertyValue",
                "name": subfolder.name
            })
            object_ids.append({"@id": obj_id})

    crate.add_jsonld({
        "@id": f"#{uuid.uuid4()}",
        "@type": "CreateAction",
        "name": "Simulation Run",
        "object": object_ids,
    })
    
    crate.write_zip(f"RO.zip")
    
def merge_all_rocrates_as_subcrates(
    input_folder: str,
    output_zip: str,
    parent_name: str = "Merged RO-Crate",
    parent_description: str = "This RO-Crate contains multiple nested RO-Crates as subcrates."
):
    """
    Merge all zipped RO-Crates in a folder into a single RO-Crate
    using the Subcrate mechanism (OPTION A).

    Parameters:
        input_folder (str): Folder containing .zip RO-Crates
        output_zip (str): Output merged RO-Crate zip file
        parent_name (str): Name of the merged parent crate
        parent_description (str): Description of the merged parent crate
    """

    input_path = Path(input_folder)

    if not input_path.is_dir():
        raise NotADirectoryError(f"{input_folder} is not a valid directory")

    # Create new parent crate
    merged = ROCrate()
    merged.name = parent_name
    merged.description = parent_description

    zip_files = sorted(input_path.glob("*.zip"))

    if not zip_files:
        raise ValueError("No .zip files found in the specified folder")

    for zip_path in zip_files:
        # Use zip filename (without extension) as subcrate folder name
        subcrate_name = zip_path.stem

        print(f"Adding subcrate: {zip_path.name} → {subcrate_name}/")

        merged.add_subcrate(
            source=str(zip_path),
            dest_path=subcrate_name
        )
    
    # Write final merged crate
    merged.write_zip(output_zip)

    print(f"Merged RO-Crate written to: {output_zip}")
    print(f"Total subcrates added: {len(zip_files)}")


# Example usage
if __name__ == "__main__":
    merge_all_rocrates_as_subcrates(
        input_folder="/Users/mahdi/Downloads/RoCrates",
        output_zip="/Users/mahdi/Downloads/RoCrates/Merged.zip"
    )
    
