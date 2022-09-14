..
 # Copyright (c) 2022, Arm Limited.
 #
 # SPDX-License-Identifier: MIT

#########
Run-Times
#########

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
