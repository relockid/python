import os
import sys
import logging
import binascii
import bleach

logging = logging.getLogger(__name__)

from flask import (Blueprint,
				   current_app as app, 
				   has_request_context,
				   request,
				   session)

from flask_login import (current_user as worker,
						 user_logged_in,
					     user_logged_out,
					     user_loaded_from_cookie,
					     user_loaded_from_request,
					     user_login_confirmed,
					     user_unauthorized,
					     user_needs_refresh,
					     user_accessed,
					     session_protected)

from ..tcp import TCP
from ..thread import Thread
from .login import AnonymousUserMixin
from .device import Device

bp = os.environ.get('RELOCK_ROUTE', 'relock')
bp = Blueprint(bp, __name__, url_prefix='/%s' % bp,
							 template_folder='templates',
							 static_folder='static',
							 static_url_path='/static/%s' % bp)

class Flask(object):

	def __init__(self, app=None, host=None,
								 port=None,
								 pool=1,
								 ping=False,
								 timeout=30):

		self.host    = str(os.environ.get('RELOCK_SERVICE_HOST', '127.0.0.1'))
		self.port    = int(os.environ.get('RELOCK_SERVICE_PORT', 8111))
		self.pool    = int(os.environ.get('RELOCK_SERVICE_POOL', 1))
		self.ping    = bool(os.environ.get('RELOCK_SERVICE_PING', False))
		self.timeout = int(os.environ.get('RELOCK_SERVICE_TIMEOUT', 30))

		if app is not None:
			self.init_app(app)
		self.tcp = None

	def init_app(self, app, add_context_processor=True):
		""" Configures an application. This registers an `before_request` call, and
			attaches this `Relock service` to it as `app.relock`.

			:param app: The :class:`flask.Flask` object to configure.
			:type app: :class:`flask.Flask`
			:param add_context_processor: Whether to add a context processor to
				the app that adds a `current_user` variable to the template.
				Defaults to ``True``.
			:type add_context_processor: bool
		"""
		app.relock = self

		if not hasattr(app, 'login_manager'):
			raise RuntimeError('Relock service requires Flask-Login to start first.')

		app.login_manager.anonymous_user = AnonymousUserMixin

		app.config.setdefault('RELOCK_SERVICE_HOST', self.host)
		app.config.setdefault('RELOCK_SERVICE_PORT', self.port)
		app.config.setdefault('RELOCK_SERVICE_POOL', self.pool)
		app.config.setdefault('RELOCK_SERVICE_PING', self.ping)
		app.config.setdefault('RELOCK_SERVICE_TIMEOUT', self.timeout)

		with app.app_context():
			try:
				#: Create and initialize the unix sockets TCP client. Client is 
				#: responsible for connection pooling and socket access management.
				self.tcp = TCP(host=app.config.get('RELOCK_SERVICE_HOST'),
							   port=app.config.get('RELOCK_SERVICE_PORT'),
							   pool=app.config.get('RELOCK_SERVICE_POOL'),
							   ping=app.config.get('RELOCK_SERVICE_PING'),
							   timeout=app.config.get('RELOCK_SERVICE_TIMEOUT'))
			except (SystemExit, KeyboardInterrupt):
				sys.exit()
			except Exception as e:
				raise RuntimeError('Relock service host is not available.')
			else:
				#: Setup 'before' and 'after' request calls to the relock service. 
				#: Every new incoming request will create Device object and sends 
				#: the data to relock service.
				app.before_request(Device.before)
				app.after_request(Device.after)
				#: Context methods allows to comunicate with relock service within 
				#: Jinja templates.
				from .context import (x_key_xsid_processor,
									  x_key_screen_processor,
									  x_key_nonce_processor,
									  x_key_signature_processor,
									  x_key_credential_processor,
									  x_key_remote_addr_processor)
				#: Import specific to this Flask plugin routes working inside the 
				#: web application.
				from .routes import (exchange,
									 validate,
									 close,
									 clear,
									 clean,
									 open,
									 js,
									 remote,
									 register,
									 authenticate)
				#: Relock service protects routes from access from 
				#: untrusted/not-registered devices, and as so require to expose
				#: routes that can be accessed public. Expose relock blueprint 
				#: related routes to the relock service.
				app.register_blueprint(bp)
				for p in app.url_map.iter_rules():
					if 'relock' in str(p) and ':' not in str(p):
						self.tcp.expose(str(p))

		#: Expose the main route to the web app.
		self.tcp.expose('/')
