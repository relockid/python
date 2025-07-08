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
from .cluster import Cluster
from .events import Events

from threading import Lock

class TCP(Events, Base):

	_response: Any = None

	def __init__(self, host: list  = list(), 
					   port: int   = 8111,
					   pool: int   = 1,
					   ping: bool  = False,
					   timeout:int = 300,
					   schema:str  = 'tcp'):
		self.id       = str(uuid4())
		self.pool     = pool
		self.ping     = ping
		self.lock     = Lock()
		self.servers  = []
		self._exposed = []
		if not isinstance(host, list):
			self.host = [(host, int(port)),]
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
							logging.debug('TCP server connection has gone. Rounding.')
							if round(self, server):
								return self(route, **kwargs)
				except (IndexError, OSError, ConnectionRefusedError):
					logging.debug('Route to relock no longer exists, host {blue}%s:%s{z}{g} have gone down.', server.host, server.port)
					if round(self, server):
						return self(route, **kwargs)
				except Exception as e:
					logging.error('No route to the TCP server host %s could be found.', e)
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
			logging.info('Serever %s:%s is down', server.host, server.port)
		if self.servers:
			with self('members') as self:
				if self.response:
					for id, sentinel in self.response.items():
						if not (sentinel.get('addr'),
								sentinel.get('port')) in self.servers:
							try:
								#: Try to add new server to the connection pooling
								self.servers(sentinel.get('addr'), 
											 sentinel.get('port'))
							except:
								#: Remove an unreachable server from the ring
								if self.servers:
									with self.servers as server:
										try:
											with server.pool as conn:
												if conn and conn._put(**{'route': 'missing', **sentinel}):
													_response = conn._get()
										except:
											logging.info('The attempt to remove the dead server %s:%s from the ring is unsuccessful.', 
														sentinel.get('addr'),
														sentinel.get('port'))
										else:
											logging.info('Remove an unreachable server %s:%s from the ring', 
																sentinel.get('addr'),
																sentinel.get('port'))
							else:
								logging.info('New server %s:%s in pool', 
												sentinel.get('addr'),
												sentinel.get('port'))
				else:
					for server in self.servers:
						if not abs(server):
							self.servers.remove(server)
					if self.servers:
						return round(self)
		if not self.servers:
			self.make()
		logging.debug('Rounding routes, available: %s', len(self.servers))
		return len(self.servers)

	def make(self):
		self.servers = Cluster(self.pool, 
							   self.ping, 
							   self.lock)
		for host, port in self.host:
			self.servers(host, port)
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
