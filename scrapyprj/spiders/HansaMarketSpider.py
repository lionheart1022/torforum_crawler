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

class HansaMarketSpider(MarketSpider):
	name = "hansa_market"

	custom_settings = {
		'IMAGES_STORE' : './files/img/hansamarket',
		'RANDOMIZE_DOWNLOAD_DELAY' : True,
		'RESCHEDULE_RULES' : {}
	}


	def __init__(self, *args, **kwargs):
		super(HansaMarketSpider, self).__init__( *args, **kwargs)
		
		self.logintrial = 0

		self.set_max_concurrent_request(1)      # Scrapy config
		self.set_download_delay(0)              # Scrapy config
		self.set_max_queue_transfer_chunk(1)    # Custom Queue system
		self.statsinterval = 60;			# Custom Queue system

		self.parse_handlers = {
				'index' 		: self.parse_index,
				'category' 		: self.parse_category,
				'userprofile' 	: self.parse_userprofile,
				'listing' 		: self.parse_listing,
				'listing_feedback' : self.parse_listing_feedback,
				'user_feedback' : self.parse_user_feedback
			}

	def start_requests(self):
		yield self.make_request('index')


	def make_request(self, reqtype,  **kwargs):

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
		elif reqtype=='ddos_protection':
			req = self.create_request_from_ddos_protection(kwargs['response'])
			req.dont_filter=True
		elif reqtype in ['category', 'listing', 'userprofile', 'listing_feedback', 'user_feedback', 'image']:
			req = Request(self.make_url(kwargs['url']))
			req.meta['shared'] = True
		else:
			raise Exception('Unsuported request type %s ' % reqtype)

		if reqtype == 'listing_feedback':
			req.meta['product_rating_for'] = kwargs['listing_id']

		elif reqtype == 'user_feedback':
			req.meta['user_rating_for'] = kwargs['username']

		req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
		req.meta['proxy'] = self.proxy  #meta[proxy] is handled by scrapy.

		if 'req_once_logged' in kwargs:
			req.meta['req_once_logged'] = kwargs['req_once_logged']


		if reqtype == 'user_feedback':	# Disabled user feedback because it is redundant with ads_feedback
			return None	

		return req


	def parse(self, response):
		if not self.loggedin(response):	

			if self.isloginpage(response):
				req_once_logged = None if not 'req_once_logged' in response.meta else response.meta['req_once_logged']

				self.logintrial +=1
				self.logger.info("Trying to login")
				if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
					self.wait_for_input("Too many failed login trials. Giving up.", response.meta['req_once_logged'])
					self.logintrial=0
					return 

				yield self.make_request(reqtype='dologin', req_once_logged=req_once_logged, response=response)
			elif self.is_ddos_challenge(response):
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
			else:
				self.logger.info("Not logged, going to login page.")
				yield self.make_request(reqtype='loginpage', req_once_logged=response.request)
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
		for url in response.css('a.list-group-item::attr(href)').extract():
			yield self.make_request(reqtype='category', url=url)


	def parse_category(self, response):
		for user_link in response.xpath('//a[starts-with(@href, "/vendor/")]'):
			user = items.User()
			user['username'] = self.get_text(user_link)
			user['relativeurl'] = user_link.xpath('@href').extract_first()
			user['fullurl'] = self.make_url(user['relativeurl'])

			yield user
			yield self.make_request('userprofile', url=user['relativeurl'])

		for listing_url in response.xpath('//a[starts-with(@href, "/listing/") and not(contains(@href, "also-available"))]/@href').extract():
			yield self.make_request('listing', url=listing_url)

		for cat_url in response.css('ul.pagination li a::attr(href)').extract():
			yield self.make_request('category', url=cat_url)


	def parse_userprofile(self, response):
		try:
			user = items.User()
			user['username'] = self.get_username_from_profile(response)
			user['relativeurl'] = '/vendor/%s' % user['username']
			user['fullurl'] = self.make_url(user['relativeurl'])

			containertop = response.xpath('//h1/..')
			labels = self.get_text(containertop.css("span.label")).lower()
			user['trusted_seller'] = True if 'trusted vendor' in labels else False
			m = re.search('level (\d+)', labels)
			if m:
				user['level'] = m.group(1)
			
			containertext = self.get_text(containertop)

			m = re.search(r'last seen\s*-\s*([^\s]+)',containertext, re.IGNORECASE)
			if m:
				user['last_active'] = self.parse_timestr(m.group(1))

			m = re.search(r'vendor since\s*-\s*([^\s]+)',containertext, re.IGNORECASE)
			if m:
				user['join_date'] = self.parse_timestr(m.group(1))

			m = re.search(r'(\d+) subscribers',containertext, re.IGNORECASE)
			if m:
				user['subscribers'] = m.group(1)


			fbcontainer = response.xpath("//h3[contains(text(), 'Feedback Ratings')]/..")
			m = re.search(r'\d+', self.get_text(fbcontainer.xpath('.//a[contains(@href, "show=positive")]')))
			if m:
				user['positive_feedback'] = m.group(0)

			m = re.search(r'\d+', self.get_text(fbcontainer.xpath('.//a[contains(@href, "show=neutral")]')))
			if m:
				user['neutral_feedback'] = m.group(0)

			m = re.search(r'\d+', self.get_text(fbcontainer.xpath('.//a[contains(@href, "show=negative")]')))
			if m:
				user['negative_feedback'] = m.group(0)

			m = re.search(r"(\d+(.\d+)?\s*\%)\s*positive feedback", self.get_text(fbcontainer), re.IGNORECASE)
			if m:
				user['average_rating'] = m.group(1)

			user['successful_transactions'] = self.get_text(response.xpath("//h3[contains(text(), 'Orders')]/../p"))

			avg_volume_str = self.get_text(response.xpath("//h3[contains(text(), 'Average Volume')]/../p"))
			m = re.search(r'(\d+(.\d+)?)\s*\(\s*USD\s*(\d+(.\d+)?)\s*\)\s*per order',avg_volume_str)
			if m:
				user['avg_volume'] = m.group(1)

			# Big tabs at bottom. Only one per page. We will ne to reload the prodifle to get the rest.
			active_presentation = self.get_text(response.css("ul.nav li[role='presentation'].active")).lower()
			if active_presentation == 'profile':
				user['profile'] = self.get_text(response.xpath('//h4[contains(text(), "Vendor Profile")]/../p'))
			elif active_presentation == 'terms & conditions':
				user['terms_and_conditions'] = self.get_text(response.xpath('//h4[contains(text(), "Terms & Conditions")]/../p'))
			elif active_presentation == 'pgp':
				user['public_pgp_key'] = self.get_text(response.xpath('//h4[contains(text(), "Vendor Public PGP Key")]/../code'))

			# Ratings from other websites.
			fbhistory_container = response.xpath("//h3[contains(text(), 'Feedback History')]/..")
			agora_score = self.get_text(fbhistory_container.xpath("span[contains(@title, 'Agora')]"))
			m = re.search(r'(\d+(.\d+)?\/\d+)*', agora_score)
			if m :
				user['agora_rating'] = m.group(1)

			abraxas_score = self.get_text(fbhistory_container.xpath("span[contains(@title, 'Abaxas')]"))
			m = re.search(r'(\d+(.\d+)?\/\d+)', abraxas_score)
			if m :
				user['abraxas_rating'] = m.group(1)

			nucleus_score = self.get_text(fbhistory_container.xpath("span[contains(@title, 'Nucleus')]"))
			m = re.search(r'(\d+(.\d+)?\/\d+)', nucleus_score)
			if m :
				user['nucleus_rating'] = m.group(1)

			dreammarket_score = self.get_text(fbhistory_container.xpath("span[contains(@title, 'Dream Market')]"))
			m = re.search(r'(\d+(.\d+)?)\/\d+,', dreammarket_score)
			if m :
				user['dreammarket_rating'] = "%s/5" % m.group(1)

			valhalla_score = self.get_text(fbhistory_container.xpath("span[contains(@title, 'Valhalla')]"))
			m = re.search(r'\d+/\d+', valhalla_score)
			if m :
				user['valhalla_rating'] =  m.group(0)

			oasis_score = self.get_text(fbhistory_container.xpath("span[contains(@title, 'Oasis')]"))
			m = re.search(r'\d+/\d+/\d+', oasis_score)
			if m :
				user['oasis_rating'] =  m.group(0)

			yield user

			for url in response.css("ul li[role='presentation'] a::attr(href)").extract():
				if 'feedback' in url :
					yield self.make_request('user_feedback', url=url, username=user['username'])
				else:
					yield self.make_request('userprofile', url=url)	# Will reload profile with new info in it. They will add in database.

		except WarningException as e:
			self.logger.warning("Could not parse profile at %s. %s" % (response.url, e))

			
	def parse_listing(self, response):
		try:
			ads = items.Ads()
			lis = response.css('.container ol li')
			title_cat = []
			[title_cat.append(self.get_text(li)) for li in lis]
			if (len(title_cat) < 1):
				raise WarningException("Cannot determine title of listing.")

			m = re.search('listing\/(\d+)', response.url)
			if not m:
				raise WarningException('Cannot find listing ID')

			ads['offer_id'] = m.group(1)
			ads['relativeurl'] = '/listing/%s' % ads['offer_id']
			ads['fullurl'] = self.make_url(ads['relativeurl'])		
			ads['title'] = title_cat[-1]  # Last item
			ads['category'] = '/'.join(title_cat[:-1])  # Last item
			ads['price'] = self.get_text(response.css(".listing-price .fa-btc").xpath('..'))

			lines  = response.css(".container form table").xpath('.//td[contains(text(), "Vendor")]/../../tr')
			for line in lines:
				tds = line.css('td')

				if len(tds) != 2:
					raise WarningException("Listing property table line does not have two cells.")

				prop = self.get_text(tds[0]).lower()
				val = tds[1]
				if prop == 'vendor':
					vendor_link = val.xpath('a[contains(@href, "vendor")]')
					yield self.make_request('userprofile', url=vendor_link.xpath('@href').extract_first())
					ads['vendor_username'] = self.get_text(vendor_link)
				elif prop == 'class':
					ads['ads_class'] = self.get_text(val)
				elif prop == 'ships from':
					ads['ships_from'] = self.get_text(val)
				elif prop == 'ships to':
					ads['ships_to'] = self.get_text(val)
				elif prop == 'except':
					ads['ships_to_except'] = self.get_text(val)
				elif prop == 'delivery':
					ads['shipping_options'] = json.dumps([self.get_text(val)])
				else:
					self.logger.warning("New property found : %s. Listing at %s" % (prop, response.url))

			shipping_options_elements = response.css('select[name="shippingID"] option:not([value="0"])')
			shipping_options = []
			for element in shipping_options_elements:
				shipping_options.append(self.get_text(element))

			if len(shipping_options) > 0:
				ads['shipping_options'] = json.dumps(shipping_options)
					
			ads['description'] 			= self.get_presentation_text(response, 'Details')
			ads['terms_and_conditions'] = self.get_presentation_text(response, 'Terms & Conditions')

			ads['in_stock'] = True if len(response.css(".listing-stock .label-success")) > 0 else False
			stock_text = self.get_text(response.css(".listing-stock .label-success")).lower()
			m = re.search('(\d+) in stock', stock_text)
			if m:
				ads['stock'] = m.group(1)

			yield ads


			## ===================== IMAGES =====================
			images_url = response.css('img.img-thumbnail::attr(src)').extract();
			for url in images_url:
				if url:
					img_item = items.AdsImage(image_urls = [])
					img_item['image_urls'].append(self.make_request('image', url=url))	# Need Scrapy > 1.4.0 for this to work (base64 url encoded data).
					img_item['ads_id'] = ads['offer_id']
					yield img_item

			#self.dao.flush(dbmodels.AdsImage)
			## =========


			presetations = response.css("li[role='presentation'] a");
			for presentation in presetations:
				name = self.get_text(presentation).lower()
				link = presentation.xpath('@href').extract_first()
				if name in ['details', 'terms & conditions'] : 
					yield self.make_request('listing', url=link)
				elif name == 'feedback':
					yield self.make_request('listing_feedback', url=link, listing_id=ads['offer_id'])
				else:
					self.logger.warning('Encountered an unknown tab %s. Listing at %s' % (name, response.url))

		except WarningException as e:
			self.logger.warning("Cannot parse listing.  %s" % e) 
		except:
			raise

	def parse_listing_feedback(self, response):
		
		m = re.search('listing\/(\d+)', response.url)
		if not m:
			raise Exception('Cannot find listing ID')
		listing_id= m.group(1)
		
		for line in response.css('ul.nav li[role="presentation"].active').xpath("./../../table/tbody/tr"):
			try:
				rating = items.ProductRating()
				cells = line.css('td')
				expected_cols = 5
				if len(cells) != expected_cols:
					raise WarningException("Feedback tables does not have %d columns as expected." % expected_cols)

				if len(cells[0].css('.label-danger')) > 0:
					rating['rating'] = 'Negative'
				elif len(cells[0].css('.label-success')) > 0:
					rating['rating'] = 'Positive'
				elif len(cells[0].css('.label-default')) > 0:
					rating['rating'] = 'Neutral'
				else:
					raise WarningException('Unknown rating icon')

				rating['delivery_time'] = self.get_text(cells[2])
				rating['submitted_on'] 	= self.parse_timestr(self.get_text(cells[4]))
				rating['comment'] 		= self.get_text(cells[1].css("p:first-child"))
				rating['ads_id'] = listing_id

				m = re.match(r'([^\[]+)(\[\d+\])?', self.get_text(cells[3]))
				if m:
					rating['submitted_by'] 	= self.get_text(m.group(1))

				yield rating

			except WarningException as e:
				self.logger.warning("Could not get listing feedback at %s. %s" % (response.url, e))
			except:
				raise

			for url in response.css(".pages ul.pagination a::attr(href)").extract():
				if not url.endswith('page=1'):  # We already saw that page, but maybe with a different URL (no page parameter)
					yield self.make_request('listing_feedback', url=url, listing_id=listing_id)



	def parse_user_feedback(self, response):
		username = self.get_username_from_profile(response)
		for line in response.css('ul.nav li[role="presentation"].active').xpath("./../../table/tbody/tr"):
			try:
				rating = items.UserRating()
				cells = line.css('td')
				expected_cols = 5
				if len(cells) != expected_cols:
					raise WarningException("Feedback tables does not have %d columns as expected." % expected_cols)

				if len(cells[0].css('.label-danger')) > 0:
					rating['rating'] = 'Negative'
				elif len(cells[0].css('.label-success')) > 0:
					rating['rating'] = 'Positive'
				elif len(cells[0].css('.label-default')) > 0:
					rating['rating'] = 'Neutral'
				else:
					raise WarningException('Unknown rating icon')

				rating['delivery_time'] = self.get_text(cells[2])
				rating['submitted_on'] 	= self.parse_timestr(self.get_text(cells[4]))
				rating['comment'] 		= self.get_text(cells[1].css("p:first-child"))
				rating['username'] 		= username
				m = re.match(r'([^\[]+)(\[\d+\])?', self.get_text(cells[3]))
				if m:
					rating['submitted_by'] 	= self.get_text(m.group(1))

				yield rating	# Will be flush later if all requests are completed.

			except WarningException as e:
				self.logger.warning("Could not get listing feedback at %s. %s" % (response.url, e))
			except:
				raise
		
		for url in response.css(".pages ul.pagination a::attr(href)").extract():
			if not url.endswith('page=1'):  # We already saw that page, but maybe with a different URL (no page parameter)
				yield self.make_request('user_feedback', url=url, username=username)
		


	def get_presentation_text(self, response, name):
		container = response.css("h3").xpath("u[contains(text(), '%s')]/../.." % name )
		container_text = self.get_text(container)
		ul_text = self.get_text(container.css('ul'))
		h3_text = self.get_text(container.css('h3'))
		if ul_text and container_text.startswith(ul_text):
			container_text= container_text.split(ul_text,1)[1].strip()
		if h3_text and container_text.startswith(h3_text):
			container_text= container_text.split(h3_text,1)[1].strip()

		return container_text

	def isloginpage(self, response):
		return True if len(response.css('form[action="/login"]')) > 0 else False

	def is_ddos_challenge(self, response):
		return True if 'Security Challenge' in response.css('title').extract_first() else False

	def loggedin(self, response):
		activeuser = self.get_text(response.css(".active-user"))
		return True if self.login['username'].lower() in activeuser.lower() else False

	def craft_login_request_from_form(self, response):
		data = {
			'username' : self.login['username'],
			'pw' : self.login['password'],
			'action' : 'login',
			'sec' : ''
		}

		req = FormRequest.from_response(response, formdata=data, formcss='form[action="/login"]')

		captcha_src = response.css("form img::attr(src)").extract_first()
		
		req.meta['captcha'] = {        # CaptchaMiddleware will take care of that.
			'request' : self.make_request('captcha', url=captcha_src),
			'name' : 'sec'   
		}

		return req

	def get_username_from_profile(self, response):
		h1 = response.css("h1::text")
		if not h1:
			raise WarningException("No username available.")
		return self.get_text(h1.extract_first().strip())

	def parse_timestr(self, timestr):
		try:
			timestr = timestr.replace('UTC', '').strip()
			dt = self.to_utc(dateutil.parser.parse(timestr))
			return dt
		except Exception as e:
			self.logger.error("Cannot parse time string '%s'. Error : %s" % (timestr, e))


	def create_request_from_ddos_protection(self, response):
		captcha_src = response.css('.container img::attr(src)').extract_first().strip()
		req = FormRequest.from_response(response, formcss='form[action="/challenge/"]')
		
		req.meta['captcha'] = {		# CaptchaMiddleware will take care of that.
			'request' : self.make_request('captcha', url=captcha_src),
			'name' : 'sec'
			}
		return req
