import time
import logging
import sys
import socket
import signal

from ctypes import c_ulong
from termios import TIOCOUTQ
from fcntl import ioctl

from .base import Base

from gevent import sleep

class Socket(Base):

	length:int  	 = 2048
	connected:bool 	 = False

	def __init__(self, host:str, 
					   port:str, 
					   lock:object = None,
					   **kwargs):

		self.__id__		  = kwargs.get('id', 0)
		self.__response	  = None
		self.addr         = (host, port)
		self.lock         = lock
		self.expire		  = time.time() + kwargs.get('expire', 3600)
		self.connected    = False

		self.request = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.request.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.request.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
		# self.request.setblocking(0)

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

	def __abs__(self, _:bytes = bytes()):
		try:
			self.request.connect(self.addr)
		except ConnectionRefusedError:
			logging.notify('Connection Refused %s:%s, host is down.', *self.addr)
			raise ConnectionRefusedError('Host %s:%s is down.' % self.addr)
		except TimeoutError:
			logging.notify('Timeout error, host %s:%s is down.', *self.addr)
			raise ConnectionRefusedError('Host %s:%s is down.' % self.addr)
		else:
			self.connected = True
		return self

	def __bool__(self, _:bool = False, bytes:bytes = bytes()) -> bool:
		if not self.connected:
			abs(self)
		try:
			if self._put(b'PING'):
				bytes = self.request.recv(self.length, socket.MSG_DONTWAIT)
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

	def recv(self):
		return self.request.recv(self.length)

	def send(self, value:bytes):
		if not self.request._closed:
			return self.request.send(value)

	def sendall(self, value:bytes):
		if not self.request._closed:
			return self.request.sendall(value)

	def shutdown(self, how=0):
		logging.notify(
				"Client closing connection from %s:%s",
				*self.addr)
		try:
			if not self.request._closed:
				self.request.shutdown(how)
		except OSError:
			self.close()

	def close(self):
		try:
			if not self.request._closed:
				self.request.close()
		except Exception as e:
			logging.notify(e)
		finally:
			self.disconnected()

	def disconnected(self):
		if hasattr(self, 'addr'):
			logging.notify('Client disconnected from server %s:%s', *self.addr)

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
		while self.request.fileno() != -1: # if fd is -1, then it has been probably close()'d
			remaining = c_ulong.from_buffer_copy(
				ioctl(self.request.fileno(), TIOCOUTQ, bytearray(8), False)).value
			if remaining == 0:
				# all data has been sent and ACKed
				return True
			# wait a bit before retrying,
			# sleep(0) was meant like yield current thread,
			# but will probably be close to busy-waiting,
			# feel free to change it to fit your needs
			sleep(0)
		# not all data has been sent
		return False