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
import dateutil.parser

class CannabisGrowersCoopSpider(MarketSpider):
	name = "cgmc_market"

	custom_settings = {
		'IMAGES_STORE' : './files/img/cgmp',
		'RANDOMIZE_DOWNLOAD_DELAY' : True
	}

	def __init__(self, *args, **kwargs):
		super(CannabisGrowersCoopSpider, self).__init__( *args, **kwargs)
		
		self.logintrial = 0

		self.set_max_concurrent_request(2)      # Scrapy config
		self.set_download_delay(12)              # Scrapy config
		self.set_max_queue_transfer_chunk(1)    # Custom Queue system
		self.statsinterval = 60;				# Custom Queue system

		self.parse_handlers = {
				'index' 		: self.parse_index,
				'ads_list' 		: self.parse_ads_list,
				'ads' 			: self.parse_ads,
				'ads_images'	: self.parse_ads_images,
				'ads_ratings'	: self.parse_ads_ratings,
				'user' 			: self.parse_user,
				'user_ratings'	: self.parse_user_ratings
			}

	def start_requests(self):
		yield self.make_request('index')

	def make_request(self, reqtype,  **kwargs):

		if 'url' in kwargs:
			kwargs['url'] = self.make_url(kwargs['url'])

		if reqtype == 'index':
			req = Request(self.make_url('index'))
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
		elif reqtype in ['ads_list', 'ads', 'ads_ratings', 'user', 'image', 'user_ratings', 'ads_images']:
			req = Request(self.make_url(kwargs['url']))
			req.meta['shared'] = True

		if reqtype == 'ads':
			req.meta['product_rating_for'] = kwargs['ads_id']

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
		
		if 'accepted_currencies' in kwargs:
			req.meta['accepted_currencies'] = kwargs['accepted_currencies']
		
		if 'sublisting_quantity' in kwargs:
			req.meta['sublisting_quantity'] = kwargs['sublisting_quantity']

		return req

	def parse(self, response):
		if not self.loggedin(response):	

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
			else:
				self.logger.warning('Something went wrong. See the exception and investigate %s. Dumping html: %s' % (response.url, response.body))
				raise Exception("Not implemented yet, figure what to do here !")
		else : 
			self.logintrial = 0

			# We restore the missed request when protection kicked in
			if response.meta['reqtype'] == 'dologin':
				self.logger.info("Login Success!")
				yield response.meta['req_once_logged']
			
			# Normal parsing
			else:
				it = self.parse_handlers[response.meta['reqtype']].__call__(response)
				if it:
					for x in it:
						if x:
							yield x

		
	def parse_index(self, response):
		if 'donotparse' in response.meta and response.meta['donotparse']:
			self.logger.debug('Do not parse index')
		else:
			yield self.make_request('ads_list', url='ads_list')


	def parse_ads_list(self, response):

		ads_info = response.css("div.listing")
		for ad_info in ads_info:
			accepts_btc = ad_info.css("div.cryptocurrencies i.icon-bitcoin").extract_first()
			accepts_ltc = ad_info.css("div.cryptocurrencies i.icon-litecoin").extract_first()
			accepted_currencies = ""
			if accepts_btc and accepts_ltc:
				accepted_currencies = "btc,ltc"
			elif accepts_btc and not accepts_ltc:
				accepted_currencies = "btc"
			elif accepts_ltc and not accepts_btc:
				accepted_currencies = "ltc"

			options = ad_info.css("div.options a")
			if len(options) > 0: # We found the different sublistings with quantities
				for option in options:
					url = option.css("::attr(href)").extract_first()
					qty = self.get_text(option)
					yield self.make_request('ads', url=url, ads_id = self.get_ad_id(url), sublisting_quantity = qty, accepted_currencies = accepted_currencies)
			else: # No sublisting, single item
				url = ad_info.css("a.image::attr(href)").extract_first()
				yield self.make_request('ads', url=url, ads_id = self.get_ad_id(url), accepted_currencies = accepted_currencies)
				
		#ads_url = response.css("div.listing a.image::attr(href)").extract()
		#for url in ads_url:
		#	yield self.make_request('ads', url=url, ads_id = self.get_ad_id(url))

		next_page_url = response.css(".listing-cols a.arrow-right::attr(href)").extract_first()
		if next_page_url:
			yield self.make_request('ads_list', url=next_page_url)

	def parse_ads(self, response):
		ads_id = self.get_ad_id(response.url)
		ads_item = items.Ads()
		ads_item['offer_id'] = ads_id
		ads_item['title'] = self.get_text(response.css('section#main .product h2'))
		ads_item['vendor_username'] = self.get_text(response.css('section#main .product .col-7.rows-10 .row.rows-20 .row a'))
		ads_item['description'] = self.get_text(response.css('section#main .row.cols-20 .top-tabs .formatted'))
		if 'accepted_currencies' in response.meta:
			ads_item['accepted_currencies'] = response.meta['accepted_currencies']
			accepted_currencies = response.meta['accepted_currencies']
		else: 
			accepted_currencies = ""
		if 'sublisting_quantity' in response.meta:
			ads_item['price_options'] = response.meta['sublisting_quantity']
		
		price = self.get_text(response.css('section#main .product .price .small'))
		if 'LTC' in price:
			ads_item['price_ltc'] = price
		elif 'BTC' in price:
			ads_item['price'] = price
		elif 'minimum' in price:
			self.logger.info('No price in cryptocurrency available at %s. Trying to exchange into BTC using exchange rate.' % (response.url))
			# Get the exchange rate.
			exchange_rate = response.xpath('.//div[@class="exchange-rate"]/text()').extract_first()
			exchange_rate = re.search('\$([0-9\\.,]*)', exchange_rate).group(1)
			exchange_rate = exchange_rate.replace(',','')
			exchange_rate = float(exchange_rate)
			# Get the price.
			price = response.css('section#main .product .price .big').extract_first()
			price = re.search('\$([0-9\\.]*)', price).group(1)
			price = float(price)
			# Calculate price in BTC.
			price = price/exchange_rate
			price = str(price) + " BTC"
			ads_item['price'] = price
		else:
			self.logger.warning('Unhandled price input.' % (response.url))
		
		ads_item['ships_from'] = self.get_text(response.css('section#main .row.cols-20 .top-tabs .col-6.label.big:last-child'))
		ads_item['fullurl'] = response.url
		parsed_url = urlparse(response.url)
		ads_item['relativeurl'] = parsed_url.path
		ads_item['shipping_options'] = json.dumps(self.get_shipping_options(response))

		image_urls = response.css('section#main .product figure a::attr(href)').extract()
		if len(image_urls) > 0:
			yield self.make_request('ads_images', url = response.url + '?q=1') # hack to make urls unique

		# Sublistings
		product_options = response.css("div.listing_options a::attr(href)").extract()
		if len(product_options) > 0:
			ads_item['multilisting'] = True
			for sublisting_url in product_options:
				yield self.make_request('ads', url=sublisting_url, ads_id=self.get_ad_id(sublisting_url), accepted_currencies = accepted_currencies)
		else:
			ads_item['multilisting'] = False

		yield ads_item

		vendor_url = response.css('section#main .product .col-7.rows-10 .row.rows-20 .row a::attr(href)').extract_first()

		yield self.make_request('user', url = vendor_url, priority=5)
		
		ratings_url = response.css('section#main .product .row.big-list a::attr(href)').extract_first()

		# We don't get ratings from the products page anymore, only from vendor pages
		#if ratings_url:
		#		yield self.make_request('ads_ratings', url=ratings_url, priority=5, ads_id=ads_id)

	def parse_ads_images(self, response):
		# Somehow CGMC doesn't like when ads images and ads are scapred from the same page and keeps
		# throwing foreign key exceptions (trying to save images before the ad is saved)
		# Hack : Make a new request only for images, not clean, but it works :\ 
		ads_id = self.get_ad_id(response.url)
		image_urls = response.css('section#main .product figure a::attr(href)').extract()
		if len(image_urls) > 0:
			img_item = items.AdsImage(image_urls = [])
			for img_url in image_urls:
				img_item['image_urls'].append(self.make_request('image', url=img_url))
			img_item['ads_id'] = ads_id
			yield img_item

	def parse_ads_ratings(self, response):
		for rating_element in response.css("ul.list-ratings li"):
			rating = items.ProductRating()
			rating['ads_id'] = response.meta['ads_id']
			#rating['submitted_on'] = self.get_text(rating_element.css('.left date'))
			rating['submitted_on'] = self.to_utc(dateutil.parser.parse(self.get_text(rating_element.css('.left date'))))
			rating['rating'] = len(rating_element.css('.rating.stars i.full'))
			rating['comment'] = self.get_text(rating_element.css('div.right.formatted'))
			yield rating


	def get_shipping_options(self, response):
		options_list = []
		options = response.css('section#main .row.cols-20 .top-tabs .zebra li')
		for option in options:
			option_dict = {
				'price' : self.get_text(option.css('.aux span')),
				'name' : self.get_text(option.css('.main'))
				}
			options_list.append(option_dict)
		return options_list

	def get_ad_id(self, url):
		return self.get_text(url).split("/")[-2]

	def parse_user(self, response):
		user = items.User()
		user['username'] = self.get_text(response.css('section#main .vendor-box h2'))
		user['public_pgp_key'] = self.get_text(response.css('.textarea.pgp textarea'))
		
		news = response.css('section#main .vendor-box .grey-box.formatted div.formatted')
		if news:
			user['news'] = self.get_text(news)
			# News history in /blog/[username], is there a way to collect all news for a vendor?

		ratings = response.css('section#main .vendor-box .rating.stars')
		if ratings:
			ratings_text = self.get_text(ratings)
			match = re.search('\[(.*)\]\((\d+) ratings\)', ratings_text)
			if match:
				user['average_rating'] = match.group(1)
				user['feedback_received'] = match.group(2)

		user['last_active'] = self.parse_timestr(self.get_text(response.css('section#main .vendor-box .corner li:first-child>div:first-child')))
		user['forum_posts'] = self.get_text(response.css('section#main .vendor-box .corner li:nth-child(2)>div:first-child'))
		user['subscribers'] = self.get_text(response.css('section#main .vendor-box .corner li:last-child>div:first-child'))
		user['relativeurl'] = urlparse(response.url).path
		user['fullurl']     = response.url

		tabs_buttons_list = response.css('.special-tabs input[name="vendor-section"]')
		tabs_list = response.css('.special-tabs .right .contents .formatted')
		if tabs_buttons_list and tabs_list and len(tabs_buttons_list) == len(tabs_list):
			i = 0
			profile = list()
			for tab_button in tabs_buttons_list:
				tab = tabs_list[i]
				section = self.get_text(tab_button.css('::attr(id)').extract_first())
				if 'terms' in section:
					user['terms_and_conditions'] = self.get_text(tab)
				elif 'ship' in section:
					user['shipping_information'] = self.get_text(tab)
				elif 'news' in section:
					user['news'] = self.get_text(tab)
				elif 'refund' in section:
					user['refund_policy'] = self.get_text(tab)
				elif 'reship' in section:
					user['reship_policy'] = self.get_text(tab)
				else:
					profile.append(self.get_text(tab))
					#self.logger.warning('Found an unknown section on profile page : %s (%s)' % (section, response.url))
				i += 1
			user['profile'] = "".join(profile)
		yield user

		reviews_url = response.css('section#main .vendor-box .rating.stars a::attr(href)').extract_first()
		if reviews_url:
			yield self.make_request('user_ratings', url=reviews_url, username=user['username'], priority=5)

	def parse_user_ratings(self, response):
		for rating_element in response.css("ul.list-ratings li"):
			product_name_element = rating_element.css('div.left small')
			product_url = product_name_element.css("a::attr(href)").extract_first()
			if (product_url):
				rating = items.ProductRating()
				ad_id = self.get_ad_id(product_url)
				rating['ads_id'] = ad_id
				yield self.make_request('ads', url=product_url, ads_id = ad_id)
			else: # No product URL found, still save it with the product name
				rating = items.UserRating()
				rating['username'] = response.meta['username']
				rating['item_name'] = self.get_text(product_name_element)
			
			#rating['submitted_on'] = self.get_text(rating_element.css('.left date'))
			rating['submitted_on'] = self.to_utc(dateutil.parser.parse(self.get_text(rating_element.css('.left date'))))

			rating['rating'] = len(rating_element.css('.rating.stars i.full'))
			rating['comment'] = self.get_text(rating_element.css('div.right.formatted'))
			yield rating
		
		
		next_page_url = response.css("section#main a.arrow-right::attr(href)").extract_first()
		if next_page_url:
			yield self.make_request('user_ratings', url=next_page_url, username=response.meta['username'])
		
	def parse_timestr(self, timestr):
		try:	
			utcnow = datetime.utcnow()
			if timestr.lower() == 'today':
				return utcnow.replace(hour=12, minute=0, second=0, microsecond=0)
			
			m = re.search('~?(\d+) (minute|hour|day|week|month|year)s? ago', timestr)
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

	def loggedin(self, response):
		my_account_link = response.css('header .right .menu .drop:last-child > a')
		if my_account_link and my_account_link.css("::text").extract_first() == "My Account":
			return True

		return False

	def isloginpage(self, response):
		loginform = response.css('form#login-form').extract_first()
		if loginform:
			return True
		
		return False

	def create_request_from_login_page(self, response):

		data = {
			'username' : self.login['username'],
			'password' : self.login['password'],
			'user_action' : 'login',
			'return' : '/',
		}

		req = FormRequest.from_response(response, formdata=data, formcss='form#login-form')

		captcha_src = '/login/showCaptcha?' + str(randint(100000, 999999))

		req.meta['captcha'] = {        # CaptchaMiddleware will take care of that.
			'request' : self.make_request('captcha_img', url=captcha_src),
			'name' : 'captcha'   
		}

		return req
