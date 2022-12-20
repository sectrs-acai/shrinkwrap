# Copyright (c) 2022, Arm Limited.
# SPDX-License-Identifier: MIT

import os
import subprocess
import sys
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
		self._mountpoints = set()

		self._rt = tuxmake.runtime.Runtime.get(name)
		self._rt.set_image(image)
		if not sys.platform.startswith('darwin'):
			# Macos uses GIDs that overlap with already defined GIDs
			# in the container so this fails. However, it appears
			# that on macos, if we run as root in the container, any
			# generated files on the host filesystem are still owned
			# my the real macos user, so it seems we don't need this
			# UID/GID fixup in the first place on macos.
			self._rt.set_user('shrinkwrap')
			self._rt.set_group('shrinkwrap')

		if self._modal:
			_stack.append(self)

	def start(self):
		for mp in self._mountpoints:
			self._rt.add_volume(mp)

		self._rt.prepare()

	def add_volume(self, src):
		# Podman can't deal with duplicate mount points, so filter out
		# duplicates here, including mount-points that are children of
		# other mount points. Then defer registering the actual final
		# volumes until start() time.

		if not src:
			return

		mountpoints = set()

		for mp in self._mountpoints:
			common = os.path.commonpath([src, mp])
			if common == mp:
				# mp is parent (or duplicate) of src, so src
				# already covered.
				return
			elif common != src:
				# src is not a parent of mp. So include mp in
				# filtered set of mount points.
				mountpoints.add(mp)

		# If we got here, then src is a unique mountpoint. Add it, and
		# commit the filtered set.
		mountpoints.add(src)
		self._mountpoints = mountpoints

	def mkcmd(self, cmd, interactive=False):
		return self._rt.get_command_line(cmd, interactive, False)

	def ip_address(self):
		"""
		Returns the primary ip address of the runtime.
		"""

		script = """
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(0)
try:
	s.connect(('10.254.254.254', 1))
	ip = s.getsockname()[0]
except Exception:
	ip = '127.0.0.1'
finally:
	s.close()
print(ip)
""".replace('\n', '\\n').replace('\t', '\\t')

		cmd = ['python3', '-c', f'exec("{script}")']
		res = subprocess.run(self.mkcmd(cmd),
				     universal_newlines=True,
				     stdout=subprocess.PIPE,
				     stderr=subprocess.PIPE)
		if res.returncode == 0:
			return res.stdout.strip()
		return '127.0.0.1'

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
