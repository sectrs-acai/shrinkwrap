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

config = _get_loc('SHRINKWRAP_CONFIG', os.path.join(_code_root, 'config'))
build = _get_loc('SHRINKWRAP_BUILD', os.path.join(_data_root, 'build'))
package = _get_loc('SHRINKWRAP_PACKAGE', os.path.join(_data_root, 'package'))
