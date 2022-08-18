import os

def _get_loc(var, default):
	root = os.path.dirname(os.path.dirname(__file__))
	path = os.environ.get(var, os.path.join(root, default))
	return os.path.abspath(path)

config = _get_loc('SHRINKWRAP_CONFIG', 'config')
build = _get_loc('SHRINKWRAP_BUILD', 'build')
package = _get_loc('SHRINKWRAP_PACKAGE', 'package')
