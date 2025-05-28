import time

class AnonymousUserMixin:
	"""
	This is the default object for representing an anonymous user.
	"""
	def __enter__(self):
		return self
 
	def __exit__(self, *args):
		pass

	@property
	def is_authenticated(self):
		return False

	@property
	def is_active(self):
		return False

	@property
	def is_anonymous(self):
		return True

	@property
	def veryficated(self):
		return False

	def get_id(self):
		return None

	def get_email(self):
		return str()

	def check_password(self, _):
		return False

	def remove(self):
		return False

	def __abs__(self):
		return 0

	def __int__(self):
		return 0

	def __str__(self):
		return str(self.get_email())