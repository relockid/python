import pickle
import zlib
import ujson as json
import logging

from typing import Any
from time import sleep

class Base(object):

	def _get(self, _:bytes = bytes(), abs:int = 0):
		with self.lock as lock:
			try:
				_ = self.recvall()
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
		# print('got:', _)
		return _

	def _put(self, _: bytes = bytes(), offset: int = 0, **kwargs) -> Any:
		with self.lock as lock:
			if not len(kwargs) and _ == b'':
				_ = None #Can't send a null byte
			if not len(kwargs) and isinstance(_, (bool, type(None))):
				if _ := str(_).encode():
					_ = self.sendall(_)
			elif isinstance(_, bytes) and not len(kwargs):
				_ = self.sendall(_)
			else:
				if _ := json.dumps(_ if _ else kwargs, 
								   separators=(', ', ':')).encode():
					_ = self.sendall(_)
		# print('snd:', _)
		return len(_)
