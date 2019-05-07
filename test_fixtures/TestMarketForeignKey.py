from TestTools import *

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

class TestMarketForeignKeys(unittest.TestCase):

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
		db.init(dbsetting)

	def test_process_scrape_deletion(self):
		market, process, scrape = self.create_market_process_scrape()
		market.save(force_insert=True)
		process.save(force_insert=True)
		scrape.save(force_insert=True)

		try:
			try:
				Scrape.get(id = scrape.id)
			except DoesNotExist as e:
				self.fail(str(e))

			process.delete_instance()
			with self.assertRaises(DoesNotExist):
				Scrape.get(id = scrape.id)

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(scrape, process, market)
			except:pass
			raise t, v, tb

		delete_all(scrape, process, market)

	## Make sure a scrape market is set to null when market is deleted
	def test_market_scrape_deletion(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)

			try:
				Scrape.get(id = scrape.id)
			except DoesNotExist as e:
				self.fail(str(e))

			market.delete_instance()

			try:
				Scrape.get(id = scrape.id)
			except DoesNotExist as e:
				self.fail(str(e))

			scrape2 = Scrape.get(id=scrape.id)
			with self.assertRaises(DoesNotExist):
				x = scrape2.market

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(scrape, process, market)
			except:pass
			raise t, v, tb

		delete_all(scrape, process, market)

	def test_scrape_scrapestat_deletion(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)

			scrapestat = ScrapeStat(scrape=scrape, logtime=random_datetime())
			scrapestat.save()

			try:
				ScrapeStat.get(id = scrapestat.id)
			except DoesNotExist as e:
				self.fail(str(e))

			scrape.delete_instance()
			with self.assertRaises(DoesNotExist):
				ScrapeStat.get(id = scrapestat.id)
			
		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(scrapestat, scrape, process, market)
			except:pass
			raise t, v, tb

		delete_all(scrapestat, scrape, process, market)






	################### Ads ##################### 
	def test_scrape_ads_deletion(self):
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
			propval = AdsProperty(key = propkey, owner = ads,scrape=scrape)
			propval.save(force_insert=True)

			try:
				AdsProperty.get(scrape=scrape)
			except DoesNotExist as e:
				self.fail(str(e))

			try:
				Ads.get(scrape=scrape)
			except DoesNotExist as e:
				self.fail(str(e))

			scrape.delete_instance()

			with self.assertRaises(DoesNotExist ):
				AdsProperty.get(scrape=scrape)

			with self.assertRaises(DoesNotExist ):
				Ads.get(scrape=scrape)

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(propval, propkey, ads, user, scrape,process,  market )
			except:pass
			raise t, v, tb

		delete_all(propval, propkey, ads, user, scrape,process,  market )


	def test_ads_propkey_ads_propval_deletion(self):
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
			propval = AdsProperty(key = propkey, owner = ads,scrape=scrape)
			propval.save(force_insert=True)

			try:
				AdsProperty.get(scrape=scrape, propkey=propkey)
			except DoesNotExist as e:
				self.fail(str(e))

			propkey.delete_instance()

			with self.assertRaises(DoesNotExist ):
				AdsProperty.get(scrape=scrape, propkey=propkey)

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(propval, propkey, ads, user, scrape,process,  market )
			except:pass
			raise t, v, tb

		delete_all(propval, propkey, ads, user, scrape,process,  market )

	#############################################

	######### Ads Feedback ###############

	def test_scrape_ads_feedback_deletion(self):
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
			propval = AdsFeedbackProperty(key = propkey, owner = ads_feedback,scrape=scrape)
			propval.save(force_insert=True)

			try:
				AdsFeedbackProperty.get(scrape=scrape)
			except DoesNotExist as e:
				self.fail(str(e))

			try:
				AdsFeedback.get(scrape=scrape)
			except DoesNotExist as e:
				self.fail(str(e))

			scrape.delete_instance()

			with self.assertRaises(DoesNotExist ):
				AdsFeedbackProperty.get(scrape=scrape)

			with self.assertRaises(DoesNotExist ):
				AdsFeedback.get(scrape=scrape)

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(propval, propkey, ads_feedback, ads, user, scrape,process,  market )
			except:pass
			raise t, v, tb

		delete_all(propval, propkey, ads_feedback, ads, user, scrape,process,  market )


	def test_ads_feedback_propkey_propval_deletion(self):
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
			propval = AdsFeedbackProperty(key = propkey, owner = ads_feedback,scrape=scrape)
			propval.save(force_insert=True)

			try:
				AdsFeedbackProperty.get(scrape=scrape, propkey=propkey)
			except DoesNotExist as e:
				self.fail(str(e))

			propkey.delete_instance()

			with self.assertRaises(DoesNotExist ):
				AdsFeedbackProperty.get(scrape=scrape, propkey=propkey)

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(propval, propkey, ads_feedback, ads, user, scrape,process,  market )
			except:pass
			raise t, v, tb

		delete_all(propval, propkey, ads_feedback, ads, user, scrape,process,  market )

