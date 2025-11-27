#!/usr/bin/env bash
set -euo pipefail

# Load config
source "$(dirname "$0")/config.sh"

# Detect OS
OS_TYPE="$(uname -s)"
PLATFORM=""
if [[ "$OS_TYPE" == "Darwin" ]]; then
    PLATFORM="--platform linux/amd64"
fi

# Build Docker images if they don't exist
build_image_if_missing() {
    local image_name=$1
    local dockerfile=$2

    if ! docker image inspect "$image_name" > /dev/null 2>&1; then
        echo "Building Docker image: $image_name"
        if [[ -n "$PLATFORM" ]]; then
            docker buildx build $PLATFORM --load -t "$image_name" -f "$dockerfile" .
        else
            docker build -t "$image_name" -f "$dockerfile" .
        fi
    else
        echo "Docker image $image_name already exists"
    fi
}

# Ensure ci-base exists and built for correct platform
if ! docker image inspect ci-base:latest > /dev/null 2>&1; then
    echo "Building local ci-base image from Dockerfile.base"
    if [[ -n "$PLATFORM" ]]; then
        docker buildx build $PLATFORM --load -t ci-base:latest -f "$PROJECT_ROOT/dockerfiles/Dockerfile.base" .
    else
        docker build -t ci-base:latest -f "$PROJECT_ROOT/dockerfiles/Dockerfile.base" .
    fi
fi

# Build benchmark images
build_image_if_missing "$IMG_MESH"  "$PROJECT_ROOT/dockerfiles/Dockerfile.mesh"
build_image_if_missing "$IMG_FENICS" "$PROJECT_ROOT/dockerfiles/Dockerfile.fenics"
build_image_if_missing "$IMG_KRATOS" "$PROJECT_ROOT/dockerfiles/Dockerfile.kratos"
build_image_if_missing "$IMG_POST" "$PROJECT_ROOT/dockerfiles/Dockerfile.postprocessing"

# Paths on host (for mkdir purposes)
OUTPUT_DIR="$BENCHMARKS_DIR/linear-elastic-plate-with-hole/results"
mkdir -p "$OUTPUT_DIR/mesh" "$OUTPUT_DIR/fenics" "$OUTPUT_DIR/kratos"

echo "Running benchmark: linear-elastic-plate-with-hole"
echo "Benchmark path: $BENCHMARKS_DIR/linear-elastic-plate-with-hole"
echo "Output path: $OUTPUT_DIR"

# Generate config files inside container
docker run --rm -v "$PROJECT_ROOT":/workspace -w "/workspace/benchmarks/linear-elastic-plate-with-hole" "$IMG_MESH" \
    python3 generate_config.py

# Mesh generation for all parameter files inside container
docker run --rm -v "$PROJECT_ROOT":/workspace -w "/workspace/benchmarks/linear-elastic-plate-with-hole" "$IMG_MESH" \
    bash -c "for f in parameters_*.json; do \
                 python3 create_mesh.py --input_parameter_file \"\$f\" \
                     --output_mesh_file \"results/mesh/mesh_\${f%.json}.msh\"; \
             done"


echo "Running Kratos simulations for benchmark: linear-elastic-plate-with-hole"

# Run Kratos simulations inside container
docker run --rm -v "$PROJECT_ROOT":/workspace -w "/workspace/benchmarks/linear-elastic-plate-with-hole" "$IMG_KRATOS" \
    bash -c "for f in parameters_*.json; do \
                 # Convert mesh to MDPA
                 python kratos/msh_to_mdpa.py \
                     --input_parameter_file \"\$f\" \
                     --input_mesh_file \"results/mesh/mesh_\${f%.json}.msh\" \
                     --output_mdpa_file \"results/kratos/mesh_\${f%.json}.mdpa\"; \
                 \
                 # Create Kratos input files
                 python kratos/create_kratos_input.py \
                     --input_parameter_file \"\$f\" \
                     --input_mdpa_file \"results/kratos/mesh_\${f%.json}.mdpa\" \
                     --input_kratos_input_template kratos/input_template.json \
                     --input_material_template kratos/StructuralMaterials_template.json \
                     --output_kratos_inputfile \"results/kratos/ProjectParameters_\${f%.json}.json\" \
                     --output_kratos_materialfile \"results/kratos/MaterialParameters_\${f%.json}.json\"; \
                 \
                 # Run Kratos simulation
                 python kratos/run_kratos_simulation.py \
                     --input_parameter_file \"\$f\" \
                     --input_kratos_inputfile \"results/kratos/ProjectParameters_\${f%.json}.json\" \
                     --input_kratos_materialfile \"results/kratos/MaterialParameters_\${f%.json}.json\"; \
             done"

echo "Running Fenics simulations for benchmark: linear-elastic-plate-with-hole"

# Run Fenics simulations inside container
docker run --rm -v "$PROJECT_ROOT":/workspace -w "/workspace/benchmarks/linear-elastic-plate-with-hole" "$IMG_FENICS" \
    bash -c "for f in parameters_*.json; do \
                 config_name=\"\${f%.json}\"; \
                 python fenics/run_fenics_simulation.py \
                     --input_parameter_file \"\$f\" \
                     --input_mesh_file \"results/mesh/mesh_\${config_name}.msh\" \
                     --output_solution_file_zip \"results/fenics/solution_field_data_\${config_name}.zip\" \
                     --output_metrics_file \"results/fenics/solution_metrics_\${config_name}.json\"; \
             done"

# echo "Running Postprocessing for benchmark: linear-elastic-plate-with-hole"

# # Run postprocessing inside container
# docker run --rm \
#   -v "$(pwd)":/workspace \
#   -w /workspace/benchmarks "$IMG_POST" \
#   bash -c "
#     echo 'Generating metadata...';
#     python common/parameter_extractor.py ./linear-elastic-plate-with-hole/results ./linear-elastic-plate-with-hole/metadata4ing_provenance.zip;

#     # echo 'Extracting ZIP...';
#     # mkdir -p linear-elastic-plate-with-hole/metadata4ing_provenance;
#     # unzip -o linear-elastic-plate-with-hole/metadata4ing_provenance.zip -d linear-elastic-plate-with-hole/metadata4ing_provenance;

#     echo 'Plotting provenance...';
#     python linear-elastic-plate-with-hole/plot_metrics.py ./linear-elastic-plate-with-hole/metadata4ing_provenance
#   "

# echo "Postprocessing complete. Results are in: $OUTPUT_DIR"

echo "Benchmark linear-elastic-plate-with-hole completed!"
