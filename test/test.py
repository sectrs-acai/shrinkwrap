#!/usr/bin/env python3
# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT


import argparse
import json
import os
import subprocess


RUNTIME = None
IMAGE = None


ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
KERNEL = os.path.join(ASSETS, 'Image')
BOOTWRAPPER = os.path.join(ASSETS, 'linux-system.axf')
ROOTFS = os.path.join(ASSETS, 'rootfs.ext4')


CONFIGS = [
	'ns-preload.yaml',
	'ns-edk2-acpi.yaml',
	'ns-edk2-dt.yaml',
]


ARCHES = [
	'arch/v8.0.yaml',
	'arch/v8.1.yaml',
	'arch/v8.2.yaml',
	'arch/v8.3.yaml',
	'arch/v8.4.yaml',
	'arch/v8.5.yaml',
	'arch/v8.6.yaml',
	'arch/v8.7.yaml',
	'arch/v8.8.yaml',
	'arch/v9.0.yaml',
	'arch/v9.1.yaml',
	'arch/v9.2.yaml',
	'arch/v9.3.yaml',
]


results = []


def print_result(r):
	def report(status, type, config, overlay):
		desc = f'{status.upper()}: {type}: {config},{overlay}'
		count = (1, 0) if status == 'pass' else (0, 1)
		return count[0], count[1], desc

	if r['type'] == 'build':
		configs = r['configs']
	elif r['type'] == 'run':
		configs = [r['config']]
	else:
		assert(False)

	nr_pass = 0
	nr_fail = 0
	for c in configs:
		p, f, desc = report(r['status'],
				      r['type'],
				      c,
				      r['overlay'])
		nr_pass += p
		nr_fail += f
		print(desc)

	return nr_pass, nr_fail


def print_results():
	print('TEST REPORT JSON')
	print(json.dumps(results, indent=4))

	nr_pass = 0
	nr_fail = 0
	print('TEST REPORT SUMMARY')
	for r in results:
		p, f = print_result(r)
		nr_pass += p
		nr_fail += f

	print(f'pass: {nr_pass}, fail: {nr_fail}')


class WrongExit(Exception):
	pass


def run(cmd, timeout=None, expect=0):
	print(f'+ {cmd}')
	ret = subprocess.run(cmd, timeout=timeout, shell=True)
	if ret.returncode != expect:
		raise WrongExit(ret)


def build_configs(configs, overlay=None):
	result = {
		'type': 'build',
		'status': 'fail',
		'error': None,
		'configs': configs,
		'overlay': overlay,
	}

	rt = f'-R {RUNTIME} -I {IMAGE}'
	overlay = f'-o {overlay}' if overlay else ''
	args = f'{" ".join(configs)} {overlay}'

	try:
		run(f'shrinkwrap {rt} clean {args}', None)
		run(f'shrinkwrap {rt} build {args}', None)
		result['status'] = 'pass'
	except Exception as e:
		result['error'] = str(e)

	results.append(result)


def run_config(config, overlay=None, runargs=None, runtime=120):
	result = {
		'type': 'run',
		'status': 'fail',
		'error': None,
		'config': config,
		'overlay': overlay,
		'runargs': runargs,
		'runtime': runtime,
	}

	rt = f'-R {RUNTIME} -I {IMAGE}'
	overlay = f'-o {overlay}' if overlay else ''
	runargs = runargs if runargs else ''
	args = f'{config} {overlay} {runargs}'

	try:
		run(f'shrinkwrap {rt} run {args}', runtime)
		result['status'] = 'pass'
	except Exception as e:
		result['error'] = str(e)

	results.append(result)


def run_config_kern(config, kernel, rootfs, overlay=None, runtime=120):
	kernel = f'-r KERNEL={kernel}'
	rootfs = f'-r ROOTFS={rootfs}'
	run_config(config, overlay, f'{kernel} {rootfs}', runtime)


def run_config_bootwrap(config, bootwrap, rootfs, overlay=None, runtime=120):
	bootwrap = f'-r BOOTWRAPPER={bootwrap}'
	rootfs = f'-r ROOTFS={rootfs}'
	run_config(config, overlay, f'{bootwrap} {rootfs}', runtime)


def do_main():
	for arch in ARCHES:
		build_configs(CONFIGS, arch)
		for config in CONFIGS:
			run_config_kern(config, KERNEL, ROOTFS, arch)

	for arch in ARCHES:
		build_configs(['bootwrapper.yaml'], arch)
		run_config_bootwrap('bootwrapper.yaml', BOOTWRAPPER, ROOTFS, arch)

	print_results()


def main():
	parser = argparse.ArgumentParser()

	parser.add_argument('-R', '--runtime',
		metavar='engine', required=False, default='docker',
		choices=['null', 'docker', 'docker-local'],
		help="""Specifies the environment in which to execute build and
		     run commands. If 'null', executes natively on the host.
		     'docker' attempts to download the image from dockerhub and
		     execute the commands in a container. 'docker-local' is like
		     'docker' but will only look for the image locally. Defaults
		     to 'docker'.""")

	parser.add_argument('-I', '--image',
		metavar='name',
		required=False,
		default='shrinkwraptool/base-slim:latest',
		help="""If using a container runtime, specifies the name of the
		     image to use. Defaults to the official shrinkwrap image.""")

	args = parser.parse_args()

	global RUNTIME
	global IMAGE
	RUNTIME = args.runtime
	IMAGE = args.image

	do_main()


if __name__ == "__main__":
	main()
