from IPython import embed
import scrapy
from scrapyprj.thirdparties.deathbycaptcha import deathbycaptcha as dbc
from urlparse import urlparse, parse_qs, parse_qsl
import urllib
import logging
from scrapy.exceptions import IgnoreRequest
from scrapyprj.captcha.DreamMarketRectangleCropper import DreamMarketRectangleCropper
from scrapyprj.captcha.WallstreetMarketAddBackground import WallstreetMarketAddBackground
import base64

# this middleware handles captcha images by sending request to death by captcha
class CaptchaMiddleware(object):

	def __init__(self):
		self.dbc_client = None
		self.logger = logging.getLogger('CaptchaMiddleware')

	def process_request(self, request, spider):
		if isinstance(request, scrapy.http.FormRequest):
			if 'captcha' in request.meta:
				if not 'request' in request.meta['captcha'] and not 'b64' in request.meta['captcha']:
					raise ValueError('Missing request or b64 content for CaptchaMiddleWare')
				if not 'name' in request.meta['captcha']:
					raise ValueError('Missing parameter name for CaptchaMiddleWare')
				
				if 'request' in request.meta['captcha']:
					captcha_req = request.meta['captcha']['request']	# This request download the captcha image
					captcha_req.priority += 1
					captcha_req.meta['original_request'] = request
					captcha_req.callback = self.receive_captcha	# This callback will send the captcha to death by captcha
					captcha_req.meta['spider'] = spider	
					self.logger.info("Requesting Captcha")
					return captcha_req
				elif 'b64' in request.meta['captcha']:	# b64 format should not be used since scrapy 1.4.0+ handle base64 request
					req = self.solve_captcha(base64.b64decode(request.meta['captcha']['b64']), spider, request)
					if req:
						return req

	def receive_captcha(self, response):
		req = self.solve_captcha(response.body, response.meta['spider'], response.meta['original_request']) # Sends request to DBC
		if req:
			yield req


	def solve_captcha(self, data, spider, request):
		error = False
		data = bytearray(data)

		# Some captcha needs some image processing
		if 'preprocess' in request.meta['captcha']:
			if request.meta['captcha']['preprocess'] == 'DreamMarketRectangleCropper':
				cropper = DreamMarketRectangleCropper()
				data = cropper.process(data)
			elif request.meta['captcha']['preprocess'] == 'WallstreetMarketAddBackground':
				bgadder = WallstreetMarketAddBackground()
				data = bgadder.process(data)
		
		dbc_username = spider.settings['DEATHBYCAPTHA']['username']
		dbc_password = spider.settings['DEATHBYCAPTHA']['password']
		dbc_client = dbc.SocketClient(dbc_username, dbc_password)		# This object is available in a library provided by death by captcha organization

		captcha_answer = None
		try:
			self.logger.info("Trying to solve captcha")
			captcha_answer = dbc_client.decode(data)
		except Exception, e:
			self.logger.error("Failed to decode Captcha using Death By Captcha : %s" % e)
			error = True
			
		if not captcha_answer:
			self.logger.error("Failed to decode Captcha using Death By Captcha")
			error = True

		if not error:
			self.logger.info("Got Captcha : %s" % captcha_answer['text'])

			# Update the original request body with a new string url containing the Captcha solution
			formdata = dict(parse_qsl(request.body, keep_blank_values=True))
			formdata[request.meta['captcha']['name']] = captcha_answer['text']
			request._set_body(urllib.urlencode(formdata))

		if 'captcha' in request.meta:
			del request.meta['captcha']

		return request