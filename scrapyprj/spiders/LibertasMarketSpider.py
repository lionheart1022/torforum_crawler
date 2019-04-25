# coding=utf-8

from scrapyprj.spiders.MarketSpider import MarketSpider
from scrapy.shell import inspect_response
from scrapy.http import FormRequest,Request
import scrapy
import re
from IPython import embed
import parser
import scrapyprj.items.market_items as items
from urlparse import urlparse, parse_qsl
import json
import scrapyprj.database.markets.orm.models as dbmodels
from datetime import datetime, timedelta, date
from random import randint


class LibertasMarketSpider(MarketSpider):
	name = "libertas_market"

	custom_settings = {
		'IMAGES_STORE' : './files/img/cgmp',
		'RANDOMIZE_DOWNLOAD_DELAY' : True,
		'HTTPERROR_ALLOW_ALL' : True,
		'RETRY_ENABLED' : True,
		'RETRY_TIMES' : 3
	}

	def __init__(self, *args, **kwargs):
		super(LibertasMarketSpider, self).__init__( *args, **kwargs)
		
		self.logintrial = 0

		self.set_max_concurrent_request(1)      # Scrapy config
		self.set_download_delay(12)             # Scrapy config
		self.set_max_queue_transfer_chunk(1)    # Custom Queue system
		self.statsinterval = 60;				# Custom Queue system

		self.parse_handlers = {
				'ads_list' 		: self.parse_ads_list,
				'ads' 			: self.parse_ads,
				'ads_ratings'	: self.parse_ads_ratings,
				'user' 			: self.parse_user,
				'user_ratings'	: self.parse_user_ratings
			}

	def start_requests(self):
		yield self.make_request('login')

	def make_request(self, reqtype,  **kwargs):

		if 'url' in kwargs:
			kwargs['url'] = self.make_url(kwargs['url'])

		if reqtype == 'login':
			req = Request(self.make_url('login'))
			if 'donotparse' in kwargs:
				req.meta['donotparse'] = True
			req.dont_filter=True
		elif reqtype == 'captcha_img':
			req  = Request(kwargs['url'])
			req.dont_filter = True

		elif reqtype == 'dologin':
			req = self.create_request_from_login_page(kwargs['response'])
			req.meta['req_once_logged'] = kwargs['req_once_logged']
			req.dont_filter=True
		elif reqtype == 'dochallenge':
			req = self.create_request_from_challenge_page(kwargs['response'])
			req.meta['req_once_logged'] = kwargs['req_once_logged']
			req.dont_filter=True
		elif reqtype in ['ads_list', 'ads', 'ads_ratings', 'user', 'image', 'user_ratings']:
			req = Request(self.make_url(kwargs['url']))
			req.meta['shared'] = True

		if reqtype == 'ads':
			req.meta['product_rating_for'] = kwargs['ads_id']
			req.meta['ads_id'] = kwargs['ads_id']

		if reqtype == 'user_ratings':
			req.meta['user_rating_for'] = kwargs['username']
			req.meta['username'] = kwargs['username']

		if reqtype == 'ads_ratings':
			req.meta['ads_rating_for'] = kwargs['ads_id']
			req.meta['ads_id'] = kwargs['ads_id']

		req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
		req.meta['proxy'] = self.proxy  #meta[proxy] is handled by scrapy.
		req.meta['slot'] = self.proxy

		if 'priority' in kwargs:
			req.priority = kwargs['priority']

		return req

	def parse(self, response):

		if response.status in range(400, 600):
			self.logger.warning("Got response %s at URL %s" % (response.status, response.url))
		elif not self.loggedin(response):	

			if self.isloginpage(response):
				self.logger.debug('Encountered a login page.')
				if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
					req_once_logged = response.meta['req_once_logged'] if  'req_once_logged' in response.meta else None
					self.wait_for_input("Too many login failed", req_once_logged)
					self.logintrial = 0
					return
				self.logger.info("Trying to login.")
				self.logintrial += 1

				req_once_logged = response.request
				if ('req_once_logged' in response.meta):
					req_once_logged = response.meta['req_once_logged']

				yield self.make_request('dologin', req_once_logged=req_once_logged, response=response, priority=10)
			elif self.ischallengepage(response):
				self.logger.debug('Encountered a challenge page.')
				if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
					req_once_logged = response.meta['req_once_logged'] if  'req_once_logged' in response.meta else None
					self.wait_for_input("Too many login failed", req_once_logged)
					self.logintrial = 0
					return
				self.logger.info("Trying to solve challenge.")
				self.logintrial += 1

				req_once_logged = response.request
				if ('req_once_logged' in response.meta):
					req_once_logged = response.meta['req_once_logged']
				yield self.make_request('dochallenge', req_once_logged=req_once_logged, response=response, priority=10)
			else:
				self.logger.warning('Something went wrong. See the exception and investigate %s. Dumping html: %s' % (response.url, response.body))
				raise Exception("Not implemented yet, figure what to do here !")
		else : 
			self.logintrial = 0

			# We restore the missed request when protection kicked in
			if response.meta['reqtype'] == 'dologin':
				self.logger.info("Login Success!")
				yield self.make_request('ads_list', url='ads_list')
			
			# Normal parsing
			else:
				it = self.parse_handlers[response.meta['reqtype']].__call__(response)
				if it:
					for x in it:
						if x:
							yield x

	def parse_ads_list(self, response):
		ad_links = response.css('section.main_items article a.lesser.button.wide.colored::attr(href)').extract()
		for link in ad_links:
			yield self.make_request('ads', url=link, ads_id=self.get_url_id(link))
		next_page_exists = response.xpath('.//ul[@class="pagi"]/li[3]/a/text()').extract_first() == 'Next page'
		if next_page_exists == True:
			self.logger.info("Debug info: Going to next page in the ads-list.")
			next_page = response.xpath('.//ul[@class="pagi"]/li[3]/a/@href').extract_first()
			yield self.make_request('ads_list', url=next_page)


	def parse_ads(self, response):
				
		ad_id = self.get_url_id(response.url)
		ad = items.Ads()
		ad['offer_id'] = ad_id
		ad['title'] = self.get_text(response.css('header h2'))
		vendor_profile_link = response.css('#containing-div div.inside a[href*="/profile/"]::attr(href)').extract_first()
		if vendor_profile_link:
			ad['vendor_username'] = self.get_url_id(vendor_profile_link)
			yield self.make_request('user', url=vendor_profile_link)
		
		ad['description'] = self.get_text(response.css('section.main_items article pre'))
		ad['fullurl'] = response.url
		parsed_url = urlparse(response.url)
		ad['relativeurl'] = parsed_url.path

		category_breadcrumb = response.css('div.containing-div a[href*="/advanced-search"]::text').extract_first()
		if category_breadcrumb:
			category = self.get_text(category_breadcrumb.split(u'→')[-1])
			ad['category'] = category

		tables = response.css('div.containing-div table')
		for table in tables:
			table_headers = table.css('thead th')
			table_columns = table.css('tbody td')
			if len(table_headers) == len(table_columns) and len(table_headers) > 0:
				for i in range(len(table_headers)):
					header = self.get_text(table_headers[i]).lower()
					text = self.get_text(table_columns[i])
					if header == 'price:':
						price = text
						ad['price_usd'] = re.search('\\$[0-9\\.]*', price).group()
						ad['price_xmr'] = re.search('\\[(.*?XMR)', price).group(1)
					elif header == 'sales:':
						ad['already_sold'] = text
					elif header == 'stock count:':
						ad['stock'] = text
					elif header == 'ships from:':
						ad['ships_from'] = text
					elif header == 'payment option:':
						ad['escrow'] = text

		feedback_link = response.css('div.inside a[href*="/item-feedback/"]::attr(href)').extract_first()
		if feedback_link:
			yield self.make_request('ads_ratings', url=feedback_link, ads_id=response.meta['ads_id'])

		yield ad

		# ad images doesn't work, maybe because they're base64? need to investigate...
		# ad_image_src = response.css('article div.image img::attr(src)').extract_first()
		# if ad_image_src:
		# 	img_item = items.AdsImage(image_urls = [])
		# 	img_item['image_urls'].append(self.make_request('image', url=ad_image_src))
		# 	img_item['ads_id'] = ad_id
		# 	yield img_item

	def parse_user(self, response):
		
		username = self.get_url_id(response.url)
		
		user = items.User()
		user['username'] = username
		user['public_pgp_key'] = self.get_text(response.css('section.main_items textarea'))
		
		tables = response.css('div.containing-div table')
		for table in tables:
			table_headers = table.css('thead th')
			table_columns = table.css('tbody td')
			if len(table_headers) == len(table_columns) and len(table_headers) > 0:
				for i in range(len(table_headers)):
					header = self.get_text(table_headers[i]).lower()
					text = self.get_text(table_columns[i])
					if header == 'rank':
						user['level'] = text
					elif header == 'last active:':
						user['last_active'] = self.parse_timestr(text)
					elif header == 'registered on libertas:':
						user['join_date'] = self.parse_timestr(text)
					elif header == 'ships from:':
						user['ship_from'] = text
					elif header == 'sales:':
						user['successful_transactions'] = text

		vendor_feedback = response.css('a[href*="/feedback/"]::attr(href)').extract_first()
		if vendor_feedback:
			feedback_text = self.get_text(response.css('a[href*="/feedback/"]'))
			user['average_rating'] = feedback_text.count('&starf;') # &starf; is the html entity for ★
			yield self.make_request('user_ratings', url=vendor_feedback, username=username)

		vendor_ads_link = response.css('article a[href*="/item/"]::attr(href)').extract()
		for link in vendor_ads_link:
			yield self.make_request('ads', url=link, ads_id=self.get_url_id(link))

		yield user
			

	def parse_ads_ratings(self, response):
		for rating_element in response.css('section.main_items article'):
			rating = items.ProductRating()
			rating['ads_id'] = response.meta['ads_id']
			header = self.get_text(rating_element.css('h1'))
			# header contains a bunch of info, formatted like this :
			# ★☆☆☆☆ 4 hours, 33 minutes ago: 2017-12-10
			header_parts = header.split(' ')
			last_part = header_parts[-1]
			if re.match('\d{4}-\d{2}-\d{2}', last_part):
				rating['submitted_on'] = last_part
			first_part = header_parts[0]
			rating['rating'] = first_part.count('&starf;') # &starf; is the html entity for ★
			rating['comment'] = self.get_text(rating_element.css('p'))
			yield rating

	def parse_user_ratings(self, response):
		for rating_element in response.css('section.main_items article'):
			rating = items.UserRating()
			rating['username'] = response.meta['username']
			rating['item_name'] = self.get_text(rating_element.css('h1 a'))
			rating['submitted_on'] = self.parse_timestr(self.get_text(rating_element.css('h4')))
			rating['rating'] = self.get_text(rating_element.css('h2')).count('&starf;') # &starf; is the html entity for ★ 
			rating['comment'] = self.get_text(rating_element.css('p'))
			yield rating

	def get_url_id(self, url):
		return self.get_text(url).split("/")[-1]

	def parse_timestr(self, timestr):
		try:	
			utcnow = datetime.utcnow()
			if timestr.lower() == 'today':
				return utcnow.replace(hour=12, minute=0, second=0, microsecond=0)
			
			m = re.search('(\d+) (minute|hour|day|week|month|year)s?, .* ago', timestr)
			if m:
				amount 	= int(m.group(1))
				unit 	= m.group(2)
				if unit == 'minute':
					delta = timedelta(minutes= amount)
				elif unit == 'hour':
					delta = timedelta(hours	= amount)
				elif unit == 'day':
					delta = timedelta(days	= amount)
				elif unit == 'week':
					delta = timedelta(days	= amount*7)
				elif unit == 'month':
					delta = timedelta(days = amount*30)
				elif unit == 'year':
					delta = timedelta(days = amount*365)

				# We try to roundup the date to avoid polluting the data history because datetime will change depending on 
				#when the crawler is launched.
				dt = datetime.utcnow() - delta
				dt = dt.replace(hour=12, minute=0, second=0, microsecond=0)	
				if unit == 'month':
					dt = dt.replace(day=1)
				elif unit == 'year':
					dt = dt.replace(month=1)
					dt = dt.replace(day=1)
				return dt
			else:
				return self.to_utc(dateutil.parser.parse(timestr))
			
		except Exception as e:
			self.logger.error("Cannot parse time string '%s'. Error : %s" % (timestr, e))

	def create_request_from_login_page(self, response):
		token = response.css('input[name="token"]::attr(value)').extract_first()
		
		data = {
			'username' : self.login['username'],
			'password' : self.login['password'],
			'token' : token,
		}

		req = FormRequest.from_response(response, formdata=data, formcss='section.main_items form')

		captcha_src = response.css('#challenge_code_img::attr(src)').extract_first()

		req.meta['captcha'] = {        # CaptchaMiddleware will take care of that.
			'request' : self.make_request('captcha_img', url=captcha_src),
			'name' : 'challenge_code'   
		}

		return req

	def create_request_from_challenge_page(self, response):
		token = response.css('input[name="token"]::attr(value)').extract_first()
		
		data = {
			'challenge_code' : '', # Filled by captcha middleware
		}

		req = FormRequest.from_response(response, formdata=data, formcss='#central form')

		captcha_src = response.css('#challenge_code_img::attr(src)').extract_first()

		req.meta['captcha'] = {        # CaptchaMiddleware will take care of that.
			'request' : self.make_request('captcha_img', url=captcha_src),
			'name' : 'challenge_code'
		}

		return req

	def loggedin(self, response):
		logout_link = response.css('#header nav a[title="Logout"]')
		if logout_link:
			return True

		return False

	def isloginpage(self, response):
		loginform = response.css('form input[name="username"]').extract_first()
		if loginform:
			return True
		
		return False

	def ischallengepage(self, response):
		loginform = response.css('form input[name="challenge_code"]').extract_first()
		if loginform:
			return True
		
		return False