import os
import re
import tempfile
import shrinkwrap.utils.config as config
import shrinkwrap.utils.logger as logger
import shrinkwrap.utils.process as process
import shrinkwrap.utils.rtvars as rtvars
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
		help="""Boot and run the FVP for the specified config.""",
		epilog="""FW is accessed from <SHRINKWRAP_PACKAGE>.
		     <SHRINKWRAP_PACKAGE> defaults to 'package' directory within
		     the directory containing the shrinkwrap program, but the
		     user can override it by setting the environment
		     variable.""")

	cmdp.add_argument('config',
		metavar='config',
		help="""Config to run. Must have been previously built into
		     <SHRINKWRAP_PACKAGE>.""")

	cmdp.add_argument('-o', '--overlay',
		metavar='cfgfile', required=False,
		help="""Optional config file overlay to override run-time
		     settings. Only entries within the "run" section are
		     used.""")

	cmdp.add_argument('-r', '--rtvar',
		metavar='key=value', required=False, default=[],
		action='append',
		help="""Override value for a single runtime variable defined by
		     the config. Specify option multiple times for multiple
		     variables. Overrides for variables that have a default
		     specified by the config are optional.""")

	cmdp.add_argument('-n', '--dry-run',
		required=False, default=False, action='store_true',
		help="""If specified, none of the run commands will be
		     executed. Instead the set of commands that would have been
		     executed are output to stdout.""")

	return cmd_name


def dispatch(args):
	"""
	Part of the command interface expected by shrinkwrap.py. Called to
	execute the subcommand, with the arguments the user passed on the
	command line. The arguments comply with those requested in add_parser().
	"""
	overlay = None
	if args.overlay:
		overlay = config.filename(args.overlay)
		overlay = config.load(overlay)
		overlay = {'run': overlay['run']}

	filename = os.path.join(workspace.package, args.config)
	resolveb = config.load(filename, overlay)
	rtvars_dict = rtvars.parse(args.rtvar)
	resolver = config.resolver(resolveb, rtvars_dict)
	cmds = '\n'.join(resolver['run']['prerun'] + resolver['run']['run'])

	# If dry run, just output the FVP command that we would have run. We
	# don't include the netcat magic to access the fvp terminals.
	if args.dry_run:
		print('# Boot FVP.')
		print(cmds)
		return

	# The FVP and any associated uart terminals are output to our terminal
	# with a tag to indicate where each line originated. Figure out how big
	# that tag field needs to be so that everything remains aligned.
	max_name_field = 10
	name_field = 0
	terminals = resolver['run']['terminals']
	terminals = dict(sorted(terminals.items()))
	for t in terminals.values():
		t['port'] = None
		if len(t['friendly']) > name_field:
			name_field = min(len(t['friendly']), max_name_field)

	log = logger.Logger(name_field)

	def _find_term_ports(pm, proc, data):
		"""
		Initial handler function called by ProcessManager. When the fvp
		starts, we must parse the output to determine the port numbers
		to connect to with netcat to access the fvp uart terminals. We
		look for all the ports, start the netcat instances, add them to
		the process manager and finally switch the handler to the
		standard logger.
		"""
		# First, forward to the standard log handler.
		log.log(pm, proc, data)

		found_all_ports = True

		# Iterate over the terminals dict from the config applying the
		# supplied regexes to try to find the ports for all the
		# terminals.
		for t in terminals.values():
			if t['port'] is None:
				res = re.search(t['port_regex'], data)
				if res:
					t['port'] = res.group(1)
				else:
					found_all_ports = False

		# Once all ports have been found, launch the netcat processes
		# and change the handler so we never get called again.
		if found_all_ports:
			wait = False
			for t in terminals.values():
				name = t['friendly']
				type = t['type']
				port = t["port"]

				if type in ['stdout', 'stdinout']:
					interactive = type == 'stdinout'
					cmd = f'nc localhost {port}'
					pm.add(process.Process(cmd,
							interactive,
							(log.alloc_data(name),),
							False))
				if type in ['xterm']:
					# Nothing to do. The FVP will start this
					# automatically.
					pass
				if type in ['telnet']:
					wait = True
					ip = runtime.get().ip_address()
					print(f'To start {name} terminal, run:')
					print(f'    telnet {ip} {port}')
			if wait:
				print()
				input("Press Enter to continue...")

			pm.set_handler(log.log)

	# Run under a runtime environment, which may just run commands natively
	# on the host or may execute commands in a container, depending on what
	# the user specified.
	with runtime.Runtime(args.runtime, args.image) as rt:
		for rtvar in resolver['run']['rtvars'].values():
			if rtvar['type'] == 'path':
				rt.add_volume(rtvar['value'])
		rt.add_volume(workspace.package)
		rt.start()

		# Write the script out to a file in a temp directory, and wrap
		# the directory name and command to run in a Process. Add the
		# Process to the ProcessManager. On completion, the caller must
		# destroy the directory.
		with tempfile.TemporaryDirectory(dir=workspace.package) as tmpdir:
			tmpfilename = os.path.join(tmpdir, 'script.sh')
			with open(tmpfilename, 'w') as tmpfile:
				tmpfile.write(cmds)

			# Create a process manager with 1 process; the fvp. As
			# it boots _find_term_ports() will add the netcat
			# processes in parallel. It will exit once all processes
			# have terminated. The fvp will terminate when its told
			# to `poweroff` and netcat will terminate when it sees
			# the fvp has gone.
			pm = process.ProcessManager(_find_term_ports)
			pm.add(process.Process(f'bash {tmpfilename}',
					False,
					(log.alloc_data('fvp'),),
					True))
			pm.run()
