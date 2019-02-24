from scrapy import Request
import logging
import collections
from IPython import embed
import profiler

# This middleware will sends the Reqests that have meta[shared] = True into the spider custom queue system with enqueue_request()
class StartRequestCookie(object):
	def __init__(self):
		self.logger = logging.getLogger('StartRequestCookie')

	def process_start_requests(self,start_requests, spider):
		for x in start_requests:
			if isinstance(x, Request):
				if 'START_COOKIE' in spider.settings:
					spider.set_cookies(spider.settings['START_COOKIE'])
					self.logger.debug("Adding cookie to start request : %s" % spider.settings['COOKIE'])
			yield x
