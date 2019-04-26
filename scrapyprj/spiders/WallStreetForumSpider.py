from __future__ import absolute_import
import scrapy
from scrapy.http import FormRequest,Request
from scrapy.shell import inspect_response
from scrapyprj.spiders.ForumSpiderV2 import ForumSpiderV2
from scrapyprj.database.orm import *
import scrapyprj.database.forums.orm.models as models
import scrapyprj.items.forum_items as items
from datetime import datetime, timedelta
from urlparse import urlparse, parse_qsl
import logging
import time
import hashlib 
import traceback
import re
import pytz
import dateutil
from IPython import embed
from random import randint

# Fix up timezone.
# Set up max login retries

class WallStreetForumSpider(ForumSpiderV2):
	name = "wallstreet_forum"
	
	custom_settings = {
		'MAX_LOGIN_RETRY' : 10,
		'IMAGES_STORE' : './files/img/wallstreet_forum',
		'RANDOMIZE_DOWNLOAD_DELAY' : True
	}

	
	def __init__(self, *args, **kwargs):
		super(WallStreetForumSpider, self).__init__(*args, **kwargs)

		self.set_max_concurrent_request(1)	  # Scrapy config
		self.set_download_delay(0)			 # Scrapy config
		self.set_max_queue_transfer_chunk(1)	# Custom Queue system
		self.statsinterval = 60 				# Custom Queue system

		self.logintrial = 0
	
	def parse_response(self, response):
		#self.logger.warning("Debugging. requested URL: %s. Header: %s. Meta: %s. Response header: %s" % (response.request.url, response.request.headers, response.request.meta, response.headers))
		parser = None
		if self.is_loggedin(response) == True:
			# we're logged in!
			self.logger.info('Logged in!')
		elif self.is_loggedin(response) is False and self.is_loginpage(response) is False:
		 	self.logger.info('Not logged in.')
		 	yield self.go_to_login(response)
		elif self.is_loggedin(response) is False and self.is_loginpage(response) is True: # It's a login page! Create the request and submit it.
		 	self.logger.info('Login page.')
		 	yield self.do_login(response)


	def go_to_login(self, response):
		self.logger.info('Requesting login page.')
		req = Request(self.make_url('login'), dont_filter=True, priority=10)
		return req


	def do_login(self, response):
		#dump = response.xpath(".//body").extract_first()
		self.logger.warning('On login page. Submitting login.')
		# data = {
		# 	'form_sent' : response.xpath('.//input[@name="form_sent"]/@value').extract_first(),
		# 	'redirect_url' : response.xpath('.//input[@name="redirect_url"]/@value').extract_first(),
		# 	'csrf_token' : response.xpath('.//input[@name="csrf_token"]/@value').extract_first(),
		# 	'req_username' : self.login['username'],
		# 	'req_password' : self.login['password'],
		# 	'login' : 'Login'
		# 	}
		data = {
			'req_username' : self.login['username'],
			'req_password' : self.login['password'],
			}
		req = FormRequest.from_response(response, formdata=data, formxpath='.//form[@id="afocus"]', priority = 11)
		self.logger.warning('%s' % req.body)
		return req

	def is_loggedin(self, response):
		if response.xpath('.//p[@id="welcome"]/span[1]/text()').extract_first() == "You are not logged in.":
			return False
		else:
			return True

	def is_loginpage(self, response):
		if len(response.xpath('.//form[@id="afocus"]')) == 1:
			return True
		else:
			return False
