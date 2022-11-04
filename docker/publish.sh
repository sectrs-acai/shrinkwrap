#!/bin/bash
# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

set -ex

function usage()
{
    cat << EOF
Creates a manifest list for a multiarch docker image and publishes it so that
users can pull an image using a generic name and the variant for their machine
architecture is automatically selected.

Usage:
$(basename $0) <tag>

Where:
  <tag> is something like "latest" or "v1.0.0".

An image for each of the supported architectures must have already been built
and published with <tag>.
EOF
}

# Parse command line.
if [ "$#" -ne 1 ]; then
    usage
    exit 1
fi
VERSION="$1"
REGISTRY=oss-kernel--docker.artifactory.geo.arm.com/shrinkwrap

# base-slim-nofvp
docker manifest create ${REGISTRY}/base-slim-nofvp:${VERSION} \
	${REGISTRY}/base-slim-nofvp-aarch64:${VERSION} \
	${REGISTRY}/base-slim-nofvp-x86_64:${VERSION}
docker manifest push ${REGISTRY}/base-slim-nofvp:${VERSION}
docker manifest rm ${REGISTRY}/base-slim-nofvp:${VERSION}

# base-slim
docker manifest create ${REGISTRY}/base-slim:${VERSION} \
	${REGISTRY}/base-slim-aarch64:${VERSION} \
	${REGISTRY}/base-slim-x86_64:${VERSION}
docker manifest push ${REGISTRY}/base-slim:${VERSION}
docker manifest rm ${REGISTRY}/base-slim:${VERSION}

# base-full-nofvp
docker manifest create ${REGISTRY}/base-full-nofvp:${VERSION} \
	${REGISTRY}/base-full-nofvp-aarch64:${VERSION} \
	${REGISTRY}/base-full-nofvp-x86_64:${VERSION}
docker manifest push ${REGISTRY}/base-full-nofvp:${VERSION}
docker manifest rm ${REGISTRY}/base-full-nofvp:${VERSION}

# base-full
docker manifest create ${REGISTRY}/base-full:${VERSION} \
	${REGISTRY}/base-full-aarch64:${VERSION} \
	${REGISTRY}/base-full-x86_64:${VERSION}
docker manifest push ${REGISTRY}/base-full:${VERSION}
docker manifest rm ${REGISTRY}/base-full:${VERSION}
