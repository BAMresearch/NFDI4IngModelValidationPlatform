"""
Provenance Validation Module

This module provides functionality to validate research object provenance data
against defined profiles. It processes RO-Crate metadata to ensure compliance
with provenance standards.

"""

import argparse
from provenance import ProvenanceAnalyzer


def parse_args():
    """
    Parse command-line arguments for provenance validation.

    Returns:
        argparse.Namespace: Parsed command-line arguments containing:
            - provenance_folderpath (str): Path to the folder containing provenance data
            - provenance_filename (str): Name of the provenance metadata file
                                        (default: 'ro-crate-metadata.json')
    """
    parser = argparse.ArgumentParser(
        description="Process research object zip to validate against profile."
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
    return parser.parse_args()


def run(args):
    """
    Execute the provenance validation process.

    Creates a ProvenanceAnalyzer instance with the provided arguments and
    runs the validation against the configured profile.

    Args:
        args (argparse.Namespace): Parsed command-line arguments containing
                                   provenance folder path and filename

    Raises:
        FileNotFoundError: If the specified provenance file doesn't exist
        ValidationError: If the provenance data fails validation checks
    """
    analyzer = ProvenanceAnalyzer(
        provenance_folderpath=args.provenance_folderpath,
        provenance_filename=args.provenance_filename,
    )

    analyzer.validate_provenance()


def main():
    """
    Main entry point for the provenance validation script.

    Parses command-line arguments and initiates the validation process.
    This function is called when the script is executed directly.

    Usage:
        python validate_provenance.py --provenance_folderpath /path/to/folder
        python validate_provenance.py --provenance_folderpath /path/to/folder \
            --provenance_filename custom-metadata.json

    Exits:
        The script will exit with a non-zero status code if validation fails
        or if required arguments are not provided.
    """
    args = parse_args()
    run(args)


if __name__ == "__main__":
    main()