import time
import logging
import sys
import socket
import signal

from dataclasses import dataclass
from contextlib import closing

from .socket import Socket

@dataclass
class Server:
	
	host: str        = str()
	port: int 	     = 0
	ping: bool       = False
	pool: object     = None

	def __abs__(self):
		with self.pool as conn:
			return bool(conn)
		# with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
		# 	if sock.connect_ex((self.host, self.port)) == 0:
		# 		return True
		return False

class Pool(list):

	length: int  	 = 2048
	ping: bool  	 = False
	size: int 		 = 1
	host: str   	 = str()
	port: int   	 = 0
	expire: int 	 = 60

	__id__: int 	 = 0
	__cn__: int 	 = 1

	def __init__(self, host:str    = str(), 
					   port:int    = int(), 
					   pool:int    = 1, 
					   ping:bool   = False,
					   lock:object = None,
					   expire:int  = 60):
		Pool.host   = host
		Pool.port   = port
		Pool.pool   = pool
		Pool.ping   = ping
		Pool.lock   = lock
		Pool.expire = expire
		for x in range(pool):
			self(host, port)

	def __enter__(self):
		return next(self)

	def __exit__(self, *args):
		pass

	def __call__(self, host:str, port:int):
		if id := self.__cn__ + 1:
			self.__cn__ = id

			if conn := Socket(host, port, 
									expire=self.expire,
									lock=self.lock,
								    id=id):
				self.append(conn)
			# with self[-1] as conn:
		return self[-1]

	def __iter__(self):
		for i in range(len(self)):
			yield self[i]

	def __next__(self):
		if self.__id__ == len(self):
			self.__id__ = 0
		self.__id__ = self.__id__ + 1
		if conn := self[self.__id__ - 1]:
			# if time.time() > conn.expire:
			# 	return next(self.restore(conn))
			return conn
		if len(self):
			if conn := self.restore(self[self.__id__ - 1]):
				return next(self)
		raise ConnectionRefusedError('Connection has been lost. %s:%s:%s', self.__id__, len(self), self[0])

	def __bool__(self):
		return True if len(self) else False

	def shutdown(self, conn):
		if conn in self:
			super().remove(conn)
		self.__cn__ = self.__cn__ - 1
		del conn
		return self

	def restore(self, conn):
		if self(*conn.addr):
			self.shutdown(conn)
		return self

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