import os


cmd_name = os.path.splitext(os.path.basename(__file__))[0]


def add_parser(parser, formatter):
	"""
	Part of the command interface expected by shrinkwrap.py. Adds the
	subcommand to the parser, along with all options and documentation.
	Returns the subcommand name.
	"""
	cmdp = parser.add_parser(cmd_name,
		formatter_class=formatter,
		help="""Outputs to stdout info about either all (non-partial)
		     standard configs or an explicitly specified set of configs.
		     Info includes name, description and runtime variables with
		     their default values.""",
		epilog="""The config store exists at at
		     <SHRINKWRAP_CONFIG>. <SHRINKWRAP_CONFIG> defaults to
		     'config' directory within the directory containing the
		     shrinkwrap program, but the user can override it by setting
		     the environment variable.""")

	cmdp.add_argument('configs',
		metavar='config', nargs='*',
		help="""0 or more configs to inspect. If a config contains a
		     path separator, it is treated as a filesystem path. Else it
		     is first searched for in the current directory, and if not
		     found, it is searched for in the config store. If no
		     configs are provided, all non-partial configs in the config
		     store are inspected.""")

	return cmd_name


def dispatch(args):
	"""
	Part of the command interface expected by shrinkwrap.py. Called to
	execute the subcommand, with the arguments the user passed on the
	command line. The arguments comply with those requested in add_parser().
	"""
	print(args.configs)
