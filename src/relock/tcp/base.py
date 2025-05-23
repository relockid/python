import pickle
import zlib
import ujson as json
import logging

from typing import Any
from time import sleep

class Base(object):

	length = 1024
	eot    = b'\n\r\n'

	def _get(self, _:bytes = bytes()):
		if self.connected:
			with self.lock as lock:
				try:
					while slice := self.request.recv(Base.length):
						_ += slice
						if slice[-3:] == self.eot:
							_ = _[:-3]; break
				except Exception as e:
					logging.error('Recive faild %s', e)
				else:
					if _ == b'PING':
						self.request.sendall(b'PONG')
					elif _ == b'PONG':
						pass
					elif _ == b'False':
						_ = False
					elif _ == b'True':
						_ = True
					elif _ == b'None':
						_ = None
					elif _ == b'SHUTDOWN':
						if self.connected:
							self.shutdown(2)
					elif _:
						try:
							_ = json.loads(_)
						except Exception as e:
							logging.error('Socket decode faild. %s', e)
							logging.notify(_)
				finally:
					sleep(0)
		return _

	def _put(self, _: bytes = bytes(), offset: int = 0, **kwargs) -> Any:
		with self.lock as lock:
			if not len(kwargs) and _ == b'':
				_ = None #Can't send a null byte
			if not len(kwargs) and isinstance(_, (bool, type(None))):
				if _ := str(_).encode() + self.eot:
					self.request.sendall(_); offset += len(_)
			elif isinstance(_, bytes) and not len(kwargs):
				self.request.sendall(_ + self.eot); offset += len(_)
			else:
				if _ := json.dumps(_ if _ else kwargs, 
								   separators=(', ', ':')).encode():
					try:
						self.request.sendall(_ + self.eot)
					except Exception as e:
						logging.error('Send to socket faild. %s', e)
					else:
						offset = len(_)
					finally:
						sleep(0)
		return offset + len(self.eot)
