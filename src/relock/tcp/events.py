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

	def timeadd(self, key:str, **kwargs):
		"""Event creates of a new thread-specific connection, and send request to put in a sorted set a new item with value passed in kwargs argument collection. Sorted set is created by using current timestamp.

		Args:
		    `key`: A unique, constant identifier for database identyfication.
		    (optional) `kwargs`: A collection of any kind key/value pairs saved together with unqiue `key`.
		Returns:
		    None
		"""
		if conn := abs(self):
			if conn._put(route = 'zadd', 
						 key = key,
						 score = time.time(),
						 value = kwargs):
				return conn._get()

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
		with self('expose', **{'url': url}) as self:
			return self.response

