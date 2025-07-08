import time
import logging
import sys
import socket
import signal

from dataclasses import dataclass
from contextlib import closing

from .socket import Socket

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
					   expire:int  = 600):
		Pool.host   = host
		Pool.port   = port
		Pool.pool   = pool
		Pool.ping   = ping
		Pool.lock   = lock
		Pool.expire = expire
		for x in range(pool):
			self(host, port)

	def __enter__(self):
		with next(self) as conn:
			return conn
		raise ConnectionRefusedError('Connection has been lost. %s:%s:%s', self.__id__, len(self), self[0])

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
			if time.time() > conn.expire and conn.closed:
				if hash(conn):
					return next(self.restore(conn))
				else:
					raise ConnectionRefusedError('Connection has been lost. %s:%s:%s', self.__id__, len(self), self[0])
			elif not conn.closed:
				conn.expire = time.time() + self.expire
			return conn
		if len(self) < self.pool:
			if conn := self(self.host, self.port):
				return next(self)
		raise ConnectionRefusedError('Connection has been lost. %s:%s:%s', self.__id__, len(self), self[0])

	def __bool__(self):
		return True if len(self) else False

	def shutdown(self, conn):
		if conn in self:
			conn.shutdown(2)
			super().remove(conn)
		self.__cn__ = self.__cn__ - 1
		del conn
		return self

	def restore(self, conn):
		if self(*conn.addr):
			self.shutdown(conn)
		return self

