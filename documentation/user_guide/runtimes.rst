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
null         (default). Shell commands are executed natively on the user's system. The user is responsible for ensuring the the required toolchain, environment variables and any other dependencies are set up.
docker       Shell commands are executed in a docker container. By default, the official shrinkwrap image will be pulled and used, which contains all dependencies already setup.
docker-local Like docker, but will only look for the container image on the local system. Will not attempt to pull over the network.
podman       Like docker, but runs the container using podman.
podman-local Like docker-local, but runs the container using podman.
============ ====

.. warning::

  ``podman`` and ``podman-local`` are not well-tested, and are probably broken.

The desired runtime can be specified using the ``--runtime`` option, which is a
top-level argument (must come before the command):

.. code-block:: shell

  shrinkwrap --runtime=<name> ...

If using a container runtime (anything other than null), a custom image can
optionally be specified. If omitted, the official shrinkwrap image is used:

.. code-block:: shell

  shrinkwrap --runtime=<name> --image=<name> ...

***********************************
Log into Arm Artifactory Repository
***********************************

The official shrinkwrap docker images are stored in Arm's Artifactory
repository. shrinkwrap will look here for the default image, but will fail
unless you have previously logged your local docker instance into the
repository. This is a one-time operation.

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
