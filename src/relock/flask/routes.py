from flask import (current_app as app, 
				   session, 
				   request, 
				   Response, 
				   url_for, 
				   json,
				   render_template, 
				   flash, 
				   jsonify, 
				   redirect, 
				   abort, 
				   make_response, 
				   session)

from flask_login import (current_user as worker, 
						 login_required)
from . import bp, logging

import bleach
import random, os
import time
import zstd
import pickle
import base64
import hashlib
import binascii
import subprocess

from datetime import datetime
from datetime import timedelta
from jsmin import jsmin
from gevent import sleep

from urllib.parse import urlparse

@bp.route('/remote', methods=['POST'])
def remote():
	""" This is a demo purpose only method. It should not be implemented 
		in production ready systems. The method when invoked (and should be
		invoked manually) emulates the behavior of stolen keys attack.

		This route is invoked by a user manually by a pressing the button
		inside the demo application.
	"""
	if response := request.device.remote():
		return response
	return dict()

@bp.route('/register', methods=['POST'])
def register():
	""" This method is invoked by a javascript component when the user
		is trying to register the passkey. The credential is passed from
		request directly to relock service.
	"""
	if request.method == 'POST' and request.json.get('credential'):
		return request.device.webauthn(request.json)
	return request.device.webauthn()

@bp.route('/authenticate', methods=['POST'])
def authenticate():
	""" This method is invoked by a javascript component when the user
		is trying to authenticate using passkey.
	"""
	if request.method == 'POST' and 'credential' in request.json:
		return request.device.authenticate(request.json.get('credential'))
	return request.device.authenticate()

@bp.route("/open", methods=['POST'])
def open(token=None):
	""" This method is invoked by the browser side javascript automatically, 
		when the user starts a new tab in browser durring the session.
	"""
	request.device.open(request.form.get('screen', str()),
						request.form.get('origin', str()),
						request.form.get('path', str()),
						request.form.get('xsid', str()),
						request.form.get('server', str()))
	return ('', 204)

@bp.route("/close", methods=['POST'])
def close(token=None, delay=1.5):
	""" This method is invoked by the browser at he moment of website 
		beeing unloaded from the browser tab. The browser sends a hash
		specyfic to the closed tab, if this is a last tab on browser 
		side the server will close a session and logout a user.
	"""
	request.device.close(request.form.get('screen', str()),
						 request.form.get('origin', str()),
						 request.form.get('path', str()))
	return ('', 204)

@bp.route("/exchange", methods=['POST'])
def exchange():
	""" This method is invoked by javascript at the moment when the browser
		has no registered keys for the domain. Before establish of trust the 
		browser and the server need to agree the secret material of the key.
	"""
	if not isinstance(request.json.get('key'), str):
		return dict(error='The key should be an hexlified bytes')
	if not isinstance(request.json.get('hash'), str):
		return dict(error='The hash should be an hexlified bytes')
	if keys := request.device.exchange(request.json.get('key'),
									   request.json.get('hash'),
									   request.json.get('xsid'),
									   request.json.get('screen')):
		return keys
	return dict(error='Key agreement failure.')

@bp.route("/validate", methods=['POST'])
def validate(token=None, signature=None):
	""" This route is invoked by a browser every time when the transient
		key has been rotated and/or whenever the confirmation of the keys 
		is needed. The parameters are passed in headers and/or as a json 
		message directly to the device object and next by a SDK connector 
		to the relock service.
	"""
	if keys := request.device.validate(request.json.get('screen', str()),
									   request.json.get('nonce', str()),
									   request.headers.get('X-Key-Token', str()),
									   request.headers.get('X-Key-Signature', str())):
		return keys
	return dict(status=False)

@bp.route('/relock.js', methods=['GET'])
def js(minified=True):
	""" This route is invoked manually, if relock javascript is embeded 
		to web page. To reduce the processing time the compiled data from 
		the relock service are assigned to the object in the current 	
		server process memory. Local data are modyficated only when 
		server-side returns different checksum of the compiled javascript 
		file.
	"""
	# print(app.extensions.get('relock_id', str()) and app.extensions.get('relock_id', str())[:-2] in \
	#       request.headers.get('If-None-Match', str()))
	if app.extensions.get('relock_id', str()) and \
	   app.extensions.get('relock_id', str())[:-2] in \
	   request.headers.get('If-None-Match', str()):
	   #: If request headers contains If-None-Match confirming
	   #: actual ETag hash there is no need to send the entire
	   #: javascript content.
		return ('', 304)
	# print(request.headers.get('If-None-Match', str()))
	if not 'relock_id' in app.extensions or app.config.get('DEBUG',False):
		if response := request.device.js(id=app.extensions.get('relock_id', str()),
										 minified=True,
										 debug=app.config.get('DEBUG',False),
										 host=app.config.get('SERVER_HOST')):
			if response.get('js'):
				app.extensions['relock_js'] = response.get('js')
			if response.get('id'):
				app.extensions['relock_id'] = response.get('id')
				app.extensions['relock_in'] = response.get('integrity')
				app.extensions['relock_cc'] = response.get('cache', None)
	if _ := Response(app.extensions.get('relock_js', bytes()), status=200, 
													 		   content_type='text/javascript; charset=utf-8'):
		_.headers.add('Etag', app.extensions.get('relock_id', str()))
		_.headers.add('If-Match', app.extensions.get('relock_id', str()))
		if cache := app.extensions.get('relock_cc', None):
			_.headers.add('Cache-Control', 'private,max-age='+ str(cache) +',must-revalidate')
		return _

@bp.route("/clear", methods=['POST', 'GET'])
def clear():
	""" This method is invoked by a relock javascript at the moment of 
		the failure of key agreement process. If invoked it will erase
		all information about device from server repository.
	"""
	if response := request.device.clear():
		return response
	return dict(status=False)

@bp.route("/clean", methods=['POST', 'GET'])
def clean():
	""" This route is used by a server-side at the moment when key
		agreement cannot be finalized and server required complete 
		key cleanup on browser-side.
	"""
	if response := request.device.clear():
		#: response contains names to be removed from 
		#: local/session storage and also the cookies names 
		#: need to be deleted.
		if html := '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">' + \
				   '<script type="text/javascript" nonce="'+ getattr(request, '__nonce', str()) +'">' + \
				   'localStorage.removeItem("signature");' + \
				   'localStorage.removeItem("tesseract");' + \
				   'localStorage.removeItem("server");' + \
				   'localStorage.removeItem("'+ response.get('stamp', 'stamp') +'");' + \
				   'localStorage.removeItem("client");' + \
				   'localStorage.removeItem("xsid");' + \
				   'sessionStorage.removeItem("'+ response.get('cookie', 'relock') +'");' + \
				   'sessionStorage.removeItem("screen");' + \
				   'setTimeout(() => {' + \
				   'document.location=\''+ url_for('index.index') + '\';' + \
				   '}, 500);' + \
				   '</script></head><body></body></html>':
			if resp := Response(html, status=200, 
								  	  content_type='text/html; charset=utf-8'):
				resp.delete_cookie(response.get('stamp', 'stamp'), path='/')
				resp.delete_cookie(response.get('cookie', 'relock'), path='/')
				return resp
	return abort(503)