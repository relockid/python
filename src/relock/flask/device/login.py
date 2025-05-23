import binascii
import logging
import time

from flask import (current_app as app,
				   request,
				   Response,
				   session,
				   redirect,
				   url_for,
				   abort)

from flask_login import (current_user as worker,
						 logout_user,
						 user_logged_in,
						 user_logged_out,
						 user_loaded_from_cookie,
						 user_loaded_from_request,
						 user_login_confirmed,
						 user_unauthorized,
						 user_needs_refresh,
						 user_accessed,
						 session_protected)

from ...thread import Thread

class Login(object):

	#: Sent when a user is logged in. In addition to the app (which is the
	#: sender), it is passed `user`, which is the user being logged in.
	@user_logged_in.connect
	def _user_logged_in(self, user):
		with self.relock.tcp(**{'route': 'user_logged_in',
							    'sid': session.sid,
							    'rid': request.id,
								'user': user.get_id(),
						        'email': user.email,
						        'authenticated': user.is_authenticated,
						        'active': user.is_active,
						        'anonymous': user.is_anonymous,						    
							    'host': app.config.get('SERVER_HOST')}) as tcp:
			if tcp.response in (423, 410):
				if '_user_id' in session:
					del session['_user_id']

	#: Sent when a user is logged out. In addition to the app (which is the
	#: sender), it is passed `user`, which is the user being logged out.
	@user_logged_out.connect
	def _user_logged_out(self, *args, **kwargs):
		with self.relock.tcp(**{'route': 'user_logged_out',
							    'sid': session.sid,
							    'rid': request.id,
							    'addr': request.remote_addr,
							    'host': app.config.get('SERVER_HOST')}) as tcp:
			if tcp.response in (423, 410):
				if '_user_id' in session:
					del session['_user_id']

	#: Sent when the user is loaded from the cookie. In addition to the app (which
	#: is the sender), it is passed `user`, which is the user being reloaded.
	@user_loaded_from_cookie.connect
	def _user_loaded_from_cookie(self, *args, **kwargs):
		logging.debug('_user_loaded_from_cookie')

	#: Sent when the user is loaded from the request. In addition to the app (which
	#: is the #: sender), it is passed `user`, which is the user being reloaded.
	@user_loaded_from_request.connect
	def _user_loaded_from_request(self, *args, **kwargs):
		logging.debug('user_loaded_from_request')

	#: Sent when a user's login is confirmed, marking it as fresh. (It is not
	#: called for a normal login.)
	#: It receives no additional arguments besides the app.
	@user_login_confirmed.connect
	def _user_login_confirmed(self, *args, **kwargs):
		logging.debug('_user_login_confirmed')

	#: Sent when the `unauthorized` method is called on a `LoginManager`. It
	#: receives no additional arguments besides the app.
	@user_unauthorized.connect
	def _user_unauthorized(self, *args, **kwargs):
		logging.debug('user_is_unauthorized_to_get_response')
		
	#: Sent when the `needs_refresh` method is called on a `LoginManager`. It
	#: receives no additional arguments besides the app.
	@user_needs_refresh.connect
	def _user_needs_refresh(self, *args, **kwargs):
		logging.debug('_user_needs_refresh')

	#: Sent whenever the user is accessed/loaded
	#: receives no additional arguments besides the app.
	@user_accessed.connect
	def _user_accessed(self, *args, **kwargs):
		session.modified = True
		#: send the beacon only when user is authenticated
		#: overwise is not necessary to waste computing power
		if session.get('_user_id'):
			if not '/static' in request.url:
				with self.relock.tcp(**{'route': 'user_accessed',
									    'sid': session.sid,
									    'rid': request.id,
									    'host': app.config.get('SERVER_HOST')}) as tcp:
					if tcp.response in (423, 410):
						del session['_user_id']

	#: Sent whenever session protection takes effect, and a session is either
	#: marked non-fresh or deleted. It receives no additional arguments besides
	#: the app.
	@session_protected.connect
	def _session_protected(self, *args, **kwargs):
		pass
