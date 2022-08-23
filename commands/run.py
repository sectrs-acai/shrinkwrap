import os
import re
import sys
import termcolor
import shrinkwrap.utils.config as config
import shrinkwrap.utils.process as process
import shrinkwrap.utils.rtvars as rtvars
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

	cmdp.add_argument('-r', '--rtvars',
		metavar='rtvars', required=False,
		help="""Comma-separated list of <key>=<value> pairs, specifying
		     override values for any runtime variables defined by the
		     config. Overrides for variables that have a default
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
	assert(not args.tune)

	filename = os.path.join(workspace.package, args.config)
	resolveb = config.load(filename)
	rtvars_dict = rtvars.parse(args.rtvars)
	resolver = config.resolver(resolveb, rtvars_dict)

	# If dry run, just output the FVP command that we would have run. We
	# don't include the netcat magic to access the fvp terminals.
	if args.dry_run:
		print('# Boot FVP.')
		print(resolver['run']['cmd'])
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

	# Some state needed for allocating colors to fvp uart terminals and for
	# ensuring the output is pretty.
	colors = ['cyan', 'blue', 'green', 'yellow', 'magenta', 'grey', 'red']
	color_next = 0
	proc_prev_name = None
	proc_prev_char = None

	def _next_color():
		"""
		Returns the name of the next color in the set. Cycles through
		the 7 colors we have available. I've never seen an FVP with more
		than 6 terminals so this should be sufficient.
		"""
		nonlocal color_next
		color = color_next
		color_next += 1
		color_next %= len(colors)
		return colors[color]

	def _log(pm, proc, data):
		"""
		Logs text data from one of the processes (FVP or one of its uart
		terminals) to the terminal. Text is colored and a tag is added
		on the left to identify the originating process.
		"""
		nonlocal name_field
		nonlocal proc_prev_name
		nonlocal proc_prev_char

		name = proc.data[0]
		color = proc.data[1]

		# Make the tag.
		if len(name) > name_field:
			name = name[:name_field-3] + '...'
		name = f'{{:>{max_name_field}}}'.format(name)

		lines = data.splitlines(keepends=True)
		start = 0

		# If the cursor is not at the start of a new line, then if the
		# new log is for the same proc that owns the first part of the
		# line, just continue from there without adding a new tag. If
		# the first part of the line has a different owner, insert a
		# newline and add a tag for the new owner.
		if proc_prev_char != '\n':
			if proc_prev_name == name:
				termcolor.cprint(f'{lines[0]}', color, end='')
				start = 1
			else:
				print(f'\n', end='')

		for line in lines[start:]:
			termcolor.cprint(f'[ {name} ] {line}', color, end='')

		proc_prev_name = name
		proc_prev_char = lines[-1][-1]

		sys.stdout.flush()

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
		_log(pm, proc, data)

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
			for t in terminals.values():
				name = t['friendly']
				interactive = t['interactive']
				cmd = f'nc localhost {t["port"]}'

				pm.add(process.Process(cmd,
						       interactive,
						       (name, _next_color())))

			pm.set_handler(_log)

	# Create a process manager with 1 process; the fvp. As it boots
	# _find_term_ports() will add the netcat processes in parallel. It will
	# exit once all processes have terminated. The fvp will terminate when
	# its told to `poweroff` and netcat will terminate when it sees the fvp
	# has gone.
	pm = process.ProcessManager(_find_term_ports)
	pm.add(process.Process(resolver['run']['cmd'],
			       False,
			       ('fvp', _next_color())))
	pm.run()
