from scrapy.exceptions import DropItem
import scrapyprj.items.forum_items as forum_items
import scrapyprj.items.market_items as market_items
import scrapyprj.database.forums.orm.models as forum_models
import scrapyprj.database.markets.orm.models as market_models
from IPython import embed
import hashlib

# This pipeline stages convert items to its equivalent PeeWee ORM model.
# We also ensure the integrity of data and respect of foreign key before sending that to the Database DAO queue.

class map2db(object):
	def __init__(self, *args, **kwargs):
		super(self.__class__, self).__init__(*args, **kwargs)

		self.forum_mapper = ForumMapper()
		self.market_mapper = MarketMapper()

		# For each item type, what function does the conversion
		self.handlers = {
			forum_items.Thread 		: self.forum_mapper.map_thread,
			forum_items.Message 	: self.forum_mapper.map_message,
			forum_items.User 		: self.forum_mapper.map_user,
			market_items.Ads 		: self.market_mapper.map_ads,
			market_items.AdsImage 	: self.market_mapper.map_adsimage,
			market_items.User 		: self.market_mapper.map_user,
			market_items.ProductRating 	: self.market_mapper.map_product_rating,
			market_items.UserRating 	: self.market_mapper.map_user_rating
		}

	# What is actually called by Scrapy
	def process_item(self, item, spider):
		for item_type in self.handlers.keys():
			if item_type == type(item):
				return {'model' : self.handlers[item_type].__call__(item,spider), 'item' : item}	#Scrapy don't like PeeWee models, but likes dict.
		
		raise Exception('Unknown item type : %s' % item.__class__.__name__)


class BaseMapper:
	def set_if_exist(self, item, model, field):		# Mainly used for propval/propkey
		if field in item:
			if isinstance(item[field], basestring):
				item[field]  = self.make_utf8(item[field])
			model.__setattr__(field, item[field])

	def drop_if_missign(self, item, field):
		if field not in item:
			raise DropItem("Missing %s in %s" % (field, item))

	def drop_if_empty(self, item, field):
		self.drop_if_missign(item, field)
		
		if not item[field]:
			raise DropItem("Empty %s in %s" % (field, item))

	def make_utf8(self, text):
		try:
			if not isinstance(text, basestring):
				text = str(text)

			if isinstance(text, unicode):
				text = text.encode('utf-8', 'ignore')	# Encode in UTF-8 and remove unknown char.
			else:
				text = text.decode('utf-8', 'ignore').encode('utf-8', 'ignore')
		except:
			# Some hand crafted characters can throw an exception. Remove them silently.
			text = text.encode('cp1252', 'ignore').decode('utf-8','ignore') # Remove non-utf8 chars. 

		return text



