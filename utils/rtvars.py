import csv


def parse(text):
	rtvars = {}

	if text is not None:
		for pairs in csv.reader([text], delimiter=','):
			for key, value in csv.reader(pairs, delimiter='='):
				rtvars[key] = value

	return rtvars
