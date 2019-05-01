import random
import string
import unittest
import scrapy
from datetime import datetime, timedelta
from scrapyprj.database import db
from scrapyprj.database.settings import markets as dbsetting
from scrapyprj.database.markets.orm.models import *
from IPython import embed
from TestTools import *
from scrapyprj.database.dao import DatabaseDAO
import sys
import logging
from scrapy.utils.log import configure_logging



class MockedSpider(scrapy.Spider):
	name = 'mocked_spider'
	

class TestDao(unittest.TestCase):

	def create_market(self):
		return Market(name=randstring(50), spider=randstring(50))

	def create_process(self):
		return Process(start=random_datetime(), end=random_datetime(), pid=random.randint(0,9999999), cmdline = randstring(100))

	def create_scrape(self, market, process):
		return Scrape(process=process, market=market, start=random_datetime(), end=random_datetime(), reason=randstring(100), login=randstring(100), proxy=randstring(100))

	def create_market_process_scrape(self):
		market = self.create_market()
		process = self.create_process()
		scrape = self.create_scrape(market, process)

		return (market, process, scrape)


######################################
	def setUp(self):
		configure_logging(install_root_handler=False)
		logging.basicConfig(
		    format='%(levelname)s: %(message)s',
		    level=logging.INFO
		)
		self.spider = MockedSpider();

		self.dao = DatabaseDAO('markets')
		db.init(dbsetting)


	def test_queue_save(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)

			user1 = User(market = market, scrape=scrape, username=randstring(50))
			user2 = User(market = market, scrape=scrape, username=randstring(50))
			user3 = User(market = market, scrape=scrape, username=randstring(50))
			

			self.dao.enqueue(user1)
			self.dao.enqueue(user2)
			self.dao.enqueue(user3)

			with self.assertRaises(DoesNotExist ):
				User.get(id=user1.id)

			with self.assertRaises(DoesNotExist ):
				User.get(id=user2.id)

			with self.assertRaises(DoesNotExist ):
				User.get(id=user3.id)

			self.dao.flush(User)
			
			user1x = User.get(id=user1.id)
			user2x = User.get(id=user2.id)
			user3x = User.get(id=user3.id)

			self.assertEqual(user1.id, user1x.id)
			self.assertEqual(user2.id, user2x.id)
			self.assertEqual(user3.id, user3x.id)
		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(user1, user2, user3, scrape, process,  market)
			except:pass
			raise t, v, tb

		delete_all(user1, user2, user3, scrape, process,  market)

	def test_market_config(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)

			user 	= User(market = market, scrape=scrape, username=randstring(50))
			ads 	= Ads(market=market, scrape=scrape, external_id=randstring(50), title=randstring(50))
			captchaquestion = CaptchaQuestion(market=market, hash=randstring(50))
			ads_fb = AdsFeedback(market=market, ads=ads, scrape=scrape, external_id=randstring(50), hash=randstring(64))
			seller_fb = SellerFeedback(market=market, scrape=scrape, seller=user, external_id=randstring(50), hash=randstring(64))

			self.dao.enqueue(user)
			with self.assertRaises(DoesNotExist ):
				User.get(id=user.id)
			self.dao.flush(User)
			user2 = User.get(id=user.id)
			self.assertEqual(user.id, user2.id)

			self.dao.enqueue(ads)
			with self.assertRaises(DoesNotExist ):
				Ads.get(id=ads.id)
			self.dao.flush(Ads)
			ads2 = Ads.get(id=ads.id)
			self.assertEqual(ads.id, ads2.id)
			
			self.dao.enqueue(captchaquestion)
			with self.assertRaises(DoesNotExist ):
				CaptchaQuestion.get(id=captchaquestion.id)
			self.dao.flush(CaptchaQuestion)
			captchaquestion2 = CaptchaQuestion.get(id=captchaquestion.id)
			self.assertEqual(captchaquestion.id, captchaquestion2.id)

			with self.assertRaises(DoesNotExist ):
				AdsFeedback.get(id=ads_fb.id)
			ads_fb.save(force_insert=True)
			
			self.dao.enqueue(ads_fb)
			self.dao.flush(AdsFeedback)
			ads_fb2 = AdsFeedback.get(id=ads_fb.id)
			self.assertEqual(ads_fb.id, ads_fb2.id)

			with self.assertRaises(DoesNotExist ):
				SellerFeedback.get(id=seller_fb.id)
			seller_fb.save(force_insert = True) # We save because no usable unique key for caching. We'll use primary key
			self.dao.enqueue(seller_fb)
			self.dao.flush(SellerFeedback)
			seller_fb2 = SellerFeedback.get(id=seller_fb.id)
			self.assertEqual(seller_fb.id, seller_fb2.id)						


		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(user, ads, captchaquestion, ads_fb, seller_fb,  scrape, process, market)
			except:pass
			raise t, v, tb

		delete_all(user, ads, captchaquestion, ads_fb, seller_fb,  scrape, process, market)


