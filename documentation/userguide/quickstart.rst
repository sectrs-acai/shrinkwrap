#################
Quick Start Guide
#################

******************
Install Shrinkwrap
******************

Packages don't yet exist, so currently the only way to install Shrinkwrap is to
install its dependencies and clone the git repository.

Shrinkwrap requires **at least Python 3.7** (for ordered dicts). Older versions
may work, but are not tested.

.. code-block:: shell

  sudo apt-get install docker.io netcat-openbsd python3 python3-pip telnet
  sudo pip3 install termcolor tuxmake
  git clone git@git.gitlab.oss.arm.com:engineering/linux-arm/shrinkwrap.git
  export PATH=$PWD/shrinkwrap/shrinkwrap:$PATH

If using a Python version older than 3.9, you will also need to install the
``graphlib-backport`` pip package:

.. code-block:: shell

  sudo pip3 install graphlib-backport

Now invoke the tool to view help:

.. code-block:: shell

  shrinkwrap --help
  shrinkwrap <command> --help

*********
Use Cases
*********

.. note::

  Before executing the below commands, you must log your local docker install
  into Arm's Artifactory repository. See :ref:`userguide/runtimes:Log into Arm
  Artifactory Repository` for instructions.

  Alternatively, you can choose to run with the ``null`` runtime (which is the
  default if the ``--runtime`` option is omitted). This will cause all commands
  to be executed on the native system. Users are responsible for setting up the
  environment in this case.

********************************************
Use Case: Build & Run ns-preload.yaml Config
********************************************

First, inspect the available configs:

.. code-block:: shell

  shrinkwrap --runtime=docker inspect

This will show all of the (concrete) configs in the config store. The below
output shows a sample. Notice that each config lists its runtime variables along
with their default values. ``None`` means there is no default and the user must
provide a value when running the config.

.. raw:: html

  <p>
  <details>
  <summary><a>Expand</a></summary>

.. code-block:: none

  name:                cca.yaml

  description:         Brings together TF-A, RMM, Hafnium and a set of simple
                       secure partitions to demonstrate Arm CCA running on FVP.

  concrete:            True

  run-time variables:  LOCAL_NET_PORT:         8022
                       BL1:                    ${artifact:BL1}
                       FIP:                    ${artifact:FIP}
                       ROOTFS:                 None
                       KERNEL:                 None

  --------------------------------------------------------------------------------

  name:                ns-edk2-acpi.yaml

  description:         Best choice for: I want to run Linux on FVP, booting with
                       ACPI, and have easy control over its command line.

                       Brings together TF-A and EDK2 to provide a simple non-
                       secure world environment running on FVP. Allows easy
                       specification of the kernel image and command line, and
                       rootfs at runtime (see rtvars). ACPI is provided by UEFI.

                       By default (if not overriding the rtvars) a sensible
                       command line is used that will set up the console for
                       logging and attempt to mount the rootfs image from the
                       FVP's virtio block device. However the default rootfs image
                       is empty, so the kernel will panic when attempting to
                       mount; the user must supply a rootfs if it is required that
                       the kernel completes its boot. No default kernel image is
                       supplied and the config will refuse to run unless it is
                       explicitly specified.

                       Note that the config will boot to the EDK2 main screen and
                       the user must navigate to Boot Manager -> UEFI Shell. Then
                       hit enter to execute startup.nsh, which will boot the
                       kernel as specified. The main UART console is redirected to
                       telnet and the user will be prompted to run the required
                       telnet command in a separate window. This is required due
                       to EDK2's ncurses-like output.

  concrete:            True

  run-time variables:  LOCAL_NET_PORT:         8022
                       BL1:                    ${artifact:BL1}
                       FIP:                    ${artifact:FIP}
                       CMDLINE:                console=ttyAMA0
                                               earlycon=pl011,0x1c090000
                                               root=/dev/vda ip=dhcp
                       KERNEL:                 None
                       ROOTFS:

  --------------------------------------------------------------------------------

  name:                ns-edk2-dt.yaml

  description:         Best choice for: I want to run Linux on FVP, booting with
                       device tree, and have easy control over its command line.

                       Builds on ns-edk2-acpi.yaml, but adds a device tree that is
                       passed to the kernel to use instead of ACPI. See the
                       description in that file for details.

                       An extra rtvar is added (DTB) which allows specification of
                       a custom device tree. By default (if not overriding the
                       rtvar), the upstream kernel device tree is used.

  concrete:            True

  run-time variables:  LOCAL_NET_PORT:         8022
                       BL1:                    ${artifact:BL1}
                       FIP:                    ${artifact:FIP}
                       CMDLINE:                console=ttyAMA0
                                               earlycon=pl011,0x1c090000
                                               root=/dev/vda ip=dhcp
                       KERNEL:                 None
                       ROOTFS:
                       DTB:                    ${artifact:DTB}

  --------------------------------------------------------------------------------

  name:                ns-preload.yaml

  description:         Best choice for: I just want to run Linux on FVP.

                       A simple, non-secure-only configuration where all
                       components are preloaded into memory (TF-A's BL31, DTB and
                       kernel). The system resets directly to BL31. Allows easy
                       specification of a custom command line at build-time (via
                       build.dt.params dictionary) and specification of the device
                       tree, kernel image and rootfs at run-time (see rtvars).

                       By default (if not overriding the rtvars), the upstream
                       kernel device tree is used along with a sensible command
                       line that will set up the console for logging and attempt
                       to mount the rootfs image from the FVP's virtio block
                       device. However the default rootfs image is empty, so the
                       kernel will panic when attempting to mount; the user must
                       supply a rootfs if it is required that the kernel completes
                       its boot. No default kernel image is supplied and the
                       config will refuse to run unless it is explicitly
                       specified.  Note: If specifying a custom dtb at runtime,
                       this will also override any command line specified at build
                       time, since the command line is added to the chosen node of
                       the default dtb.

  concrete:            True

  run-time variables:  LOCAL_NET_PORT:         8022
                       BL1:                    ${artifact:BL1}
                       FIP:                    ${artifact:FIP}
                       BL31:                   ${artifact:BL31}
                       DTB:                    ${artifact:DTB}
                       KERNEL:                 None
                       ROOTFS:

.. raw:: html

  </details>
  </p>

Now build the ``ns-preload.yaml`` config. This is the simplest config that
allows booting a kernel on FVP. (optionally add ``--verbose`` to see all the
output from the component build systems).

.. code-block:: shell

  shrinkwrap --runtime=docker build ns-preload.yaml

This will sync all the required repos, build the components and package the
artifacts.

Alternatively, pass ``--dry-run`` to view the shell script that would have been
run:

.. code-block:: shell

  shrinkwrap --runtime=docker build --dry-run ns-preload.yaml

.. raw:: html

  <p>
  <details>
  <summary><a>Expand</a></summary>

.. code-block:: none

  #!/bin/bash
  # SHRINKWRAP AUTOGENERATED SCRIPT.

  # Exit on error, error on unbound vars and echo commands.
  set -eux

  # Remove old package.
  rm -rf <root>/package/ns-preload.yaml > /dev/null 2>&1 || true
  rm -rf <root>/package/ns-preload > /dev/null 2>&1 || true

  # Create directory structure.
  mkdir -p <root>/build/source/ns-preload
  mkdir -p <root>/package/ns-preload

  # Sync git repo for config=ns-preload component=dt.
  pushd <root>/build/source/ns-preload
  if [ ! -d "dt/.git" ] || [ -f "./.dt_sync" ]; then
          rm -rf dt > /dev/null 2>&1 || true
          mkdir -p .
          touch ./.dt_sync
          git clone git://git.kernel.org/pub/scm/linux/kernel/git/devicetree/devicetree-rebasing.git dt
          pushd dt
          git checkout --force master
          git submodule update --init --checkout --recursive --force
          popd
          rm ./.dt_sync
  fi
  popd

  # Sync git repo for config=ns-preload component=tfa.
  pushd <root>/build/source/ns-preload
  if [ ! -d "tfa/.git" ] || [ -f "./.tfa_sync" ]; then
          rm -rf tfa > /dev/null 2>&1 || true
          mkdir -p .
          touch ./.tfa_sync
          git clone https://git.trustedfirmware.org/TF-A/trusted-firmware-a.git tfa
          pushd tfa
          git checkout --force master
          git submodule update --init --checkout --recursive --force
          popd
          rm ./.tfa_sync
  fi
  popd

  # Build for config=ns-preload component=dt.
  pushd <root>/build/source/ns-preload/dt
  DTS_IN=<root>/build/source/ns-preload/dt/src/arm64/arm/fvp-base-revc.dts
  DTS_OUT=<root>/build/source/ns-preload/dt/src/arm64/arm/fvp-base-revc_args.dts
  if [ -z "console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp" ]; then
  cp $DTS_IN $DTS_OUT
  else
  ESC_PARAMS=$(printf '%s\n' "console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp" | sed -e 's/[\/&]/\\&/g')
  sed "s/chosen {.*};/chosen { bootargs = \"$ESC_PARAMS\"; };/g" $DTS_IN > $DTS_OUT
  fi
  make CPP=${CROSS_COMPILE}cpp -j28 src/arm64/arm/fvp-base-revc_args.dtb
  popd

  # Build for config=ns-preload component=tfa.
  pushd <root>/build/source/ns-preload/tfa
  make BUILD_BASE=<root>/build/build/ns-preload/tfa PLAT=fvp DEBUG=0 LOG_LEVEL=40 ENABLE_SVE_FOR_NS=1 ENABLE_SVE_FOR_SWD=1 ARM_DISABLE_TRUSTED_WDOG=1 FVP_HW_CONFIG_DTS=fdts/fvp-base-gicv3-psci-1t.dts ARM_ARCH_MINOR=5 BRANCH_PROTECTION=1 CTX_INCLUDE_PAUTH_REGS=1 CTX_INCLUDE_MTE_REGS=1 RESET_TO_BL31=1 ARM_LINUX_KERNEL_AS_BL33=1 PRELOADED_BL33_BASE=2214592512 ARM_PRELOADED_DTB_BASE=2181038080 all fip
  popd

  # Copy artifacts for config=ns-preload.
  cp <root>/build/source/ns-preload/dt/src/arm64/arm/fvp-base-revc_args.dtb <root>/package/ns-preload/fvp-base-revc_args.dtb
  cp <root>/build/build/ns-preload/tfa/fvp/release/bl1.bin <root>/package/ns-preload/bl1.bin
  cp <root>/build/build/ns-preload/tfa/fvp/release/bl2.bin <root>/package/ns-preload/bl2.bin
  cp <root>/build/build/ns-preload/tfa/fvp/release/bl31.bin <root>/package/ns-preload/bl31.bin
  cp <root>/build/build/ns-preload/tfa/fvp/release/fip.bin <root>/package/ns-preload/fip.bin

.. raw:: html

  </details>
  </p>

Now start the FVP. We will pass our own kernel and rootfs disk image (you could
add ``--dry-run`` here too to see the FVP command that would have been run):

.. code-block:: shell

  shrinkwrap --runtime=docker run --rtvar=KERNEL=path/to/Image --rtvar=ROOTFS=path/to/rootfs.img ns-preload.yaml

This starts the FVP and multiplexes all the UART terminals to stdout and
forwards stdin to the ``tfa+linux`` uart terminal:

.. raw:: html

  <p>
  <details>
  <summary><a>Expand</a></summary>

.. code-block:: none

  [       fvp ] terminal_0: Listening for serial connection on port 5000
  [       fvp ] terminal_1: Listening for serial connection on port 5001
  [       fvp ] terminal_2: Listening for serial connection on port 5002
  [       fvp ] terminal_3: Listening for serial connection on port 5003
  [       fvp ]
  [       fvp ] Info: FVP_Base_RevC_2xAEMvA: FVP_Base_RevC_2xAEMvA.bp.flashloader0: FlashLoader: Loaded 100 kB from file '<root>/package/ns-preload/fip.bin'
  [       fvp ]
  [       fvp ] Info: FVP_Base_RevC_2xAEMvA: FVP_Base_RevC_2xAEMvA.bp.secureflashloader: FlashLoader: Loaded 30 kB from file '<root>/package/ns-preload/bl1.bin'
  [       fvp ]
  [       fvp ] libdbus-1.so.3: cannot open shared object file: No such file or directory
  [       fvp ] libdbus-1.so.3: cannot open shared object file: No such file or directory
  [ tfa+linux ] NOTICE:  BL31: v2.7(release):v2.7.0-391-g9dedc1ab2
  [ tfa+linux ] NOTICE:  BL31: Built : 09:41:20, Sep 15 2022
  [ tfa+linux ] INFO:    GICv3 with legacy support detected.
  [ tfa+linux ] INFO:    ARM GICv3 driver initialized in EL3
  [ tfa+linux ] INFO:    Maximum SPI INTID supported: 255
  [ tfa+linux ] INFO:    Configuring TrustZone Controller
  [ tfa+linux ] INFO:    Total 8 regions set.
  [ tfa+linux ] INFO:    BL31: Initializing runtime services
  [ tfa+linux ] INFO:    BL31: Preparing for EL3 exit to normal world
  [ tfa+linux ] INFO:    Entry point address = 0x84000000
  [ tfa+linux ] INFO:    SPSR = 0x3c9
  [ tfa+linux ] [    0.000000] Booting Linux on physical CPU 0x0000000000 [0x410fd0f0]
  [ tfa+linux ] [    0.000000] Linux version 5.15.0-rc2-gca9bfbea162d (ryarob01@e125769) (aarch64-none-linux-gnu-gcc (GNU Toolchain for the A-profile Architecture 9.2-2019.12 (arm-9.10)) 9.2.1 20191025, GNU ld (GNU Toolchain for the A-profile Architecture 9.2-2019.12 (arm-9.10)) 2.33.1.20191209) #1 SMP PREEMPT Thu Aug 4 11:31:55 BST 2022
  [ tfa+linux ] [    0.000000] Machine model: FVP Base RevC
  [ tfa+linux ] [    0.000000] earlycon: pl11 at MMIO 0x000000001c090000 (options '')
  [ tfa+linux ] [    0.000000] printk: bootconsole [pl11] enabled
  [ tfa+linux ] [    0.000000] efi: UEFI not found.
  [ tfa+linux ] [    0.000000] Reserved memory: created DMA memory pool at 0x0000000018000000, size 8 MiB
  [ tfa+linux ] [    0.000000] OF: reserved mem: initialized node vram@18000000, compatible id shared-dma-pool
  [ tfa+linux ] [    0.000000] NUMA: No NUMA configuration found
  [ tfa+linux ] [    0.000000] NUMA: Faking a node at [mem 0x0000000080000000-0x00000008ffffffff]
  [ tfa+linux ] [    0.000000] NUMA: NODE_DATA [mem 0x8ff7efc00-0x8ff7f1fff]
  [ tfa+linux ] [    0.000000] Zone ranges:
  [ tfa+linux ] [    0.000000]   DMA      [mem 0x0000000080000000-0x00000000ffffffff]
  [ tfa+linux ] [    0.000000]   DMA32    empty
  [ tfa+linux ] [    0.000000]   Normal   [mem 0x0000000100000000-0x00000008ffffffff]
  [ tfa+linux ] [    0.000000] Movable zone start for each node
  [ tfa+linux ] [    0.000000] Early memory node ranges
  [ tfa+linux ] [    0.000000]   node   0: [mem 0x0000000080000000-0x00000000ffffffff]
  [ tfa+linux ] [    0.000000]   node   0: [mem 0x0000000880000000-0x00000008ffffffff]
  [ tfa+linux ] [    0.000000] Initmem setup node 0 [mem 0x0000000080000000-0x00000008ffffffff]
  [ tfa+linux ] [    0.000000] cma: Reserved 32 MiB at 0x00000000fe000000
  [ tfa+linux ] [    0.000000] psci: probing for conduit method from DT.
  [ tfa+linux ] [    0.000000] psci: PSCIv1.1 detected in firmware.
  [ tfa+linux ] [    0.000000] psci: Using standard PSCI v0.2 function IDs
  [ tfa+linux ] [    0.000000] psci: MIGRATE_INFO_TYPE not supported.
  [ tfa+linux ] [    0.000000] psci: SMC Calling Convention v1.2
  ...

.. raw:: html

  </details>
  </p>

************************************
Use Case: Override Component Version
************************************

You can change many, many configuration options by overlaying a config on top of
an existing config. Here we modify the revision of the TF-A component from the
``master`` branch (the default defined in tfa-base.yaml), to the ``v2.7.0`` tag.
You could also specify the revision as a SHA or override the remote repo URL,
etc.

We will use the ``ns-edk2-dt.yaml`` config to spice things up a bit. This loads
EDK2 on top of TF-A then EDK2 pulls the kernel, dtb and command line from the
host system using semihosting.

.. warning::

  If you have previously built this config, shrinkwrap will skip syncing the git
  repos since they will already exist and it doesn't want to trample any user
  changes. So you will need to force shrinkwrap to re-sync. One approach is to
  delete the following directories:

  - ``<SHRINKWRAP_BUILD>/source/ns-edk2-dt``
  - ``<SHRINKWRAP_BUILD>/build/ns-edk2-dt``

Create a file called ``my-overlay.yaml``:

.. code-block:: yaml

  build:
    tfa:
      repo:
        revision: v2.7.0

Optionally, you can view the final, merged config as follows:

.. code-block:: shell

  shrinkwrap --runtime=docker process --action=merge --overlay=my-overlay.yaml ns-edk2-dt.yaml

Now do a build, passing in the overlay:

.. code-block:: shell

  shrinkwrap --runtime=docker build --overlay=my-overlay.yaml ns-edk2-dt.yaml

Finally, boot the config. Here, were are providing a custom kernel command line.
But you could omit this and a sensible default would be used. Note that because
EDK2 outputs ncurses-like output, this config starts the appropriate terminal in
telnet mode and provides the command that you need to enter in a separate
window. Follow the instructions, then in EDK2, navigate to Boot Manager -> UEFI
Shell. This will cause the kernel to boot:

.. code-block:: shell

  shrinkwrap --runtime=docker run --rtvar=KERNEL=path/to/Image --rtvar=ROOTFS=path/to/rootfs.img --rtvar="CMDLINE=console=ttyAMA0 earlycon=pl011,0x1c090000 root=/dev/vda ip=dhcp" ns-edk2-dt.yaml

***********************************
Use Case: Reuse Existing Local Repo
***********************************

By default, shrinkwrap will sync the git repos for all required components to a
private location the first time you build a given config. However, sometimes you
want shrinkwrap to reuse a repo that already exists on your local system. In
this case, Shrinkwrap will build this source into its own private build tree,
leaving the source tree unmodified.

.. warning::

  Components support building in a tree separate from the source to differing
  degrees. For example, TF-A will always build fiptool in the source tree,
  although it will build all the FW components in the correct build tree. So
  depending on the component you are sharing source for, you may see some build
  artifacts appear.

Create a file called ``my-overlay.yaml``:

.. code-block:: yaml

  build:
    tfa:
      sourcedir: /path/to/my/tfa/git/repo

Now do a build, passing in the overlay:

.. code-block:: shell

  shrinkwrap --runtime=docker build --overlay=my-overlay.yaml ns-edk2-dt.yaml
