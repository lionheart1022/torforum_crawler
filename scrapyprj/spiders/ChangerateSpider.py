import scrapy
from datetime import datetime
from scrapyprj.database import db
from scrapyprj.database.settings import markets as dbsettings
from scrapyprj.database.markets.orm.models import *

from IPython import embed
from fake_useragent import UserAgent

from scrapy import Request
import json

class ChangerateSpider(scrapy.Spider):
	user_agent  = UserAgent().random
	name = "changerate"
	def __init__(self, *args, **kwargs):
		super(ChangerateSpider, self).__init__( *args, **kwargs)
		db.init(dbsettings)
		self.download_delay = 60*60
		self.max_concurrent_requests = 1


	def make_request(self):
		return Request('https://blockchain.info/fr/ticker', dont_filter=True)

	def start_requests(self):
		yield self.make_request()

	def parse(self, response):
		yield self.make_request()

		rates = json.loads(response.body)
		usdrate = float(rates['USD']['15m'])
		dbentry = Changerate(time=datetime.utcnow(), btc=1, usd=usdrate)
		dbentry.save(force_insert=True)
