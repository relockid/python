import re
import json
import os
import time
import hashlib
import xxhash
import binascii
import base64
import secrets
import logging
import pickle
import zlib

from flask import (current_app as app, 
				   url_for, 
				   redirect,
				   request,
				   abort,
				   has_request_context,
				   session, 
				   Response)
from flask_login import current_user as worker

from datetime import (datetime,
					  timedelta)

from uuid import uuid4
from typing import Any

from ...thread import Thread
from .login import Login

class Device(Login):

	def __init__(self):
		""" The Device object is created with each Flask request and is 
			accessible via a request.device link. Object is responsible 
			for communication with the relock service via TCP Unix sockets.

			The object is initialised before the request processing and 
			it lives as long as the request is being processed.

			Returns:
			    None
		"""
		self.__xsid      = bytes()
		self.__screen    = bytes()
		self.__owner     = False
		self.__nonce     = bytes()
		self.__signature = bytes()
		self.response    = dict()
		self.sid         = str(session.sid)
		self.rid         = str(request.id)
		self.host        = app.config.get('SERVER_HOST')
		#: The relock service TCP socket client registered as a flask 
		#: extension when app was initialized.
		self.relock      = app.relock
		
		if not '/static' in request.path or 'relock.js' in request.path:
			#: Flask request.path has a full url path requested by a user, but 
			#: the relock service requires a version stripped of parameters. 
			#: If possible, all params should be removed to avoid 403 errors 
			#: for forbidden routes.
			if request.url_rule:
				if path := str(request.url_rule) or request.path:
					if request.url_rule:
						if path := re.sub(r'\<.*',"", str(request.url_rule)):
							if len(path) > 1 and path[-1] == '/':
								path = path[:-1]
			else:
				path = request.path			
			#: For each non-static URL path, the relock service requires 
			#: registration of basic information about the request. To simplify 
			#: the management of this data, the initialised object passes the 
			#: required to relock service data by default.
			cookies = dict(session=request.cookies.get('session', str()))
			if request.cookies.get('relock'):
				cookies['relock'] = request.cookies.get('relock')
				cookies['stamp'] = request.cookies.get('stamp')
			with self('before', **{'cookies': cookies,
								   'host': request.headers.get('Host'),
								   'agent': request.headers.get('User-Agent'),
								   'addr': request.remote_addr,
								   'method': request.method,
								   'url': request.url,
								   'path': (path or request.path),
								   'user': worker.get_id(),
								   'email': worker.get_email(),
								   'authenticated': worker.is_authenticated,
								   'active': worker.is_active,
								   'anonymous': worker.is_anonymous,
								   'X-Key-Token': request.headers.get('X-Key-Token', str()) or 
									 		  	  request.form.get('X-Key-Token', str()) or
									 		  	  request.cookies.get('X-Key-Token', str()),
								   'X-Key-Signature': request.headers.get('X-Key-Signature', str()) or 
									 		  	  	  request.form.get('X-Key-Signature', str()) or
									 		  	  	  request.cookies.get('X-Key-Signature', str())}) as tcp:
				if tcp.response in (406, 426):
					#: The server may require to force user to re-authenticate if the 
					#: service-side session expires or the network location changes.
					if worker.is_authenticated:
						worker.logout()
					abort(redirect('/'))
				elif tcp.response in (400, 409, 410):
					#: If server side has key conflict or suspects malicious behaviour 
					#: it may require fresh establish of trust for user. This may require
					#: to cleanup the browser-side keys and new device registration.
					if worker.is_authenticated:
						worker.logout()
					if not path == url_for('relock.clean'):
						abort(redirect(url_for('relock.clean')))
				elif tcp.response in (401, 403):
					#: The response from the service may be forbidden if the 
					#: user keys do not match the server side or if data 
					#: manipulation was detected.
					if worker.is_authenticated:
						worker.logout()
					abort(tcp.response)
				elif tcp.response:
					#: If the request presents valid data that has been verified, 
					#: the server-side response registers in the object key 
					#: parameters. 
					#: 
					#: The key verification is made in separate dedicated 
					#: validation request, as the 'before' route only verificates 
					#: possession of appropriate data, not the ability to rotate 
					#: the transient key. 
					self.__xsid   = tcp.response.get('xsid', str())
					self.__screen = tcp.response.get('screen', str())
					self.__owner  = tcp.response.get('owner', False)
				else:
					#: This can only happen if the TCP socket is broken - it's 
					#: sensible to display 503 error, otherwise the user 
					#: keys may be broken.
					abort(503)

	def __call__(self, route:str = str(), **kwargs):
		""" The object call method is used as a router to the 
			relock service each	time the query to the service is 
			needed.

			:param route: The name of the action on service-side
			:type route: string

			Returns:
			    The service-side generated response for a call.
		"""
		with self.relock.tcp(**{'route': route,
							    'sid': self.sid,
							    'rid': self.rid,
							    'host': self.host,
								**kwargs}) as tcp:
			self.response = tcp.response
		return self

	def __enter__(self):
		return self
 
	def __exit__(self, *args):
		self.response = dict()

	def js(self, id:bytes = bytes(),
				 minified:bool = True,
				 debug:bool = True,
				 host:str = str()):
		""" This method recives the javascript library from the service 
			server. If neccessary the js content may be minified on the 
			relock service side. If debug mode is True the service will 
			check CRC32 sum of the js content and if it change it will 
			send a new version of compiled library otherwise service will 
			provide the checksum of the current version.

			:param id: Checksum of the actuall version of js librarry
			:type id: bytes
			:param minified: Minified version of the javascript requested
			:type minified: boolean
			:param debug: Debug mode allows on-the-fly changes of javascript
			:type debug: boolean
			:param host: Actual service hostname
			:type host: string

			Returns:
			    The server-side generated javascript librarry.
		"""
		with self('js', **{'id': id,
					       'minified': minified,
					       'debug': debug,
						   'host': host}) as tcp:
			if response := tcp.response:
				if response.get('js'):
					response['js'] = bytes(response.get('js', list()))
				return response
		return dict(status=False,
					error='Internal service error.')

	def check(self, token:str = str()) -> bool:
		""" The check method may be used to validate/vertficate the raw 
			token. This method will not validate the signature even if 
			providate as an argument. The token should be providad in a 
			RAW form of bytes or hexlified string. 

			:param token: Token that needs to be validated
			:type token: string

			Returns:
			    Token veryfication boolean confirmation.
		"""
		with self('check', **{'token': token,
							  'reuse': False}) as tcp:
			#: Server side response is always dict with boolean 'status' 
			#: parameter inside. Method itself returns bool True/False 
			#: as a result.
			if tcp.response.get('status'):
				return True
		return dict(status=False,
					error='Internal service error.')

	def confirm(self, reuse:bool = False) -> bool:
		""" This method may be used to validate tokens and signature of 
			token in the same time. The token and signature is not provided 
			directly in arguments but is 'downloaded' from Flask request 
			data. Optional reuse argument switch between alowing the server 
			to reuse token twice, if reuse is False token can be checked 
			only once.

			:param reuse: Allow token reuse, by default the service restricts 
				token verification to one-time use. If reuse is set to True, 
				the relock service will skip checking the previously used list.
			:type reuse: boolean

			Returns:
			    Token veryfication boolean confirmation.
		"""
		with self('confirm', **{'token': request.headers.get('X-Key-Token', str()) or 
								 		 request.form.get('X-Key-Token', str()) or 
								 		 request.cookies.get('X-Key-Token', str()),
							    'signature': request.headers.get('X-Key-Signature', str()) or 
								 		  	 request.form.get('X-Key-Signature', str()) or 
								 		 	 request.cookies.get('X-Key-Signature', str()),
								'reuse': reuse}) as tcp:
			if tcp.response.get('status', False):
				return True
		return False

	def clear(self) -> dict:
		""" This method erase all data about device on the server side. 
			After this command data restore is not possible. 
			
			Server side response does not matter as no data left anyway, 
			so as a	result of this method we got always empty dictionary.
		"""
		with self('clear') as tcp:
			return tcp.response
		return None

	def unlink(self) -> dict:
		""" Same as a clear method, unlink will destroy all informations 
			about the device on server-side. This method is explictly used 
			when user wants to unlink the passkey from the account.
		"""
		with self('unlink') as tcp:
			return None
		return dict(status=False,
					error='Internal service error.')

	def exchange(self, key:bytes = bytes(), 
					   hash:bytes = bytes(), 
					   xsid:bytes = bytes(), 
					   screen:bytes = bytes()) -> dict():
		""" Exchange method is invoked in the moment when a browser is 
			wanted to agree the secret material. The browser generates own 
			private sercret	key material and basis on this public key. 
			Current version of the relock service supports only ECDHE 
			key agreement method.

			If the key agreement is sucessful, the service will return 
			dictionary with a set of the informations:

			key, the public key generated explictly for this browser by a server
			signer, the public key for server signatures 
			token, the set of bytes used by a server to rotate the transient key
			xsid, the hash of the current session id
			recovery, encrypted by a shared key future session key material
			restore, bool information about restoration of the session key
			status, bool information about exchnage process succeed or not
			error, string explanation about eventual failure

			
			:param key: The public key generated by the browser in javascript, 
				the key is dedicated/assigned to this specyfic browser.
			:type key: bytes
			:param hash: The hash of the current version of the transient key, 
				hash is generated by a javascript library.
			:type hash: bytes
			:param xsid: Hash representing current session ID shared by the 
				relock service and browser. Hash is constant to the server side
				session and provided by a relock service to the browser.
			:type xsid: bytes
			:param screen: Hash associated with the current tab opened by a 
				user's browser. This hash is automatically generated by a 
				javascript when new browser session storage is sandboxed.
			:type screen: bytes
		"""
		with self('exchange', **{'key': key,
							     'hash': hash,
							     'xsid': xsid,
							     'screen': screen}) as tcp:
			return tcp.response
		return dict(status=False,
					error='Internal service error.')

	def validate(self, screen:bytes = bytes(), 
					   nonce:bytes = bytes(), 
					   token:[str|bytes] = str(), 
					   signature:[str|bytes] = str()) -> dict:
		""" The validate method is invoked by a browser every time when the key
			has been rotated and/or needs confirmation. As a result the method 
			returns a dictionary with a set of informations:

			status, boolean value representing the state of the process
			authenticated, bool information about user authentication status
			credential, bool confirmation that passkey is assigned to the device
			url, string url address required to be redirected after the process
			reprocess, bool indicator is fresh registration possible or not
			timeout, int value about required delay before redirect
			owner, bool confimration that device has been assigned to the owner

			:param screen: Dedicated hash generated by the browser for the 
				currently in use browser tab.
			:type screen: bytes
			:param nonce: Random set of bytes used to renew the secret material 
				of the transient key
			:type nonce: bytes
			:param token: The set of bytes generated basis on the current 
				version of the transient key. Defaults hexlified to the form of 
				the str object.
			:type token: bytes
			:param signature: The set of bytes generated using private key and 
				token that confirms the token comes from legitimate source.
				By default hexlified to the form of the str object.
			:type signature: bytes
		"""
		with self('validate', **{'screen': screen,
							     'nonce': nonce,
							     'token': token,
							     'signature': signature}) as tcp:
			if response := tcp.response:
				if not response.get('status'):
					#: The False status means we can't confirm the session and
					#: confirm device keys. To ensure secure state, user session
					#: should be revoked imidietly.
					if worker.is_authenticated:
						worker.logout()
				return response
		return dict(status=False)

	def webauthn(self, options:dict = dict()) -> dict:
		""" Generate options for registering a credential via 
			navigator.credentials.create()

			Returns:
			    Registration options ready for the browser. Consider 
			    using `helpers.options_to_json()` in this library to 
			    quickly convert the options to JSON.
		"""
		with self('webauthn', **{'options': options}) as tcp:
			return tcp.response

	def authenticate(self, credential:dict = dict()) -> dict:
		""" Generate options for authentication and also if credential 
			resolving the challange by a browser is passed authenticates 
			the user to the system.

			Returns:
				Dictionary for a stringified JSON version of the 
				WebAuthn response.
		"""
		with self('credential', **{'credential': credential}) as tcp:
			return tcp.response

	@property
	def credential(self) -> bool:
		""" Check if actual device has registered a corresponding
			credential for passkey authentication. If credentail is 
			assigned returns True.
		"""
		with self('credential') as tcp:
			return bool(tcp.response)
		return False

	@Thread.daemon
	def open(self, screen:str = str(), 
				   origin:str = str(), 
				   path:str = str(),
				   xsid:str = str(),
				   server:str = str()) -> dict:
		""" ...

			:param screen: Hash of the actuall tab id openend in browser
			:type screen: string
			:param origin: Hostname passed by a javascript librarry
			:type origin: string
			:param path: Document location passed by a js lib
			:type path: string

			Returns:
				None
		"""
		with self('open', **{'screen': screen,
							 'origin': origin,
							 'path': path,
							 'xsid': xsid,
							 'server': server}) as tcp:
			return None

	@Thread.daemon
	def close(self, screen:str = str(), 
					origin:str = str(), 
					path:str = str()) -> dict:
		""" Each time the browser unloads the web page content from a 
			sandbox, the JavaScript library sends a beacon with information 
			about unloaded page. This method can be called asynchronously 
			as it does not return a response.

			:param screen: Hash of the actuall tab id openend in browser
			:type screen: string
			:param origin: Hostname passed by a javascript librarry
			:type origin: string
			:param path: Document location passed by a js lib
			:type path: string

			Returns:
				None
		"""
		with self('close', **{'screen': screen,
							  'origin': origin,
							  'path': path}) as tcp:
			return None

	def remote(self, screen:str = str()) -> dict:
		""" Demo purpose only. This method emulates compromised key 
			usage by a remote server.
		"""
		with self('remote', **{'screen': screen}) as tcp:
			return tcp.response

	def sign(self, value:bytes) -> bool:
		""" This method signs the data using dedicated for the device
			private key.
		"""
		with self('sign', **{'value': value}) as tcp:
			if tcp.response:
				return tcp.response
		return None

	def token(self) -> bytes:
		""" This method generates a fresh token using current version of 
			the server-side transient key. Multiple tokens per request 
			may be generated. 
		"""
		with self('token') as tcp:
			if tcp.response:
				return tcp.response
		return None

	def verify(self, value:bytes = bytes(), 
					 signature:bytes = bytes()) -> bool:
		""" This method validates the token and a signature passed as 
			parameters. If the signature is appropriate and the token 
			matches the server-side transient key, it returns True. 

			:param value: Token that has to be verificated
			:type value: bytes
			:param signature: Token signature by a corresponding private key
			:type signature: bytes
		"""
		with self('verify', **{'value': value,
							   'signature': signature}) as tcp:
			if tcp.response:
				return tcp.response
		return None

	@property
	def protected(self):
		""" Setup a protected mode for the device. If protected mode is
			set to True, relock service will not allow to create any
			new device for user account and all request to the application
			will be allowed only from authorized devices only.

			This turns on the strict device veryfication mode.
		"""
		with self('protected', **{'state': None,
								  'user': session.get('_user_id'),
								  'email': session.get('email')}) as tcp:
			return bool(tcp.response)
		return False

	@protected.setter
	def protected(self, state:bool = None):
		with self('protected', **{'state': bool(state),
								  'user': session.get('_user_id'),
								  'email': session.get('email')}) as tcp:
			if tcp.response:
				return tcp.response
		return None

	@property
	def owner(self):
		""" The x-owner is generated along with the object initialization, 
			if attribute exists and server-side Device object is assigned 
			to this practicular id, the property returns exactly the same 
			id as passed to init of the object.

			Returns:
				The user identity registered to the device.
		"""
		return self.__owner

	@property
	def screen(self):
		""" The x-screen is generated along with the object initialization, 
			if attribute exists, the property returns a hexadecimal version 
			of the bytes. It represents the actual, random, identity of the 
			user tab in the browser.

			Returns:
				Hexlified bytes representing server-side screen id.
		"""
		return self.__screen

	@property
	def xsid(self):
		""" The x-session-id is generated along with the object initialization, 
			if attribute exists, the property returns a hexadecimal version of 
			the bytes.

			Returns:
				Hexlified bytes representing server-side session id.
		"""
		return self.__xsid

	@property
	def signature(self):
		""" The signature is generated along with the nonce, if exists, 
			the property returns a hexadecimal version of the signature 
			bytes.

			Returns:
				Hexlified bytes representing nonce signature.
		"""
		if self.__nonce and self.__signature:
			return binascii.hexlify(self.__signature).decode()
		return str()

	@property
	def nonce(self) -> str:
		""" The nonce property is used manually to trigger the re-keying of 
			the transient key on the selected page views. Once triggered the
			nonce will be used in key rotation before validation request.

			Returns:
				Hexlified bytes generated for re-keying / nonce bytes.
		"""
		if not self.__nonce:
			#: re-keying nonce may be generated only one-time per request
			#: processing, so there is no sense to ask relock service
			#: multiple times about it.
			with self('nonce') as tcp:
				if tcp.response:
					if nonce := binascii.unhexlify(tcp.response.get('nonce')):
						self.__nonce = nonce
						if signature := binascii.unhexlify(tcp.response.get('signature')):
							self.__signature = signature
		if self.__nonce:
			return binascii.hexlify(self.__nonce).decode()
		return str()

	""" Before processing the request, we need to initialise the Device object 
		on the application side. The application will have access to the relock 
		service via the TCP socket handled by this connector.

		The relock service require two identifaction items, the session Id 
		and the rquest Id to process the request correctly.

		Returns:
			None
	"""
	@classmethod
	def before(cls) -> None:
		#: If current session has nothing in a server-side storage, Flask 
		#: will create a new fresh session id for each new incoming request. 
		#: Thats the reason of creating the random ['id'] in session storage.
		if not 'id' in session:
			session['id'] = str(uuid4())
		#: If request has no any identyficator that we can use it, let's 
		#: create one before sending data to relock service.
		if not hasattr(request, 'id'):
			setattr(request, 'id', str(uuid4()))
		#: Durring the request processing we can use the same/single TCP
		#: pipeline, that will speed up relock-side processing.
		if not hasattr(request, 'device'):
			if request.method.lower() in ('get', 'post'):
				setattr(request, 'device', Device())


	"""	After processing of the request the relock service may return cookie
		directives (set or delete cookie).

		:param response: Response generated by the Flask framework for this 
			practicular request.
		:type response: Flask response object

		Returns:
			Flask response object
	"""
	@classmethod
	def after(cls, response) -> object:
		#: Request finalization may return information about cookies needed 
		#: to be set after request, however there is no need to process
		#: anyting if we are processing the /static path. Static files don't
		#: set cookies.
		if request.method.lower() in ('get', 'post'):
			if not '/static' in request.path:
				#: Flask is closing TCP connection after request processing so
				#: it's required to use fresh pipeline to finalize the operation.
				#: New pipe may not neccessary be connected to the same relock 
				#: service, and request may be processed by different server.
				with app.relock.tcp(**{'route': 'after',
									   'sid': session.sid,
									   'rid': request.id,
									   'status': response.status,
									   'code': response.status_code,
								  	   'host': app.config.get('SERVER_HOST')}) as tcp:
					if tcp.response:
						#: The cookie data coming from relock service are raw, so 
						#: we need to convert seconds to the apropriate timestamp 
						#: for browser cookie set.
						for name, cookie in tcp.response.items():
							if 'value' in cookie:
								response.set_cookie(name, value=cookie.get('value'),
														  expires=datetime.now() + timedelta(seconds=cookie.get('expires')),
														  max_age=timedelta(seconds=cookie.get('max_age')),
														  path=cookie.get('path'),
														  domain=cookie.get('domain'),
														  secure=cookie.get('secure'), 
														  httponly=cookie.get('httponly'),
														  samesite=cookie.get('samesite'))
							else:
								#: If cookie has no any value this means relock service
								#: require cookie delete.
								response.delete_cookie(name, path='/')
		return response

