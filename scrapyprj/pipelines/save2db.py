import collections

class save2db(object):

	def process_item(self, item, spider):
		if not 'model' in item.keys():
			raise Exception("Sent an item with no 'model' key to %s pipeline" % self.__class__.__name__)
		
		if isinstance(item['model'], collections.Iterable):
			for model in item['model']:
				self.route_to_queue(model,spider)
		else:
			self.route_to_queue(item['model'],spider)		
		
		return item['item']

	def route_to_queue(self, model,spider):
		queue_name = spider.get_queuename(model)
		spider.dao.enqueue(model, spider=spider, waiting_queue=queue_name)	# If None, will go to main queue. Only main queue can reach database.

		