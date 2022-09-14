..
 # Copyright (c) 2022, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

########
Overview
########

************
Introduction
************

Shrinkwrap is a tool to simplify the process of building and running firmware on
Arm Fixed Virtual Platforms (FVP). Users simply invoke the tool to build the
required config, then pass their own kernel and rootfs to the tool to boot the
full system on FVP.

Firmware for Arm platforms is becoming increasingly complex with both more
firmware components (TF-A, Hafnium, OP-TEE, Trusty, RMM, EDK2, U-Boot, etc) and
more configuration options, both when building the components and when launching
the FVP. Shrinkwrap solves this problem by abstracting all of this complexity
into a set of configurations, which can be composed and extended. The tool reads
the config and generates appropriate shell commands to build, package and run
the firmware.

See :ref:`user_guide/quickstart:Quick Start Guide` to get up and running.

************
Architecture
************

Shrinkwrap is implemented in Python and has a command line interface similar to
git, with sub-commands that take options. The Python code parses the supplied
config(s) to generate shell commands that are executed in a backend runtime. The
runtime is specified by the user and may be ``null`` (executed natively on the
user's system), or a container runtime such as ``docker`` or ``podman``. For the
container runtimes, a standard image is provided with all tools preinstalled.

********
Features
********

- A simple and intuitive command line interface enables:

  - Building all required firmware components for a given configuration
  - Packaging built firmware components for easy distribution
  - Configuring and booting the FVP with the packaged firmware components

- Introspect and use any of supplied the out-of-box configurations
- Create your own configurations by composing with and extending others
- Choose from multiple runtime engines (Docker, Podman, native)
- Ensure Reproducible builds with supplied runtime container images
- Transparently view the generated bash commands for a given config build or run
- Parallelize builds to make best use of available resources
- Acquire source from Git remote or point to existing Git local repo
- Choose how to redirect each FVP UART terminal I/O:

  - mux to stdout
  - launch telnet
  - automatically launch xterm (only in native runtime)

********************
Repository Structure
********************

=================== ====
Directory           Description
=================== ====
./docker            Scripts to generate docker images used by shrinkwrap's
                    container runtimes.
./documentation     Source for this documentation.
./shrinkwrap        Shrinkwrap Python tool implementation.
./shrinkwrap/config Shrinkwrap standard config store.
=================== ====

******************
Repository License
******************

The software is provided under an MIT license (more details in
:ref:`license_file_link:License`).

Contributions to the project should follow the same license.

*****************************
Contributions and Bug Reports
*****************************

This project has not put in place a process for contributions currently.

For bug reports, please contact Ryan Roberts <ryan.roberts@arm.com>.

********************
Feedback and support
********************

To request support please contact Arm at support@arm.com. Arm licensees may also
contact Arm via their partner managers.

*************
Maintainer(s)
*************

- Ryan Roberts <ryan.roberts@arm.com>
