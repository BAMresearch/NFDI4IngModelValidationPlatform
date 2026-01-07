#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright © DuMux Project contributors, see AUTHORS.md in root folder
# SPDX-License-Identifier: GPL-3.0-or-later

IMAGE_NAME=git.iws.uni-stuttgart.de:4567/benchmarks/rotating-cylinders:1.0

# the host directory ...
SHARED_DIR_HOST="$(pwd)"
# ... that is mounted into this container directory:
SHARED_DIR_CONTAINER="/dumux/shared"

help ()
{
    echo ""
    echo "Usage: docker_rotatingCylinders.sh <command> [options]"
    echo ""
    echo "  docker_rotatingCylinders.sh open [image]      - run a container from the image."
    echo "  docker_rotatingCylinders.sh help              - display this message."
    echo ""
    echo "Optionally supply a Docker image name to the open command."
    echo ""
}

# start a container. Only argument is the Docker image.
open()
{
    IMAGE="$1"

    if docker ps -a --format '{{.Names}}' | grep -Eq "^dumux_rotatingCylinders\$"; then
        echo "Removing existing container 'dumux_rotatingCylinders'"
        docker rm -f dumux_rotatingCylinders
    fi

    docker run --rm \
        -e HOST_UID=$(id -u) \
        -e HOST_GID=$(id -g) \
        -v "$SHARED_DIR_HOST:$SHARED_DIR_CONTAINER" \
        --name dumux_rotatingCylinders \
        "$IMAGE"
}

# Check if user specified valid command otherwise print help message
if [ "$1" == "open" ]; then
    IMAGE="$2" : ${IMAGE:="$IMAGE_NAME"}
    open $IMAGE
else
    help
    exit 1
fi
