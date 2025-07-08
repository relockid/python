import time
import logging
import binascii
import ujson as json

from typing import Any

from ..thread import Thread
from .pool import Pool

class Events(object):

	def __init__(self):
		pass

	def notify(self, **kwargs):
		"""
		Event creates of a new thread-specific connection, and send request to 
		sentinel with a value passed in kwargs argument collection.

		Args:
		    `kwargs`: A collection of any kind key/value pairs.
		Returns:
		    None
		"""
		with self('notify', **kwargs) as self:
			return self.response

	def expose(self, url):
		"""
		Send to the relock exposed route address/name and register as
		unprotected route.

		Args:
		    `kwargs`: A collection of any kind key/value pairs.
		Returns:
		    None
		"""
		if not url in self._exposed:
			self._exposed.append(url)
		with self('expose', **{'url': url}) as self:
			return self.response

	def exposed(self, url):
		return url in self._exposed