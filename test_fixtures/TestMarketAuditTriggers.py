import sys
import random
import string
import unittest
from datetime import datetime, timedelta
from scrapyprj.database import db
from scrapyprj.database.settings import markets as dbsetting
from scrapyprj.database.markets.orm.models import *
from IPython import embed
from TestTools import *

class TestMarketModels(unittest.TestCase):

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


	def setUp(self):
		db.init(dbsetting)


	def test_user_propval_audit(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)

			user = User(market = market, scrape=scrape, username=randstring(100))
			user.save(force_insert=True)
			
			propkey = UserPropertyKey(name = randstring(50), prettyname=randstring(50))
			propkey.save(force_insert=True)
			propval = UserProperty(key = propkey, owner = user,scrape=scrape,data=randstring(1000), modified_on=random_datetime())
			propval.save(force_insert=True)


			with self.assertRaises(DoesNotExist ):
				UserPropertyAudit.get(user=user)

			propval.data= randstring(1000);
			propval.save()
			
			try:
				propvalaudit = UserPropertyAudit.get(user=user)

				self.assertEqual(propval.modified_on, propvalaudit.modified_on)

				propvalaudit.delete_instance()
			except DoesNotExist as e:
				self.fail(str(e))

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(propval, propkey, user, scrape,process,  market )
			except:pass
			raise t, v, tb

		delete_all(propval, propkey, user, scrape,process,  market )


	def test_ads_propval_audit(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)

			user = User(market = market, scrape=scrape, username=randstring(100))
			user.save(force_insert=True)
			ads = Ads(market = market, scrape=scrape, seller=user, title=randstring(20))
			ads.save(force_insert=True)
			propkey = AdsPropertyKey(name = randstring(50), prettyname=randstring(50))
			propkey.save(force_insert=True)
			propval = AdsProperty(key = propkey, owner = ads,scrape=scrape,data=randstring(1000), modified_on=random_datetime())
			propval.save(force_insert=True)


			with self.assertRaises(DoesNotExist ):
				AdsPropertyAudit.get(ads=ads)

			propval.data= randstring(1000);
			propval.save()
			
			try:
				propvalaudit = AdsPropertyAudit.get(ads=ads)

				self.assertEqual(propval.modified_on, propvalaudit.modified_on)

				propvalaudit.delete_instance()
			except DoesNotExist as e:
				self.fail(str(e))

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(propval, propkey, ads, user, scrape,process,  market )
			except:pass
			raise t, v, tb

		delete_all(propval, propkey, ads, user, scrape,process,  market )


	def test_ads_feedback_propval_audit(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)

			user = User(market = market, scrape=scrape, username=randstring(100))
			user.save(force_insert=True)
			ads = Ads(market = market, scrape=scrape, seller=user, title=randstring(20))
			ads.save(force_insert=True)

			ads_feedback = AdsFeedback(market = market, scrape=scrape, ads=ads)
			ads_feedback.save(force_insert=True)

			propkey = AdsFeedbackPropertyKey(name = randstring(50), prettyname=randstring(50))
			propkey.save(force_insert=True)
			propval = AdsFeedbackProperty(key = propkey, owner = ads_feedback, scrape=scrape, data=randstring(1000), modified_on=random_datetime())
			propval.save(force_insert=True)


			with self.assertRaises(DoesNotExist ):
				AdsFeedbackPropertyAudit.get(feedback=ads_feedback)

			propval.data= randstring(1000);
			propval.save()
			
			try:
				propvalaudit = AdsFeedbackPropertyAudit.get(feedback=ads_feedback)

				self.assertEqual(propval.modified_on, propvalaudit.modified_on)
				propvalaudit.delete_instance()
			except DoesNotExist as e:
				self.fail(str(e))

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(propval, propkey, ads_feedback, ads, user, scrape,process,  market )
			except:pass
			raise t, v, tb

		delete_all(propval, propkey, ads_feedback, ads, user, scrape,process,  market )		


	def test_seller_feedback_propval_audit(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)

			user = User(market = market, scrape=scrape, username=randstring(100))
			user.save(force_insert=True)

			seller_feedback = SellerFeedback(market = market, scrape=scrape, seller=user)
			seller_feedback.save(force_insert=True)

			propkey = SellerFeedbackPropertyKey(name = randstring(50), prettyname=randstring(50))
			propkey.save(force_insert=True)
			propval = SellerFeedbackProperty(key = propkey, owner = seller_feedback, scrape=scrape, data=randstring(1000), modified_on=random_datetime())
			propval.save(force_insert=True)


			with self.assertRaises(DoesNotExist ):
				SellerFeedbackPropertyAudit.get(feedback=seller_feedback)

			propval.data= randstring(1000);
			propval.save()
			
			try:
				propvalaudit = SellerFeedbackPropertyAudit.get(feedback=seller_feedback)

				self.assertEqual(propval.modified_on, propvalaudit.modified_on)
				propvalaudit.delete_instance()
			except DoesNotExist as e:
				self.fail(str(e))

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(propval, propkey, seller_feedback,  user, scrape,process,  market )
			except:pass
			raise t, v, tb

		delete_all(propval, propkey, seller_feedback, user, scrape,process,  market )				