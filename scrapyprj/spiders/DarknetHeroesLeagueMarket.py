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


class DarknetHeroesLeague(MarketSpider):
	name = "dhl_market"

	custom_settings = {
		'IMAGES_STORE' : './files/img/dhl_market',
		'RANDOMIZE_DOWNLOAD_DELAY' : True,
		'RESCHEDULE_RULES' : {},
		'MAX_LOGIN_RETRY' : 10
	}


	def __init__(self, *args, **kwargs):
		super(DarknetHeroesLeague, self).__init__( *args, **kwargs)
		
		self.logintrial = 0

		self.set_max_concurrent_request(4)      # Scrapy config
		self.set_download_delay(0)             # Scrapy config
		self.set_max_queue_transfer_chunk(5)    # Custom Queue system
		self.statsinterval = 60;			# Custom Queue system

		self.parse_handlers = {
				'index' 		: self.parse_index,			# Home page
				'category'		: self.parse_category,		# Category content
				'product'		: self.parse_product,			# Listing page
				
				'userprofile'	: self.parse_userprofile,	# User profile page
				'userproduct'	: self.parse_userproduct,	# User profile page
				'userpgp'		: self.parse_userpgp,			# User profile page
				'userfeedback'	: self.parse_userfeedbacks			# User profile page
			}


		self.yielded_category_page = {};

	def start_requests(self):
		#yield self.make_request('userprofile', url='/vendor_profile?vid=216', dont_filter=True, username='StarkoftheNorth')
		yield self.make_request('index')


	def make_request(self, reqtype,  **kwargs):

		passthru = ['category', 'escrow', 'username']

		if 'url' in kwargs:
			kwargs['url'] = self.make_url(kwargs['url'])

		if reqtype == 'index':
			req = Request(self.make_url('index'))
			req.dont_filter=True
		elif reqtype == 'dologin':
			req = self.craft_login_request_from_form(kwargs['response'])
			req.dont_filter=True
		elif reqtype == 'captcha':
			req = Request(self.make_url(kwargs['url']))
			req.dont_filter=True
		elif reqtype == 'image':
			req = Request(self.make_url(kwargs['url']))
		
		elif reqtype in ['category', 'product', 'userprofile', 'userproduct', 'userpgp', 'userfeedback']:
			req = Request(self.make_url(kwargs['url']))
			req.meta['shared'] = True
		else:
			raise Exception('Unsuported request type %s ' % reqtype)

		req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
		req.meta['proxy'] = self.proxy  #meta[proxy] is handled by scrapy.

		if 'priority' in kwargs:
			req.priority = kwargs['priority']

		if 'dont_filter' in kwargs:
			req.dont_filter = kwargs['dont_filter']

		if reqtype == 'userfeedback':
			req.meta['user_rating_for'] = kwargs['username']

		for k in passthru:
			if k in kwargs:
				req.meta[k] = kwargs[k]

		if 'req_once_logged' in kwargs:
			req.meta['req_once_logged'] = kwargs['req_once_logged']

		return req


	def parse(self, response):
		if not self.loggedin(response):	
			if self.isloginpage(response):
				req_once_logged = response.request if not 'req_once_logged' in response.meta else response.meta['req_once_logged']

				self.logintrial +=1
				self.logger.info("Trying to login")
				if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
					self.wait_for_input("Too many failed login trials. Giving up.", response.meta['req_once_logged'])
					self.logintrial=0
					return 

				yield self.make_request(reqtype='dologin', req_once_logged=req_once_logged, response=response)
		else: 
			self.logintrial = 0

			# We restore the missed request when protection kicked in
			if response.meta['reqtype'] in ['dologin']:
				if response.meta['reqtype'] == 'dologin':
					self.logger.info("Login Success!")

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
		for subcat in response.css('nav.main-nav ul li ul li a'):
			category = self.get_text_first(subcat)
			url = subcat.xpath('@href').extract_first()

			yield self.make_request('category', url=url, category=category)

		for url in response.xpath('//a[contains(@href, "product/")]/@href').extract():
			yield self.make_request('product', url=url) 	# We do not have a category from here. It won't delete an existing entry having a category


	def parse_category(self, response):
		for row in  response.css('table.product-list tbody tr'):
			user_link = row.xpath('.//a[contains(@href, "vid=")]')
			username = self.get_text(user_link)
			url = user_link.xpath('@href').extract_first()
			vendor_id = self.get_vendor_id_from_url(url)

			yield self.make_request('userproduct', 	url='home?vid=%s' % vendor_id, 				username=username)
			yield self.make_request('userprofile', 	url='vendor_profile?vid=%s' % vendor_id, 	username=username)
			yield self.make_request('userpgp', 		url='ourpgp?vid=%s' % vendor_id,			username=username)
			yield self.make_request('userfeedback', url='feedback?vid=%s' % vendor_id, 			username=username)

			product_link = row.xpath('.//a[contains(@href, "product/") and not(img)]');
			url = product_link.xpath('@href').extract_first()
			yield self.make_request('product', url=url, username=username, category=response.meta['category'])	

			for page_url in response.css('.pagination a::attr(href)').extract():
				yield self.make_request('category', url=page_url, category=response.meta['category'])
			
	def parse_product(self, response):
		ads = items.Ads()

		if 'username' in response.meta:
			username = response.meta['username']
		else:
			username = self.get_username_from_header(response)

		ads['offer_id'] 		= self.get_product_id_from_url(response.url)
		ads['relativeurl'] 		= 'product/%s' % ads['offer_id']
		ads['fullurl'] 			= self.make_url(ads['relativeurl'])
		ads['vendor_username'] 	= username

		if 'category' in response.meta and response.meta['category'] != None:
			ads['category'] 	= response.meta['category']

		ads['title'] 			= self.get_text_first(response.css('.container h1'))
		ads['description'] 		= self.get_text(response.css('article.internal-product-desc')) 
		
		ads['escrow'] = False
		ads['in_stock'] = False
		price_options = []
		# for each trable line
		for tr in response.css('.internal-product-varieties table tr'):
			qty = self.get_text(tr.xpath('./td[1]'))
			for btn in tr.css('.btn'):	# Many options per line possible, separated by a Buy button
				option = {}
				option['qty'] = qty
				btn_txt = self.get_text(btn)
				btn_text_lower = btn_txt.lower();
				if 'escrow' in btn_text_lower:
					option['method'] 	= 'escrow'
					ads['in_stock'] = True
				elif 'direct-pay' in btn_text_lower:
					option['method'] 	= 'direct-pay'
					ads['in_stock'] = True
				elif 'out of stock' in btn_text_lower:
					option['method'] = 'out of stock'
					pass
				else:
					option['method'] = ''
					self.logger.warning('Unknown price payment method from string "%s" at %s' % (btn_text_lower, response.url))
				
				# Scan each line to find the price that preceed the actual button
				last_price_seen = ''
				for td in tr.css('td'):
					td_txt = self.get_text(td)
					m = re.search('BTC\s*(\d+(.\d+)?)', td_txt, re.IGNORECASE)
					if m:
						last_price_seen = m.group(1)	# We found a price in bitcoin, if we encounter the actual button, this price will be the right one

					btn_in_cell = td.css('.btn')
					if btn_in_cell:
						if self.get_text(btn_in_cell) == btn_txt:	
							option['price'] 	= last_price_seen
							break

				if 'price' not in option:
					self.logger.warning('Could not find price for product at %s' % response.url)
					option['price'] = ''

				
				if option['method'] == 'escrow':
					ads['escrow'] = True

				price_options.append(option)

		ads['price_options'] = json.dumps(price_options)

		if len(price_options) == 1:
			ads['price'] = price_options[0]['price']

		ads_img 				= items.AdsImage()
		ads_img['ads_id'] 		= ads['offer_id']
		img_src 				= response.css('.main-content').xpath('.//img[contains(@src, "product_images")]/@src').extract_first()
		if img_src:
			ads_img['image_urls'] 	= [self.make_request('image', url=img_src)]
		yield ads_img

		yield ads

	def parse_userprofile(self, response):
		user = items.User()

		user['username'] 	= response.meta['username']
		user['fullurl'] 	= response.url
		user['relativeurl'] = self.get_relative_url(response.url)
		user['profile'] 	= self.get_text(response.css('.vendor-profile-details'))

		# =============== Top list of properties
		for line in response.css('.vendor-profile .vendor-profile-list li'):
			key = self.get_text(line.xpath('./span[1]')).lower()
			val_span = line.xpath('./span[2]')
			if key:
				if key == 'ships from':
					user['ship_from'] 				= self.get_text(val_span.xpath('.//img[1]/@alt').extract_first()).upper()

				elif key == 'last seen':
					user['last_active'] 			= self.parse_timestr(self.get_text(val_span))

				elif key == 'vendor deals':
					user['successful_transactions']	= self.get_text(val_span)

				elif key == 'vendor %':
					user['level'] 					= self.get_text(val_span)

				elif key == 'vendor rating':
					user['average_rating'] 			= self.get_text(val_span)

				elif key == 'fans':
					user['subscribers'] 			= self.get_text(val_span)

				else:
					self.logger.warning('New property found in user profile. Property = %s.  URL=%s' % (key, response.url))

		# ======  State machine to parse the rightmost feed containing news and terms of service =========
		# We make a list of news, then gather
		parse_state = 'unknown'
		news_entry = None
		last_content = ''
		news = []
		terms_sel_list = scrapy.selector.unified.SelectorList()
		rightmost_block = response.css('.vendor-profile-news')
		for node in response.css('.vendor-profile-news>*'):
			if node.root.tag == 'h2':
				if self.get_text(node).lower() == 'news':
					parse_state = 'news'
				elif self.get_text(node).lower() == 'terms of service':
					parse_state = 'terms'


			if parse_state == 'news':
				if news_entry != None and (node.root.tag == 'h3' or node.root.tag == 'h2'):
					news.append(news_entry)
					news_entry = None
				

				if node.root.tag == 'h3':
					if news_entry == None:
						news_entry = {'title' : '', 'content' : ''}
					news_entry['title'] = self.get_text(node)
					last_content = ''
				elif node.root.tag == 'p':
					news_entry['content'] += self.get_text(node)
			elif parse_state == 'terms':
				pass
		
		if len(news) > 0:
			user['news'] = json.dumps(news)
		## ==========================================================

		# === Try to get Terms of service by splitting HTML. Best we can do with scrapy ====
		blocks = ''.join(response.css('.vendor-profile-news').extract()).split('<h2>Terms of Service</h2>')
		if len(blocks) == 2:
			sel = scrapy.Selector(text = '<article>'+blocks[1])
			user['terms_and_conditions'] 	= self.get_text(sel)
		# =====================

		yield user

	def parse_userproduct(self, response):	
		for url in response.xpath('//a[contains(@href, "product/")]/@href').extract():
			yield self.make_request('product', url=url, username=response.meta['username']) 	# We do not have a category from here. It won't delete an existing entry having a category

	def parse_userpgp(self, response):
		user = items.User()
		user['username'] = response.meta['username']	# Mandatory information to add info to a user
		user['public_pgp_key'] = self.get_text(response.css('.main-content textarea'))
		yield user

	def parse_userfeedbacks(self, response):
		table = response.css('.main-content table')
		header_map = self.parse_table_header(table.css('thead'))
		
		for tr in response.css('.main-content table tbody tr'):
			try:
				rating = items.UserRating()
				rating['submitted_on'] 	= self.parse_timestr(self.get_text(self.get_cell(tr, 'age', header_map)))
				rating['comment'] 		= self.get_text(self.get_cell(tr, 'feedback', header_map))
				rating['username'] 		= response.meta['username']
				
				rating['communication'] 	= self.get_score(self.get_cell(tr, 'communication', header_map))
				rating['speed'] 			= self.get_score(self.get_cell(tr, 'shippingspeed', header_map))
				rating['stealth'] 			= self.get_score(self.get_cell(tr, 'stealth', header_map))
				rating['quality'] 			= self.get_score(self.get_cell(tr, 'productquality', header_map))
				rating['payment_type'] 		= self.get_text(self.get_cell(tr, 'type', header_map))
				rating['item_name'] 		= self.get_text(self.get_cell(tr, 'item name', header_map))
				rating['submitter_level'] 	= self.get_text(self.get_cell(tr, 'level', header_map))
				
				yield rating
			except Exception as e:
				self.logger.error("Cannot parse User Feedback. Error : %s" % e)

		for url in response.css('.pagination').xpath('.//a[not(contains(@href, "start=0"))]/@href').extract():
			yield self.make_request('userfeedback', url=url, username=response.meta['username'])

	def isloginpage(self, response):
		return True if len(response.css('.main-login-form')) > 0 else False

	def loggedin(self, response):
		return True if len(response.xpath('//header//a[contains(@href, "logout")]')) > 0 else False
		
	# Receive the login page response and return a request with a filled form.
	def craft_login_request_from_form(self, response):
		data = {
			'username' : self.login['username'],
			'password' : self.login['password'],
			'ct_captcha' : ''		# Will be filled by Captcha Middleware
		}

		req = FormRequest.from_response(response, formdata=data, formcss='.main-login-form')	# No selector for form as there is just one in the page	

		captcha_src = response.css('.main-login-form img::attr(src)').extract_first().strip()
		
		req.meta['captcha'] = {        # CaptchaMiddleware will take care of that.
			'request' : self.make_request('captcha', url=captcha_src),
			'name' : 'ct_captcha'
		}

		return req

	def parse_timestr(self, timestr):
		try:	
			utcnow = datetime.utcnow()
			if timestr.lower() == 'today':
				return utcnow.replace(hour=12, minute=0, second=0, microsecond=0)

			m = re.search('(\d+) (minute|hour|day|week|month|year)s? ago', timestr)
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

	def get_product_id_from_url(self, url):
		m = re.search('/product/(\d+)', url)
		return m.group(1) if m else None

	def get_vendor_id_from_url(self, url):
		m = re.search('vid=(\d+)', url)
		return m.group(1) if m else None

	def get_username_from_header(self, response):
		return self.get_text(response.css('.vendor-header .vendor-details a'))

	def parse_table_header(self, thead):
		header_map = {}
		index = 1;
		for td in thead.css('th'):
			txt_lower = self.get_text(td).lower()
			if txt_lower in header_map:
				self.logger.warning('Repeating header in table. Skipping')
				break
			header_map[txt_lower] = index
			index+=1

		return header_map

	def get_cell(self, tr, name, header_map):
		return tr.xpath('./td[%s]' % header_map[name])

	def get_score(self, td):
		content_unicode = self.get_text(td).decode('utf8')
		blackstar = content_unicode.count(u'\u2605')
		whitestar = content_unicode.count(u'\u2606')
		return "%d/%d" %(blackstar, blackstar+whitestar)


