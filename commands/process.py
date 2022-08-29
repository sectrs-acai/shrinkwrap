import os
import shrinkwrap.utils.config as config
import shrinkwrap.utils.rtvars as rtvars


cmd_name = os.path.splitext(os.path.basename(__file__))[0]


def add_parser(parser, formatter):
	"""
	Part of the command interface expected by shrinkwrap.py. Adds the
	subcommand to the parser, along with all options and documentation.
	Returns the subcommand name.
	"""
	cmdp = parser.add_parser(cmd_name,
		formatter_class=formatter,
		help="""Outputs to stdout the result of either merging down the
		     config layers, or resolving macros within the merged
		     config.""",
		epilog="""The config store exists at at
		     <SHRINKWRAP_CONFIG>. <SHRINKWRAP_CONFIG> defaults to
		     'config' directory within the directory containing the
		     shrinkwrap program, but the user can override it by setting
		     the environment variable.""")

	cmdp.add_argument('config',
		metavar='config',
		help="""Config to process. If the config contains a path
		     separator, it is treated as a filesystem path. Else it is
		     first searched for in the current directory, and if not
		     found, it is searched for in the config store.""")

	cmdp.add_argument('-a', '--action',
		metavar='action', required=True,
		choices=['merge', 'resolveb', 'resolver'],
		help="""Action to take. Either "merge" (merge down the config
		     layers), "resolveb" (resolve build-time macros within the
		     merged config) or "resolver" (resolve run-time macros
		     within the build-time resolved config).""")

	cmdp.add_argument('-r', '--rtvars',
		metavar='rtvars', required=False,
		help="""Comma-separated list of <key>=<value> pairs, specifying
		     override values for any runtime variables defined by the
		     config. Overrides for variables that have a default
		     specified by the config are optional. Only used if action
		     is "resolver".""")

	return cmd_name


def dispatch(args):
	"""
	Part of the command interface expected by shrinkwrap.py. Called to
	execute the subcommand, with the arguments the user passed on the
	command line. The arguments comply with those requested in add_parser().
	"""
	filename = config.filename(args.config)
	merged = config.load(filename)

	if args.action == 'merge':
		print(config.dumps(merged))
	else:
		resolveb = config.resolveb(merged)

		if args.action == 'resolveb':
			print(config.dumps(resolveb))
		else:
			rtvars_dict = rtvars.parse(args.rtvars)
			resolver = config.resolver(resolveb, rtvars_dict)

			if args.action == 'resolver':
				print(config.dumps(resolver))
