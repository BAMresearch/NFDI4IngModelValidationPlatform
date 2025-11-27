#!/usr/bin/env bash
set -e

source "$(dirname "$0")/platform_utils.sh"
source "$(dirname "$0")/config.sh"

echo "======================================"
echo " LOCAL BENCHMARK WORKFLOW"
echo " Platform: $PLATFORM"
echo " Root: $PROJECT_ROOT"
echo "======================================"

# Make scripts executable
chmod +x local_workflow/*.sh

# 1. Build all Docker images
bash "$(dirname "$0")/build_all_images.sh"

# 2. Run all benchmarks
bash "$(dirname "$0")/run_all_benchmarks.sh"

echo "======================================"
echo " WORKFLOW COMPLETE"
echo "======================================"