####################################


	######### User ###############

	def test_scrape_user_deletion(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)

			user = User(market = market, scrape=scrape, username=randstring(100))
			user.save(force_insert=True)
		

			propkey = UserPropertyKey(name = randstring(50), prettyname=randstring(50))
			propkey.save(force_insert=True)
			propval = UserProperty(key = propkey, owner = user,scrape=scrape)
			propval.save(force_insert=True)

			try:
				UserProperty.get(scrape=scrape)
			except DoesNotExist as e:
				self.fail(str(e))

			try:
				User.get(scrape=scrape)
			except DoesNotExist as e:
				self.fail(str(e))

			scrape.delete_instance()

			with self.assertRaises(DoesNotExist ):
				UserProperty.get(scrape=scrape)

			with self.assertRaises(DoesNotExist ):
				User.get(scrape=scrape)

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(propval, propkey,  user, scrape,process,  market )
			except:pass
			raise t, v, tb

		delete_all(propval, propkey,  user, scrape,process,  market )

	def test_user_propkey_propval_deletion(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)

			user = User(market = market, scrape=scrape, username=randstring(100))
			user.save(force_insert=True)
		

			propkey = UserPropertyKey(name = randstring(50), prettyname=randstring(50))
			propkey.save(force_insert=True)
			propval = UserProperty(key = propkey, owner = user,scrape=scrape)
			propval.save(force_insert=True)

			try:
				UserProperty.get(scrape=scrape, propkey=propkey)
			except DoesNotExist as e:
				self.fail(str(e))

			propkey.delete_instance()

			with self.assertRaises(DoesNotExist ):
				UserProperty.get(scrape=scrape, propkey=propkey)

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(propval, propkey,  user, scrape,process,  market )
			except:pass
			raise t, v, tb

		delete_all(propval, propkey,  user, scrape,process,  market )		

####################################


	######### Seller Feedback ###############

	def test_scrape_seller_feedback_deletion(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)

			user = User(market = market, scrape=scrape, username=randstring(100))
			user.save(force_insert=True)
			ads = Ads(market = market, scrape=scrape, seller=user, title=randstring(20))
			ads.save(force_insert=True)
			seller_feedback = SellerFeedback(market = market, scrape=scrape, ads=ads)
			seller_feedback.save(force_insert=True)

			propkey = SellerFeedbackPropertyKey(name = randstring(50), prettyname=randstring(50))
			propkey.save(force_insert=True)
			propval = SellerFeedbackProperty(key = propkey, owner = seller_feedback,scrape=scrape)
			propval.save(force_insert=True)

			try:
				SellerFeedbackProperty.get(scrape=scrape)
			except DoesNotExist as e:
				self.fail(str(e))

			try:
				SellerFeedback.get(scrape=scrape)
			except DoesNotExist as e:
				self.fail(str(e))

			scrape.delete_instance()

			with self.assertRaises(DoesNotExist ):
				SellerFeedbackProperty.get(scrape=scrape)

			with self.assertRaises(DoesNotExist ):
				SellerFeedback.get(scrape=scrape)

		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(propval, propkey, seller_feedback, ads, user, scrape,process,  market )
			except:pass
			raise t, v, tb

		delete_all(propval, propkey, seller_feedback, ads, user, scrape,process,  market )

	def test_seller_feedback_propkey_propval_deletion(self):
		try:
			market, process, scrape = self.create_market_process_scrape()
			market.save(force_insert=True)
			process.save(force_insert=True)
			scrape.save(force_insert=True)

			user = User(market = market, scrape=scrape, username=randstring(100))
			user.save(force_insert=True)
			ads = Ads(market = market, scrape=scrape, seller=user, title=randstring(20))
			ads.save(force_insert=True)
			seller_feedback = SellerFeedback(market = market, scrape=scrape, ads=ads)
			seller_feedback.save(force_insert=True)

			propkey = SellerFeedbackPropertyKey(name = randstring(50), prettyname=randstring(50))
			propkey.save(force_insert=True)
			propval = SellerFeedbackProperty(key = propkey, owner = seller_feedback,scrape=scrape)
			propval.save(force_insert=True)

			try:
				SellerFeedbackProperty.get(scrape=scrape)
			except DoesNotExist as e:
				self.fail(str(e))

			propkey.delete_instance()

			with self.assertRaises(DoesNotExist ):
				SellerFeedbackProperty.get(scrape=scrape)


		except :
			t, v, tb = sys.exc_info()
			try:
				delete_all(propval, propkey, seller_feedback, ads, user, scrape,process,  market )
			except:pass
			raise t, v, tb

		delete_all(propval, propkey, seller_feedback, ads, user, scrape,process,  market )		

####################################





