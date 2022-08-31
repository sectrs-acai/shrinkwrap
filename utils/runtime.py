import tuxmake.runtime


_stack = []


class Runtime:
	"""
	Wraps tuxmake.runtime to provide an interface for executing commands in
	an abstracted runtime. Multiple runtimes are supported, identified by a
	`name`. The 'null' runtime simply executes the commands on the native
	host. The 'docker', 'docker-local', 'podman' and 'podman-local' runtimes
	execute the commands in a container.
	"""
	def __init__(self, name, image=None, modal=True):
		self._modal = modal
		self._rt = None

		self._rt = tuxmake.runtime.Runtime.get(name)
		self._rt.set_image(image)
		self._rt.set_user('shrinkwrap')
		self._rt.set_group('shrinkwrap')

		if self._modal:
			_stack.append(self)

	def start(self):
		self._rt.prepare()

	def add_volume(self, src, dst=None):
		self._rt.add_volume(src, dst)

	def mkcmd(self, cmd, interactive=False):
		cmd = self._rt.get_command_line(cmd, interactive, False)
		try:
			cmd.remove('--tty')
		except ValueError:
			pass
		return cmd

	def cleanup(self):
		if self._rt:
			self._rt.cleanup()
			self._rt = None
			if self._modal:
				s = _stack.pop()
				assert(s == self)

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.cleanup()


def get():
	"""
	Returns the current modal Runtime instance. At least one Runtime
	instance must be living that was created with modal=True.
	"""
	assert(len(_stack) > 0)
	return _stack[-1]


def mkcmd(cmd, interactive=False):
	"""
	Shorthand for get().mkcmd().
	"""
	return get().mkcmd(cmd, interactive)