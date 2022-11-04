#!/bin/bash
# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

set -e

function usage()
{
    cat << EOF
Builds and optionally publishes shrinkwrap docker images for the architecture
of the host system. (x86_64 and aarch64 are currently supported).

Usage:
$(basename $0) <tag>

Where:
  <tag> is something like "latest" or "v1.0.0".

If <tag> is "local", the resulting image is NOT pushed to the remote repository.
EOF
}

# Parse command line.
if [ "$#" -ne 1 ]; then
    usage
    exit 1
fi
VERSION="${1}"
ARCH=$(uname -p)
REGISTRY=oss-kernel--docker.artifactory.geo.arm.com/shrinkwrap

# Configure the arch-specific variables which are passed to the Dockerfile.
if [ "${ARCH}" == "x86_64" ]; then
	TCH_PKG_URL_AARCH64=https://developer.arm.com/-/media/Files/downloads/gnu/11.3.rel1/binrel
	TCH_PKG_NAME_AARCH64=arm-gnu-toolchain-11.3.rel1-x86_64-aarch64-none-elf.tar.xz
	TCH_PATH_AARCH64=arm-gnu-toolchain-11.3.rel1-x86_64-aarch64-none-elf/bin
	TCH_PKG_URL_AARCH32=https://developer.arm.com/-/media/Files/downloads/gnu/11.3.rel1/binrel
	TCH_PKG_NAME_AARCH32=arm-gnu-toolchain-11.3.rel1-x86_64-arm-none-eabi.tar.xz
	TCH_PATH_AARCH32=arm-gnu-toolchain-11.3.rel1-x86_64-arm-none-eabi/bin
	FVP_PKG_URL=https://developer.arm.com/-/media/Files/downloads/ecosystem-models
	FVP_PKG_NAME=FVP_Base_RevC-2xAEMvA_11.18_16_Linux64.tgz
	FVP_MODEL_DIR=Base_RevC_AEMvA_pkg/models/Linux64_GCC-9.3
	FVP_PLUGIN_DIR=Base_RevC_AEMvA_pkg/plugins/Linux64_GCC-9.3
elif [ "${ARCH}" == "aarch64" ]; then
	TCH_PKG_URL_AARCH64=https://developer.arm.com/-/media/Files/downloads/gnu/11.3.rel1/binrel
	TCH_PKG_NAME_AARCH64=arm-gnu-toolchain-11.3.rel1-aarch64-aarch64-none-elf.tar.xz
	TCH_PATH_AARCH64=arm-gnu-toolchain-11.3.rel1-aarch64-aarch64-none-elf/bin
	TCH_PKG_URL_AARCH32=https://developer.arm.com/-/media/Files/downloads/gnu/11.3.rel1/binrel
	TCH_PKG_NAME_AARCH32=arm-gnu-toolchain-11.3.rel1-aarch64-arm-none-eabi.tar.xz
	TCH_PATH_AARCH32=arm-gnu-toolchain-11.3.rel1-aarch64-arm-none-eabi/bin
	FVP_PKG_NAME=none
else
	echo "Host architecture ${ARCH} not supported"
	exit 1
fi

echo "Building for version ${VERSION} for ${ARCH}..."

# Build the image.
wget -q -O ${TCH_PKG_NAME_AARCH64} ${TCH_PKG_URL_AARCH64}/${TCH_PKG_NAME_AARCH64}
wget -q -O ${TCH_PKG_NAME_AARCH32} ${TCH_PKG_URL_AARCH32}/${TCH_PKG_NAME_AARCH32}
if [ "${FVP_PKG_NAME}" != "none" ]; then
	wget -q -O ${FVP_PKG_NAME} ${FVP_PKG_URL}/${FVP_PKG_NAME}
else
	touch ${FVP_PKG_NAME}
fi
docker build \
	--build-arg=BASE=docker.io/library/debian:bullseye-slim \
	--build-arg=TCH_PKG_NAME_AARCH64=${TCH_PKG_NAME_AARCH64} \
	--build-arg=TCH_PATH_AARCH64=${TCH_PATH_AARCH64} \
	--file=Dockerfile.slim \
	--tag=${REGISTRY}/base-slim-nofvp-${ARCH}:${VERSION} \
	.
docker build \
	--build-arg=BASE=${REGISTRY}/base-slim-nofvp-${ARCH}:${VERSION} \
	--build-arg=FVP_PKG_NAME=${FVP_PKG_NAME} \
	--build-arg=FVP_MODEL_DIR=${FVP_MODEL_DIR} \
	--build-arg=FVP_PLUGIN_DIR=${FVP_PLUGIN_DIR} \
	--file=Dockerfile.fvp \
	--tag=${REGISTRY}/base-slim-${ARCH}:${VERSION} \
	.
docker build \
	--build-arg=BASE=${REGISTRY}/base-slim-nofvp-${ARCH}:${VERSION} \
	--build-arg=TCH_PKG_NAME_AARCH32=${TCH_PKG_NAME_AARCH32} \
	--build-arg=TCH_PATH_AARCH32=${TCH_PATH_AARCH32} \
	--file=Dockerfile.full \
	--tag=${REGISTRY}/base-full-nofvp-${ARCH}:${VERSION} \
	.
docker build \
	--build-arg=BASE=${REGISTRY}/base-full-nofvp-${ARCH}:${VERSION} \
	--build-arg=FVP_PKG_NAME=${FVP_PKG_NAME} \
	--build-arg=FVP_MODEL_DIR=${FVP_MODEL_DIR} \
	--build-arg=FVP_PLUGIN_DIR=${FVP_PLUGIN_DIR} \
	--file=Dockerfile.fvp \
	--tag=${REGISTRY}/base-full-${ARCH}:${VERSION} \
	.
rm -rf ${TCH_PKG_NAME_AARCH64} > /dev/null 2>&1 || true
rm -rf ${TCH_PKG_NAME_AARCH32} > /dev/null 2>&1 || true
rm -rf ${FVP_PKG_NAME} > /dev/null 2>&1 || true

# If not a local version, publish the image.
if [ "${VERSION}" != "local" ]; then
	docker push ${REGISTRY}/base-slim-nofvp-${ARCH}:${VERSION}
	docker push ${REGISTRY}/base-slim-${ARCH}:${VERSION}
	docker push ${REGISTRY}/base-full-nofvp-${ARCH}:${VERSION}
	docker push ${REGISTRY}/base-full-${ARCH}:${VERSION}
fi
