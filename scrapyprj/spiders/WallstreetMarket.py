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
from dateutil.relativedelta import relativedelta


class WallstreetMarket(MarketSpider):
	name = "wallstreet_market"

	custom_settings = {
		'IMAGES_STORE' : './files/img/wallstreet_market',
		'RANDOMIZE_DOWNLOAD_DELAY' : True,
		'RESCHEDULE_RULES' : {},
		'MAX_LOGIN_RETRY' : 15
	}


	def __init__(self, *args, **kwargs):
		super(WallstreetMarket, self).__init__( *args, **kwargs)
		
		self.logintrial = 0

		self.set_max_concurrent_request(4)      # Scrapy config
		self.set_download_delay(0)              # Scrapy config
		self.set_max_queue_transfer_chunk(5)    # Custom Queue system
		self.statsinterval = 60					# Custom Queue system

		self.parse_handlers = {
				'index' 		: self.parse_index,			# Home page
				'category'		: self.parse_category,		# Category content
				'category-page' : self.parse_category,		# Category content. Page != 1
				'offer'			: self.parse_offer,			# Listing page
				'offer-refund'	: self.parse_offer,			# Listing refund policy
				'userprofile'	: self.parse_userprofile	# User profile page
			}

		self.yielded_category_page = {};

	def start_requests(self):
		yield self.make_request('index')

	def make_request(self, reqtype,  **kwargs):

		passthru = ['category']

		if 'url' in kwargs:
			kwargs['url'] = self.make_url(kwargs['url'])

		if reqtype == 'index':
			req = Request(self.make_url('index'))
			req.dont_filter=True
		elif reqtype == 'loginpage':
			req = Request(self.make_url('loginpage'))
			req.dont_filter=True
		elif reqtype == 'dologin':
			req = self.craft_login_request_from_form(kwargs['response'])
			req.dont_filter=True
		elif reqtype == 'captcha':
			req = Request(self.make_url(kwargs['url']))
			req.dont_filter=True
		elif reqtype == 'image':
			req = Request(self.make_url(kwargs['url']))
		elif reqtype=='ddos_protection':
			req = self.create_request_from_ddos_protection(kwargs['response'])
			req.dont_filter=True
		elif reqtype=='security_check':
			req = self.create_request_from_security_check(kwargs['response'])
			req.dont_filter=True
		elif reqtype == 'category':
			req = FormRequest.from_response(kwargs['response'], formcss=kwargs['formcss'], clickdata=kwargs['clickdata'])

		elif reqtype=='category-page':	# Changing page is done with a POST form.
			btn = kwargs['btn']
			name = btn.xpath('@name').extract_first()	# "page"
			val = btn.xpath('@value').extract_first()	# page number
			data = {name : val, 'dofilter' : '0'} 		# Careful, if dofilter is set to 1 (default value), page will be empty
			req = FormRequest.from_response(kwargs['response'], formdata=data, formxpath='//*[contains(@class, "pagination")]/ancestor::form')

			if req.url in self.yielded_category_page:
				if val in self.yielded_category_page[req.url]:
					return None
				else:
					self.yielded_category_page[req.url].append(val)
			else:
				self.yielded_category_page[req.url] = []

		elif reqtype in ['category', 'userprofile', 'offer', 'offer-refund']:
			req = Request(self.make_url(kwargs['url']))
			req.meta['shared'] = True
		else:
			raise Exception('Unsuported request type %s ' % reqtype)

		req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
		req.meta['proxy'] = self.proxy  #meta[proxy] is handled by scrapy.

		if 'priority' in kwargs:
			req.priority = kwargs['priority']

		if reqtype == 'offer':
			offer_id = self.get_offer_id_from_url(req.url)
			req.meta['product_rating_for'] = offer_id

		for k in passthru:
			if k in kwargs:
				req.meta[k] = kwargs[k]

		if 'req_once_logged' in kwargs:
			req.meta['req_once_logged'] = kwargs['req_once_logged']

		return req


	def parse(self, response):
		if not self.loggedin(response):	

			if response.meta['reqtype'] == 'ddos_protection' and not self.is_ddos_challenge(response):
				self.logintrial=0

			if self.isloginpage(response):
				req_once_logged = None if not 'req_once_logged' in response.meta else response.meta['req_once_logged']

				self.logintrial +=1
				self.logger.info("Trying to login")
				if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
					self.wait_for_input("Too many failed login trials. Giving up.", response.meta['req_once_logged'])
					self.logintrial=0
					return 

				yield self.make_request(reqtype='dologin', req_once_logged=req_once_logged, response=response)
			elif self.is_security_check(response):
				self.logger.warning('Encountered a Security Check (ddos protection) page.')
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

				yield self.make_request('security_check', req_once_logged=req_once_logged, response=response, priority=10)
			elif self.is_ddos_challenge(response):
				self.logger.warning('Encountered a DDOS protection page while not logged in.')
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
			else:
				self.logger.info("Not logged, going to login page.")
				yield self.make_request(reqtype='loginpage', req_once_logged=response.request, priority=10)
		# Below is an attempt at bypassing DDoS protection encountered while logged in.
		elif self.loggedin(response) == True and self.is_ddos_challenge(response) == True:
			self.logger.warning('Encountered DDOS protection while logged in.')

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

		else: 
			self.logintrial = 0

			# We restore the missed request when protection kicked in
			if response.meta['reqtype'] in ['dologin', 'ddos_protection']:
				if response.meta['reqtype'] == 'dologin':
					self.logger.info("Login Success!")
				elif response.meta['reqtype'] == 'ddos_protection':
					self.logger.info("Bypassed DDOS protection!")

				if response.meta['req_once_logged']:
					yield response.meta['req_once_logged']
			
			# Normal parsing
			else:
				it = self.parse_handlers[response.meta['reqtype']].__call__(response)
				if it:
					for x in it:
						if x:
							yield x

	def parse_index(self, response):
		formcss = '#mCont > form'
		for button in response.css(formcss + ' ol.tree button'):
			clickdata = {}
			clickdata['name'] 	= self.get_text(button.xpath('@name').extract_first())
			clickdata['value'] 	= self.get_text(button.xpath('@value').extract_first())
			yield self.make_request(reqtype='category', response=response, formcss=formcss, clickdata=clickdata)

	def parse_category(self, response):
		for url in response.xpath('.//a[contains(@href, "offer/")]/@href').extract():
			yield self.make_request(reqtype='offer', url=url)

		for url in response.xpath('.//a[contains(@href, "profile/")]/@href').extract():
			yield self.make_request(reqtype='userprofile', url=url)
	
 		#All buttons that are not disabled and are not page 1
		for btn in response.css('.pagination').xpath('.//li[contains(@class, "page-item") and not(contains(@class, "disabled"))]').xpath('.//button[@value!="1"]'):
			yield self.make_request('category-page', btn=btn, response=response)

	def parse_offer(self, response):
		ads = items.Ads()
		ads['offer_id']	= self.get_offer_id_from_url(response.url)
		
		layout= 'unknown'
		info_block = response.xpath('//h1[text()="Info"]/..')			# Two known layout. Try first, fallback on second
		
		if len(info_block) == 1:
			layout = 'with_headings'
		else:
			layout = 'without_headings'

		if layout == 'without_headings':
			info_block = response.xpath('//h1[contains(@class, "fheading")]/..')

		ads['title']			= self.get_text(response.css('h1.fheading'))
		ads['vendor_username']	= self.get_text(info_block.xpath('.//a[contains(@href, "profile")]'))
		if 'category' in response.meta and response.meta['category'] is not None:
			ads['category']			= response.meta['category'];
		else:
			ads['category']	 = None
		
		
		ads['fullurl']		= response.url.replace('/refund', '');
		ads['relativeurl']	= "/offer/%s" % ads['offer_id'];

		# =====  Info block 1 - Ships from/to, escrot, multisig, etc ==========
		# We determine the type of info by the icon in front of it. Most reliable way to do it as layout changes freely between listings

		if layout == 'with_headings':
			p = info_block.xpath('./p[1]')
		elif layout == 'without_headings':
			p = info_block.xpath('./p[1]')

		for line in p.extract_first().split('<br>'):
			linesel = scrapy.Selector(text=line)
			line_txt = self.get_text(linesel)

			if len(linesel.css(".ion-log-out")) > 0:	# Ships From icon
				m = re.search('ships from:(.+)', line_txt, re.IGNORECASE)
				if m : 
					ads['ships_from']	= self.get_text(m.group(1));
			elif len(linesel.css(".ion-log-in")) > 0:	# Ships To icon
				m = re.search('only ships to certain countries\s*\(([^\)]+)\)', line_txt, re.IGNORECASE)
				if m:
					ads['ships_to']	= json.dumps([self.get_text(x.upper()) for x in m.group(1).split(',')]);
				elif 'Worldwide' in line_txt:
					ads['ships_to'] = 'Worldwide'
					m = re.search('with Exceptions\s*\(([^\)]+)\)', line_txt, re.IGNORECASE)
					if m : 
						ads['ships_to_except']	= json.dumps([self.get_text(x.upper()) for x in m.group(1).split(',')]);
				else:
					self.logger.warning("New format of 'ships_to' string  (%s) at %s" % (line_txt, response.url))
			elif len(linesel.css(".ion-android-share-alt")) > 0:	# Properties icons
				if line_txt:
					line_txt = line_txt.lower()
					ads['multisig'] = True if 'multisig' in line_txt else False
					ads['escrow'] = True if 'escrow' in line_txt else False
			elif len(linesel.css(".ion-android-checkmark-circle")) > 0:	# Auto Accept icon
				if line_txt:
					line_txt = line_txt.lower()
					ads['auto_accept'] = True if 'auto-accept' in line_txt else False
			elif len(linesel.css(".ion-ios-monitor-outline")) > 0:	# Digital Good icon
				pass
			else:
				icontype = linesel.css('.ionicons')
				if icontype:
					iconclass = icontype[0].xpath('@class').extract_first()
					self.logger.warning('Unhandled information available with icon of type (%s) in offer page at %s' % (iconclass, response.url))
		# =========================================

		## ============= Prices Options =======
		price_opt_table = response.xpath(".//h4[contains(text(), 'Prices')]/../table")
		options = []
		for line in price_opt_table.css('tbody tr'):
			option = {}
			option['amount'] 	= self.get_text(line.css('td:nth-child(1)'))
			option['price_btc'] = self.get_text(line.css('td:nth-child(3)'))
			options.append(option)
		
		if len(options) > 0:
			ads['price_options']	= json.dumps(options);
			if len(options) == 1:
				m = re.search('(\d+(\.\d+)?) BTC.+', options[0]['price_btc'])
				if m:
					ads['price']	= m.group(1);
				
		## ==============

		## ============ Shipping Options ========
		shipping_opt_table = response.xpath(".//h4[contains(text(), 'Shipping Options')]/../table")
		options = []
		for line in shipping_opt_table.css('tbody tr'):
			option = {}
			option['name'] 		= self.get_text(line.css('td:nth-child(1)'))
			amount_raw 			= line.css('td:nth-child(2)').extract_first()
			amount_raw 			= amount_raw.replace('<i class="ionicons ion-ios-infinite"></i>', 'inf')	# Infinity
			option['amount'] 	= self.get_text(scrapy.Selector(text=amount_raw))
			option['price_btc'] = self.get_text(line.css('td:nth-child(4)')).replace(' BTC', '')
			options.append(option)

		if len(options) > 0:
			ads['shipping_options']	= json.dumps(options);
		## =====================


		# ===================   Info block 2. List of key/value with key in bold.
		if layout == 'with_headings':
			p = response.xpath('.//h4[contains(text(), "Information")]/..').extract_first()
			if p is None: # BUG P IS NONE
				self.logger.warning("Invalid layout, could not find h4 element with text 'Information' on url " + response.url)
				p = ""
			p = re.sub('<h4>[^<]+</h4>','', p)
		elif layout == 'without_headings':
			p = info_block.xpath('./p[2]').extract_first()

		for line in p.split('<br>'):
			line_txt = self.get_text(scrapy.Selector(text=line))
			known = False
			m = re.search('minimum amount per order:?\s*(.+)', line_txt, re.IGNORECASE)
			if m:
				ads['minimum_order'] = m.group(1)
				known = True
			
			m = re.search('maximum amount per order:?\s*(.+)', line_txt, re.IGNORECASE)
			if m:
				ads['maximum_order'] = m.group(1)
				known = True

			m = re.search('views:?\s*(.+)', line_txt, re.IGNORECASE)
			if m:
				ads['views'] = m.group(1)
				known = True

			m = re.search('Quantity in stock:?\s*(.+)', line_txt, re.IGNORECASE)
			if m:
				ads['stock'] = m.group(1)
				known = True
			
			m = re.search('Already sold:?\s*(.+)', line_txt, re.IGNORECASE)
			if m:
				ads['already_sold'] = m.group(1)
				known = True

			m = re.search('Country:?\s*(.+)', line_txt, re.IGNORECASE)
			if m:
				ads['country'] = m.group(1)
				known = True
			
			m = re.search('Replace-Time:?\s*(.+)', line_txt, re.IGNORECASE)
			if m:
				ads['replace_time'] = m.group(1)
				known = True

			m = re.search('Category', line_txt, re.IGNORECASE)
			if m:
				known = True
				if ads['category'] is None:
					splitted_html = re.sub('\s*<i[^\>]+>\s*</i>\s*', '/', line)
					line_txt2 = self.get_text(scrapy.Selector(text=splitted_html))

					m = re.search('Category:\s*(.+)\s*', line_txt2, re.IGNORECASE)
					if m:
						ads['category'] = m.group(1)
						known = True

			if not known:
				self.logger.warning('Unknown information type (%s) in ads at %s' % (line_txt, response.url))
		if response.url.endswith('refund'):
			ads['terms_and_conditions']		= self.get_text(response.css("#tabcontent"))
		else:
			#ads['description']				= self.get_text(response.css("#tabcontent"));
			ads['description']				= self.get_text(response.css("#tabcontent"))
			yield self.make_request('offer-refund', url=response.url + '/refund', category=ads['category'])
		yield ads
		#=================================================


		#if response.url.endswith('refund'):
		#	ads['terms_and_conditions']		= self.get_text(response.css("#tabcontent"))
		#else:
		#	#ads['description']				= self.get_text(response.css("#tabcontent"));
		#	ads['description']				= self.get_text(response.css("#tabcontent"))
		#	yield self.make_request('offer-refund', url=response.url + '/refund', category=ads['category'])


		## ===================== IMAGES =====================
		images_url = response.css('img.img-thumbnail::attr(src)').extract();
		for url in images_url:
			if url:
				img_item = items.AdsImage(image_urls = [])
				img_item['image_urls'].append(self.make_request('image', url=url))	# Need Scrapy > 1.4.0 for this to work (base64 url encoded data).
				img_item['ads_id'] = ads['offer_id']
				yield img_item
		## ============================

		## ========== Feedbacks =====

		feedback_table= response.xpath('.//h3[contains(text(), "Feedback")]/../table')

		for line in feedback_table.css('tbody tr'):
			try:
				rating = items.ProductRating()
				score = self.get_text(line.css('td:nth-child(1) .text-muted'))
				m = re.search('\((\d+(.\d+)?)\)', score)
				if not m:
					self.logger.warning('Cannot read feedback score %s' % score)
					continue
				
				rating['rating'] 		= "%s/5" % m.group(1)
				#rating['comment'] 		= self.get_text(line.css('td:nth-child(2)'))
				comment = line.xpath('./td[2]/text()')[0].extract().strip()
				if comment is None:
					self.logger.warning("Couldn't find the review. Inserting an empty string at URL: %s" % url)
				else:
					rating['comment']   = comment
				rating['ads_id']		= ads['offer_id']
				rating['submitted_by']	= self.get_text(line.css('td:nth-child(3)'))
				rating['submitted_on']	= self.parse_timestr(self.get_text(line.css('td:nth-child(4)')))
				yield rating
			except Exception as e:
				self.logger.warning("Could not get product feedback. Error : %s" % e)
	

		## ====================

	# User profile. We do not read user feedbacks as requirement asked for ads feedback OR user feedback. 
	# We have ads feedback
	def parse_userprofile(self, response):
		user = items.User()

		user['username'] 		= self.get_text(''.join(response.xpath('.//h2/text()').extract()))
		user['trusted_seller'] 	= True if 'trusted vendor' in self.get_text(response.css('h2')).lower() else False
		user['relativeurl'] 	= '/profile/%s' % user['username']
		user['fullurl'] 		= self.make_url(user['relativeurl'])

		## =========== Main property table ========
		for line in response.xpath('.//h2/../table[1]//tr'):
			key_txt = self.get_text(line.xpath('.//td[1]/text()').extract_first()).lower()
			val_cell = line.xpath('.//td[2]')
			if val_cell:
				val_cell = val_cell[0]

			if key_txt in ['buyer-statistics', 'vendor-statistics']:	# Empty lines
				pass
			elif key_txt == 'last online':
				user['last_active'] = self.parse_timestr(self.get_text(val_cell))
			elif key_txt == 'member since':
				user['join_date'] = self.parse_timestr(self.get_text(val_cell))
			elif key_txt == 'completed orders':
				m = re.search('(\d+)/(\d+)', self.get_text(val_cell))
				if m:
					user['successful_transactions_as_buyer'] = m.group(2)
			elif key_txt == 'disputes involved as buyer':	# Not relevant
				pass
			elif key_txt == 'rated orders':		# Not relevant
				pass
			elif key_txt == 'average rating':
				m = re.search('\((\d+(.\d+)?)\)', self.get_text(val_cell))
				if m:
					user['average_rating'] = '%s/5' % m.group(1)	# Score is on 5 stars
			elif key_txt == 'vendor-level':
				exp = self.get_text(val_cell.css('span.badge-primary'))
				user['exp'] 		= exp.lower().replace('exp', '').strip()

				level = self.get_text(val_cell.css('span.badge-success'))
				m = re.search('level (\d+)', level, re.IGNORECASE)
				if m:
					user['level'] 	= m.group(1)
			elif key_txt == 'vendor since' :	# We have "member since"
				pass
			elif 'rating of the last' in key_txt:	# Not relevant
				pass
			elif 'open/completed orders':
				m = re.search('(\d+)/(\d+)', self.get_text(val_cell))
				if m:
					user['successful_transactions'] = m.group(2)
			else:
				self.logger.warning('New property on user profile page : %s  at %s' % (key_txt, response.url))
		
		# ================================

		# ===== Main tab =============
		if response.url.endswith('info'):
			#user['profile'] = response.xpath('.//div[@id = "tabcontent"]').extract()
			user['profile'] = self.get_text(response.css("#tabcontent"))
		elif response.url.endswith('pgp'):
			user['public_pgp_key'] = self.get_text(response.css("#tabcontent"))
		elif response.url.endswith('offers'):	# Find the link plus its category as it need to be passed by parameter
			actual_category = ''
			for line in response.css("#tabcontent table tr"):
				td = line.xpath('./td[1]')
				if len(td.css("a")) > 0:
					for url in td.css('a::attr(href)').extract():
						yield self.make_request('offer', url = url, category=actual_category)
				else:
					actual_category = '/'.join([self.get_text(x) for x in td.xpath('.//text()').extract() ])
		
		# We reload the same page with additional data. Fields will add on each other.
		elif response.url.endswith(user['username']):
			yield self.make_request('userprofile', url = '%s/offers' % response.url)	
			yield self.make_request('userprofile', url = '%s/pgp' % response.url)
			yield self.make_request('userprofile', url = '%s/info' % response.url)	
		# ===============================	

		# Some vendors also buys. We know by the amount of transaction.
		# They can be Vendor, Buyer, Vendor/Buyer
		titles = []
		if 'successful_transactions' in user and user['successful_transactions'] not in ['', ' ', '0']:
			titles.append('Vendor')
		if 'successful_transactions_as_buyer' in user and user['successful_transactions_as_buyer'] not in ['', ' ', '0']:
			titles.append('Buyer')
		if len(titles) > 0:
			user['title'] = '/'.join(titles)


		yield user


	def isloginpage(self, response):
		return True if len(response.css('form input[name="form[username]"]')) > 0 else False

	def is_ddos_challenge(self, response):
		return True if len(response.css('form input[name="form[captcha]"]')) > 0 and not self.isloginpage(response) else False

	def is_security_check(self, response):
		return len(response.css('form input#captcha_input')) > 0

	def loggedin(self, response):
		return True if len(response.css('.content').xpath('.//form[contains(@action, "logout")]')) > 0 else False

	# Some pages require only a captcha, nothing else.
	# We fill the form and return a request that will overcome the DDOS protection
	def create_request_from_ddos_protection(self, response):
		captcha_src = response.css('form img.captcha_image::attr(src)').extract_first().strip()
		formname = None
		# Must specify formname on certain pages or else the default form picked by Scrapy is the wrong one
		if len(response.css('.content').xpath('.//form[contains(@action, "logout")]')) > 0:
			if response.css('form[name=form]').extract_first():
				formname = 'form' 
		req = FormRequest.from_response(response, formname = formname)
		req.meta['captcha'] = {		# CaptchaMiddleware will take care of that.
			'request' : self.make_request('captcha', url=captcha_src),
			'name' : 'form[captcha]',
			'preprocess' : 'WallstreetMarketAddBackground'
		}
		return req
		
	def create_request_from_security_check(self, response):
		captcha_src = response.css('form div.wms_captcha_field img::attr(src)').extract_first()
		
		req = FormRequest.from_response(response)
		req.meta['captcha'] = {
			'request' : self.make_request('captcha', url=captcha_src),
			'name' : 'captcha',
			'preprocess': 'WallstreetMarketAddBackground'
		}
		return req

	# Receive the login page response and return a request with a filled form.
	def craft_login_request_from_form(self, response):
		data = {
			'form[_token]' : response.css('form input[name="form[_token]"]::attr(value)').extract_first(),
			'form[username]' : self.login['username'],
			'form[password]' : self.login['password'],
			'form[pictureQuality]' : '1',		# Picture quality. 1 = Bad (we don't need Hi resolution)
			'form[language]' : 'en',
			'form[sessionLength]' : '43200', # Session length, 12h max value = 43200
			'form[captcha]' : ''		# Will be filled by Captcha Middleware
		}

		req = FormRequest.from_response(response, formdata=data)	# No selector for form as there is just one in the page	

		captcha_src = response.css('form img.captcha_image::attr(src)').extract_first().strip()
		
		req.meta['captcha'] = {        # CaptchaMiddleware will take care of that.
			'request' : self.make_request('captcha', url=captcha_src),
			'name' : 'form[captcha]',
			'preprocess' : 'WallstreetMarketAddBackground'	# Add a black background because text is white on transparent background
		}

		return req

	def parse_timestr(self, timestr):
		try:
			if timestr.lower() == 'not available':
				return None
			elif timestr.lower() == 'online':	# Used for last login.
				return datetime.utcnow()

			# ============= Special string where time is given as an offset of now. ========
			m = re.search('about (\d+) (minute|hour|day|week|month)s? ago', timestr)
			if m:
				unit = m.group(2)
				amount = int(m.group(1))
				if unit == 'minute':
					delta = timedelta(minutes= amount)
				if unit == 'hour':
					delta = timedelta(hours	= amount)
				elif unit == 'day':
					delta = timedelta(days	= amount)
				elif unit == 'week':
					delta = timedelta(days	= amount*7)
				elif unit == 'month':
					delta = timedelta(days = amount*30)

				return datetime.utcnow() - delta
			# =========================================
			else:
				timestr = timestr.replace('UTC', '').strip()
				timestr = self.to_utc(dateutil.parser.parse(timestr))
				# If block to catch dates which are in the future.
				# For now, we just subtract a year.
				if timestr > datetime.utcnow():
					self.logger.warning("Unrealistic date. Subtracting a year.")
					timestr = timestr - relativedelta(years=1)
				return timestr
		except Exception as e:
			self.logger.error("Cannot parse time string '%s'. Error : %s" % (timestr, e))


	def get_offer_id_from_url(self, url):
		m = re.search('offer/(\d+)', url)
		if m:
			return m.group(1)
		raise Exception('Cannot find offer ID in URL %s' % url)







