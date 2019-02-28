from peewee import *

#Extension to peewee model that allows to make models that 
# have some properties listed in another table respecting a predefined structure.   
# In other word.  user and user_propval
class BasePropertyOwnerModel(Model):
	def __init__(self, *args, **kwargs):
		if not self.__class__._meta.keymodel:
			raise Exception("When using BasePropertyOwnerModel, Meta.keymodel must be defined")
		if not self.__class__._meta.valmodel:
			raise Exception("When using BasePropertyOwnerModel, Meta.valmodel must be defined")
		
		if not hasattr(self._meta.valmodel, 'owner'):
			raise Exception("When using BasePropertyModel, a key named 'owner' must be a foreign key to BasePropertyOwnerModel")


		self._properties = {}
		self._valmodel_attributes = {}
		self._extra_data = {}

		#Intercepts kwargs for _properties that goes in our property table.
		keytoremove = []
		keylist = self.__class__.get_keys()
		for k in kwargs:
			if k in keylist:
				if hasattr(self, k):
					raise KeyError("%s has a field named %s but it's also linked to a property table having a key of the same name." % (self.__class__.__name__, k))
				self._properties[k] = kwargs[k]
				keytoremove.append(k)
		for k in keytoremove:	# Remove entries from kwargs before passing the to the real peewee.Model
			del kwargs[k]


		super(BasePropertyOwnerModel, self).__init__(*args, **kwargs)

	# Intercepts _properties that goes in our external property table.
	def __setattr__(self, k ,v):
		keylist = self.__class__.get_keys()

		if k in keylist:
			self._properties[k] = v
		else:
			super(BasePropertyOwnerModel, self).__setattr__(k,v)

	def setproperties_attribute(self, *args, **kwargs):
		for k in kwargs:
			self._valmodel_attributes[k] = kwargs[k]

	def getproperties(self):
		props = [];
		keylist = self.__class__.get_keys()
		for keyname in self._properties:
			if self._properties[keyname] != None:
				params = {}
				params['key'] =  keylist[keyname] 
				params['data'] =  self._properties[keyname]  
				params[self._meta.valmodel.owner.name] = self
				for attr in self._valmodel_attributes:	# Bring back the kwargs from the object creation and pass them to the property object if it has this attribute.
					params[attr] = self._valmodel_attributes[attr]
				props.append(self._meta.valmodel(**params))
		return props

	@classmethod
	def get_keys(cls):
		if not cls.model_initialized():
			cls.reset_keys()

		if not cls.keyinitialized:
			if not cls._meta.keymodel:
				raise Exception("When using BasePropertyOwnerModel, valmodel and keymodel must be defined")

			dbkeys = cls._meta.keymodel.select()
			for k in dbkeys:
				cls.keys[k.name] = k
			cls.keyinitialized = True
		return cls.keys

	@classmethod
	def reset_keys(cls):
		cls.keys = {}
		cls.keyinitialized=False
	
	@classmethod
	def model_initialized(cls):
		if not hasattr(cls,'keys'):
			return False
		
		if not hasattr(cls, 'keyinitialized'):
			return False

		return True
		
	class Meta:
		keymodel = None
		valmodel = None

class BasePropertyModel(Model):
	key = None
	data = None

class BasePropertyKey(Model):
	id 		= PrimaryKeyField()
	name 	= CharField()
	prettyname=CharField()
