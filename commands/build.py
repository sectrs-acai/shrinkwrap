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
		help="""Builds either all (non-partial) standard configs or an
		     explicitly specified set of configs and packages them ready
		     to run.""",
		epilog="""The config store exists at at
		     <SHRINKWRAP_CONFIG>, building is done at <SHRINKWRAP_BUILD>
		     and output is saved to <SHRINKWRAP_PACKAGE>. The package
		     includes all FW binaries, a manifest and a build.sh script
		     containing all the commands that were executed. Any
		     pre-existing package directory is first deleted.
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
	print(args.dry_run)
	print(args.configs)
