#!/usr/bin/env bash
set -e

detect_platform() {
    OS=$(uname -s)
    case "$OS" in
        Linux*)   echo "linux" ;;
        Darwin*)  echo "macos" ;;
        *)        echo "unknown" ;;
    esac
}

check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo "Docker is not installed."
        echo "macOS: Install Docker Desktop"
        echo "Linux: sudo apt install docker.io"
        exit 1
    fi
}

export PLATFORM=$(detect_platform)
export -f detect_platform
export -f check_docker
