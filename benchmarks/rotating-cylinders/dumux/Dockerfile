# SPDX-FileCopyrightText: Copyright © DuMux Project contributors, see AUTHORS.md in root folder
# SPDX-License-Identifier: GPL-3.0-or-later

# dumuxModule docker container
# see https://github.com/phusion/baseimage-docker for information on the base image
# It is Ubuntu LTS customized for better Docker compatibility
FROM phusion/baseimage:jammy-1.0.4
MAINTAINER sarbani.roy@simtech.uni-stuttgart.de

# run Ubuntu update as advised on https://github.com/phusion/baseimage-docker
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get upgrade -y -o Dpkg::Options::="--force-confold" \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# install the basic dependencies
RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
        ca-certificates \
        vim \
        python3-dev \
        python3-pip \
        git \
        pkg-config \
        cmake \
        build-essential \
        gfortran \
        mpi-default-bin \
        mpi-default-dev \
        libsuitesparse-dev \
        libsuperlu-dev \
        libeigen3-dev \
        doxygen \
        wget \
        clang-15 \
        lld-15 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# set Clang 15 as default compiler
ENV CC=clang-15
ENV CXX=clang++-15

# switch to the dumux user and set the working directory
# USER dumux
WORKDIR /dumux

# create a shared volume communicating with the host
RUN mkdir /dumux/shared
VOLUME /dumux/shared

# Copy dumuxModule from local build context into the container
COPY dumuxModule /dumux/dumuxmodule

# Install the dumux module and its dependencies
# This expects the install script to do everything from clone to configure
COPY install_dumuxModule.py /dumux/install_dumuxModule.py
RUN python3 /dumux/install_dumuxModule.py && rm -f /dumux/install_dumuxModule.py

# Build and run the specific DUMUX test
RUN cd /dumux/dumuxmodule/build-cmake/test/freeflow/navierstokes/rotatingcylinders \
    && make test_ff_navierstokes_rotatingcylinders \
    && ./test_ff_navierstokes_rotatingcylinders

# set entry point like advised https://github.com/phusion/baseimage-docker
# this sets the permissions right, see above
ENTRYPOINT ["/sbin/my_init","--quiet","--","/bin/bash","-l","-c"]

# start interactive shell
CMD ["/bin/bash","-i"]