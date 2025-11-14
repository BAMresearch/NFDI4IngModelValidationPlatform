# -----------------------------
# Dockerfile for NFDI_Benchmark
# -----------------------------

# Base image similar to GitHub Actions ubuntu-latest
FROM --platform=linux/amd64 ubuntu:22.04

# Avoid interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

# Install basic dependencies
RUN apt-get update && apt-get install -y \
    wget curl git unzip zip bzip2 libbz2-dev python3 python3-pip \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Miniforge3 for amd64 architecture
RUN wget https://github.com/conda-forge/miniforge/releases/download/24.11.0-0/Miniforge3-24.11.0-0-Linux-x86_64.sh && \
    bash Miniforge3-24.11.0-0-Linux-x86_64.sh -b -p /opt/miniforge && \
    rm Miniforge3-24.11.0-0-Linux-x86_64.sh

# Add conda/mamba to PATH
ENV PATH="/opt/miniforge/bin:$PATH"

ENV OMP_NUM_THREADS=1
ENV KMP_AFFINITY=disabled
ENV OMP_PROC_BIND=FALSE

# Set working directory inside container
WORKDIR /NFDI_Benchmark

# Copy only environment yaml first to leverage Docker caching
COPY environment_benchmarks.yml /NFDI_Benchmark/

# Create model-validation environment
RUN mamba env create -n model-validation -f environment_benchmarks.yml && \
    echo "conda activate model-validation" >> ~/.bashrc

# Copy the rest of the repo into container
COPY . /NFDI_Benchmark

# Use bash login shell by default
SHELL ["bash", "-l", "-c"]

# Drop into interactive bash shell when container starts
CMD ["/bin/bash"]