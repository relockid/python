import time
import logging
import threading

from functools import wraps

class Thread(object):

	@classmethod
	def daemon(cls, function):
		@wraps(function)
		def daemon(*args, **kwargs):
			if _ := threading.Thread(target=function, 
									 name=function.__name__, 
									 args=args, 
									 kwargs=kwargs, 
									 daemon=True):
				_.start()
		return daemon

	@classmethod
	def thread(cls, function):
		@wraps(function)
		def thread(*args, **kwargs):
			if _ := threading.Thread(target=function, 
									 name=function.__name__, 
									 args=args,
									 kwargs=kwargs):
				_.start()
				return _.join()
		return thread