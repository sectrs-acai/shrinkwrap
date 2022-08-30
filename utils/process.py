import fcntl
import os
import shlex
import selectors
import subprocess
import shrinkwrap.utils.runtime as runtime


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


class ProcessManager:
	"""
	A ProcessManager can manage a set of processes running in parallel such
	that it can capture all their (stdout + stderr) output and pass it to a
	handler delegate.
	"""
	def __init__(self, handler=None):
		self._handler = handler
		self._procs = []
		self._active = 0
		self._sel = None

	def set_handler(self, handler):
		self._handler = handler

	def add(self, process):
		self._procs.append(process)
		if self._sel:
			self._activate(process)

	def run(self):
		try:
			self._sel = selectors.DefaultSelector()
			self._active = 0

			for proc in self._procs:
				self._activate(proc)

			while self._active > 0:
				for key, mask in self._sel.select():
					handler = key.data[0]
					data = key.data[1]
					handler(key.fileobj, data)
		finally:
			for proc in self._procs:
				if proc._popen:
					proc._popen.terminate()
					proc._popen.__exit__(None, None, None)
					proc._popen = None

			self._sel.close()
			self._sel = None

	def _register(self, fileobj, data):
		fl = fcntl.fcntl(fileobj, fcntl.F_GETFL)
		fcntl.fcntl(fileobj, fcntl.F_SETFL, fl | os.O_NONBLOCK)
		self._sel.register(fileobj, selectors.EVENT_READ, data)

	def _activate(self, proc):
		stdin=None if proc.interactive else subprocess.DEVNULL

		proc._popen = subprocess.Popen(runtime.mkcmd(proc.args,
							     proc.interactive),
					       stdin=stdin,
					       stdout=subprocess.PIPE,
					       stderr=subprocess.STDOUT,
					       text=True)

		self._register(proc._popen.stdout, (self._proc_handler, proc))

		if proc.run_to_end:
			self._active += 1

	def _proc_handler(self, fileobj, proc):
		data = fileobj.read()
		if data == '':
			self._sel.unregister(fileobj)
			if proc.run_to_end:
				self._active -= 1
		else:
			if self._handler:
				self._handler(self, proc, data)
