# Shrinkwrap

Shrinkwrap is a tool to simplify the process of building and running firmware on
Arm Fixed Virtual Platforms (FVP). Users simply invoke the tool to build the
required config, then pass their own kernel and rootfs to the tool to boot the
full system on FVP.

- Documentation is available at: [ReadTheDocs](https://shrinkwrap.docs.arm.com)
- Source Code is available at: [GitLab](https://gitlab.arm.com/tooling/shrinkwrap)
- Shrinkwrap Container Images are available at: [DockerHub](https://hub.docker.com/u/shrinkwraptool)

To build the docs locally, the following packages need to be installed on the
host:

    sudo apt-get install python3-pip
    pip3 install -U -r documentation/requirements.txt

To build and generate the documentation in html format, run:

    sphinx-build -b html -a -W documentation public

To render and explore the documentation, simply open `public/index.html` in a
web browser.
