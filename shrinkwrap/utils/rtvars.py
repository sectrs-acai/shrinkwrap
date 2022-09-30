# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

def parse(args):
	rtvars = {}

	for pair in args:
		try:
			key, value = pair.split('=', maxsplit=1)
			rtvars[key] = value
		except ValueError:
			raise Exception(f'Invalid rtvar {pair}')

	return rtvars
