import logging

from typing import Any

from .events import Events

class Core(Events):

	def __init__(self):
		pass

	def get(self, key:str):
		with self('get', key=key) as _:
			return self.response

	def set(self, key:str, value:Any):
		with self('set', key=key, value=value) as self:
			return self.response

	def delete(self, key:str):
		with self('delete', key=key) as self:
			return self.response

	def exists(self, key:str):
		with self('exists', key=key) as self:
			return self.response

	def keys(self, key:str):
		with self('keys', key=key) as self:
			return self.response

	def ttl(self, key:str, value:int):
		with self('ttl', key=key, value=value) as self:
			return self.response

	def expire(self, key:str, value:int):
		with self('expire', key=key, value=value) as self:
			return self.response

	def zadd(self, key:str, score:int, **kwargs):
		""" Create new connection for thread
		"""
		with self('zadd', key=key,
						  score=score,
						  value=kwargs) as self:
			return self.response

	def zrange(self, key:str, x:int=0, y:int=-1):
		with self('zrange', key=key, x=0, y=-1) as self:
			return self.response

	def zrevrange(self, key:str, x:int=0, y:int=-1):
		with self('zrevrange', key=key, x=0, y=-1) as self:
			return self.response

	def zrem(self, key:str, value:Any):
		with self('zrem', key=key, value=value) as self:
			return self.response

	def sadd(self, key:str, **kwargs):
		with self('sadd', key=key, **kwargs) as self:
			return self.response

	def srem(self, key:str, **kwargs):
		with self('srem', key=key, **kwargs) as self:
			return self.response

	def smembers(self, key:str, **kwargs):
		with self('smembers', key=key) as self:
			return self.response
