from scrapy import Request
import logging
import collections
from IPython import embed
from scrapyprj.spiders.MarketSpider import MarketSpider
import scrapyprj.items.market_items as market_items
from scrapy.utils.request import request_fingerprint
import scrapyprj.database.markets.orm.models as market_models
import traceback
from scrapy import signals
## 
## Since feedbacks are not uniques, we can't rely on the database to remove duplicate.
## We need a complete dataset as a reference. 
## We store rating until all requests that can generate them are completed.
## The user needs to identify such requests, the rest is handled here.
##
## For each rating given, it is stored and associated with its owner (username or ads id). Once all
## request are completed, the buffer will be emptied and given to next middlewares.
## 


# This class simply read/write data into a dict that is held by the spider class (not the instance) so it can be shared between instances.
class SpiderAccessor(object):
	init = False
	def __init__(self, spider):
		self.datastruct = spider.get_shared_data_struct();
		self.logger = logging.getLogger('FeedbackBufferMiddleware')

		if not hasattr(self.datastruct, '_feedback_buffer_init'):
			self.datastruct._feedback_buffer_init = True

			if not hasattr(self.datastruct, '_user_rating_items'):
				self.datastruct._user_rating_items = {}	
			
			if not hasattr(self.datastruct, '_product_rating_items'):
				self.datastruct._product_rating_items = {}
			
			if not hasattr(self.datastruct, '_user_rating_requests'):
				self.datastruct._user_rating_requests = {}
			
			if not hasattr(self.datastruct, '_product_rating_requests'):
				self.datastruct._product_rating_requests = {}

	# Add the item into the internal buffer until it is retrieved
	def hold_rating(self, rating):
		if isinstance(rating, market_items.UserRating):
			if not rating['username'] in self.datastruct._user_rating_items:
				self.datastruct._user_rating_items[rating['username']] = []
			self.datastruct._user_rating_items[rating['username']].append(rating)
		elif isinstance(rating, market_items.ProductRating):
			if not rating['ads_id'] in self.datastruct._product_rating_items:
				self.datastruct._product_rating_items[rating['ads_id']] = []
			self.datastruct._product_rating_items[rating['ads_id']].append(rating)
		else:
			raise ValueError('Item must either be UserRating or ProductRating')

	# Retrieve rating that were held inside buffer
	def retrieve_held_user_ratings(self, username):
		if username not in self.datastruct._user_rating_items:
			self.datastruct._user_rating_items[username] = []

		for rating in self.datastruct._user_rating_items[username]:
			yield rating

		self.datastruct._user_rating_items[username] = []	# Erase


	def retrieve_held_product_ratings(self, ads_id):
		if ads_id not in self.datastruct._product_rating_items:
			self.datastruct._product_rating_items[ads_id] = []

		for rating in self.datastruct._product_rating_items[ads_id]:
			yield rating

		self.datastruct._product_rating_items[ads_id] = []	# Erase

	# Empty buffer for a specific rating owner
	def erase_user_ratings(self, username):
		self.logger.debug("Dropping all ratings for user %s" % username)
		del self.datastruct._user_rating_items[username] 
		self.datastruct._user_rating_items[username] =[]

	def erase_product_ratings(self, ads_id):
		self.logger.debug("Dropping all ratings for product %s" % ads_id)
		del self.datastruct._product_rating_items[ads_id]
		self.datastruct._product_rating_items[ads_id] = []


	# Check that all request that could provide ratings have been successfully completed.
	def has_all_user_ratings(self, username):
		if username not in self.datastruct._user_rating_requests:
			self.datastruct._user_rating_requests[username] = {}

		if len(self.datastruct._user_rating_items[username]) == 0:
			return False

		for fingerprint in self.datastruct._user_rating_requests[username]:
			if self.datastruct._user_rating_requests[username][fingerprint] == False:
				return False
		return True

	def has_all_product_ratings(self, ads_id):
		if ads_id not in self.datastruct._product_rating_requests:
			self.datastruct._product_rating_requests[ads_id] = {}

		if len(self.datastruct._product_rating_items[ads_id]) == 0:
			return False

		for fingerprint in self.datastruct._product_rating_requests[ads_id]:
			if self.datastruct._product_rating_requests[ads_id][fingerprint] == False:
				return False
		return True

	# Mark a request like a dependency for the rating. 
	# We won't be ready to retrieve until all request has been completed.
	def register_request_for_user_rating(self, request, username):
		fingerprint = request_fingerprint(request)
		if username not in self.datastruct._user_rating_requests:
			self.datastruct._user_rating_requests[username] = {}

		if fingerprint not in self.datastruct._user_rating_requests[username]:
			self.logger.debug("Registering rating dependency between user %s and request %s" % (request.meta['user_rating_for'], request.url))
			self.datastruct._user_rating_requests[username][fingerprint] = False


	def register_request_for_product_rating(self, request, ads_id):
		fingerprint = request_fingerprint(request)
		if ads_id not in self.datastruct._product_rating_requests:
			self.datastruct._product_rating_requests[ads_id] = {}

		if fingerprint not in self.datastruct._product_rating_requests[ads_id]:
			self.logger.debug("Registering rating dependency between product %s and request %s" % (request.meta['product_rating_for'], request.url))
			self.datastruct._product_rating_requests[ads_id][fingerprint] = False

	#Mark a request like completed. Once they all are, we will be ready to retrieve ratings.
	def mark_request_completed_for_user_rating(self, request, username):
		fingerprint = request_fingerprint(request)
		if username not in self.datastruct._user_rating_requests:
			self.datastruct._user_rating_requests[username] = {}

		if fingerprint in self.datastruct._user_rating_requests[username]:
			if self.datastruct._user_rating_requests[username][fingerprint] == False:
				self.logger.debug("Marking request as completed  %s for user %s" % (request.url, request.meta['user_rating_for']))
		
		self.datastruct._user_rating_requests[username][fingerprint] = True

	def mark_request_completed_for_product_rating(self, request, ads_id):
		fingerprint = request_fingerprint(request)
		if ads_id not in self.datastruct._product_rating_requests:
			self.datastruct._product_rating_requests[ads_id] = {}
		
		if fingerprint in self.datastruct._product_rating_requests[ads_id]:
			if self.datastruct._product_rating_requests[ads_id][fingerprint] == False:
				self.logger.debug("Marking request as completed %s for product %s" % (request.url, request.meta['product_rating_for']))
		
		self.datastruct._product_rating_requests[ads_id][fingerprint] = True

	# Tells which user/ads is ready to get its rating retreive for further pipeline processing.
	def get_all_completed_user_ratings_username(self):
		for username in self.datastruct._user_rating_items:
			if self.has_all_user_ratings(username):
				yield username

	def get_all_completed_product_ratings_id(self):
		for ads_id in self.datastruct._product_rating_items:
			if self.has_all_product_ratings(ads_id):
				yield ads_id

	# Gives the items without checking if they are ready to be given
	def get_all_user_ratings_username(self):
		for username in self.datastruct._user_rating_items:
			yield username

	def get_all_product_ratings_id(self):
		for ads_id in self.datastruct._product_rating_items:
			yield ads_id



