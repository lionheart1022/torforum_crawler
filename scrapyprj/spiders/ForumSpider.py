import scrapy
from scrapy import signals
from peewee import *
from scrapyprj.database.forums.orm.models import *
from datetime import datetime
from scrapyprj.database.settings import forums as dbsettings
from scrapyprj.database.dao import DatabaseDAO
from scrapyprj.database import db
from scrapyprj.spiders.BaseSpider import BaseSpider
from scrapy.exceptions import DontCloseSpider
from scrapyprj.middlewares.replay_spider_middleware import ReplaySpiderMiddleware

import os, time, sys
from dateutil import parser
from scrapy import signals
from Queue import Queue
import itertools as it

from twisted.internet import reactor
from scrapy.dupefilters import RFPDupeFilter
from Queue import PriorityQueue
from IPython import embed
import json
import profiler

class ForumSpider(BaseSpider):
	
	def __init__(self, *args, **kwargs):
		super(ForumSpider, self).__init__( *args, **kwargs)
		self._baseclass = ForumSpider

		self.configure_request_sharing()

		db.init(dbsettings)
		if 'dao' in kwargs:
			self.dao = kwargs['dao']
		else:
			self.dao = self.make_dao()
						

		self.set_timezone()

		try:
			self.forum = Forum.get(spider=self.name)
		except:
			raise Exception("No forum entry exist in the database for spider " + self.name)

		if not hasattr(self._baseclass, '_cache_preloaded') or not self._baseclass._cache_preloaded:
			self.dao.cache.reload(User, User.forum == self.forum)
			self.dao.cache.reload(Thread, Thread.forum == self.forum)
			self._baseclass._cache_preloaded = True

		self.request_after_manual_input = None
		self.register_new_scrape()
		self.start_statistics()
		self.manual_input = None
		

	@classmethod
	def from_crawler(cls, crawler, *args, **kwargs):
		spider = cls(*args, settings = crawler.settings,**kwargs)
		spider.crawler = crawler
		crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
		crawler.signals.connect(spider.spider_idle, signal=signals.spider_idle)			# We will fetch some users/thread that we need to re-read from the database.

		return spider

	@classmethod
	def make_dao(cls):
		donotcache = [Message, UserProperty]

		dao = DatabaseDAO(cacheconfig='forums', donotcache=donotcache)
		dao.add_dependencies(Message, [Thread])
		return 	dao

	def configure_request_sharing(self):
		if not hasattr(self._baseclass, '_queue_size'):
			self._baseclass._queue_size = 0

		if not hasattr(self._baseclass, 'shared_dupefilter'):
			self._baseclass.shared_dupefilter = RFPDupeFilter.from_settings(self.settings)

		if not hasattr(self._baseclass, '_request_queue'):
			self._baseclass._request_queue = PriorityQueue()

		if not hasattr(self, 'request_queue_chunk'):
			self.request_queue_chunk = 100

	def enqueue_request(self, request):
		if hasattr(request, 'dont_filter') and request.dont_filter or not self._baseclass.shared_dupefilter.request_seen(request):
			self._baseclass._queue_size += 1
			self._baseclass._request_queue.put( (-request.priority, request)  )	# Priority is inverted. High priority go first for scrapy. Low Priority go first for queue
		else:
			self._baseclass.shared_dupefilter.log(request, self)

	def consume_request(self, n):
		i = 0

		while i<n and not self._baseclass._request_queue.empty():
			priority, request = self._baseclass._request_queue.get()
			self._baseclass._queue_size -= 1
			yield request
			i += 1

	# When Spider is idle, this callback is called.
	def spider_idle(self, spider):
		spider.logger.debug("IDLE")
		scheduled_request = False
		
		if hasattr(self, ReplaySpiderMiddleware.SPIDER_ATTRIBUTE):
			replay_mw = getattr(self, ReplaySpiderMiddleware.SPIDER_ATTRIBUTE)
			replay_remaining_request = replay_mw.pop_remaining_replay_request(spider)
			if replay_remaining_request is not None:
				self.crawler.engine.crawl(replay_remaining_request, spider)
				scheduled_request = True
				
		newinput = self.look_for_new_input()

		if newinput and self.request_after_manual_input:
			self.crawler.engine.crawl(self.request_after_manual_input, spider)
		else:
			if not self.manual_input:
				spider.logger.debug('%s/%s Idle. Queue Size = %d' % (self._proxy_key, self._loginkey, self._baseclass._queue_size))
				for req in self.consume_request(self.request_queue_chunk):
					self.crawler.engine.crawl(req, spider)
					scheduled_request = True

			if scheduled_request or self.manual_input or self.still_active():		# manual_input is None if not waiting for cookies
				raise DontCloseSpider()	


	#Called by Scrapy Engine when spider is closed	
	def spider_closed(self, spider, reason):
		self.scrape.end = datetime.utcnow();
		self.scrape.reason = reason
		self.scrape.save()

		if self.process_created:
			self.process.end = datetime.utcnow()
			self.process.save()

		if self.savestat_taskid:
			self.savestat_taskid.cancel()
		self.savestats()
		
		BaseSpider.spider_closed(self, spider, reason)

	# Insert a database entry for this scrape.
	def register_new_scrape(self):
		self.process_created=False 	# Indicates that this spider created the process entry. Will be responsible of adding end date
		if not hasattr(self, 'process'):	# Can be created by a script and passed to the constructor
			self.process = Process()
			self.process.start = datetime.utcnow()
			self.process.pid = os.getpid()
			self.process.cmdline = ' '.join(sys.argv)
			self.process.save()
			self.process_created = True

		self.scrape 				= Scrape();	# Create the new Scrape in the databse.
		self.scrape.start 			= datetime.utcnow()
		self.scrape.process 		= self.process
		self.scrape.forum 			= self.forum
		self.scrape.login 			= self._loginkey
		self.scrape.proxy 			= self._proxy_key
		self.scrape.save();		


	def start_statistics(self):
		self.statsinterval = 30
		self.ramreader = profiler.get_profiler('ram_reader')	# Get a profiler jsut to read ram usage
		self.ramreader.enable() # Override Config for this specific profiler.

		if 'statsinterval' in self.settings:
			self.statsinterval = int(self.settings['statsinterval'])

		self.savestats_handler()	

	def savestats(self):
		stat = ScrapeStat(scrape=self.scrape)

		stats_data = self.dao.get_stats(self)

		ram_usage 	= self.ramreader.get_usage()	
		stat.ram_usage			= ram_usage	if ram_usage else 0

		stat.thread 			= stats_data[Thread] 			if Thread 			in stats_data else 0
		stat.message 			= stats_data[Message] 			if Message 			in stats_data else 0
		stat.message_propval 	= stats_data[MessageProperty] 	if MessageProperty 	in stats_data else 0
		stat.user 				= stats_data[User] 				if User 			in stats_data else 0
		stat.user_propval 		= stats_data[UserProperty] 		if UserProperty 	in stats_data else 0

		stat.request_sent 		= self.crawler.stats.get_value('downloader/request_count') 	or 0 if hasattr(self, 'crawler') else 0
		stat.request_bytes 		= self.crawler.stats.get_value('downloader/request_bytes') 	or 0 if hasattr(self, 'crawler') else 0
		stat.response_received 	= self.crawler.stats.get_value('downloader/response_count') or 0 if hasattr(self, 'crawler') else 0
		stat.response_bytes 	= self.crawler.stats.get_value('downloader/response_bytes') or 0 if hasattr(self, 'crawler') else 0
		stat.item_scraped 		= self.crawler.stats.get_value('item_scraped_count') 		or 0 if hasattr(self, 'crawler') else 0
		stat.item_dropped 		= self.crawler.stats.get_value('item_dropped_count') 		or 0 if hasattr(self, 'crawler') else 0

		stat.save()

	def savestats_handler(self):
		self.savestat_taskid = None
		self.savestats()
		self.savestat_taskid = reactor.callLater(self.statsinterval, self.savestats_handler)



	def wait_for_input(self, details, request_once_done=None):
		self.logger.warning("Waiting for manual input from database")

		self.request_after_manual_input = request_once_done

		self.manual_input					= ManualInput()
		self.manual_input.date_requested 	= datetime.utcnow()
		self.manual_input.spidername		= self.name
		self.manual_input.proxy 			= self._proxy_key
		self.manual_input.login 			= self._loginkey
		self.manual_input.login_info 		= json.dumps(self.login)
		self.manual_input.user_agent 		= self.user_agent
		self.manual_input.cookies 			= self.get_cookies()
		self.manual_input.reload 			= False
		self.manual_input.save(force_insert=True)
		
		subject = "Spider crawling forum %s needs inputs. Id = %d" % (self.forum.name, self.manual_input.id)

		msg 	= """
			Spider crawling forum %s has requested new input to continue crawling.

			Configuration : 
				- Proxy : %s 
				- Login : %s 
				- Login Info : %s
				- User agent : %s
				- Cookies : %s
			
			Details : %s

			Please, go insert relevant data string in database for manual input id=%d.
			*** You can modify : proxy, login, user agent, cookies
			""" % (
				self.forum.name, 
				self.manual_input.proxy, 
				self.manual_input.login, 
				self.manual_input.login_info, 
				self.manual_input.user_agent ,
				self.manual_input.cookies , 
				details, 
				self.manual_input.id
				)
		try:
			self.send_mail(subject, msg)
		except Exception, e:
			self.logger.error('Could not send email telling that we are waiting for input : %s' % e)


	def look_for_new_input(self):
		new_input = False
		if self.manual_input:
			
			new_manual_input = ManualInput.get(self.manual_input._pk_expr())	# Reload from database
			
			if new_manual_input.reload:
				self.logger.info("New input given! Continuing")
				error = False
				try:
					if new_manual_input.proxy != self._proxy_key:
						self.configure_proxy(new_manual_input.proxy)

					if new_manual_input.login != self._loginkey:
						self.configure_login(new_manual_input.login)

					if new_manual_input.cookies:
						self.set_cookies(new_manual_input.cookies)
					
					if new_manual_input.user_agent:
						self.user_agent
				except Exception, e:
					self.logger.error("Could not reload new data. %s" % e)
					error = True
				
				if error:
					self.manual_input.save()
				else:
					self.manual_input = None
					new_input = True
				new_manual_input.delete_instance()
			else:
				self.logger.debug('No new input given by database.')
		return new_input

	def get_shared_data_struct(self):
		return self._baseclass			