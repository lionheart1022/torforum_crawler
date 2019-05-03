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
	

class TestMarketProvals(unittest.TestCase):

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

	def test_user_propval(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)


			user_propkey = UserPropertyKey(name=randstring(30), prettyname=randstring(30))
			user_propkey.save(force_insert=True)
			User.reset_keys()
			
			user 	= User(market = market, scrape=scrape, username=randstring(50))
			data = randstring(100)
			setattr(user, user_propkey.name, data)

			self.assertEqual(len(user.getproperties()),1)
			propval = user.getproperties()[0]
			self.assertEqual(propval.data, data)


			user.setproperties_attribute(scrape = scrape)
			self.dao.enqueue(user)
			self.dao.flush(User)

			userpropval2 = UserProperty.get(key=user_propkey, owner=user)

			self.assertEqual(propval.data, userpropval2.data)

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(user, user_propkey, scrape, process, market)
			except:pass
			raise t, v, tb

		delete_all(user, user_propkey, scrape, process, market)

	def test_ads_propval(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)


			ads_propkey = AdsPropertyKey(name=randstring(30), prettyname=randstring(30))
			ads_propkey.save(force_insert=True)
			Ads.reset_keys()
			
			ads 	= Ads(market=market, scrape=scrape, external_id=randstring(50), title=randstring(50))
			data = randstring(100)
			setattr(ads, ads_propkey.name, data)

			self.assertEqual(len(ads.getproperties()),1)
			propval = ads.getproperties()[0]
			self.assertEqual(propval.data, data)


			ads.setproperties_attribute(scrape = scrape)
			self.dao.enqueue(ads)
			self.dao.flush(Ads)

			adspropval = AdsProperty.get(key=ads_propkey, owner=ads)

			self.assertEqual(propval.data, adspropval.data)

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(ads, ads_propkey, scrape, process, market)
			except:pass
			raise t, v, tb

		delete_all(ads, ads_propkey, scrape, process, market)


	def test_ads_feedback_propval(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)


			adsfb_propkey = AdsFeedbackPropertyKey(name=randstring(30), prettyname=randstring(30))
			adsfb_propkey.save(force_insert=True)
			AdsFeedback.reset_keys()
			
			ads 			= Ads(market=market, scrape=scrape, external_id=randstring(50), title=randstring(50))
			ads_feedback 	= AdsFeedback(market=market, scrape=scrape, ads=ads, external_id=randstring(50), hash=randstring(64))
			ads.save(force_insert=True)
			ads_feedback.save(force_insert=True) # Will retrieve a unique ID for caching as there is no other unique key
			data = randstring(100)
			setattr(ads_feedback, adsfb_propkey.name, data)

			self.assertEqual(len(ads_feedback.getproperties()),1)
			propval = ads_feedback.getproperties()[0]
			self.assertEqual(propval.data, data)


			ads_feedback.setproperties_attribute(scrape = scrape)
			self.dao.enqueue(ads_feedback)
			self.dao.flush(AdsFeedback)
			adsfb_propval = AdsFeedbackProperty.get(key=adsfb_propkey, owner=ads_feedback)

			self.assertEqual(propval.data, adsfb_propval.data)

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(ads_feedback, ads, adsfb_propkey, scrape, process, market)
			except:pass
			raise t, v, tb

		delete_all(ads_feedback, ads, adsfb_propkey, scrape, process, market)


	def test_seller_feedback_propval(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)

			sellerfb_propkey = SellerFeedbackPropertyKey(name=randstring(30), prettyname=randstring(30))
			sellerfb_propkey.save(force_insert=True)
			SellerFeedback.reset_keys()
			
			user 	= User(market = market, scrape=scrape, username=randstring(50))
			seller_feedback 	= SellerFeedback(market=market, scrape=scrape, seller=user, external_id=randstring(50), hash=randstring(64))
			
			user.save(force_insert=True) 
			seller_feedback.save(force_insert=True) # That will generate a unique ID. Otherwise, we can't cache this object as there is no other unique key
			data = randstring(100)
			setattr(seller_feedback, sellerfb_propkey.name, data)

			self.assertEqual(len(seller_feedback.getproperties()),1)
			propval = seller_feedback.getproperties()[0]
			self.assertEqual(propval.data, data)


			seller_feedback.setproperties_attribute(scrape = scrape)
			self.dao.enqueue(seller_feedback)
			self.dao.flush(SellerFeedback)

			sellerfb_propval = SellerFeedbackProperty.get(key=sellerfb_propkey, owner=seller_feedback)

			self.assertEqual(propval.data, sellerfb_propval.data)

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(seller_feedback, user, sellerfb_propkey, scrape, process, market)
			except:pass
			raise t, v, tb

		delete_all(seller_feedback, user, sellerfb_propkey, scrape, process, market)		





