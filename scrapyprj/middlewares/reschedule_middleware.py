from scrapy import Request
import logging
import collections
from IPython import embed
import re
from twisted.internet import reactor
from scrapy.utils.defer import defer_result
from scrapy.utils.spider import iterate_spider_output

class RescheduleException(Exception):
	def __init__(self, delay=60, *args, **kwargs):
		self.delay = delay
		super(RescheduleException, self).__init__(*args, **kwargs)

class TooManyRescheduleException(Exception):
	pass	
	
# This middleware will sends the Reqests that have meta[shared] = True into the spider custom queue system with enqueue_request()
class RescheduleMiddleware(object):
	max_reschedule = 3
	rules = {}
	meta_cnt = '__rescheduled__'


	def __init__(self):
		self.logger = logging.getLogger('RescheduleMiddleware')
		self.active_request = 0

	def process_spider_input(self, response, spider):
		self.read_settings(spider.settings)
		for regex in self.rules:
			if re.search(regex, response.body):
				if self.meta_cnt in response.meta and response.meta[self.meta_cnt] >= self.max_reschedule:
					raise TooManyRescheduleException('Request has been rescheduled more than %d time' % self.max_reschedule)
				self.logger.warning('%s response body matches regex %s, rescheduling in %d sec' % (response.url, regex, self.rules[regex]))
				raise RescheduleException(self.rules[regex])
		
	
	def process_spider_exception(self, response, exception, spider):
		if isinstance(exception, RescheduleException):
			if self.meta_cnt not in response.request.meta:
				response.request.meta[self.meta_cnt]=0
			response.request.meta[self.meta_cnt]+=1

			response.request.dont_filter = True
			response.request.priority-=1
			response.request.meta['shared'] = True
			self.active_request +=1
			reactor.callLater(exception.delay, self.recrawl, spider, response)
			yield {}	#Silently exit
		elif isinstance(exception, TooManyRescheduleException):
			self.logger.error('Dropping request %s after %d rescheduling' % (response.url, self.max_reschedule))

	def recrawl(self, spider, response):
		spider.crawler.engine.crawl(response.request, spider)
		self.active_request -= 1

	def is_active(self):
		return True if self.active_request > 0 else False

	def read_settings(self, settings):
		if 'MAX_RESCHEDULE' in settings:
			self.max_reschedule = settings['MAX_RESCHEDULE']

		if 'RESCHEDULE_RULES' in settings:
			self.rules = settings['RESCHEDULE_RULES']





