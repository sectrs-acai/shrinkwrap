import graphlib
import multiprocessing
import os
import stat
import subprocess
import tempfile
import shrinkwrap.utils.config as config
import shrinkwrap.utils.label as label
import shrinkwrap.utils.runtime as runtime
import shrinkwrap.utils.workspace as workspace


cmd_name = os.path.splitext(os.path.basename(__file__))[0]


def add_parser(parser, formatter):
	"""
	Part of the command interface expected by shrinkwrap.py. Adds the
	subcommand to the parser, along with all options and documentation.
	Returns the subcommand name.
	"""
	cmdp = parser.add_parser(cmd_name,
		formatter_class=formatter,
		help="""Builds either all (non-partial) standard configs or an
		     explicitly specified set of configs and packages them ready
		     to run.""",
		epilog="""The config store exists at at
		     <SHRINKWRAP_CONFIG>, building is done at <SHRINKWRAP_BUILD>
		     and output is saved to <SHRINKWRAP_PACKAGE>. The package
		     includes all FW binaries, a manifest and a build.sh script
		     containing all the commands that were executed per config.
		     Any pre-existing config package directory is first deleted.
		     <SHRINKWRAP_CONFIG>, <SHRINKWRAP_BUILD> and
		     <SHRINKWRAP_PACKAGE> default to 'config', 'build' and
		     'package' directories within the directory containing the
		     shrinkwrap program, but the user can override them by
		     setting the environment variables.""")

	cmdp.add_argument('configs',
		metavar='config', nargs='*',
		help="""0 or more configs to build. If a config contains a
		     path separator, it is treated as a filesystem path. Else it
		     is first searched for in the current directory, and if not
		     found, it is searched for in the config store. If no
		     configs are provided, all non-partial configs in the config
		     store are built.""")

	cmdp.add_argument('-p', '--parallelism',
		required=False, default=4, metavar='count', type=int,
		help="""Maximum number of tasks that will be performed in
		     parallel. Tasks include syncing git repositories, building
		     componenents and copying artifacts.""")

	cmdp.add_argument('-v', '--verbose',
		required=False, default=False, action='store_true',
		help="""If specified, the output from all executed commands will
		     be displayed. It is advisable to set parallelism to 1 when
		     this option is selected.""")

	cmdp.add_argument('-n', '--dry-run',
		required=False, default=False, action='store_true',
		help="""If specified, <SHRINKWRAP_BUILD> and
		     <SHRINKWRAP_PACKAGE> will not be touched and none of the
		     build commands will be executed. Instead the set of
		     commands that would have been executed are output to stdout
		     as a bash script.""")

	return cmd_name


def dispatch(args):
	"""
	Part of the command interface expected by shrinkwrap.py. Called to
	execute the subcommand, with the arguments the user passed on the
	command line. The arguments comply with those requested in add_parser().
	"""
	configs = config.load_resolveb_all(args.configs)
	graph = config.graph(configs)

	if args.dry_run:
		script = _mk_script(graph)
		print(_mk_script(graph))
	else:
		# Run under a runtime environment, which may just run commands
		# natively on the host or may execute commands in a container,
		# depending on what the user specified.
		with runtime.Runtime(args.runtime, args.image) as rt:
			os.makedirs(workspace.build, exist_ok=True)
			rt.add_volume(workspace.build)

			os.makedirs(workspace.package, exist_ok=True)
			rt.add_volume(workspace.package)

			rt.start()

			_build(graph, args.parallelism, args.verbose)

		for c in configs:
			# Dump the config.
			cfg_name = os.path.join(workspace.package, c['name'])
			with open(cfg_name, 'w') as cfg:
				config.dump(c, cfg)

			# Dump the script to build the config.
			graph = config.graph([c])
			script = _mk_script(graph)
			build_name = os.path.join(workspace.package,
						  c['name'] + '_artifacts',
						  'build.sh')
			with open(build_name, 'w') as build:
				build.write(script)


def _mk_script(graph):
	# Start the script with the preamble from the first script fragment in
	# the graph. The preamble for each script is identical and we only need
	# it once since we are concatenating the fragments together.
	script = '' + list(graph.keys())[0].preamble() + '\n'

	# Walk the graph, adding each script fragment to the final script
	# (without its preamble).
	ts = graphlib.TopologicalSorter(graph)
	ts.prepare()
	while ts.is_active():
		for frag in ts.get_ready():
			script += frag.commands(False) + '\n'
			ts.done(frag)

	return script


