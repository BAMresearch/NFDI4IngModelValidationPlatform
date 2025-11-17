# NFDI Benchmark Setup on macOS with Docker

Kratos Multiphysics is **not natively supported on macOS**, so we use Docker to run it. Below is a step-by-step guide to set up and run the NFDI Benchmark workflow on a Mac with Apple Silicon (ARM) architecture.  

---

## 1. Choose a Base Docker Image

Kratos is distributed only for **x86_64 (amd64) Linux**. Since Apple Silicon uses ARM, we need to emulate x86_64 in Docker:

```dockerfile
FROM --platform=linux/amd64 ubuntu:22.04
```

This `--platform=linux/amd64` flag ensures Docker emulates an x86_64 environment, allowing Kratos to run correctly.

---

## 2. Build the Docker Image

Navigate to the repository folder and build the Docker image:

```bash
cd ~/NFDI_benchmark/NFDI4IngModelValidationPlatform
docker build -t nfdi_benchmark -f dockerfiles/Dockerfile
```

---

## 3. Run the Docker Container

Run the container and mount the local repository inside it:
```bash
docker run --platform linux/amd64 -it \
    --name nfdi_benchmark_container \
    -v $(pwd):/NFDI_Benchmark \
    nfdi_benchmark:latest
```

This makes the local repository available inside the container and opens an interactive shell.  

To rerun the same container
```bash
docker start -ai <con_id>
```

> **Note:** Docker containers do not start with an interactive login shell, so `conda activate` does not work immediately. We must initialize Conda first.

```bash
# Initialize Conda
source /opt/miniforge/etc/profile.d/conda.sh

# Activate the model-validation environment
conda activate model-validation

# Navigate to the benchmark folder
cd benchmarks/linear-elastic-plate-with-hole
```

---

## 4. Generate Configuration and Run Workflow

Generate configuration files:

```bash
python generate_config.py
```

Run the Snakemake workflow:

```bash
snakemake --use-conda --force --cores all
```

Snakemake will look for a `Snakefile` inside `linear-elastic-plate-with-hole` and execute it.

---

## 5. Pre-build Conda Environments (Workaround for Architecture Issues)

Snakemake’s automatic Conda environment creation fails under Docker emulation due to architecture mismatches. The solution is to pre-create the environments manually.

### 5.1 Kratos Environment

```bash
source /opt/miniforge/etc/profile.d/conda.sh
mamba env create -n kratos-sim -f kratos/environment_simulation.yml
conda activate kratos-sim

# Test Kratos installation
python -c "import KratosMultiphysics; print(KratosMultiphysics.__version__)"
```

### 5.2 FEniCS Environment

FEniCS can fail when running multiple threads under emulation, so we limit it to a single thread:

```bash
mamba env create -f fenics/environment_simulation.yml -n fenics-sim
conda activate fenics-sim

# Limit threads to avoid OpenMP/QEMU errors
export OMP_NUM_THREADS=1
export KMP_AFFINITY=disabled

# Test FEniCS installation
python -c "import dolfinx; print('FEniCSx imported OK')"
```

### 5.3 Mesh Environment

```bash
conda deactivate
mamba env create -f environment_mesh.yml -n mesh
```

### 5.4 Postprocessing Environment

```bash
mamba env create -f environment_postprocessing.yml -n postprocessing
```

> Once these environments are created, Snakemake will skip environment creation, significantly speeding up workflow execution.

---

## 6. Re-run Snakemake Using Pre-built Environments

```bash
snakemake --use-conda --cores all
```

---

## 7. Generate Metadata / Provenance Report

```bash
snakemake --use-conda --force --cores all \
    --reporter metadata4ing \
    --report-metadata4ing-paramscript parameter_extractor.py \
    --report-metadata4ing-filename metadata4ing_provenance
```

This updates all metadata and provenance information without re-running the simulations.

---

## 8. Extract Snakemake Outputs (Optional)

```bash
mkdir -p ./metadata4ing_provenance
unzip -o ./metadata4ing_provenance.zip -d ./metadata4ing_provenance
```

---

## 9. Plot Results

```bash
python plot_provenance.py ./metadata4ing_provenance
```

---

✅ **Notes / Tips:**
- Always initialize Conda inside the Docker container before activating environments.
- Limit FEniCS to a single thread on macOS with ARM to avoid OpenMP errors.
- Pre-building environments avoids repeated environment creation and reduces workflow runtime.

