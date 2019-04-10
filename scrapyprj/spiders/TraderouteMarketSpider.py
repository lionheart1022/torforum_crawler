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
from datetime import datetime, timedelta
import dateutil

class WarningException(Exception):
	pass

class TraderouteMarketSpider(MarketSpider):
	name = "traderoute_market"

	custom_settings = {
		'IMAGES_STORE' : './files/img/traderoute_market',
		'RANDOMIZE_DOWNLOAD_DELAY' : True,
		'RESCHEDULE_RULES' : {
		'An error occured, please refresh the page or contact support if the problem persists' : 60 
		}
	}


	def __init__(self, *args, **kwargs):
		super(TraderouteMarketSpider, self).__init__( *args, **kwargs)
		
		self.logintrial = 0

		self.set_max_concurrent_request(1)		# Scrapy config
		self.set_download_delay(1.5)			# Scrapy config
		self.set_max_queue_transfer_chunk(1) 	# Custom Queue system
		
		self.statsinterval = 30;				# Custom Queue system

		self.parse_handlers = {
				'index' 		: self.parse_index,
				'category' 		: self.parse_category,
				'userprofile' 	: self.parse_userprofile,
				'listing' 		: self.parse_listing
			}

	def start_requests(self):
		yield self.make_request('index')


	def make_request(self, reqtype,  **kwargs):

		passthru_kwargs = ['category', 'relativeurl']

		if 'url' in kwargs:
			kwargs['url'] = self.make_url(kwargs['url'])

		if reqtype == 'index':
			req = Request(self.make_url('index'))
			req.dont_filter=True
		elif reqtype == 'loginpage':
			req = Request(self.make_ur('login'))
			req.dont_filter=True
		elif reqtype == 'dologin_username':
			req = req = self.craft_login_username_request_from_form(kwargs['response'])
			req.dont_filter=True
		elif reqtype == 'dologin_password':
			req = req = self.craft_login_password_request_from_form(kwargs['response'])
			req.dont_filter=True
		elif reqtype=='image':
			req = Request(url = kwargs['url'])
			if 'referer' in kwargs:
				req.headers['Referer'] = kwargs['referer']

		elif reqtype in ['category', 'listing', 'userprofile']:
			req = Request(url=kwargs['url'])
			req.meta['shared'] = True
		else:
			raise Exception('Unsuported request type %s ' % reqtype)

		for arg in passthru_kwargs:
			if arg in kwargs:
				req.meta[arg] = kwargs[arg]

		if reqtype == 'listing':
			req.meta['product_rating_for'] = kwargs['ads_id']

		req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
		req.meta['proxy'] = self.proxy  # meta[proxy] is handled by scrapy.

		if 'req_once_logged' in kwargs:
			req.meta['req_once_logged'] = kwargs['req_once_logged']

		return req


	def parse(self, response):
		if self.is_expulsed(response):
			self.wait_for_input("Crawler have been expulsed.", self.make_request('index'))
		elif self.isloginpage_username(response):
			self.logintrial +=1
			self.logger.info("Trying to login. Page 1 (Login + Captcha)")
			
			if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
				self.wait_for_input("Too many failed login trials. Giving up.", self.make_request('index'))
				self.logintrial=0
				return 

			yield self.make_request(reqtype='dologin_username', response=response)
		elif self.isloginpage_password(response):
			self.logintrial +=1
			self.logger.info("Trying to login. Page 2 (Password)")
			
			if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
				self.wait_for_input("Too many failed login trials. Giving up.", self.make_request('index'))
				self.logintrial=0
				return 

			yield self.make_request(reqtype='dologin_password', response=response)
		else: 
			self.logintrial = 0

			# We restore the missed request when protection kicked in
			if response.meta['reqtype'] == 'dologin_password':
				self.logger.info("Login Success!")
				yield self.make_request('index')
			
			# Normal parsing
			else:
				it = self.parse_handlers[response.meta['reqtype']].__call__(response)
				if it:
					for x in it:
						if x:
							yield x

	def parse_index(self, response):
		categories=response.css(".menu-item h4")
		for category in categories:
			subcategories = category.xpath('following-sibling::ul/li/a')
			for subcategory in subcategories:
				category_path = '%s/%s' % (self.get_text(category.xpath('a/text()').extract_first()), self.get_text(subcategory.xpath('text()').extract_first()))
				url = subcategory.xpath('@href').extract_first();
				yield self.make_request(reqtype='category', url=url, category=category_path)

	def parse_category(self, response):
		for listing_container in response.css(".wLf"):
			listing_url = listing_container.css(".wLfName a::attr(href)").extract_first()
			ads_id = self.get_url_param(self.make_url(listing_url), 'lid')			# Used to gather feedbacks correctly.  feedback_buffer_middleware uses that
			yield self.make_request('listing', url=listing_url, category=response.meta['category'], relativeurl=listing_url, ads_id=ads_id)

			user_url = response.css('.wLfVendor a::attr(href)').extract_first()
			yield self.make_request('userprofile', url=user_url)

			for url in response.css('.main-content div.pagination a::attr(href)').extract():
				if self.get_url_param(url, 'pg') != '1':
					yield self.make_request('category', url=url, category=response.meta['category'])

	def parse_userprofile(self, response):
		user = items.User();
		profile_content = response.css("#content1")

		user['username'] 	= self.get_url_param(response.url, 'user')
		user['fullurl'] 	= response.url
		user['profile']	= self.get_text_first(profile_content.css('.bubble p'))

		up = urlparse(response.url)
		user['relativeurl']	= up.path
		if up.query:
			user['relativeurl'] += '?%s' % up.query
		
		# Username text has a title like "Vendor Steve has xx feedback lbah blah blah". We grab the title there.
		user_title_text = self.get_text(profile_content.css('.grid .grid').xpath('.//span[contains(text(), "%s")]/@title' % user['username']).extract_first())
		m = re.search('(\w+)\s*%s' % user['username'],  user_title_text, re.IGNORECASE)
		if m:
			user['title'] = m.group(1)

		# Lot of property listed in listing
		# So it's hard to pinpoint the right data here. What we do is that we find the data div (<div><label>Feedback Score</label> <htmlhtml> xxx</div>)
		# We normalize text, search for the label content, take the rest as the value.
		for label in profile_content.css('.grid .grid label'):
			fulltext = self.get_text(label.xpath('..'))
			label_text = self.get_text(label).lower()
			m = re.search('%s(.+)' % label_text, fulltext, re.IGNORECASE | re.S)
			if m:
				value = m.group(1).strip()
				if label_text == 'feedback score':
					user['average_rating'] = value
				elif label_text == 'Sales':
					user['successful_transactions'] = value
				elif label_text == 'last logged':
					user['last_active'] = self.parse_timestr(value)
				elif label_text == 'member since':
					user['join_date'] = self.parse_timestr(value)
				elif label_text == 'shipping from':
					user['ship_from'] = value
				elif label_text == 'shipping to':
					user['ship_to'] = value
		# PGP Key
		pgp_key = self.get_text(profile_content.css(".pgp_box"))	# Will be normalized by pipeline
		if 'has not been set yet' not in pgp_key:
			user['public_pgp_key'] 	= pgp_key


		# Score on other markets.
		for score in response.css(".externalFeedback"):
			score_text = self.get_text(score)
			score_title = self.get_text(score.xpath("@title").extract_first())

			if re.search('dreammarket', score_title, re.IGNORECASE | re.S):
				user['dreammarket_rating'] = score_text
			elif re.search('hansa', score_title, re.IGNORECASE | re.S):
				user['hansa_rating'] = score_text
			elif re.search('alphabay', score_title, re.IGNORECASE | re.S):
				user['alphabay_rating'] = score_text
			else:
				self.logger.warning('Unknown other website score. Title is : %s' % (score_title))
		# Number of sales.
		user['successful_transactions'] = self.get_text(profile_content.xpath('.//div[@class = "col-2"]/span[@class = "bigInfo"]/text()').extract_first())

		yield user
	

	def parse_listing(self, response):
		ads = items.Ads()
		ads_img = items.AdsImage()

		listing_content = response.css("#content1")		# Tabs
		feedback_content = response.css("#content2")	# Tabs

		ads['title'] 		= self.get_text_first(response.css('.listing_right span'))
		#ads['offer_id']		= self.get_url_param(response.url, 'lid')
		try:
			offer_id	= self.get_url_param(response.url, 'lid')
			ads['offer_id']		= self.get_url_param(response.url, 'lid')
		except:
			self.logger.warning("Ran into a URL parameter issue at URL: %s. Offer_ID is not recorded." % (response.url))
			ads['offer_id']		= self.get_url_param(response.url, 'lid')
		ads['relativeurl']	= response.meta['relativeurl']
		ads['fullurl']		= self.make_url(ads['relativeurl'])
		user_url			= response.css('.listing_right').xpath('.//a[contains(@href, "page=profile")]/@href').extract_first()
		# Some items don't have an associated vendor.
		try:	
			ads['vendor_username']	= self.get_url_param(user_url, 'user') 
		except:
			self.logger.warning('No seller available at URL: %s. Seller is noted as \'\'. Inspect the URL post-crawl.' % (response.url))
			ads['vendor_username']  = ''
		
		ads['category'] = response.meta['category']

		multilisting_select = listing_content.css('select[name="multilistingChild"]') 	# 2 types of Ads. Multilisting or not.

		if not multilisting_select:
			ads['multilisting'] = False
			listing_right_p = self.get_text(listing_content.css(".listing_right p"))
			m = re.search(r'\((\d+(\.\d+)?)\s*\xe0\xb8\xbf\)',listing_right_p)		# Search for bitcoin icon \xe0\b8\xbf is unicode char for bitcoin encoded in UTF8
			m2 = re.search(r'([0-9.]{1,10}) \xe0\xb8\xbf', listing_right_p) 
			if m:
				ads['price'] = m.group(1)
			# minor error handling in case the previous regex written by Pier-Yver doesn't catch bitcoin prices.
			elif m is None and m2 is not None:
				ads['price']= m2.group(1)
				#self.logger.warning('Encountered an error with the old price-regex. Using RM\'s regex at URL: %s' % (response.url))
		else:
			ads['multilisting'] = True
			options = []
			# Just added @ below which should fix everything.
			for option in multilisting_select.xpath('.//option[@value!=""]'):
				options.append(self.get_text(option))

			ads['price'] = json.dumps(options)

		#Bunches of regex to parse the page.
		listing_right_html = self.get_text(listing_content.css('.listing_right').extract_first())	# Read HTML. We need tags as separator.
		listing_right_span_text = self.get_text(listing_content.css('.listing_right span'))
		m = re.search('<b>shipping from\s*:\s*</b>\s*([^<]+)', listing_right_html, re.IGNORECASE)
		if m:
			ads['ships_from'] = m.group(1)

		m = re.search('<b>shipping to\s*:\s*</b>\s*([^<]+)', listing_right_html, re.IGNORECASE)
		if m:
			ads['ships_to'] = m.group(1)	
		shipping_options = []
		for option in listing_content.css('.listing_right form select[name="shipment"] option[value!=""]::text').extract():
			shipping_options.append(self.get_text(option))
		ads['shipping_options'] = json.dumps(shipping_options)
		ads['description'] = self.get_text(listing_content.xpath('./p'))
		stocks_possibilities = ['Excellent stock', 'Good stock', 'Low stock', 'Very low stock']
		for possibility in stocks_possibilities:
			if possibility in listing_right_span_text:
				ads['stock'] = possibility
				break;

		yield ads

		# Ads Image.
		ads_img['ads_id'] 		= ads['offer_id']
		ads_img['image_urls']	= [self.make_request('image', url=listing_content.css(".listing_image img::attr(src)").extract_first(), referer=response.url)]
		yield ads_img
		

		# Handling listing feedbacks
		for feedback in feedback_content.css(".feedback"):
			try:
				rating = items.ProductRating()
				rating['ads_id'] 		= ads['offer_id']
				rating['comment'] 		= self.get_text(feedback.css('p'))
				#rating['submitted_by'] 	= self.get_text(feedback.css('.feedback_header span a'))
				try:
					username            = feedback.css('.feedback_header span a').xpath("./text()")[0].extract().strip()
				except:
					username            = ''
					self.logger.warning('Found a review with no username. URL: %s' % response.url)
				rating['submitted_on'] 	= self.parse_timestr(self.get_text(feedback.css('.feedback_header').xpath('span/text()').extract_first()))
				rating['submitted_by']  = username
				#star_styles = feedback.css('.feedback_subheader').xpath('./div[1]/@style').extract_first()
				star_styles = feedback.css('.feedback_subheader').xpath('./div/div')[0].extract()
				m = re.search(r'width:(\d+)px', star_styles)
				if m:	
					width =	int(m.group(1))
					rating['rating'] = '%d/5' % (width//24)	# One star is 24 px wide
				else:
					self.logger.warning('Cannot find product rating score.')
				yield rating
			except Exception as e:
				self.logger.warning('Could not get listing feedback at %s. Error %s' % (response.url, e))

		#If there is several pages of feedback. feedback_buffer_middleware will buffer them until we have them all and then sends them further in pipeline
		for url in feedback_content.css('div.pagination a::attr(href)').extract():
			if self.get_url_param(url, 'pg') != '1':
				yield self.make_request('listing', url=url, relativeurl=response.meta['relativeurl'], ads_id=ads['offer_id'], category=response.meta['category'])
		# If statement to avoid requesting vendors pages when there is no vendor associated with an item.
		if ads['vendor_username'] is not '':
			yield self.make_request('userprofile', url=user_url)


	def isloginpage_username(self, response):
		return True if len(response.css(".login_form #username")) else False

	def isloginpage_password(self, response):
		return True if len(response.css(".login_form #password")) else False

	def is_expulsed(self, response):
		return True if 'action=expulsed' in response.url else False

	def craft_login_username_request_from_form(self, response):
		data = {
			'username' : self.login['username'],
		}

		req = FormRequest.from_response(response, formdata=data, formcss='.login_form form')

		captcha_src = response.css("div.captcha_div img::attr(src)").extract_first()
		
		req.meta['captcha'] = {        # CaptchaMiddleware will take care of that.
			'request' : self.make_request('image', url=captcha_src),
			'name' : 'captcha'   
		}

		return req

	def craft_login_password_request_from_form(self, response):
		data = {
			'password' : self.login['password']
		}

		req = FormRequest.from_response(response, formdata=data, formcss='.login_form form')

		return req

	def parse_timestr(self, timestr):
		try:
			timestr = timestr.replace('UTC', '').strip()
			dt = self.to_utc(dateutil.parser.parse(timestr))
			return dt
		except Exception as e:
			self.logger.error("Cannot parse time string '%s'. Error : %s" % (timestr, e))