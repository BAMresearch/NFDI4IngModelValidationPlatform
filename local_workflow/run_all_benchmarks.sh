#!/usr/bin/env bash
set -e

source "$(dirname "$0")/config.sh"

WF_DIR="$(dirname "$0")"

echo "Running ALL benchmarks..."

for BENCH in $(ls "$BENCHMARKS_DIR"); do
    BENCH_PATH="$BENCHMARKS_DIR/$BENCH"

    if [[ -d "$BENCH_PATH" ]]; then
        SCRIPT="$WF_DIR/run_${BENCH}.sh"

        if [[ -f "$SCRIPT" ]]; then
            echo "======================================"
            echo "Running benchmark script for: $BENCH"
            echo "$SCRIPT"
            echo "======================================"
            bash "$SCRIPT"
        else
            echo "No script found for benchmark: $BENCH"
            echo "Expected: run_${BENCH}.sh"
        fi
    fi
done

echo "All benchmark scripts executed."
