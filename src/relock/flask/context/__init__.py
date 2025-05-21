import logging
import binascii
from flask import (current_app as app, 
				   has_request_context,
				   request,
				   session)

#: Context functions that can be used directly 
#: by Jinja templates.

@app.context_processor
def x_key_xsid_processor():
	
	def x_key_xsid():
		if hasattr(request, 'device'):
			if xsid := request.device.xsid:
				return xsid
		return str()
	return dict(x_key_xsid=x_key_xsid)

@app.context_processor
def x_key_screen_processor():
	def x_key_screen():
		if hasattr(request, 'device'):
			if screen := request.device.screen:
				return request.device.screen
		return str()
	return dict(x_key_screen=x_key_screen)

@app.context_processor
def x_key_nonce_processor():
	def x_key_nonce():
		if hasattr(request, 'device'):
			return request.device.nonce
		return str()
	return dict(x_key_nonce=x_key_nonce)

@app.context_processor
def x_key_signature_processor():
	def x_key_signature():
		if hasattr(request, 'device'):
			return request.device.signature
		return str()
	return dict(x_key_signature=x_key_signature)

@app.context_processor
def x_key_credential_processor():
	def x_key_credential():
		if hasattr(request, 'device'):
			if credential := request.device.credential:
				return credential
		return str()
	return dict(x_key_credential=x_key_credential)

@app.context_processor
def x_key_remote_addr_processor():
	def x_key_remote_addr():
		if hasattr(request, 'device'):
			if addr := request.remote_addr:
				return addr
		return str()
	return dict(x_key_remote_addr=x_key_remote_addr)