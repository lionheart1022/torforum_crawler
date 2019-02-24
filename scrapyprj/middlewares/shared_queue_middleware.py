from scrapy import Request
import logging
import collections
from IPython import embed
import profiler

# This middleware will sends the Reqests that have meta[shared] = True into the spider custom queue system with enqueue_request()
class SharedQueueMiddleware(object):
	def __init__(self):
		self.logger = logging.getLogger('SharedQueueMiddleware')

	def process_spider_output(self, response, result, spider):
		profiler.start('shared_queue_process')
		for x in self.process_result(result,spider):
			yield x
		profiler.stop('shared_queue_process')


	def process_start_requests(self,start_requests, spider):
		for x in self.process_result(start_requests,spider):
			yield x
	
	def process_result(self, result, spider):
		if isinstance(result, collections.Iterable):
			for x in result:
				obj = self.process_single_object(x,spider)
				if obj:
					yield  obj
		else:
			obj = self.process_single_object(result,spider)
			if obj:
				yield  obj

	def process_single_object(self, x, spider):
		if isinstance(x, Request):
			if 'shared' in x.meta and x.meta['shared'] == True:
				spider.enqueue_request(x)
			else:
				return x
		else:
			return x
