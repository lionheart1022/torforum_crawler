import scrapy
from scrapy.pipelines.images import ImagesPipeline

class ImagePipelineFromRequest(scrapy.pipelines.images.ImagesPipeline):
	def get_media_requests(self, item, info):
		return [x for x in item.get(self.images_urls_field, [])]	# images_url are request, not string.
