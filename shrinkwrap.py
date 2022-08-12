#!/usr/bin/env python3


# Fixup PythonPath to avoid confusion between (this) module and package.
import sys
import os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if os.path.basename(p) != 'shrinkwrap']
sys.path = [root] + sys.path


import argparse
import shutil


from shrinkwrap.commands import build
from shrinkwrap.commands import inspect
from shrinkwrap.commands import process
from shrinkwrap.commands import run


def formatter(prog):
	width = shutil.get_terminal_size().columns
	width -= 2
	width = min(80, width)
	return argparse.HelpFormatter(prog, width=width)


def main():
	"""
	Main entry point. Parses command line and dispatches to appropriate
	command handler.
	"""

	tool_name = os.path.splitext(os.path.basename(__file__))[0]

	# Parse the arguments. The parser will raise an exception if the
	# required arguments are not present, which will tell the user what they
	# did wrong.

	parser = argparse.ArgumentParser(epilog='To file a bug report, contact '
						'<ryan.roberts@arm.com>.',
					 formatter_class=formatter)

	subparsers = parser.add_subparsers(dest='command',
					   metavar='<command>',
					   title=f'Supported commands (run '
						 f'"{tool_name} <command> '
						 f'--help" for more info')

	# Register all the commands.
	cmds = {}
	cmds[build.add_parser(subparsers, formatter)] = build
	cmds[inspect.add_parser(subparsers, formatter)] = inspect
	cmds[process.add_parser(subparsers, formatter)] = process
	cmds[run.add_parser(subparsers, formatter)] = run

	# Parse the arguments.
	args = parser.parse_args()

	# Dispatch to the correct command.
	if args.command in cmds:
		cmds[args.command].dispatch(args)
	else:
		print(f'Unknown command {args.command}')
		parser.print_help()


if __name__ == "__main__":
	main()


