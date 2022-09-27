import sys
from collections import namedtuple
termcolor = None

_colors = ['blue', 'cyan', 'green', 'yellow', 'magenta', 'grey', 'red']
Data = namedtuple("Data", "tag color")


class Logger:
	def __init__(self, tag_size, colorize):
		self._tag_size = tag_size
		self._colorize = colorize
		self._color_next = 0
		self._prev_tag = None
		self._prev_char = '\n'

		if self._colorize:
			global termcolor
			import termcolor as tc
			termcolor = tc

	def alloc_data(self, tag):
		"""
		Returns the object that should be stashed in proc.data[0] when
		log() is called. Includes the tag for the process and an
		allocated colour.
		"""
		idx = self._color_next
		self._color_next += 1
		self._color_next %= len(_colors)
		color = _colors[idx]
		return Data(tag, color)

	def log(self, pm, proc, data):
		"""
		Logs text data from one of the processes (FVP or one of its uart
		terminals) to the terminal. Text is colored and a tag is added
		on the left to identify the originating process.
		"""
		tag = proc.data[0].tag
		color = proc.data[0].color

		# Make the tag.
		if len(tag) > self._tag_size:
			tag = tag[:self._tag_size-3] + '...'
		tag = f'{{:>{self._tag_size}}}'.format(tag)

		lines = data.splitlines(keepends=True)
		start = 0

		# If the cursor is not at the start of a new line, then if the
		# new log is for the same proc that owns the first part of the
		# line, just continue from there without adding a new tag. If
		# the first part of the line has a different owner, insert a
		# newline and add a tag for the new owner.
		if self._prev_char != '\n':
			if self._prev_tag == tag:
				self.print(f'{lines[0]}', color, end='')
				start = 1
			else:
				print(f'\n', end='')

		for line in lines[start:]:
			self.print(f'[ {tag} ] {line}', color, end='')

		self._prev_tag = tag
		self._prev_char = lines[-1][-1]

		sys.stdout.flush()

	def print(self, text, color=None, on_color=None, attrs=None, **kwargs):
		if self._colorize:
			text = termcolor.colored(text, color, on_color, attrs)
		print(text, **kwargs)