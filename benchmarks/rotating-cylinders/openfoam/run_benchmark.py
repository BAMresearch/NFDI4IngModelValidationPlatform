import subprocess
from pathlib import Path

root_dir = Path(__file__).resolve().parent
snakefile_path = root_dir / "Snakefile"

subprocess.run([
    "snakemake",
    "-s",
    str(snakefile_path),
    "--use-singularity",
    "--cores",
    "all",
    "--resources",
    "serial_run=1",
    "--force"
], check=True, cwd=root_dir)
