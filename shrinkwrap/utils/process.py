# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import fcntl
import io
import os
import pty
import shlex
import selectors
import subprocess
import sys
import shrinkwrap.utils.runtime as runtime
import shrinkwrap.utils.tty as tty


class Process:
	"""
	A wrapper to a process that should be managed by the ProcessManager.
	"""
	def __init__(self, args, interactive, data, run_to_end):
		self.args = shlex.split(args)
		self.interactive = interactive
		self.data = data
		self.run_to_end = run_to_end
		self._popen = None
		self._stdout = None
		self._stdin = None


class ProcessManager:
	"""
	A ProcessManager can manage a set of processes running in parallel such
	that it can capture all their (stdout + stderr) output and pass it to a
	handler delegate.
	"""
	def __init__(self, handler=None, terminate_handler=None):
		self._handler = handler
		self._terminate_handler = terminate_handler
		self._procs = []
		self._active = 0
		self._sel = None

	def set_handler(self, handler):
		self._handler = handler

	def add(self, process):
		self._procs.append(process)
		if self._sel:
			self._proc_activate(process)

	def run(self, forward_stdin=False):
		try:
			self._sel = selectors.DefaultSelector()
			self._active = 0

			if forward_stdin:
				self._stdin_activate()

			for proc in self._procs:
				self._proc_activate(proc)

			while self._active > 0:
				for key, mask in self._sel.select():
					handler = key.data[0]
					handler(key, mask)
		finally:
			for proc in self._procs:
				try:
					self._proc_deactivate(proc, force=True)
				except:
					pass

			if forward_stdin:
				self._stdin_deactivate()

			self._sel.close()
			self._sel = None

	def _register(self, fileobj, data):
		fl = fcntl.fcntl(fileobj, fcntl.F_GETFL)
		fcntl.fcntl(fileobj, fcntl.F_SETFL, fl | os.O_NONBLOCK)
		self._sel.register(fileobj, selectors.EVENT_READ, data)

	def _proc_handle(self, key, mask):
		proc = key.data[1]
		data = key.fileobj.read()

		if data == '':
			self._proc_deactivate(proc)
		else:
			if self._handler:
				self._handler(self, proc, data)

	def _proc_activate(self, proc):
		cmd = runtime.mkcmd(proc.args, proc.interactive)

		if proc.interactive:
			master, slave = pty.openpty()

			proc._popen = subprocess.Popen(cmd,
						       stdin=slave,
						       stdout=slave,
						       stderr=slave)

			proc._stdin = io.open(master, 'wb', buffering=0)
			proc._stdout = io.open(master, 'rb', -1, closefd=False)
			proc._stdout = io.TextIOWrapper(proc._stdout)
		else:
			proc._popen = subprocess.Popen(cmd,
						       stdin=subprocess.DEVNULL,
						       stdout=subprocess.PIPE,
						       stderr=subprocess.STDOUT,
						       text=True)

			proc._stdin = None
			proc._stdout = proc._popen.stdout

		self._register(proc._stdout, (self._proc_handle, proc))

		if proc.run_to_end:
			self._active += 1

	def _proc_deactivate(self, proc, force=False):
		if not proc._popen:
			return

		if proc.run_to_end:
			self._active -= 1

		self._sel.unregister(proc._stdout)

		proc._popen.kill()
		try:
			proc._popen.communicate()
		except:
			pass
		proc._popen.__exit__(None, None, None)
		retcode = None if force else proc._popen.poll()
		proc._popen = None

		if proc._stdin:
			proc._stdin.close()
			proc._stdin = None

		if proc._stdout:
			proc._stdout.close()
			proc._stdout = None

		if self._terminate_handler:
			self._terminate_handler(self, proc, retcode)

	def _stdin_handle(self, key, mask):
		data = key.fileobj.read()
		for proc in self._procs:
			if proc._stdin:
				proc._stdin.write(data)

	def _stdin_activate(self):
		# Replace stdin with unbuffered binary stream so we can pass
		# input to the ptys without any modification.
		self._stdin_orig = sys.stdin
		sys.stdin = io.open(self._stdin_orig.fileno(),
				    'rb',
				    buffering=0,
				    closefd=False)

		# Set the terminal to raw input mode.
		self._tty_orig = tty.configure(sys.stdin)

		# Register stdin so we get notified when there is data.
		self._register(sys.stdin, (self._stdin_handle,))

	def _stdin_deactivate(self):
		# Unregister for notifications.
		self._sel.unregister(sys.stdin)

		# Restore terminal mode.
		tty.restore(sys.stdin, self._tty_orig)

		# Restore stdin to being buffered text.
		sys.stdin.close()
		sys.stdin = self._stdin_orig
		self._stdin_orig = None