def _mk_labels(graph):
	"""
	Returns a tuple of labels and mask. Each is a two level dictionary,
	where there is an entry for each config/component that we are building.
	Mask is initially set to true.
	"""
	labels = {}
	mask = {}

	ts = graphlib.TopologicalSorter(graph)
	ts.prepare()
	while ts.is_active():
		for frag in ts.get_ready():
			ts.done(frag)

			cfg = frag.config
			cmp = frag.component

			if cfg is None or cmp is None:
				continue

			if cfg not in labels:
				labels[cfg] = {}
				mask[cfg] = {}
			if cmp not in labels[cfg]:
				labels[cfg][cmp] = label.Label()
				mask[cfg][cmp] = True

	return labels, mask


def _mk_label_controller(labels, overdraw):
	"""
	Makes a label controller for all the labels in the labels two-level
	dictionary.
	"""
	label_list = []
	for sl in labels.values():
		for l in sl.values():
			label_list.append(l)
	return label.LabelController(label_list, overdraw=overdraw)


def _mk_tag(config, component):
	"""
	Makes a fixed-width tag string for a config and component.
	"""
	def _clamp(text, max):
		if len(text) > max:
			text = text[:max-3] + '...'
		return text

	config = '' if config is None else config
	component = '' if component is None else component
	config = _clamp(config, 16)
	component = _clamp(component, 8)
	return '[ {:>16} : {:8} ]'.format(config, component)


def _update_labels(labels, mask, config, component, summary):
	"""
	Updates all the labels whose mask is True and which match config and
	component (if specified, then only update for that config/component. If
	None, then update all configs/components). summary provides the text to
	update the labels with.
	"""
	def iter(labels, mask, key):
		if key is None:
			for key in labels:
				yield key, labels[key], mask[key]
		else:
			yield key, labels[key], mask[key]

	for cfg, l0, m0 in iter(labels, mask, config):
		for cmp, l1, m1 in iter(l0, m0, component):
			if m1:
				l1.update(_mk_tag(cfg, cmp) + ' ' + summary)


def _run_script(args):
	"""
	Runs a provided script fragment. Intendend to be called in parallel from
	worker threads.
	"""
	script = args[0]
	verbose = args[1]

	# Write the script out to a file in a temp directory, which will get
	# automatically destroyed when we exit the scope. We can't use a temp
	# file directly because it won't let us add the executable permission
	# while its open.
	with tempfile.TemporaryDirectory(dir=workspace.build) as tmpdir:
		tmpfilename = os.path.join(tmpdir, 'script.sh')

		with open(tmpfilename, 'w') as tmpfile:
			tmpfile.write(script.commands())

		# Run the script and save the output.
		res = subprocess.run(runtime.mkcmd(['bash', tmpfilename]),
				text=True,
				stdin=subprocess.DEVNULL,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT)

	# Only print the output if it failed or we are in verbose mode.
	if verbose or res.returncode:
		print(res.stdout)

	# Raise an exception if it failed.
	if res.returncode:
		raise Exception(f'Error: Failed to execute {script}')

	return script


def _build(graph, parallelism, verbose):
	labels, mask = _mk_labels(graph)
	lc = _mk_label_controller(labels, not verbose)

	ts = graphlib.TopologicalSorter(graph)
	ts.prepare()

	with multiprocessing.Pool(processes=parallelism) as pool:
		while ts.is_active():
			frags =  [(f, verbose) for f in ts.get_ready()]

			# Put any components that do not have active jobs for
			# this cycle in the wait state, and advertise what the
			# active components are doing.
			_update_labels(labels, mask, None, None, 'Waiting...')
			for frag, _ in frags:
				_update_labels(labels,
					       mask,
					       frag.config,
					       frag.component,
					       frag.summary + '...')
			lc.update()

			# Queue up all the script fragments to the pool and mark
			# their components as waiting as the scripts finish.
			for frag in pool.imap_unordered(_run_script, frags):
				state = 'Done' if frag.final else 'Waiting...'
				_update_labels(labels,
					       mask,
					       frag.config,
					       frag.component,
					       state)

				if frag.final:
					mask[frag.config][frag.component] = False

				lc.update()
				ts.done(frag)

	# Mark all components as done. This should be a nop since the script
	# should have indicated if it was the last step for a given
	# config/component and we would have already set it to done. But this
	# catches anything that might have slipped through.
	_update_labels(labels, mask, None, None, 'Done')

	lc.update()
