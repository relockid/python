import time
import logging
import sys
import socket
import signal

from ctypes import c_ulong
from fcntl import ioctl

from .base import Base

from gevent import sleep

class Socket(Base):

	length:int  	 = 2048
	connected:bool 	 = False
	
	_bytes:int 		 = 3

	def __init__(self, host:str, 
					   port:str, 
					   lock:object = None,
					   **kwargs):

		self.__id__		  = kwargs.get('id', 0)
		self.__response	  = None
		self.addr         = (host, port)
		self.lock         = lock
		self.expire		  = time.time() + kwargs.get('expire', 600)
		self.connected    = False

		self.request = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.request.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.request.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
		# self.request.setblocking(0)
		abs(self)

	def __call__(self, route:str, **kwargs):
		if self._put(**{'route': route, **kwargs}):
			self.__response = self._get()
		return self

	def __enter__(self):
		if not bool(self):
			return abs(self)
		return self

	def __exit__(self, *args):
		self.__response = None

	def __hash__(self, _:int = 0):
		try:
			with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
				if sock.connect_ex(self.addr) == 0:
					_ = 1
		except Exception as e:
			logging.info('socket pre-check - The TCP host is no longer operational.')
		else:
			logging.info('pre-check of server - The TCP connection has been checked and it is valid.')
		return _

	def __abs__(self, _:bytes = bytes()):
		if not self.connected:
			try:
				self.request.connect(self.addr)
			except ConnectionRefusedError:
				logging.debug('Connection Refused %s:%s, host is down.', *self.addr)
				raise ConnectionRefusedError('Host %s:%s is down.' % self.addr)
			except TimeoutError:
				logging.debug('Timeout error, host %s:%s is down.', *self.addr)
				raise ConnectionRefusedError('Host %s:%s is down.' % self.addr)
			except Exception as e:
				raise ConnectionRefusedError('Host %s:%s is down.' % self.addr)
			else:
				self.connected = True
		return self

	def __bool__(self, _:bool = False, bytes:bytes = bytes()) -> bool:
		try:
			if int := self.sendall(b'PING'):
				bytes = self.recvall()
		except ConnectionRefusedError: #host is down
			logging.error('ConnectionRefusedError')
			_ = False
		except BlockingIOError:
			logging.error('BlockingIOError')
			_ = True
		except OSError as e: #not connected yet
			logging.error(e)
			_ = False
		except ConnectionResetError: #broken pipe
			logging.error('ConnectionResetError')
			_ = False
		except socket.timeout as e:
			logging.error('SocketTimouetError')
			_ = False
		except Exception as e:
			logging.exception("Unexpected problem when checking socket connection.")
			_ = False
		else:
			if bytes == b'PONG':
				_ = True
			# if hash := b'PONG':
			# 	if hex := len(hash).to_bytes(self._bytes, byteorder='big'):
			# 		if bytes == hex + hash:
			# 			_ = True
			if _ != True:
				raise IndexError('Socket don\'t reply correct PONG.')
		finally:
			self.connected = _
		return self.connected

	@property
	def id(self):
		return self.__id__

	@id.setter
	def id(self, value:int):
		self.__id__ = value

	@property
	def response(self):
		return self.__response

	@property
	def closed(self):
		return self.request._closed

	def recv(self):
		return self.request.recv(self.length)

	def send(self, value:bytes):
		if not self.request._closed:
			return self.request.send(value)

	def sendall(self, _:bytes = bytes(), abs:bytes = bytes()):
		with self.lock:
			if abs := len(_).to_bytes(self._bytes, byteorder='big'):
				self.request.sendall(abs + _)
				# print('snd:', abs, len(abs), len(_), _)
			sleep(0)
		return int.from_bytes(abs, 'big')

	def recvall(self, *flags, _:bytes = bytes()):
		with self.lock:
			if abs := self.request.recv(self._bytes, *flags):
				# print('rcv:', abs, len(abs))
				if abs := int.from_bytes(abs, byteorder="big"):
					while slice := self.request.recv(self.length, *flags):
						_ += slice
						if len(_) >= abs:
							break
			# print('rcv:', _)
			sleep(0)
		return _

	def shutdown(self, how=0):
		logging.debug(
				"The client is closing the connection to the %s:%s",
				*self.addr)
		try:
			if not self.request._closed:
				self.request.shutdown(how)
		except OSError:
			self.close()
		else:
			self.connected = False

	def close(self):
		try:
			if not self.request._closed:
				self.request.close()
		except Exception as e:
			logging.debug(e)
		finally:
			self.disconnected()

	def disconnected(self):
		if hasattr(self, 'addr'):
			logging.debug('Client disconnected from server %s:%s', *self.addr)

	def __delete__(self):
		try:
			if not self.request._closed:
				self.request.shutdown(0)
		except Exception as e:
			logging.warning(e)
		else:
			self.request.close()
		finally:
			logging.info('Closed connection to server %s%s:', self.addr)

	def flush(self) -> bool:
		return False