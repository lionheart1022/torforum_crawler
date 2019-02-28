import scrapyprj.database as database
import inspect
from peewee import *
from scrapy import settings
from IPython import embed

class Cache:

	# We can force the cache to use a specific key. Otherwise it finds what key to use searching for unique index first, then primary key.
	# Exmaples in comments. 

	cacheconfig = {}

	def __init__(self, config={}):
		self.cachedata = {}
		self.set_config(config)

	def set_config(self, config):
		for model in config:
			cls = model
			fieldlist = cls._meta.fields
			if isinstance(config[model], basestring):
				if config[model] not in fieldlist:
					raise ValueError("Cache config is invalid. %s is not a valid field for model %s" % (config[model], model))
			else:
				for field in config[model]:
					if field not in fieldlist:
						raise ValueError("Cache config is invalid. %s is not a valid field for model %s" % (config[model], model))
		self.cacheconfig = config

	def write(self, obj,*fieldlist):
		self.assertismodelclass(obj.__class__)
		self.init_ifnotexist(obj.__class__)
		return self.unsafewrite(obj,*fieldlist)

	def bulkwrite(self, objlist, *fieldlist):
		outputlist = []
		for obj in objlist: 
			outputlist.append(self.write(obj, *fieldlist))
		return outputlist
	#Write an object to the cache without checking if the cache is initilizaed or if the object is the right type.
	# Only specified fields are written. If no fields is given, the whole object is copied.
	def unsafewrite(self, obj, *fieldlist):
		fieldname, cacheid = self.getcacheid(obj)
		table = obj._meta.db_table
		if not cacheid:
			raise ValueError("Cannot write to cache object of type "  + obj.__class__.__name__ + " no usable id to identify the record.")
		if len(fieldlist) == 0 :
			self.cachedata[table][cacheid] = obj
		else:
			for field in fieldlist:	#Partial copy
				if isinstance(field, CompositeKey):
					for fieldname in field.field_names:	# field_names is peewee internal
						self.cachedata[table][cacheid]._data[fieldname] = obj._data[fieldname]	# Copy a single field from obj to the object stored in cache. (ob1.x = obj2.x)
				else:
					self.cachedata[table][cacheid]._data[field.name] = obj._data[field.name]	# Copy a single field from obj to the object stored in cache. (ob1.x = obj2.x)

		return self.cachedata[table][cacheid]


	def unsaferead(self, modeltype, cacheid):
		table = modeltype._meta.db_table
		if table in self.cachedata:
			if cacheid in self.cachedata[table]:
				return self.cachedata[table][cacheid]
	
	def read(self, modeltype, cacheid):
		self.assertismodelclass(modeltype)
		self.init_ifnotexist(modeltype)
		return self.unsaferead(modeltype, cacheid)		


	def readobj(self, obj):
		fieldname, cacheid = self.getcacheid(obj)
		return self.read(obj.__class__, cacheid)



	def bulkdeleteobj(self, objlist):
		for obj in objlist:
			self.deleteobj(obj)

	def deleteobj(self, obj):
		fieldname, cacheid = self.getcacheid(obj)
		self.delete(obj.__class__, cacheid)

	def delete(self, modeltype, cacheid):
		self.assertismodelclass(modeltype)
		self.init_ifnotexist(modeltype)
		self.unsafedelete(modeltype, cacheid)

	def unsafedelete(self, modeltype, cacheid):
		table = modeltype._meta.db_table
		if table in self.cachedata:
			if cacheid in self.cachedata[table]:
				del self.cachedata[table][cacheid]

	# For a specific Model, returns the unique key used to cache the object.
	# return (fieldname, cacheid) 
	# fieldname is the name of the field used as a key. Can be a string for single key or a tuple for composite key
	# cacheid is the value used as the index in the cache. Can be anything (literal, string, tuple)
	def getcacheid(self, obj):
		objclass = obj.__class__
		self.assertismodelclass(objclass)
		if objclass in self.cacheconfig:	# Property that can be set in the Cache class to avoid "guessing"
			fieldname = self.cacheconfig[objclass]
			cacheid = self.read_index_value(obj, fieldname)
			return (fieldname, cacheid)

		unique_idx = []	
		for idx in objclass._meta.indexes:	# Find unique keys in model 
			if idx[1] == True: # unique
				unique_idx.append(idx[0])
		
		if objclass._meta.primary_key:	# Find the primary keys
			if isinstance(objclass._meta.primary_key, CompositeKey):
				pkeyname = objclass._meta.primary_key.field_names
			else:
				pkeyname = objclass._meta.primary_key.name
			unique_idx.append(pkeyname)

		# Use the first match between unique and primary key as the cache id.
		for fieldname in unique_idx:
			cacheid = self.read_index_value(obj, fieldname)
			if cacheid:
				return (fieldname, cacheid)

		raise ValueError("Trying to obtain the cache id from object %s but no key data is usable. Content : %s" % (obj.__class__.__name__, str(obj._data)) )
	
	# extract the value of the index from an object. index can be single field name or tuple of field name for composite key.
	def read_index_value(self, obj, idx):
		if isinstance(idx, tuple):	# we are dealing with a composite key
			complete = True
			keyval = tuple()
			for subidx in idx :
				if subidx in obj._data:
					keyvaltemp = self.getfield_or_primarykey(obj._data[subidx])
					keyvaltemp = keyvaltemp.encode('utf8') if isinstance(keyvaltemp, unicode) else keyvaltemp
					keyval += (keyvaltemp,)	# Append to tuple
				else:
					complete  = False
					break
			return keyval if complete else None 
		elif isinstance(idx, basestring): 		# Single key
			if idx in obj._data:
				keyvaltemp = self.getfield_or_primarykey(obj._data[idx])
				keyvaltemp = keyvaltemp.encode('utf8') if isinstance(keyvaltemp, unicode) else keyvaltemp
				return keyvaltemp

	def getfield_or_primarykey(self, val):
		if issubclass(val.__class__, Model):		# It's a foreign key. Get the primary key
			val = val._data[val._meta.primary_key]
		return val

	def init_ifnotexist(self, modeltype):
		if not modeltype._meta.db_table in self.cachedata:
			self.cachedata[modeltype._meta.db_table] = {}
	
	def reload(self, modeltype, whereclause, *fieldlist):
		self.assertismodelclass(modeltype)
		self.init_ifnotexist(modeltype)
		objects = modeltype.select().where(whereclause)
		outputlist = []
		for obj in objects:
			outputlist.append(self.unsafewrite(obj, *fieldlist))
		return outputlist

	def assertismodelclass(self, modeltype):
		if not inspect.isclass(modeltype):
			raise Exception("Type must be a Class")
		elif not issubclass(modeltype, Model):
			raise Exception("Given type must be a subclass of PeeWee.Model")

	#This function will reload the cache content from the databse for the given object list.
	# a list of fields can be given so that only these will get updated.
	def reloadmodels(self, objlist, *fieldlist):
		objtype = None
		chunksize = 50
		reloaded_data = []
		cacheid_per_fieldname = {} # objects in objlist might have different keys. We will osrt them in this object to avoid making incoherent SQL
		if len(objlist) > 0 :
			
			modeltype = objlist[0].__class__
			fieldname, cacheid = self.getcacheid(objlist[0])
			for obj in objlist:
				self.assertismodelclass(obj.__class__)				# Sanity check
				objtype = obj.__class__ if not objtype else objtype
				if obj.__class__ != objtype:
					raise ValueError("Trying to reload partial set of data of different type.")
				
				fieldname, cacheid = self.getcacheid(obj)	# Get the cache id of the ovject
				if fieldname not in cacheid_per_fieldname:	# Create the container for the key
					cacheid_per_fieldname[fieldname] = []
				cacheid_per_fieldname[fieldname].append(cacheid)
			
			for fieldname in cacheid_per_fieldname.keys():	# For each cache id found before.

				cacheidlist = cacheid_per_fieldname[fieldname]
				for idx in range(0, len(cacheidlist), chunksize):	# chunk data
					data = cacheidlist[idx:idx+chunksize]
					# MySQL do not uses indexes with IN statement. We will use "val=1 OR val=2 OR val=3"   instead of "val in (1,2,3)"
					if isinstance(fieldname, basestring): #single key
						col = '`%s`' % modeltype._meta.fields[fieldname].db_column
						whereclause = ' or '.join([col+'=%s' for x in data])
						reloaded_data += self.reload(modeltype, SQL(whereclause, *data), *fieldlist)

					elif isinstance(fieldname, tuple): # composite key. Peewee doesn't support that easily, we have to do some manual work
						columns = '('+','.join(map(lambda x: "`%s`" % modeltype._meta.fields[x].db_column, fieldname))+')'  # (`col1`, `col2`)
						whereclause =  ' or '.join(map(lambda entry: columns+' = ('+','.join(map(lambda val: '%s', entry )) + ')', data))   # columns = (%s,%s) or columns= (%s, %s) or ...
						flatdata = []
						for entry in data: 
							flatdata += list(entry)	# Adds tuple content to a single list
						reloaded_data += self.reload(modeltype, SQL(whereclause, *flatdata), *fieldlist)
					else:
						raise ValueError("Doesn't know how to reload object of type %s with cache field : %s" % (obj.__class__.__name__, fieldname))

		return reloaded_data
	def get_usage(self):
		report = {}
		for table in self.cachedata:
			report[table] = len(self.cachedata[table])
		return report

