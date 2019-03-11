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

class DreamMarketSpider(MarketSpider):
	name = "dreammarket"

	custom_settings = {
		'IMAGES_STORE' : './files/img/dreammarket',
		'RANDOMIZE_DOWNLOAD_DELAY' : True,
		'HTTPERROR_ALLOW_ALL' : True,
		'RETRY_ENABLED' : True
	}

	def __init__(self, *args, **kwargs):
		super(DreamMarketSpider, self).__init__( *args, **kwargs)
		
		self.logintrial = 0

		self.set_max_concurrent_request(1)      # Scrapy config
		self.set_download_delay(5)              # Scrapy config
		self.set_max_queue_transfer_chunk(1)    # Custom Queue system
		self.statsinterval = 60;				# Custom Queue system

		self.parse_handlers = {
				'index' 		: self.parse_index,
				'ads_list' 		: self.parse_ads_list,
				'ads' 			: self.parse_ads,
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
		elif reqtype == 'ddos_protection':
			req = self.create_request_from_ddos_protection(kwargs['response'])
			req.meta['req_once_logged'] = kwargs['req_once_logged']
			req.meta['ddos_protection'] = True
			req.dont_filter=True
		elif reqtype in ['ads_list', 'ads', 'user', 'image', 'user_ratings']:
			req = Request(self.make_url(kwargs['url']))
			req.meta['shared'] = True

		if reqtype == 'ads':
			req.meta['product_rating_for'] = kwargs['ads_id']

		if reqtype == 'user_ratings':
			req.meta['user_rating_for'] = kwargs['username']
			req.meta['username'] = kwargs['username']

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

			elif self.is_ddos_protection_form(response):
				self.logger.warning('Encountered a DDOS protection page')
				if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
					req_once_logged = response.meta['req_once_logged'] if  'req_once_logged' in response.meta else None
					self.logintrial = 0
					self.wait_for_input("Can't bypass DDOS Protection",req_once_logged)
					return
				self.logger.info("Trying to overcome DDOS protection")
				self.logintrial += 1

				req_once_logged = response.request
				if ('req_once_logged' in response.meta):
					req_once_logged = response.meta['req_once_logged']

				yield self.make_request('ddos_protection', req_once_logged=req_once_logged, response=response, priority=10)
			elif self.is_ddos_good_answer(response):
				self.logintrial = 0
				self.logger.info("Bypassed DDOS protection successfully!")
				yield response.meta['req_once_logged']

			elif self.is_logged_elsewhere(response) or self.is_session_expired(response):
				self.logger.warning('Need to relog')
				yield self.make_request('index', priority=10, donotparse=True)

				response.request.dont_filter = True
				yield response.request
			elif self.unknown_error(response):
				self.logger.warning('Encountered an error which Dream Market does not describe.')
			else:
				self.logger.warning('Something went wrong. See the exception and investigate %s. Dumping html: %s' % (response.url, response.body))
				raise Exception("Not implemented yet, figure what to do here !")
		else : 
			self.logintrial = 0

			# We restore the missed request when protection kicked in
			if response.meta['reqtype'] == 'dologin':
				self.logger.warning("Login Success! Going to %s" % response.meta['req_once_logged'])
				if response.meta['req_once_logged'] is None:
					self.logger.warning("We are trying to yield a None. This should not happen.")
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
			depth0_categories = response.css('.main .sidebar .category a::attr(href)').extract()
			for link in depth0_categories:
				yield self.make_request('ads_list', url=link)


	def parse_ads_list(self, response):
		ads_url = response.css(".main .content .shopItem .oTitle>a::attr(href)").extract()
		for url in ads_url:
			yield self.make_request('ads', url=url, ads_id = self.get_url_param(url, 'offer'))

		page_urls = response.css(".main .content .pageNavContainer ul.pageNav li a.pager::attr(href)").extract()
		for url in page_urls: 
			yield self.make_request('ads_list', url=url)	# Here, we rely on duplicate filter because we will generate a lot!

	def parse_ads(self, response):
		
		##  =============   ADS   ======================
		listing_not_found = self.get_text(response.xpath('.//div[@class="content"]/div/div[1]/text()').extract_first())
		if listing_not_found != 'Listing not found':
			ads_item = items.Ads()
			ads_item['title'] = self.get_text(response.css('.viewProduct .title'))
			details = response.css('div.tabularDetails>div')
			for div in details:
				label = div.css('label:first-child')
				label_txt = self.get_text(label).lower()
				span = div.xpath('./span')

				if label_txt == 'vendor':
					link = span.css('a:first-child')
					ads_item['vendor_username'] = self.get_text(link)
					url = link.css('::attr(href)').extract_first().strip()
					yield self.make_request('user', url = url, priority=5)
					
				elif label_txt == 'price':
					# ads_item['price'] = self.get_text(span) malfunctions and returns prices 
					# in different currencies. The issue is that when accidentally clicking 
					# selectCurrency we return currencies to the database that should not be there. 
					# Price is denoted in one of these formats using currency symbols.
					# BTC1 (USD5000)
					# BTC1
					# BTC1 (POUND/EURO6000)
					price 		 = self.get_text(span)
					btc_price    = re.search(r'\xe0\xb8\xbf([0-9.]{1,10})', price)
					dollar_price = re.search('\$([0-9.]{1,10})', price)
					# If the price is available in BTC, use that as the price.
					if btc_price is not None:
						price = btc_price.group(1)
						#self.logger.warning('BTC price: %s. Pier-Yver\'s price was: %s' % (price, self.get_text(span)))
					# If it's not, convert USD to BTC.
					elif btc_price is None and dollar_price is not None:
						self.logger.warning('Using dollar price %s' % (price))
						price = dollar_price.group(1)
						# Try to find the exchange rate.
						exchange_rates = response.xpath('.//*[@class = "exchangeRateListing"]').extract()[0]
						try:
							dollar_rate    = re.search('USD.*?([0-9\\.]{1,10})', exchange_rates, re.DOTALL).group(1)
						except:
							self.logger.warning("Couldn't get the dollar exchange rate. Dumping the XML: %s" % exchange_rates)
						# Then try to convert.
						try:
							dollar_rate      = float(dollar_rate)
							price = float(price) / dollar_rate
							self.logger.warning('Found a product in dollar at (%s). Converted to BTC. Math was: $ %s / exchange rate %s = %s' % (response.url, dollar_price.group(1), dollar_rate, price))
						except:
							self.logger.warning("Failed to convert. Dumping values dollar rate %s, price %s and raw price %s. Using Pier-Yver's price." % (dollar_rate, price, price_raw))
							price = self.get_text(span)						
					# Worst case scenario, use a price that works somewhat - Pier-Yver's old price.
					else:
						self.logger.warning("Couldn't determine currency. Inserted: %s" % self.get_text(span))
						price = self.get_text(span)
					# Add it to the database export pipeline.
					ads_item['price'] = price
				elif label_txt == 'ships to':
					ads_item['ships_to'] = self.get_text(span)
				elif label_txt == 'ships from':
					ads_item['ships_from'] = self.get_text(span)
				elif label_txt == 'escrow':
					ads_item['escrow'] = self.get_text(span)
				else:
					self.logger.warning('Found an ads detail (%s) that is unknown to this spider on URL: %s. Consider hadnling it.' % (label_txt, response.url))
				# Get accepted currencies.
				accepted_currencies = list()
				if response.xpath(".//label[@for='bitcoinCurrencyOption']") is not None:
					accepted_currencies.append("btc")
				if response.xpath(".//label[@for='bitcoinCashCurrencyOption']") is not None:
					accepted_currencies.append("bch")
				if response.xpath(".//label[@for='moneroCurrencyOption']") is not None:
					accepted_currencies.append("xmr")
				ads_item['accepted_currencies'] = ".".join(accepted_currencies)

					
			ads_item['description'] = self.get_text(response.css("#offerDescription"))
			ads_item['offer_id'] = self.get_url_param(response.url, 'offer')
			
			try:
				ads_item['category'] = self.get_active_category(response)
			except Exception, e:
				self.logger.warning('Cannot determine ads category : %s' % e)

			# Check if there is a shipping options field.
			# if so, it should be the first div with class newFeature.
			# If it's called cryptocurrency, then there's no shipping information.
			shipping_info_available = response.xpath(".//div[@class = 'newFeature'][1]/text()").extract_first() != "Cryptocurrency"
			if shipping_info_available == True:
				try:
					ads_item['shipping_options'] = json.dumps(self.get_shipping_options(response))
				except Exception, e:
					self.logger.warning('Cannot determine shipping options : %s' % e)

			ads_item['fullurl'] = response.url
			parsed_url = urlparse(response.url)
			ads_item['relativeurl'] = "%s?%s" % (parsed_url.path, (parsed_url.query))

			yield ads_item
		elif listing_not_found == 'Listing not found':
			self.logger.warning('Listing not found at %s' % response.url)
		else: 
			self.logger.warning('Unknown listing status %s' % response.url)

		## ===================== IMAGES =====================
		images_url = response.css('img.productImage::attr(src)').extract();
		for url in images_url:
			img_item = items.AdsImage(image_urls = [])
			img_item['image_urls'].append(self.make_request('image', url=url))
			img_item['ads_id'] = ads_item['offer_id']
			yield img_item

		## ===================== Product Ratings (feedback) =========
		rating_lines = response.css('.ratings table tr')
		for tr in rating_lines:
			try:
				rating_item = items.ProductRating()

				age = self.get_text(tr.css('td.age'))
				m = re.search('(\d+)d', age)
				if m:
					days_offset = m.group(1)
					# A sanity check. Dream has some dates which are in 1969 and 1970..
					submitted_on = (datetime.utcnow() - timedelta(days=int(days_offset))).date()
					if submitted_on < date(2011, 1, 1):
						submitted_on = ''
						self.logger.warning("Encountered a date outside the acceptable range. See URL: %s" % response.url)
					else:
						rating_item['submitted_on'] = submitted_on
				elif re.search('\d\d:\d\d', age):
					rating_item['submitted_on'] = datetime.utcnow().date()
				stars = len(tr.css('td.rating img.star[src="img/star_gold.png"]'))
				rating_item['rating'] 	= "%d/5" % stars
				rating_item['comment'] 	= self.get_text(tr.css('td.ratingText'))
				rating_item['ads_id'] 	= ads_item['offer_id']
				yield rating_item

			except Exception, e:
				self.logger.warning("Could not get product rating. %s" % e)

	
	def parse_user(self, response):
		
		user_item = items.User()
		details = response.css('div.tabularDetails>div')
		verified_list = []

		user_item['username'] = dict(parse_qsl(urlparse(response.url).query))['member']	# Read get parmater "member" from url

		for div in details:
			label = div.css('label:first-child')
			label_txt = self.get_text(label).lower()
			content = div.css('div>:not(label)')

			if label_txt == 'username':
				ratings = self.parse_ratings(content)
				for key in ratings:
					user_item[key] = ratings[key]
			else:
				content = div.css('div>:not(label)')
				if label_txt == 'trusted seller':
					user_item['trusted_seller'] = self.get_text(content)
				elif label_txt == 'verified':
					verified_list.append(self.get_text(content))
				elif label_txt == 'fe enabled':
					user_item['fe_enabled'] 	= self.get_text(content)
				elif label_txt == 'join date':
					user_item['join_date'] 		= self.get_text(content)
				elif label_txt == 'last active':
					user_item['last_active'] 	= self.get_text(content)
				else:
					#self.logger.warning('Found a user detail (%s) that is unknown to this spider. Consider handling it.' % label_txt)
					self.logger.warning('Found a user detail (%s) that is unknown to this spider. Consider handling it. It should be on URL: %s' % (label_txt, response.url))
			user_item['verified'] = json.dumps(verified_list)

			for div in response.css('div.messagingTab>div'):
				try:
					title = self.get_text(div.css('div>div:first-child'))
					content = self.get_text(div.css('div>div:nth-child(2)'))

					lower_title = title.lower()
					if lower_title == 'public pgp key':
						user_item['public_pgp_key'] = content
					elif lower_title == 'terms and conditions':
						user_item['terms_and_conditions'] = content
				except Exception, e:
					self.logger.warning('Error while reading messaging tab. Error : %s' % e)


		user_item['fullurl'] = response.url
		parsed_url = urlparse(response.url)
		user_item['relativeurl'] = "%s?%s" % (parsed_url.path, (parsed_url.query))

		yield user_item

		for user_tabs in response.css("a.pTabLabel"):
			if self.get_text(user_tabs) == "Ratings":
				ratings_url = user_tabs.css("::attr(href)").extract_first()
				if ratings_url.startswith("?"):
					ratings_url = "contactMember" + ratings_url
				yield self.make_request("user_ratings", url=ratings_url, username=user_item['username'])

		for url in response.css("div.shop div.oTitle a::attr(href)").extract():
			yield self.make_request('ads', url=url, ads_id=self.get_url_param(url, 'offer')) 	# We rely on dupe filter te remove duplicate.

	def parse_user_ratings(self, response):
		for rating_row in response.css("table.ratingTable tr"):
			rating_cells = rating_row.css("td")
			if len(rating_cells) == 5:
				rating = items.UserRating()
				rating['username'] = response.meta['username']
				rating['submitted_on'] = self.parse_days_ago(self.get_text(rating_cells[0]))
				rating['rating'] = len(rating_cells[1].css('img[alt="gold"]'))
				rating['comment'] = self.get_text(rating_cells[2])
				rating['submitted_by'] = self.get_text(rating_cells[3])
				rating['price'] = self.get_text(rating_cells[4])

				yield rating
			
	def parse_days_ago(self, daysstr):
		try:
			match = re.search('(\d+)d.*', daysstr)
			if match:
				days_ago = timedelta(days = int(match.group(1)))
				dt = datetime.utcnow() - days_ago
				dt = dt.replace(hour=12, minute=0, second=0, microsecond=0)
				return dt
		except Exception as e:
			self.logger.error("Cannot parse days ago string '%s'. Error : %s" % (daystr, e))
			return datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)

	def loggedin(self, response):
		profile_links = response.css('.main .headNavitems ul li a[href="./profile"]')
		if profile_links and len(profile_links) > 0:
			return True

		return False
		

	def isloginpage(self, response):
		title = response.css('head title::text').extract_first()
		if title:
			if 'login' in title.lower():
				return True
		
		return False

	def is_ddos_protection_form(self, response):
		ddos_form = response.css('form div.ddos')
		if len(ddos_form) > 0:
			submit_btn = response.css('form input[type="submit"]')
			if len(submit_btn) > 0:
				return True

		return False

	def is_ddos_good_answer(self, response):
		ddos_form = response.css('form div.ddos')
		if len(ddos_form) > 0:
			body_text = self.get_text(response.css('form'))
			if 'Correct answer, thank you' in body_text:
				return True

		return False

	def is_logged_elsewhere(self, response):
		return True if 'You have been logged in elsewhere' in response.body else False

	def is_session_expired(self, response):
		return True if 'Your session has expired' in response.body else False

	def unknown_error(self, response):
		return True if self.get_text(response.xpath('.//title/text()').extract_first()) == 'An Error has occured' else False

	def create_request_from_ddos_protection(self, response):
		challenge = ''.join(response.css('.iline').xpath('./label[contains(text(), "Challenge")]/../text()').extract()).strip()
		captcha_src = response.css('label[for="captcha"] img::attr(src)').extract_first().strip()
		
		code = parser.expr(challenge).compile()	# Code injection safe eval.
	 	result = eval(code)
		self.logger.info('Answering DDOS protection challenge "%s" with answer %s' % (challenge, result))

		req = FormRequest.from_response(response, formdata={'result' : str(result)})
		req.meta['captcha'] = {		# CaptchaMiddleware will take care of that.
			'request' : self.make_request('captcha_img', url=captcha_src),
			'name' : 'captcha',
			'preprocess' : 'DreamMarketRectangleCropper'	# Preprocess image to extract what's within the rectangle
			}
		return req

	def create_request_from_login_page(self, response):
		username_txtbox_list = response.css('.formInputs').xpath('.//label[contains(text(), "Username")]/..').css('input[value=""], input[value="%s"]' % self.login['username'])
		password_txtbox_list = response.css('.formInputs').xpath('.//label[contains(text(), "Password")]/..').css('input[value=""]')
		captcha_txt_id = response.css('.formInputs').xpath('.//label[contains(text(), "Captcha code")]').css('::attr(for)').extract_first()

		#The website try to mislead us by adding a bunch of random hidden textbox next to username and password.
		# We aprse css with regex to find which one are hidden.
		
		# Username
		style = ''.join(response.css('style').extract())

		username_txtbox_list2 = []
		for txtbox in username_txtbox_list:
			nodeid = txtbox.xpath("@id").extract_first()
			regex = '#%s\s*\{[^\}]*display\s*:\s*none\s*;[^\}]*\}' % nodeid
			m = re.search(regex, style)
			if not m:
				username_txtbox_list2.append(txtbox)

		#Password
		password_txtbox_list2 = []
		for txtbox in password_txtbox_list:
			nodeid = txtbox.xpath("@id").extract_first()
			regex = '#%s\s*\{[^\}]*display\s*:\s*none\s*;[^\}]*\}' % nodeid
			m = re.search(regex, style)
			if not m:
				password_txtbox_list2.append(txtbox)

		#Success validation
		if len(username_txtbox_list2) != 1:
			raise Exception("Cannot find the right username textbox. There is %d candidates" % len(username_txtbox_list))

		username_txt_id = username_txtbox_list2[0].xpath("@id").extract_first()
		
		if len(password_txtbox_list2) != 1:
			raise Exception("Cannot find the right username textbox. There is %d candidates" % len(username_txtbox_list))
		password_txt_id = password_txtbox_list2[0].xpath("@id").extract_first()

		if not captcha_txt_id:
			raise Exception("Cannot find captcha text box in login page")

		# We have the ID of the textbox, let's find their form name
		username_formname = response.css('#%s::attr(name)' % username_txt_id).extract_first()
		password_formname = response.css('#%s::attr(name)' % password_txt_id).extract_first()
		captcha_formname = response.css('#%s::attr(name)' % captcha_txt_id).extract_first()

		if not username_formname:
			raise Exception("Cannot find username text box name in login page")
		
		if not password_formname:
			raise Exception("Cannot find password text box name in login page")
		
		if not captcha_formname:
			raise Exception("Cannot find captcha text boxname  in login page")

		captcha_src = response.css('.captcha img::attr(src)').extract_first()	# The captcha url

		data  = {}
		data[username_formname] =  self.login['username']
		data[password_formname] =  self.login['password']
		captcha_src = response.css('.captcha img::attr(src)').extract_first()
		if not captcha_src:
			raise Exception('Cannot find Captcha src')

		req = FormRequest.from_response(response, formdata=data)
		req.meta['captcha'] = {		# CaptchaMiddleware will take care of that.
			'request' : self.make_request('captcha_img', url=captcha_src),
			'name' : captcha_formname,
			'preprocess' : 'DreamMarketRectangleCropper'	# Preprocess image to extract what's within the rectangle
			}

		return req

	def get_active_category(self, response):
		categories = response.css('.sidebar.browse>div.category')
		category_list = []

		actual_depth = 0
		last_depth = -1
		last_name = ''
		for div in categories:
			name = ''.join(div.xpath('./a/text()').extract()).strip()
			
			nodeclass = div.xpath('@class').extract_first();
			m = re.search('depth(\d+)', nodeclass)
			if m :
				actual_depth = int(m.groups(1)[0])
			else:
				raise RuntimeError("Depth not specified in category menu")

			if actual_depth > last_depth and last_name:
				category_list.append(last_name)

			if actual_depth < last_depth and last_name:
				category_list = category_list[:-1]

			if len(div.css('.selected')) > 0:
				category_list.append(name)
				break

			last_depth = actual_depth
			last_name = name

		return '/'.join(category_list)

	def get_shipping_options(self, response):
		options_list = []
		options = response.xpath('.//table[@class="shippingTable hoverable"][1]/tbody/tr')
		for option in options:
			option_dict = {
				'price' : option.xpath('td[@class = "coinsNoWrap"]/label/text()').extract_first(),
				'name' : option.xpath('td[@class = "text"]/label/text()').extract_first()
				}
			options_list.append(option_dict)
		return options_list

	def parse_ratings(self, content):
		ratings = {}

		s = self.get_text(content.css('.userRating'))
		if s:
			ratings['average_rating'] = s

		s = self.get_text(content.css('.alphabayLinkedUserRating'))
		if s:
			ratings['alphabay_rating'] = s

		s = self.get_text(content.css('.nucleusLinkedUserRating'))
		if s:
			ratings['nucleus_rating'] = s
			
		s = self.get_text(content.css('.abraxasLinkedUserRating'))
		if s:
			ratings['abraxas_rating'] = s		
				
		s = self.get_text(content.css('.agoraLinkedUserRating'))
		if s:
			ratings['agora_rating'] = s		
				
		s = self.get_text(content.css('.hansaLinkedUserRating'))
		if s:
			ratings['hansa_rating'] = s	
				
		s = self.get_text(content.css('.middleEarthLinkedUserRating'))
		if s:
			ratings['midlle_earth_rating'] = s

		return ratings
