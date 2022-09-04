import graphlib
import io
import os
import re
import yaml
import shrinkwrap.utils.clivars as uclivars
import shrinkwrap.utils.workspace as workspace


def _component_normalize(component, name):
	"""
	Fills in any missing lists or dictionaries with empty ones.
	"""
	if 'repo' not in component:
		component['repo'] = {}

	if all(type(v) != dict for v in component['repo'].values()):
		component['repo'] = {'.': component['repo']}

	for repo in component['repo'].values():
		if 'remote' not in repo:
			repo['remote'] = None

		if 'revision' not in repo:
			repo['revision'] = None

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
	for name, component in build.items():
		_component_normalize(component, name)


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


def _mk_params(params, separator):
	pairs = [f'{k}' if v is None else f'{k}{separator}{v}'
						for k, v in params.items()]
	return ' '.join(pairs)


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


def load(filename, overlay=None):
	"""
	Load a config from disk and return it as a dictionary. The config is
	fully normalized, validated and merged.
	"""
	def _config_load(filename):
		with open(filename) as file:
			config = yaml.safe_load(file)
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

	if overlay:
		config = _config_merge(config, overlay)

	# Now that the config is fully merged, we don't need the layers
	# property. Its also useful to store the name.
	del config['layers']
	config['name'] = os.path.basename(filename)

	return _config_sort(config)


def dumps(config):
	return dump(config, None)


def dump(config, fileobj):
	return yaml.safe_dump(config,
			      fileobj,
			      explicit_start=True,
			      sort_keys=False,
			      version=(1, 2))


def resolveb(config, clivars={}):
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

	def _substitute_macros(config, artifacts, clivars):

		for desc in config['build'].values():
			lut = {
				'artifact': artifacts,
				'param': dict(clivars),
			}

			for k in desc['params']:
				v = desc['params'][k]
				if v:
					desc['params'][k] = _string_substitute(str(v), lut)

			lut['param']['join_equal'] = _mk_params(desc['params'], '=')
			lut['param']['join_space'] = _mk_params(desc['params'], ' ')

			for i, s in enumerate(desc['prebuild']):
				desc['prebuild'][i] = _string_substitute(s, lut)
			for i, s in enumerate(desc['build']):
				desc['build'][i] = _string_substitute(s, lut)
			for i, s in enumerate(desc['postbuild']):
				desc['postbuild'][i] = _string_substitute(s, lut)

	graph = _resolve_build_graph(config)
	artifact_map = _resolve_artifact_map(config)
	artifact_src_map = {k: os.path.join(workspace.build, v['src']) for k, v in artifact_map.items()}
	clivars = uclivars.get(**clivars)
	_substitute_macros(config, artifact_src_map, clivars)

	config['graph'] = graph
	config['artifacts'] = artifact_map

	return _config_sort(config)


def resolver(config, rtvars={}, clivars={}):
	"""
	Resolves the run-time macros (artifacts, rtvars, etc) and fixes up the
	config. Expects a config that was previously resolved with resolveb().
	"""
	clivars = uclivars.get(**clivars)
	run = config['run']

	#Override the rtvars with any values supplied by the user and check that
	#all rtvars are defined.
	for k in run['rtvars']:
		if k in rtvars:
			run['rtvars'][k]['value'] = rtvars[k]
	for k, v in run['rtvars'].items():
		if v['value'] is None:
			raise Exception(f'Error: {k} run-time variable not ' \
					'set by user and no default available.')

	# Create a lookup table with all the artifacts in their package
	# locations, then do substitution to fully resolve the rtvars. An
	# exception will be thrown if there are any macros that we don't have
	# values for.
	lut = {
		'param': dict(clivars),
		'artifact': {k: os.path.join(workspace.package, v['dst'])
				for k, v in config['artifacts'].items()},
	}
	for k in run['rtvars']:
		v = run['rtvars'][k]
		v['value'] = _string_substitute(str(v['value']), lut)
		if v['type'] == 'path':
			v['value'] = os.path.abspath(v['value'])

	# Now create a lookup table with all the rtvars and resolve all the
	# parameters. An exception will be thrown if there are any macros that
	# we don't have values for.
	lut = {
		'param': dict(clivars),
		'rtvar': {k: v['value'] for k, v in run['rtvars'].items()}
	}
	for k in run['params']:
		v = run['params'][k]
		if v:
			run['params'][k] = _string_substitute(str(v), lut)

	# Assemble the final runtime command and stuff it into the config.
	params = _mk_params(run['params'], '=')
	terms = ' '.join([f'-C {t}.mode=raw' for t in run['terminals']])
	run['cmd'] = f'{run["name"]} {params} {terms}'

	return _config_sort(config)


def load_resolveb_all(names, overlayname=None, clivars={}):
	"""
	Takes a list of config names and returns a corresponding list of
	resolved configs. If the input list is None or empty, all non-partial
	standard configs are loaded and resolved.
	"""
	explicit = names is not None and len(names) != 0
	configs = []

	if not explicit:
		p = workspace.config
		names = [f for f in os.listdir(p)
				if os.path.isfile(os.path.join(p, f))]

	overlay = None
	if overlayname:
		overlay = filename(overlayname)
		overlay = load(overlay)
		overlay = {'build': overlay['build']}

	for name in names:
		try:
			file = filename(name)
			merged = load(file, overlay)
			resolved = resolveb(merged, clivars)
			configs.append(resolved)
		except Exception:
			if explicit:
				raise

	return configs


