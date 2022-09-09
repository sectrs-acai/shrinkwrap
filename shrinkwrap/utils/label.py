import os
import sys


class Label:
	"""
	Container for a string. Intended to be used with LabelController to
	display labels (strings of text) on a terminal at a fixed location and
	be able to update them in place. Instantiate with desired text, and
	update the text by calling update(). Nothing actually changes on screen
	until the LabelController does an update().
	"""
	def __init__(self, text=''):
		self.text = text
		self._prev_text = ''
		self._lc = None

	def update(self, text=''):
		self.text = text
		if self._lc:
			self._lc._update_pending = True


class LabelController:
	"""
	Coordinates printing and updating a set of labels at a fixed location on
	a terminal. The controller manages a list of labels, which are provided
	at construction and are displayed one under the other on the terminal.
	update() can be periodically called to redraw the labels if their
	contents has changed. Only works as long as no other text is printed to
	the terminal while the labels are active. If the provided file is not
	backed by a terminal, overdrawing is not performed.
	"""
	def __init__(self, labels=[], file=sys.stdout, overdraw=True):
		self._labels = labels
		self._file = file
		self._overdraw = overdraw
		self._first = True
		self._update_pending = True
		try:
			term_sz = os.get_terminal_size(file.fileno())
			self._term_lines = term_sz.lines
			self._term_cols = term_sz.columns
		except OSError:
			self._overdraw = False

		for label in self._labels:
			label._lc = self

	def _move_up(self, line_count):
		assert(self._overdraw)
		self._file.write('\033[F' * line_count)

	def _line_count(self, text):
		assert(self._overdraw)
		return (len(text) + self._term_cols - 1) // self._term_cols

	def update(self):
		if not self._update_pending:
			return

		if not self._first and self._overdraw:
			line_count = 0
			for l in self._labels:
				line_count += self._line_count(l.text)
			self._move_up(line_count)

		for l in self._labels:
			if self._overdraw or l.text != l._prev_text:
				cc = len(l.text)
				pcc = len(l._prev_text)
				self._file.write(l.text)
				self._file.write(' ' * (pcc - cc))
				self._file.write('\n')
				l._prev_text = l.text

		self._file.flush()

		self._first = False
		self._update_pending = False
