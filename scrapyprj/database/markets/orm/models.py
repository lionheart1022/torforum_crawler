import scrapyprj.database.db as db
import scrapyprj.database.orm as orm
from peewee import *


class Market(Model):
	id = PrimaryKeyField()
	name = CharField()
	spider = CharField(unique=True)

	class Meta:
		database = db.proxy 
		db_table = 'market'


class Process(Model):
	id = PrimaryKeyField();
	start = DateTimeField()
	end = DateTimeField()
	pid = IntegerField()
	cmdline = TextField()
	
	class Meta:
		database = db.proxy 
		db_table = 'process'


class Scrape(Model):
	id = PrimaryKeyField();
	process = ForeignKeyField(Process, 	related_name='scrapes', db_column='process')
	market = ForeignKeyField(Market, 	related_name='scrapes', db_column='market')
	start = DateTimeField()
	end = DateTimeField()
	reason = TextField()
	login = CharField()
	proxy = CharField()

	class Meta:
		database = db.proxy 
		db_table = 'scrape'


class ScrapeStat(Model):
	id = PrimaryKeyField()
	scrape = ForeignKeyField(Scrape, related_name='stats', db_column='scrape')
	logtime = DateTimeField()
	ram_usage = BigIntegerField()
	request_sent = BigIntegerField()
	request_bytes = BigIntegerField()
	response_received = BigIntegerField()
	response_bytes = BigIntegerField()
	item_scraped = BigIntegerField()
	item_dropped = BigIntegerField()
	ads = BigIntegerField()
	ads_propval = BigIntegerField()
	ads_feedback = BigIntegerField()
	ads_feedback_propval = BigIntegerField()
	user = BigIntegerField()
	user_propval = BigIntegerField()
	seller_feedback = BigIntegerField()
	seller_feedback_propval = BigIntegerField()


	class Meta : 
		database = db.proxy
		db_table = 'scrapestat'


class CaptchaQuestion(Model):
	id = PrimaryKeyField()
	market = ForeignKeyField(Market, related_name='captcha_questions', db_column='market')
	hash = CharField(unique = True)
	question = TextField()
	answer = TextField()

	class Meta:
		database = db.proxy # We assign the proxy object and we'll switch it for a real connection in the configuration.
		db_table = 'captcha_question'
		indexes = (
			(('market', 'hash'), True),	# unique index
		)		


################  User  ############### 

class UserPropertyKey(orm.BasePropertyKey):
	class Meta:
		database = db.proxy 
		db_table='user_propkey'

DeferredUser = DeferredRelation() #Overcome circular dependency

class UserProperty(orm.BasePropertyModel):
	key = ForeignKeyField(UserPropertyKey, 	db_column='propkey')
	owner = ForeignKeyField(DeferredUser,  	db_column='user')
	data = TextField()
	scrape = ForeignKeyField(Scrape, 		db_column='scrape')
	modified_on = DateTimeField()


	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database = db.proxy 
		db_table='user_propval'

class UserPropertyAudit(orm.BasePropertyModel):
	key = ForeignKeyField(UserPropertyKey, 	db_column='propkey')
	owner = ForeignKeyField(DeferredUser,  	db_column='user')
	data = TextField()
	scrape = ForeignKeyField(Scrape, 		db_column='scrape')
	modified_on = DateTimeField()


	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database = db.proxy 
		db_table='user_propvalaudit'		


class User(orm.BasePropertyOwnerModel):
	id = PrimaryKeyField()
	market = ForeignKeyField(Market, related_name='users', 	db_column='market')
	username = CharField()
	relativeurl = TextField()
	fullurl = TextField() 
	scrape = ForeignKeyField(Scrape, related_name='users', 	db_column='scrape')
	modified_on = DateTimeField()

	class Meta:
		database = db.proxy 
		db_table = 'user'
		indexes = (
 			(('forum', 'username'), True),	# unique index
			)

		#Custom properties, not part of peewee
		valmodel = UserProperty
		keymodel = UserPropertyKey

DeferredUser.set_model(User)	#Overcome circular dependency

#######################################


############### Ads ###################

class AdsPropertyKey(orm.BasePropertyKey):
	class Meta:
		database = db.proxy 
		db_table='ads_propkey'

DeferredAds = DeferredRelation() #Overcome circular dependency

class AdsProperty(orm.BasePropertyModel):
	key 	= ForeignKeyField(AdsPropertyKey, 	db_column='propkey')
	owner 	= ForeignKeyField(DeferredAds,  	db_column='ads')
	data 	= TextField()
	scrape 	= ForeignKeyField(Scrape, 			db_column='scrape')
	modified_on = DateTimeField()


	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database = db.proxy 
		db_table='ads_propval'

class AdsPropertyAudit(orm.BasePropertyModel):
	key 	= ForeignKeyField(AdsPropertyKey, 	db_column='propkey')
	owner 	= ForeignKeyField(DeferredAds,  	db_column='ads')
	data 	= TextField()
	scrape 	= ForeignKeyField(Scrape, 			db_column='scrape')
	modified_on =  DateTimeField()

	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database = db.proxy 
		db_table='ads_propvalaudit'


class Ads(orm.BasePropertyOwnerModel):
	id 			= PrimaryKeyField()
	external_id = CharField()
	market 		= ForeignKeyField(Market, 	related_name='ads', db_column='market')
	title 		= TextField()
	seller 		= ForeignKeyField(User, 	related_name='ads', db_column='seller')
	relativeurl = TextField()
	fullurl 	= TextField()
	last_update = DateTimeField()
	scrape 		= ForeignKeyField(Scrape, 	related_name='ads', db_column='scrape')
	modified_on = DateTimeField()

	class Meta:
		database 	= db.proxy 
		db_table 	= 'ads'
		indexes 	= (
 			(('market', 'external_id'), True),	# unique index
			)
		valmodel = AdsProperty
		keymodel = AdsPropertyKey		

