import time
import logging
import sys
import socket
import signal

from dataclasses import dataclass
from contextlib import closing

from .socket import Socket
from .pool import Pool


@dataclass
class Server:
	
	host: str        = str()
	port: int 	     = 0
	ping: bool       = False
	pool: object     = None

	def __bool__(self):
		with self.pool as conn:
			return bool(conn)
		return False

	def __abs__(self, _:bool = False):
		try:
			with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
				if sock.connect_ex((self.host, self.port)) == 0:
					_ = True
		except Exception as e:
			logging.info('pre-connect to server - The TCP host is no longer operational.')
		else:
			logging.info('pre-connect to server - The TCP connection has been checked and it is valid.')
		return _

class Cluster(list):

	ping: bool  = False
	pool: int 	= 1

	__id__: int = 0

	def __init__(self, pool:int = 1, 
					   ping:bool = False,
					   lock:object = None):
		self.pool = int(pool)
		self.ping = bool(ping)
		self.lock = lock

	def __enter__(self):
		return next(self)

	def __exit__(self, *args):
		pass

	def __call__(self, host:str, port:int):
		if not (host, port) in self:
			if _ := Server(host,
						   port,
						   self.ping,
						   Pool(host, 
						   		port, 
						   		self.pool, 
						   		self.ping,
						   		self.lock)):
				if abs(_):
					self.append(_)
					return _

	def __iter__(self):
		for i in range(len(self)):
			yield self[i]

	def __contains__(self, addr:tuple):
		if isinstance(addr, tuple):
			for server in self:
				if server.host == addr[0] and server.port == addr[1]:
					return True
		else:
			for server in self:
				if server == addr:
					return True
		return False

	def __next__(self):
		if self.__id__ >= len(self):
			self.__id__ = 0
		self.__id__ += 1
		if _ := len(self):
			if server := self[self.__id__ - 1]:
				# if abs(server):
				return server

	def __bool__(self):
		# for server in self:
		# 	if not abs(server):
		# 		self.servers.remove(server)
		return True if len(self) else False

	def remove(self, item):
		# if not len(self):
		# 	raise ValueError('No active servers left.')
		for server in list(self):
			if server == item:
				super().remove(server)	
			elif server.host == item.host and server.port == item.port:
				super().remove(server)