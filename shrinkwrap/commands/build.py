import graphlib
import os
import shutil
import tempfile
import shrinkwrap.utils.config as config
import shrinkwrap.utils.logger as logger
import shrinkwrap.utils.label as label
import shrinkwrap.utils.process as process
import shrinkwrap.utils.runtime as runtime
import shrinkwrap.utils.workspace as workspace


cmd_name = os.path.splitext(os.path.basename(__file__))[0]


def dflt_jobs():
	return min(os.cpu_count() // 2, 32)


def add_parser(parser, formatter):
	"""
	Part of the command interface expected by shrinkwrap.py. Adds the
	subcommand to the parser, along with all options and documentation.
	Returns the subcommand name.
	"""
	cmdp = parser.add_parser(cmd_name,
		formatter_class=formatter,
		help="""Builds either all concrete standard configs or an
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
		help="""0 or more configs to build. If a config exists relative
		     to the current directory that config is used. Else if a
		     config exists relative to the config store then it is used.
		     If no configs are provided, all concrete configs in the
		     config store are built.""")

	cmdp.add_argument('-o', '--overlay',
		metavar='cfgfile', required=False,
		help="""Optional config file overlay to override build-time
		     settings. Only entries within the "build" section are
		     used. Applied to all configs being built.""")

	cmdp.add_argument('-t', '--tasks',
		required=False, default=dflt_jobs(), metavar='count', type=int,
		help="""Maximum number of "high-level" tasks that will be
		     performed in parallel by Shrinkwrap. Tasks include syncing
		     git repositories, building components and copying
		     artifacts. Default={}""".format(dflt_jobs()))

	cmdp.add_argument('-j', '--jobs',
		required=False, default=dflt_jobs(), metavar='count', type=int,
		help="""Maximum number of low-level jobs that will be
		     performed in parallel by each component build task.
		     Default={}""".format(dflt_jobs()))

	cmdp.add_argument('-v', '--verbose',
		required=False, default=False, action='store_true',
		help="""If specified, the output from all executed commands will
		     be displayed. It is advisable to set tasks to 1 when
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
	clivars = {'jobs': args.jobs}
	configs = config.load_resolveb_all(args.configs, args.overlay, clivars)
	if len(args.configs) == 0:
		configs = [c for c in configs if c['concrete']]
	graph = config.graph(configs)

	if args.dry_run:
		script = _mk_script(graph)
		print(_mk_script(graph))
	else:
		# Run under a runtime environment, which may just run commands
		# natively on the host or may execute commands in a container,
		# depending on what the user specified.
		with runtime.Runtime(args.runtime, args.image) as rt:
			def add_volume(path, levels_up=0):
				while levels_up:
					path = os.path.dirname(path)
					levels_up -= 1
				os.makedirs(path, exist_ok=True)
				rt.add_volume(path)

			add_volume(workspace.build)
			add_volume(workspace.package)

			for conf in configs:
				for comp in conf['build'].values():
					add_volume(comp['sourcedir'], 1)
					add_volume(comp['builddir'])

			rt.start()

			_build(graph, args.tasks, args.verbose)

		for c in configs:
			# Dump the config.
			cfg_name = os.path.join(workspace.package,
						c['fullname'])
			with open(cfg_name, 'w') as cfg:
				config.dump(c, cfg)

			# Dump the script to build the config.
			graph = config.graph([c])
			script = _mk_script(graph)
			build_name = os.path.join(workspace.package,
						  c['name'],
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


def _run_script(pm, data, script):
	# Write the script out to a file in a temp directory, and wrap the
	# directory name and command to run in a Process. Add the Process to the
	# ProcessManager. On completion, the caller must destroy the directory.

	tmpdir = tempfile.mkdtemp(dir=workspace.build)
	tmpfilename = os.path.join(tmpdir, 'script.sh')
	with open(tmpfilename, 'w') as tmpfile:
		tmpfile.write(script.commands())

	# Start the process asynchronously.
	pm.add(process.Process(f'bash {tmpfilename}',
			       False,
			       (data, script, tmpdir),
			       True))


def _build(graph, tasks, verbose):
	labels, mask = _mk_labels(graph)
	lc = _mk_label_controller(labels, not verbose)

	queue = []
	active = 0
	log = logger.Logger(20)
	ts = graphlib.TopologicalSorter(graph)

	def _pump(pm):
		nonlocal queue
		nonlocal active
		nonlocal log
		while len(queue) > 0 and active < tasks:
			frag = queue.pop()
			_update_labels(labels,
				       mask,
				       frag.config,
				       frag.component,
				       frag.summary + '...')
			data = log.alloc_data(str(frag)) if verbose else []
			_run_script(pm, data, frag)
			active += 1

	def _log(pm, proc, data):
		if verbose:
			log.log(pm, proc, data)
		else:
			proc.data[0].append(data)

	def _complete(pm, proc, retcode):
		nonlocal queue
		nonlocal active
		nonlocal ts

		data = proc.data[0]
		frag = proc.data[1]
		tmpdir = proc.data[2]

		shutil.rmtree(tmpdir)

		if retcode is None:
			# Forcibly terminated due to errors elsewhere. No need
			# to do anything further.
			return

		if retcode:
			if not verbose:
				print(''.join(data))
			raise Exception(f"Error: Failed to execute '{frag}'")

		state = 'Done' if frag.final else 'Waiting...'
		_update_labels(labels,
			       mask,
			       frag.config,
			       frag.component,
			       state)
		if frag.final:
			mask[frag.config][frag.component] = False

		ts.done(frag)
		active -= 1
		queue.extend(ts.get_ready())
		_pump(pm)

		lc.update()

	# Initially set all labels to waiting. They will be updated as the
	# fragments execute.
	_update_labels(labels, mask, None, None, 'Waiting...')

	# The process manager will run all added processes in the background and
	# give callbacks whenever there is output available and when each
	# process terminates. _pump() adds processes to the set.
	pm = process.ProcessManager(_log, _complete)

	# Fill the queue with all the initial script fragments which do not have
	# start dependencies.
	ts.prepare()
	queue.extend(ts.get_ready())

	# Call _pump() initially to start as many tasks as are allowed.
	# Then enter the pm.
	_pump(pm)
	lc.update()
	pm.run()

	# Mark all components as done. This should be a nop since the script
	# should have indicated if it was the last step for a given
	# config/component and we would have already set it to done. But this
	# catches anything that might have slipped through.
	_update_labels(labels, mask, None, None, 'Done')
	lc.update()