DeferredAds.set_model(Ads)	#Overcome circular dependency


###########################################



############### Ads Feedback ###################

class AdsFeedbackPropertyKey(orm.BasePropertyKey):
	class Meta:
		database 	= db.proxy 
		db_table	='ads_feedback_propkey'

DeferredAdsFeedback = DeferredRelation() #Overcome circular dependency

class AdsFeedbackProperty(orm.BasePropertyModel):
	key 	= ForeignKeyField(AdsFeedbackPropertyKey, 	db_column='propkey')
	owner 	= ForeignKeyField(DeferredAdsFeedback,  	db_column='feedback')
	data 	= TextField()
	scrape 	= ForeignKeyField(Scrape, 					db_column='scrape')
	modified_on = DateTimeField()

	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database 	= db.proxy 
		db_table	='ads_feedback_propval'

class AdsFeedbackPropertyAudit(orm.BasePropertyModel):
	key 	= ForeignKeyField(AdsFeedbackPropertyKey, 	db_column='propkey')
	owner 	= ForeignKeyField(DeferredAdsFeedback,  	db_column='feedback')
	data 	= TextField()
	scrape 	= ForeignKeyField(Scrape, 					db_column='scrape')
	modified_on = DateTimeField()

	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database 	= db.proxy 
		db_table	='ads_feedback_propvalaudit'


class AdsFeedback(orm.BasePropertyOwnerModel):
	id 			= PrimaryKeyField()
	hash 		= CharField()
	market 		= ForeignKeyField(Market, 	related_name='ads_feedback', 	db_column='market')
	ads 		= ForeignKeyField(Ads, 		related_name='feedback', 		db_column='ads')
	scrape 		= ForeignKeyField(Scrape, 	related_name='ads_feedback',	db_column='scrape')
	modified_on = DateTimeField()
	count 		= BigIntegerField()

	class Meta:
		database 	= db.proxy 
		db_table 	= 'ads_feedback'
		valmodel 	= AdsFeedbackProperty
		keymodel 	= AdsFeedbackPropertyKey

DeferredAdsFeedback.set_model(AdsFeedback)	#Overcome circular dependency


###########################################


############## User Feedback ###################

class SellerFeedbackPropertyKey(orm.BasePropertyKey):
	class Meta:
		database 	= db.proxy 
		db_table	='seller_feedback_propkey'

DeferredSellerFeedback = DeferredRelation() #Overcome circular dependency

class SellerFeedbackProperty(orm.BasePropertyModel):
	key 		= ForeignKeyField(SellerFeedbackPropertyKey, 	db_column='propkey')
	owner 		= ForeignKeyField(DeferredSellerFeedback,  		db_column='feedback')
	data 		= TextField()
	scrape 		= ForeignKeyField(Scrape, 						db_column='scrape')
	modified_on = DateTimeField()

	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database 	= db.proxy 
		db_table	='seller_feedback_propval'

class SellerFeedbackPropertyAudit(orm.BasePropertyModel):
	key 		= ForeignKeyField(SellerFeedbackPropertyKey, 	db_column='propkey')
	owner 		= ForeignKeyField(DeferredSellerFeedback,  		db_column='feedback')
	data 		= TextField()
	scrape 		= ForeignKeyField(Scrape, 						db_column='scrape')
	modified_on = DateTimeField()

	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database 	= db.proxy 
		db_table	='seller_feedback_propvalaudit'	


class SellerFeedback(orm.BasePropertyOwnerModel):
	id 			= PrimaryKeyField()
	hash 		= CharField()
	market 		= ForeignKeyField(Market, 	related_name='seller_feedback',	db_column='market')
	seller 		= ForeignKeyField(User, 	related_name='feedback', 		db_column='seller')
	scrape 		= ForeignKeyField(Scrape, 	related_name='seller_feedback',	db_column='scrape')
	modified_on = DateTimeField()
	count 		= BigIntegerField()

	class Meta:
		database 	= db.proxy 
		db_table 	= 'seller_feedback'
		valmodel = SellerFeedbackProperty
		keymodel = SellerFeedbackPropertyKey

DeferredSellerFeedback.set_model(SellerFeedback)	#Overcome circular dependency


###########################################


class AdsImage(Model):
	id 				= PrimaryKeyField()
	ads 			= ForeignKeyField(Ads,  db_column='ads')
	path 			= CharField()
	hash 			= CharField()
	modified_on 	= DateTimeField()
	scrape 			= ForeignKeyField(Scrape, db_column='scrape')

	class Meta:
		database 	= db.proxy 
		db_table 	= 'ads_img'

		indexes 	= (
			(('hash'), True),	#unique
			)


class ManualInput(Model):
	id = PrimaryKeyField()
	date_requested = DateTimeField()
	spidername = CharField()
	proxy = CharField()
	login = CharField()
	login_info = TextField()
	cookies = TextField()
	user_agent = TextField()
	reload = BooleanField()
		

	class Meta:
		database 	= db.proxy 
		db_table 	= 'manual_input'

class Changerate(Model):
	time = DateTimeField()
	btc = FloatField()
	usd = FloatField()

	class Meta:
		database 	= db.proxy 
		db_table 	= 'changerate'