class Script:
	def __init__(self,
		     summary,
		     config=None,
		     component=None,
		     preamble=None,
		     final=False):
		self.summary = summary
		self.config = config
		self.component = component
		self.final = final
		self._cmds = ''
		self._sealed = False
		self._preamble = preamble

	def append(self, *args, **kwargs):
		assert(not self._sealed)

		buf = io.StringIO()
		print(*args, **kwargs, file=buf)

		self._cmds += buf.getvalue()

	def seal(self):
		assert(not self._sealed)
		self._sealed = True

	def preamble(self):
		return self._preamble

	def commands(self, inc_preamble=True):
		if inc_preamble:
			return self._preamble + '\n' + self._cmds
		else:
			return self._cmds

	def __eq__(self, other):
		return self.summary == other.summary and \
			self.config == other.config and \
			self.component == other.component and \
			self._cmds == other._cmds and \
			self._sealed == other._sealed

	def __hash__(self):
		assert(self._sealed)
		return hash((
			self.summary,
			self.config,
			self.component,
			self._cmds,
			self._sealed
		))

	def __repr__(self):
		return f'{self.config}:{self.component} {self.summary}'


def graph(configs):
	"""
	Returns a graph of scripts where the edges represent dependencies. The
	scripts should be executed according to the graph in order to correctly
	build all the configs.
	"""
	graph = {}

	pre = Script(None)
	pre.append(f'#!/bin/bash')
	pre.append(f'# SHRINKWRAP AUTOGENERATED SCRIPT.')
	pre.append()
	pre.append(f'# Exit on error, error on unbound vars and echo commands.')
	pre.append(f'set -eux')
	pre.append()
	pre.append(f'# Define variables.')
	pre.append(f'BUILD={workspace.build}')
	pre.append(f'PACKAGE={workspace.package}')
	pre = pre.commands(False)

	gl1 = Script('Removing old package', preamble=pre)
	gl1.append(f'# Remove old package.')
	for config in configs:
		gl1.append(f'rm -rf $PACKAGE/{config["name"]} > /dev/null 2>&1 || true')
	gl1.seal()
	graph[gl1] = []

	gl2 = Script('Creating directory structure', preamble=pre)
	gl2.append(f'# Create directory structure.')
	for config in configs:
		gl2.append(f'mkdir -p $BUILD/{config["name"]}')
		dirs = set()
		for artifact in config['artifacts'].values():
			dst = f'$PACKAGE/{artifact["dst"]}'
			dir = os.path.dirname(dst)
			if dir not in dirs:
				gl2.append(f'mkdir -p {dir}')
				dirs.add(dir)
	gl2.seal()
	graph[gl2] = [gl1]

	for config in configs:
		build_scripts = {}

		ts = graphlib.TopologicalSorter(config['graph'])
		ts.prepare()
		while ts.is_active():
			for name in ts.get_ready():
				component = config['build'][name]

				g = Script('Syncing git repo', config["name"], name, preamble=pre)
				g.append(f'# Sync git repo for config={config["name"]} component={name}.')
				g.append(f'pushd $BUILD/{config["name"]}')

				for gitlocal, repo in component['repo'].items():
					gitlocal = os.path.normpath(os.path.join(name, gitlocal))
					gitremote = repo['remote']
					gitrev = repo['revision']

					g.append(f'if [ ! -d "{gitlocal}" ]; then')
					g.append(f'\tgit clone {gitremote} {gitlocal}')
					g.append(f'\tpushd {gitlocal}')
					g.append(f'\tgit checkout --force {gitrev}')
					g.append(f'\tgit submodule update --init --checkout --recursive --force')
					g.append(f'\tpopd')
					g.append(f'fi')

				g.append(f'popd')
				g.seal()
				graph[g] = [gl2]

				b = Script('Building', config["name"], name, preamble=pre)
				b.append(f'# Build for config={config["name"]} component={name}.')
				b.append(f'pushd $BUILD/{config["name"]}/{name}')
				for cmd in component['prebuild']:
					b.append(cmd)
				for cmd in component['build']:
					b.append(cmd)
				for cmd in component['postbuild']:
					b.append(cmd)
				b.append(f'popd')
				b.seal()
				graph[b] = [g] + [build_scripts[s] for s in config['graph'][name]]

				build_scripts[name] = b
				ts.done(name)

		a = Script('Copying artifacts', config["name"], preamble=pre, final=True)
		a.append(f'# Copy artifacts for config={config["name"]}.')
		for artifact in config['artifacts'].values():
			src = f'$BUILD/{artifact["src"]}'
			dst = f'$PACKAGE/{artifact["dst"]}'
			a.append(f'cp {src} {dst}')
		a.seal()
		graph[a] = [gl2] + [s for s in build_scripts.values()]

	return graph
