..
 # Copyright (c) 2022, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

#########
Run-Times
#########

Shrinkwrap uses a "runtime" to execute all of its shell commands and allows the
user to choose which runtime to use. Both the design and implementation of this
is borrowed from `Tuxmake <https://tuxmake.org>`_.

Shrinkwrap supports the following set of runtimes:

============ ====
runtime      description
============ ====
null         Shell commands are executed natively on the user's system. The user is responsible for ensuring the the required toolchain, environment variables and any other dependencies are set up.
docker       (default). Shell commands are executed in a docker container. By default, the official shrinkwrap image will be pulled and used, which contains all dependencies already setup.
docker-local Like docker, but will only look for the container image on the local system. Will not attempt to pull over the network.
============ ====

The desired runtime can be specified using the ``--runtime`` option, which is a
top-level argument (must come before the command):

.. code-block:: shell

  shrinkwrap --runtime=<name> ...

If using a container runtime (anything other than null), a custom image can
optionally be specified. If omitted, the official shrinkwrap image is used:

.. code-block:: shell

  shrinkwrap --runtime=<name> --image=<name> ...

*********************
Docker Image Variants
*********************

Shrinkwrap runs on both x86_64 and aarch64 architectures, and provides multiarch
container images so that the correct variant is automatically selected for your
platform. Images are automatically downloaded by shrinkwrap when the ``docker``
runtime is selected.

.. warning::

  There is currently no FVP available for aarch64, so the current aarch64 arch
  images do not include any FVP, and as a consequence, the ``run`` command will
  not work. For the time being, when wanting to run on aarch64 you must install
  your own FVP on your system and follow the recipe at
  :ref:`userguide/recipes:Use a Custom FVP Version`.

====================================================================== ====
image name                                                             description
====================================================================== ====
oss-kernel--docker.artifactory.geo.arm.com/shrinkwrap/base-slim:latest (default). Contains all toolchains, FVPs and other dependencies required to build and run all standard configs. This is suffcient for most use cases and is much smaller.
oss-kernel--docker.artifactory.geo.arm.com/shrinkwrap/base-full:latest Builds upon ``shrinkwraptool/base-slim:latest``, adding aarch32 toolchains (both arm-none-eabi and arm-linux-gnueabihf). These are not needed for standard configs, but will be required if creating a custom config that includes (e.g.) SCP FW. Separated out due to big size increase.
====================================================================== ====

********************
Runtime Requirements
********************

The best way to understand the requirements for the packages available within
the runtime is to look at the dockerfiles for the official shrinkwrap images.
These are available at ``docker/Dockerfile.*``.

***********************************
Log into Arm Artifactory Repository
***********************************

The official shrinkwrap docker images are stored in Arm's Artifactory
repository. shrinkwrap will look here for the default image, but will fail
unless you have previously logged your local docker instance into the
repository. This is a one-time operation.

.. note::

  Only Arm employees are able to access this repository. If you are not an Arm
  employee, you will need to build the image locally on your system. (See
  below).

First, create an **identity token** using the Artifactory UI:

- Goto https://artifactory.geo.arm.com
- Log in by pressing the "Azure" button
- In the top-right drop down menu, select "Edit Profile"
- Click "Generate Identity Token"
- Enter a description (e.g. "shrinkwrap")
- Click "Next"
- Copy the "Reference Token"

Now perform the login on your local system:

.. code-block:: shell

  docker login -u <arm email address> -p <reference token> oss-kernel--docker.artifactory.geo.arm.com

You are now logged in and able to pull shrinkwrap images.

*****************************
Build Container Image Locally
*****************************

If you have a need to build the shrinkwrap container images on your local system,
you can do it as follows:

.. code-block:: shell

  cd docker
  ./build.sh local

This will build an image called
``oss-kernel--docker.artifactory.geo.arm.com/shrinkwrap/base-slim-<ARCH>``
with the tag ``local``. To use the locally built image, call shrinkwrap as
follows if running on an x86_64 system:

.. code-block:: shell

  shrinkwrap --runtime=<name> --image=oss-kernel--docker.artifactory.geo.arm.com/shrinkwrap/base-slim-x86_64:local ...

Or like this if running on an aarch64 system:

.. code-block:: shell

  shrinkwrap --runtime=<name> --image=oss-kernel--docker.artifactory.geo.arm.com/shrinkwrap/base-slim-aarch64:local ...
