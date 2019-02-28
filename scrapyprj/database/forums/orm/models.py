import scrapyprj.database.db as db
from peewee import *
import scrapyprj.database.orm as orm


class Forum(Model):
	id = PrimaryKeyField()
	name = CharField()
	spider = CharField(unique=True)

	class Meta:
		database = db.proxy 
		db_table = 'forum'


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
	start = DateTimeField()
	end = DateTimeField()
	reason = TextField()
	forum = ForeignKeyField(Forum, related_name='scrapes', db_column='forum')
	process = ForeignKeyField(Process, related_name='scrapes', db_column='process')
	login = CharField()
	proxy = CharField()

	class Meta:
		database = db.proxy 
		db_table = 'scrape'


class UserPropertyKey(orm.BasePropertyKey):
	class Meta:
		database = db.proxy 
		db_table='user_propkey'

DeferredUser = DeferredRelation() #Overcome circular dependency
class UserProperty(orm.BasePropertyModel):
	key = ForeignKeyField(UserPropertyKey, db_column='propkey')
	owner = ForeignKeyField(DeferredUser,  db_column='user')
	data = TextField()
	scrape = ForeignKeyField(Scrape, db_column='scrape')


	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database = db.proxy 
		db_table='user_propval'


class User(orm.BasePropertyOwnerModel):
	id = PrimaryKeyField()
	forum = ForeignKeyField(Forum, related_name='users', db_column='forum')
	username = CharField()
	relativeurl = TextField()
	fullurl = TextField() 
	scrape = ForeignKeyField(Scrape, related_name='users', db_column='scrape')

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



class Thread(Model):
	id = PrimaryKeyField()
	external_id = CharField()
	forum = ForeignKeyField(Forum, related_name='threads', db_column='forum')
	title = TextField()
	author = ForeignKeyField(User, related_name='threads', db_column='author')
	relativeurl = TextField()
	fullurl = TextField()
	last_update = DateTimeField()
	scrape = ForeignKeyField(Scrape, related_name='threads', db_column='scrape')

	class Meta:
		database = db.proxy 
		db_table = 'thread'
		indexes = (
 			(('forum', 'external_id'), True),	# unique index
			)



class MessagePropertyKey(orm.BasePropertyKey):
	class Meta:
		database = db.proxy 
		db_table='message_propkey'

DeferredMessage = DeferredRelation() #Overcome circular dependency

class MessageProperty(orm.BasePropertyModel):
	key = ForeignKeyField(UserPropertyKey, db_column='propkey')
	owner = ForeignKeyField(DeferredUser,  db_column='message')
	data = TextField()
	scrape = ForeignKeyField(Scrape, db_column='scrape')


	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database = db.proxy 
		db_table='message_propval'

class Message(Model):
	id = PrimaryKeyField()
	forum = ForeignKeyField(Forum, related_name='messages', db_column='forum')
	external_id = CharField()
	thread = ForeignKeyField(Thread, related_name='messages', db_column='thread')
	author = ForeignKeyField(User, related_name='messages', db_column='author')
	contenttext = TextField()
	contenthtml = TextField()
	posted_on = DateTimeField()
	scrape = ForeignKeyField(Scrape, related_name='messages', db_column='scrape')

	class Meta:
		database = db.proxy 
		db_table = 'message'
		indexes = (
			(('forum', 'external_id'), True),	# unique index
		)
DeferredMessage.set_model(Message)	#Overcome circular dependency

class CaptchaQuestion(Model):
	id = PrimaryKeyField()
	forum = ForeignKeyField(Forum, related_name='captcha_questions', db_column='forum')
	hash = CharField(unique = True)
	question = TextField()
	answer = TextField()

	class Meta:
		database = db.proxy # We assign the proxy object and we'll switch it for a real connection in the configuration.
		db_table = 'captcha_question'
		indexes = (
			(('forum', 'hash'), True),	# unique index
		)		

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
	thread = BigIntegerField()
	message = BigIntegerField()
	user = BigIntegerField()
	message_propval = BigIntegerField()
	user_propval = BigIntegerField()

	class Meta : 
		database = db.proxy
		db_table = 'scrapestat'

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

