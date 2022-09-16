def parse(args):
	rtvars = {}

	for pair in args:
		try:
			key, value = pair.split('=', maxsplit=1)
			rtvars[key] = value
		except ValueError:
			raise Exception(f'Error: invalid rtvar {pair}')

	return rtvars