class ForumMapper(BaseMapper):
	def map_thread(self, item, spider):
		if type(item) != forum_items.Thread:
			raise Exception("Expecting an item of type forum_items.Thread. Got : " + type(item).__name__ )

		dbthread = forum_models.Thread()

		self.drop_if_empty(item, 'title')
		self.drop_if_empty(item, 'threadid')
		

		dbthread.forum 		= spider.forum
		dbthread.scrape 	= spider.scrape
		dbthread.title 		= self.make_utf8(item['title'])
		dbthread.external_id= self.make_utf8(item['threadid'])
		dbthread.author = spider.dao.get_or_create(forum_models.User,  username= item['author_username'], forum=spider.forum) # Unique key here
		dbthread.scrape = spider.scrape

		if 'scrape' not in dbthread.author._data or not dbthread.author._data['scrape']: # This could be optimized to be created in get or create above, but that would imply quite a lot of work.
			dbthread.author.scrape=spider.scrape
			dbthread.author.save()


		for key in item:
			if key not in ['title','threadid','author_username']:
				self.set_if_exist(item, dbthread, key)

		if not dbthread.author:
			raise DropItem("Invalid Thread : Unable to get User from database. Cannot respect foreign key constraint.")
		elif not dbthread.author.id :
			raise DropItem("Invalid Thread : User foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")

		return dbthread


	def map_message(self, item, spider):
		if type(item) != forum_items.Message:
			raise Exception("Expecting an item of type forum_items.Message. Got : " + type(item).__name__ )

		dbmsg = forum_models.Message()

		self.drop_if_empty(item, 'author_username')
		self.drop_if_missign(item, 'contenttext')
		self.drop_if_empty(item, 'contenthtml')
		self.drop_if_empty(item, 'threadid')
		self.drop_if_empty(item, 'postid')

		dbmsg.thread = spider.dao.get(forum_models.Thread, forum =spider.forum, external_id = item['threadid'])	#Thread should exist in database
		if not dbmsg.thread:
			raise DropItem("Invalid Message : Unable to get Thread from database. Cannot respect foreign key constraint.")
		elif not dbmsg.thread.id :
			raise DropItem("Invalid Message : Thread foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")

		dbmsg.forum 	= dbmsg.thread.forum
		dbmsg.scrape 	= spider.scrape
		dbmsg.author 	= spider.dao.get_or_create(forum_models.User, username= item['author_username'], forum=spider.forum) # Make sur only unique key in constructor
		dbmsg.scrape	= spider.scrape
		if 'scrape' not in dbmsg.author._data or not dbmsg.author._data['scrape']: # This could be optimized to be created in get or create above, but that would imply quite a lot of work.
			dbmsg.author.scrape=spider.scrape
			dbmsg.author.save()

		if not dbmsg.author:
			raise DropItem("Invalid Message : Unable to get User from database. Cannot respect foreign key constraint.")
		elif not dbmsg.author.id : # If this happens. Either data is not flush or bug.
			raise DropItem("Invalid Message : Author foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")

		for key in item:
			if key not in ['username']:
				self.set_if_exist(item, dbmsg, key)

		dbmsg.external_id = self.make_utf8(item['postid']	)
		dbmsg.contenttext = self.make_utf8(item['contenttext'])
		dbmsg.contenthtml = self.make_utf8(item['contenthtml'])

		for key in item:
			if key not in ['author_username','contenttext','contenthtml','threadid','postid']:
				self.set_if_exist(item, dbmsg, key)
		
		return dbmsg

	def map_user(self, item, spider):
		self.drop_if_empty(item, 'username')

		dbuser = forum_models.User()	# Extended PeeWee object that handles properties in different table
		dbuser.username = self.make_utf8(item['username'])
		
		dbuser.forum 	= spider.forum
		dbuser.scrape 	= spider.scrape

		dbuser.setproperties_attribute(scrape = spider.scrape)  #propagate the scrape id to the UserProperty model.

		#Proeprties with same name in model and item

		for key in item:
			if key not in ['username']:
				self.set_if_exist(item, dbuser, key)
		
		return dbuser


