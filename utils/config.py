import json
import os
import re
import shrinkwrap.utils.workspace as workspace


def _component_normalize(component):
	"""
	Fills in any missing lists or dictionaries with empty ones.
	"""
	if 'repo' not in component:
		component['repo'] = {}

	if 'fetch' not in component['repo']:
		component['repo']['fetch'] = None

	if 'name' not in component['repo']:
		component['repo']['name'] = None

	if 'revision' not in component['repo']:
		component['repo']['revision'] = None

	if 'buildroot' not in component:
		component['buildroot'] = None

	if 'prebuild' not in component:
		component['prebuild'] = []

	if 'build' not in component:
		component['build'] = []

	if 'postbuild' not in component:
		component['postbuild'] = []

	if 'params' not in component:
		component['params'] = {}

	if 'artifacts' not in component:
		component['artifacts'] = {}

	return component


def _build_normalize(build):
	"""
	Fills in any missing lists or dictionaries with empty ones.
	"""
	for component in build.values():
		_component_normalize(component)


def _run_normalize(run):
	"""
	Fills in any missing lists or dictionaries with empty ones.
	"""
	if 'name' not in run:
		run['name'] = None

	if 'rtvars' not in run:
		run['rtvars'] = {}

	if 'params' not in run:
		run['params'] = {}

	if 'cmd' not in run:
		run['cmd'] = None

	if 'terminals' not in run:
		run['terminals'] = {}


def _config_normalize(config):
	"""
	Fills in any missing lists or dictionaries with empty ones.
	"""
	if 'name' not in config:
		config['name'] = None

	if 'description' not in config:
		config['description'] = None

	if 'layers' not in config:
		config['layers'] = []

	if 'graph' not in config:
		config['graph'] = {}

	if 'build' not in config:
		config['build'] = {}

	_build_normalize(config['build'])

	if 'artifacts' not in config:
		config['artifacts'] = {}

	if 'run' not in config:
		config['run'] = {}

	_run_normalize(config['run'])

	return config


def _config_validate(config):
	"""
	Ensures the config conforms to the schema. Throws exception if any
	issues are found.
	"""
	# TODO:


def _component_sort(component):
	"""
	Sort the component so that the keys are in a canonical order. This
	improves readability by humans.
	"""
	lut = ['repo', 'buildroot', 'params',
			'prebuild', 'build', 'postbuild', 'artifacts']
	lut = {k: i for i, k in enumerate(lut)}
	return dict(sorted(component.items(), key=lambda x: lut[x[0]]))


def _build_sort(build):
	"""
	Sort the build section so that the keys are in a canonical order. This
	improves readability by humans.
	"""
	for name in build:
		build[name] = _component_sort(build[name])
	return dict(sorted(build.items()))


def _run_sort(run):
	"""
	Sort the run section so that the keys are in a canonical order. This
	improves readability by humans.
	"""
	lut = ['name', 'rtvars', 'params', 'cmd', 'terminals']
	lut = {k: i for i, k in enumerate(lut)}
	return dict(sorted(run.items(), key=lambda x: lut[x[0]]))


def _config_sort(config):
	"""
	Sort the config so that the keys are in a canonical order. This improves
	readability by humans.
	"""
	config['build'] = _build_sort(config['build'])
	config['run'] = _run_sort(config['run'])

	lut = ['name', 'description', 'layers',
			'graph', 'build', 'artifacts', 'run']
	lut = {k: i for i, k in enumerate(lut)}
	return dict(sorted(config.items(), key=lambda x: lut[x[0]]))


def _config_merge(base, new):
	"""
	Merges new config into the base config.
	"""
	_config_validate(base)
	_config_validate(new)

	def _merge(base, new, level=0):
		if new is None:
			return base

		if type(base) is list and type(new) is list:
			return base + new

		if type(base) is dict and type(new) is dict:
			d = {}
			for k in list(base.keys()) + list(new.keys()):
				d[k] = _merge(base.get(k), new.get(k), level+1)
			return d

		if type(base) is str and type(new) is str:
			return new

		return new

	return _merge(base, new)


def filename(name):
	"""
	Given a config name, finds the path to the config on disk. If the config
	name contains a path separator, it is treated as a filesystem path. Else
	it is first searched for in the current directory, and if not found, it
	is searched for in the config store.
	"""
	if os.path.sep in name:
		return os.path.abspath(name)
	elif os.path.exists(name):
		return os.path.abspath(name)
	else:
		return os.path.join(workspace.config, name)


def load(filename):
	"""
	Load a config from disk and return it as a dictionary. The config is
	fully normalized, validated and merged.
	"""
	def _config_load(filename):
		config = json.load(open(filename))
		config_dir = os.path.dirname(filename)

		config = _config_normalize(config)
		_config_validate(config)

		# Recursively load and merge the layers.
		master = _config_normalize({})
		for layer in config['layers']:
			layer = _config_load(os.path.join(config_dir, layer))
			master = _config_merge(master, layer)

		master = _config_merge(master, config)

		return master

	config = _config_load(filename)

	# Now that the config is fully merged, we don't need the layers
	# property. Its also useful to store the name.
	del config['layers']
	config['name'] = os.path.basename(filename)

	return _config_sort(config)
