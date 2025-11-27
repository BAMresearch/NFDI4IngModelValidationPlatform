#!/usr/bin/env bash

# Top-level project dir
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)

DOCKERFILES_DIR="$PROJECT_ROOT/dockerfiles"
BENCHMARKS_DIR="$PROJECT_ROOT/benchmarks"

# Image tags
IMG_BASE="benchmarks-base"
IMG_MESH="benchmarks-mesh"
IMG_FENICS="benchmarks-fenics"
IMG_KRATOS="benchmarks-kratos"
IMG_POST="benchmarks-postprocessing"
