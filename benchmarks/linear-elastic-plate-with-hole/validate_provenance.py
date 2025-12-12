import argparse
from provenance import ProvenanceAnalyzer


def parse_args():
    parser = argparse.ArgumentParser(
        description="Process research object zip to validate against profile."
    )
    parser.add_argument(
        "--provenance_folderpath",
        type=str,
        required=True,
        help="Path to the folder containing provenance data",
    )
    return parser.parse_args()


def run(args):
    analyzer = ProvenanceAnalyzer(
        provenance_folderpath=args.provenance_folderpath,
        provenance_filename=args.provenance_filename,
    )

    analyzer.validate_provevance()


def main():
    args = parse_args()
    run(args)


if __name__ == "__main__":
    main()