### This class is the middleware
class FeedbackBufferMiddleware(object):
	def __init__(self):
		self.logger = logging.getLogger('FeedbackBufferMiddleware')
		self.ads_flush_when_all_scraped = {}
		self.user_flush_when_all_scraped = {}

	@classmethod
	def from_crawler(cls, crawler):
		o = cls()
		crawler.signals.connect(o.item_scraped, signal=signals.item_scraped)	
		crawler.signals.connect(o.item_dropped, signal=signals.item_dropped)
		return o

	def process_start_requests(self, start_requests, spider):
		if isinstance(spider, MarketSpider):
			accessor = SpiderAccessor(spider)

		for x in start_requests:
			obj = self.process_single_result(x,spider)
			if obj:
				yield obj


	# Request and most items apsses through without being touched
	# Only UserRating and ProductRating get a different treatment.
	def process_spider_output(self, response, result, spider):
		checkflush_user = False
		checkflush_product = False

		for x in result:
			#These flags only tells us if the spider callback played a role in the generation of feedback item.
			checkflush_user 	= True if isinstance(x, market_items.UserRating) else checkflush_user
			checkflush_product 	= True if isinstance(x, market_items.ProductRating) else checkflush_product
			
			obj = self.process_single_result(x,spider)	# Returns None id item is put aside to be yielded later
			if obj:
				yield  obj


		#### Executed once request callback is completed! (generator empty) ###
		if isinstance(spider, MarketSpider):	# Only Market Spider handles ProductRatin and UserRating objects.
			accessor = SpiderAccessor(spider)
			if checkflush_user:	# Check only if items has been yielded. Speed optimisation			
				for username in list(accessor.get_all_completed_user_ratings_username()): # List is important. We force full tieration before yield. Dictionary can change between yields
					self.logger.debug("User ratings for user %s are ready to be processed." % (username))
					ratings_to_yield = list(accessor.retrieve_held_user_ratings(username))
					accessor.erase_user_ratings(username)	# Save some RAM

					if len(ratings_to_yield) > 0:
						spider.dao.flush(market_models.User) 	# We force flush because map2db may need a User that is waiting in the DAO queue. Item will be drop if that happen.
					
					for rating in ratings_to_yield:
						self.user_flush_when_all_scraped[id(rating)] = False
						self.logger.debug("Requiring User rating %s to be scraped before flush" % id(rating))

					for rating in ratings_to_yield:
						yield rating
			
			if checkflush_product:
				for ads_id in list(accessor.get_all_completed_product_ratings_id()):		# List is important. We force full tieration before yield. Dictionary can change between yields
					self.logger.debug("Product ratings for ads %s are ready to be processed." % (ads_id))
					ratings_to_yield = list(accessor.retrieve_held_product_ratings(ads_id))
					accessor.erase_product_ratings(ads_id)	# Save some RAM
					
					if len(ratings_to_yield) > 0:
						spider.dao.flush(market_models.Ads)	# We force flush because map2db may need a User that is waiting in the DAO queue. Item will be drop if that happen.
							
					for rating in ratings_to_yield:
						self.ads_flush_when_all_scraped[id(rating)] = False
						self.logger.debug("Requiring Product rating %s to be scraped before flush" % id(rating))
					
					for rating in ratings_to_yield:
						yield rating

	# When an item is completely processed, we check if we are in position to flush to queue.
	# We can only if all feedbacks are processed.
	def item_processed(self, item, spider):
		if isinstance(spider, MarketSpider):
			if isinstance(item, market_items.ProductRating):
				if id(item) in self.ads_flush_when_all_scraped:
					self.logger.debug("Product rating  %s scraped and found in dict" % id(item))
					self.ads_flush_when_all_scraped[id(item)] = True		# Mark this object like 'scraped'
					
					must_flush = True
					for key in self.ads_flush_when_all_scraped:
						if self.ads_flush_when_all_scraped[key] == False:	# Not scraped yet
							must_flush = False
					
					if must_flush:	# All rating has been scraped
						self.logger.debug("Must flush Ads Feedback")
						spider.dao.flush(market_models.AdsFeedback)		# Note that Autoflush middleware does not flush Ads Feedback
						self.ads_flush_when_all_scraped = {}
				else:
					self.logger.debug('Unknown product rating : %s' % id(item))

			elif isinstance(item, market_items.UserRating):
				if id(item) in self.user_flush_when_all_scraped:
					self.logger.debug("User rating  %s scraped and found in dict" % id(item))
					self.user_flush_when_all_scraped[id(item)] = True	# Mark this object like 'scraped'
					
					must_flush = True
					for key in self.user_flush_when_all_scraped:
						if self.user_flush_when_all_scraped[key] == False:	# Not scraped yet
							must_flush = False
					
					if must_flush:	# All rating has been scraped
						self.logger.debug("Must flush Seller Feedback")
						spider.dao.flush(market_models.SellerFeedback)		# Note that Autoflush middleware does not flush Seller Feedback
						self.user_flush_when_all_scraped = {}
				else:
					self.logger.debug('Unknown user rating : %s' % id(item))
						
	
	def item_scraped(self, item, response, spider):
		self.item_processed(item, spider)

	def item_dropped(self, item, response, exception, spider):
		self.item_processed(item, spider)

	# When a response comes in, we mark the request as completed
	def process_spider_input(self, response, spider ):
		if isinstance(spider, MarketSpider):
			accessor = SpiderAccessor(spider)
			if 'user_rating_for' in response.meta:
				accessor.mark_request_completed_for_user_rating(response.request, response.meta['user_rating_for'])
			elif 'product_rating_for' in response.meta:
				accessor.mark_request_completed_for_product_rating(response.request, response.meta['product_rating_for'])

	# Mark a request like a dependecy. Full dataset is not ready until each of them are completed (response received.)
	def process_single_result(self, x, spider):
		block_item = False
		if isinstance(spider, MarketSpider):
			accessor = SpiderAccessor(spider)
			if isinstance(x, Request):
				if 'user_rating_for' in x.meta:
					accessor.register_request_for_user_rating(x, x.meta['user_rating_for'])
				elif 'product_rating_for' in x.meta:
					accessor.register_request_for_product_rating(x, x.meta['product_rating_for'])
			elif isinstance(x, market_items.UserRating) or isinstance(x, market_items.ProductRating):
				accessor.hold_rating(x)
				block_item = True
		
		if not block_item:
			return x



