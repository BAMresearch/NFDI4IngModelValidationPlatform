#!/usr/bin/env bash
set -e

source "$(dirname "$0")/platform_utils.sh"
source "$(dirname "$0")/config.sh"

check_docker

echo "Building Docker images..."

docker build -t $IMG_BASE        -f $DOCKERFILES_DIR/Dockerfile.base          $PROJECT_ROOT
docker build -t $IMG_MESH        -f $DOCKERFILES_DIR/Dockerfile.mesh          $PROJECT_ROOT
docker build -t $IMG_FENICS      -f $DOCKERFILES_DIR/Dockerfile.fenics        $PROJECT_ROOT
docker build -t $IMG_KRATOS      -f $DOCKERFILES_DIR/Dockerfile.kratos        $PROJECT_ROOT
docker build -t $IMG_POST        -f $DOCKERFILES_DIR/Dockerfile.postprocessing $PROJECT_ROOT

echo "All images built."
