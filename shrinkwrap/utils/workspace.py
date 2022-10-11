# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import os

_code_root = os.path.dirname(os.path.dirname(__file__))
_data_root = os.path.expanduser('~/.shrinkwrap')

def _get_loc(var, default):
	path = os.environ.get(var, default)
	path = os.path.abspath(path)
	os.makedirs(path, exist_ok=True)
	return path

build = _get_loc('SHRINKWRAP_BUILD', os.path.join(_data_root, 'build'))
package = _get_loc('SHRINKWRAP_PACKAGE', os.path.join(_data_root, 'package'))

_configs = None

def configs():
	global _configs

	if _configs is None:
		value = os.environ.get('SHRINKWRAP_CONFIG')
		if not value:
			raise Exception('SHRINKWRAP_CONFIG environment variable not set.')
		_configs = value.split(':')

	return _configs

def config(path, join=True):
	for config in configs():
		p = os.path.join(config, path) if join else f'{config}{path}'
		if os.path.exists(p):
			return config
	return None