class MarketMapper(BaseMapper):
	def map_ads(self, item, spider):
		if type(item) != market_items.Ads:
			raise Exception("Expecting an item of type items.Ads. Got : " + type(item).__name__ )

		dbads = market_models.Ads()

		#Validation of data.
		self.drop_if_empty(item, 'title')
		self.drop_if_empty(item, 'offer_id')

		#Direct Mapping
		dbads.market 		= spider.market
		dbads.scrape 		= spider.scrape
		dbads.title 		= self.make_utf8(item['title'])
		dbads.external_id	= self.make_utf8(item['offer_id'])

		# Link the thread with the user. Request the database (or caching system) to get auto-incremented id.
		try:
			dbads.seller = spider.dao.get(market_models.User,  username= item['vendor_username'], market=spider.market) 	# Unique key here
		except market_models.User.DoesNotExist as e:
			dbads.seller = spider.dao.get_or_create(market_models.User,  username= item['vendor_username'], market=spider.market, scrape=spider.scrape) 	# Unique key here
		dbads.scrape = spider.scrape
		
		if 'scrape' not in dbads.seller._data or not dbads.seller._data['scrape']: # This could be optimized to be created in get or create above, but that would imply quite a lot of work.
			dbads.seller.scrape=spider.scrape
			dbads.seller.save()
		
		if not dbads.seller:
			raise DropItem("Invalid Ads : Unable to get User from database. Cannot respect foreign key constraint.")
		elif not dbads.seller.id :
			raise DropItem("Invalid Ads : User foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")


		for key in item:
			if key not in ['title', 'offer_id']:
				self.set_if_exist(item, dbads, key)

		dbads.setproperties_attribute(scrape = spider.scrape)


		return dbads	# This object represent a table row. Once it is returned, nothing else should be done.


	def map_adsimage(self, item, spider):
		imgs = []
		for image in item['images']:
			dbimg 			= market_models.AdsImage()
			ads_id = self.make_utf8(item['ads_id'])
			try:
				dbimg.ads 		= spider.dao.get(market_models.Ads, external_id = ads_id, market = spider.market)
			except market_models.Ads.DoesNotExist as e:
			 	raise DropItem("Invalid Ads Image : Unable to get Ads from database. Cannot respect foreign key constraint.")
			 	
			dbimg.path 		= image['path']
			dbimg.hash 		= image['checksum']
			dbimg.scrape 	= spider.scrape

			imgs.append(dbimg)

		return imgs

	def map_user(self, item, spider):
		self.drop_if_empty(item, 'username')

		dbuser = market_models.User()	# Extended PeeWee object that handles properties in different table
		dbuser.username = item['username']
		
		dbuser.market = spider.market
		dbuser.scrape = spider.scrape
		dbuser.setproperties_attribute(scrape = spider.scrape)  #propagate the scrape id to the UserProperty model.

		for key in item:
			if key not in ['username']:
				self.set_if_exist(item, dbuser, key)

		return dbuser

	def map_product_rating(self, item, spider):
		self.drop_if_empty(item, 'ads_id')

		dbfeedback = market_models.AdsFeedback()
		dbfeedback.market = spider.market
		dbfeedback.scrape = spider.scrape

		try:
			dbfeedback.ads = spider.dao.get(market_models.Ads, external_id = item['ads_id'], market = spider.market)
		except market_models.Ads.DoesNotExist :
			raise DropItem("Invalid Ads Feedback : Unable to get Ads from database. Cannot respect foreign key constraint.")

		if not dbfeedback.ads:
			raise DropItem("Invalid Ads Feedback : Unable to get Ads from database. Cannot respect foreign key constraint.")
			
		elif not dbfeedback.ads.id :
			raise DropItem("Invalid Ads Feedback : Ads foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")

		sha256 = hashlib.sha256()
		sha256.update(str(dbfeedback.ads.id))
		for key in item:
			sha256.update(self.make_utf8(item[key]))

		dbfeedback.hash = sha256.hexdigest()

		for key in item:
			if key not in ['ads_id']:
				self.set_if_exist(item, dbfeedback, key)
				
		dbfeedback.setproperties_attribute(scrape = spider.scrape)

		return dbfeedback


	def map_user_rating(self, item, spider):
		self.drop_if_empty(item, 'username')

		dbfeedback = market_models.SellerFeedback()
		dbfeedback.market = spider.market
		dbfeedback.scrape = spider.scrape

		try:
			dbfeedback.seller = spider.dao.get(market_models.User, username=item['username'], market=spider.market)
		except market_models.User.DoesNotExist :
			raise DropItem("Invalid User Feedback : Unable to get User from database. Cannot respect foreign key constraint.")

		if not dbfeedback.seller:
			raise DropItem("Invalid User Feedback : Unable to get User from database. Cannot respect foreign key constraint.")
			
		elif not dbfeedback.seller.id :
			raise DropItem("Invalid User Feedback : User foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")

		sha256 = hashlib.sha256()
		sha256.update(str(dbfeedback.seller.id))
		for key in item:
			sha256.update(self.make_utf8(item[key]))

		dbfeedback.hash = sha256.hexdigest()

		for key in item:
			if key not in ['username']:
				self.set_if_exist(item, dbfeedback, key)
				
		dbfeedback.setproperties_attribute(scrape = spider.scrape)

		return dbfeedback		








