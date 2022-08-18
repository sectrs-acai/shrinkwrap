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


def _string_tokenize(string):
	"""
	Returns ordered list of tokens, where each token has a 'type' and
	'value'. If 'type' is 'literal', 'value' is the literal string. If
	'type' is 'macro', 'value' is a dict defining 'type' and 'name'.
	"""
	regex = '\$(?:' \
			'(?P<escape>\$)|' \
			'(?:\{' \
				'(?P<type>[_a-zA-Z][_a-zA-Z0-9]*):' \
				'(?P<name>[_a-zA-Z][_a-zA-Z0-9]*)?' \
			'\})|' \
			'(?P<invalid>)' \
		')'
	pattern = re.compile(regex)
	tokens = []
	lit_start = 0

	m = pattern.search(string)
	while m:
		lit_end = m.span()[0]

		if lit_end > lit_start:
			tokens.append({
				'type': 'literal',
				'value': string[lit_start:lit_end],
			})

		lit_start = m.span()[1]

		if m['invalid'] is not None:
			raise Exception(f"Error: macro at col {lit_end}" \
					f" in '{string}' is invalid.")
		if m['escape'] is not None:
			tokens.append({
				'type': 'literal',
				'value': m['escape'],
			})
		if m['type'] is not None:
			tokens.append({
				'type': 'macro',
				'value': {
					'type': m['type'],
					'name': m['name'],
				},
			})

		m = pattern.search(string, pos=lit_start)

	tokens.append({
		'type': 'literal',
		'value': string[lit_start:],
	})

	return tokens


def _string_substitute(string, lut, partial=False):
	"""
	Takes a string containg macros and returns a string with the macros
	substituted for the values found in the lut. If partial is True, any
	macro that does not have a value in the lut will be left as a macro in
	the returned string. If partial is False, any macro that does not have a
	value in the lut will cause an interrupt.
	"""
	new = ''
	tokens = _string_tokenize(string)

	for t in tokens:
		if t['type'] == 'literal':
			new += t['value']
		elif t['type'] == 'macro':
			m = t['value']
			try:
				new += lut[m['type']][m['name']]
			except KeyError:
				if partial:
					new += f"${{{m['type']}:{m['name']}}}"
				else:
					raise

		else:
			assert(False)

	return new


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


def resolveb(config):
	"""
	Resolves the build-time macros (params, artifacts, etc) and fixes up the
	config. Based on the artifact dependencies, the component build graph is
	determined and placed into the config along with the global artifact
	map. Expects a config that was previously loaded with load().
	"""
	def _resolve_build_graph(config):
		def _exporters_update(exporters, name, component):
			new = {a: name for a in component['artifacts'].keys()}
			clash = set(exporters.keys()).intersection(new.keys())

			if len(clash) > 0:
				a = clash.pop()
				raise Exception(f"Error: duplicate artifact '{a}' exported by '{exporters[a]}' and '{new[a]}'.")

			exporters.update(new)

		def _importers_update(importers, name, component):
			artifacts = set()
			macros = []

			for s in component['params'].values():
				tokens = _string_tokenize(str(s))
				macros += [t['value'] for t in tokens if t['type'] == 'macro']

			for m in macros:
				if m['type'] != 'artifact':
					raise Exception(f"Error: '{name}' uses macro of type '{m['type']}'. Components must only use 'artifact' macros.")
				if m['name'] is None:
					raise Exception(f"Error: '{name}' uses unnamed 'artifact' macro. 'artifact' macros must be named.")
				artifacts.add(m['name'])

			importers[name] = sorted(list(artifacts))

		artifacts_exp = {}
		artifacts_imp = {}
		for name, desc in config['build'].items():
			_exporters_update(artifacts_exp, name, desc)
			_importers_update(artifacts_imp, name, desc)

		graph = {}
		for depender, deps in artifacts_imp.items():
			graph[depender] = []
			for dep in deps:
				dependee = artifacts_exp[dep]
				graph[depender].append(dependee)

		return graph

	def _resolve_artifact_map(config):

		artifact_map = {}

		for name, desc in config['build'].items():
			locs = {key: {
				'src': os.path.join(config['name'], name, desc['buildroot'], val),
				'dst': os.path.join(config['name'] + '_artifacts', os.path.basename(val)),
			} for key, val in desc['artifacts'].items()}

			artifact_map.update(locs)

		return artifact_map

	def _substitute_macros(config, artifact_src_map):

		for desc in config['build'].values():
			for k in desc['params']:
				v = desc['params'][k]
				if v:
					desc['params'][k] = _string_substitute(str(v), artifact_src_map)

			params = ' '.join([f'{k}' if v is None else f'{k}={v}' for k, v in desc['params'].items()])
			params = {'params': {None: params}}
			for i, s in enumerate(desc['prebuild']):
				desc['prebuild'][i] = _string_substitute(s, params)
			for i, s in enumerate(desc['build']):
				desc['build'][i] = _string_substitute(s, params)
			for i, s in enumerate(desc['postbuild']):
				desc['postbuild'][i] = _string_substitute(s, params)

	graph = _resolve_build_graph(config)
	artifact_map = _resolve_artifact_map(config)
	artifact_src_map = {'artifact': {k: os.path.join(workspace.build, v['src']) for k, v in artifact_map.items()}}
	_substitute_macros(config, artifact_src_map)

	config['graph'] = graph
	config['artifacts'] = artifact_map

	return _config_sort(config)

