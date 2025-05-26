import sys
import time, logging
import requests
import pickle
import binascii
import hashlib
import base64
import socket

logging = logging.getLogger('sentinel.tcp.client')

from typing import Any
from uuid import uuid4

from time import sleep

from ..thread import Thread

from .base import Base
from .pool import Pool, Cluster
from .core import Core

from threading import Lock

class TCP(Core, Base):

	_response: Any = None

	def __init__(self, host: list  = list(), 
					   port: int   = 8111,
					   pool: int   = 1,
					   ping: bool  = False,
					   timeout:int = 60,
					   schema:str  = 'tcp'):
		self.id = str(uuid4())
		self.servers = Cluster(pool, 
							   ping, 
							   Lock())
		if not isinstance(host, list):
			host = [(host, int(port)),]
		for host, port in host:
			self.servers(host, port)
		if round(self):
			super().__init__()
		self.refresh_sentinel_tenants(timeout)

	def __call__(self, route:str, **kwargs):
		if self.servers:
			with self.servers as server:
				try:
					with server.pool as conn:
						if conn and conn._put(**{'route': route, **kwargs}):
							self._response = conn._get()
						else:
							logging.notify('Sentinel connection has gone. Rounding.')
							if round(self, server):
								return self(route, **kwargs)
				except (IndexError, OSError, ConnectionRefusedError):
					logging.debug('Route to Sentinel no longer exists, host {blue}%s:%s{z}{g} have gone down.', server.host, server.port)
					if round(self, server):
						return self(route, **kwargs)
				except Exception as e:
					logging.error('Unidentified fault %s', e)
		return self

	def __abs__(self):
		with self.servers as server:
			if _ := server.pool(server.host, server.port):
				return _

	def __enter__(self):
		return self

	def __exit__(self, *args):
		self._response = None
		sleep(0)

	def __iter__(self):
		for i in range(len(self.servers)):
			yield self.servers[i]

	def __round__(self, server:str = None):
		if server is not None:
			self.servers.remove(server)
			logging.notify('Serever %s:%s is down', server.host, server.port)
		if self.servers:
			with self('members') as self:
				for id, sentinel in self.response.items():
					if not (sentinel.get('addr'),
							sentinel.get('port')) in self.servers:
						try:
							if server := self.servers(sentinel.get('addr'), 
										 			  sentinel.get('port')):
								logging.debug('New server %s:%s in pool', server.host, server.port)
						except:
							#: Remove an unreachable server from the ring
							with self.servers as server:
								try:
									with server.pool as conn:
										if conn and conn._put(**{'route': 'missing', **sentinel}):
											_response = conn._get()
								except:
									pass
				logging.debug('Rounding routes, available: %s', len(self.servers))
		return len(self.servers)

	@property
	def response(self):
		return self._response

	def shutdown(self, how):
		logging.info('Shutdown requested %s', how)
		self._response = None
		self.request.shutdown(how)
		self.request.close()

	@Thread.daemon
	def refresh_sentinel_tenants(self, timeout):
		sleep(timeout);
		if round(self):
			return self.refresh_sentinel_tenants(timeout)
