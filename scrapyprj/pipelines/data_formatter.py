import collections

import scrapyprj.items.forum_items as forum_items
import scrapyprj.items.market_items as market_items
import logging
import re
from datetime import datetime

class DataFormatterPipeline(object):

	def __init__(self, *args,**kwargs):
		self.filter_map = {
			market_items.User : {
				'public_pgp_key' 	: self.normlaize_pgp_key,
				'trusted_seller' 	: self.bool_to_str,
				'verified' 			: self.bool_to_str,
				'fe_enabled' 		: self.bool_to_str,
				'join_date'			: self.datetime_format,
				'last_active'		: self.datetime_format
			},

			market_items.Ads  : {
				'escrow'		: self.bool_to_str,
				'in_stock'		: self.bool_to_str,
				'multisig'		: self.bool_to_str,
				'auto_accept'	: self.bool_to_str
			},

			market_items.UserRating : {
				'submitted_on' : self.datetime_format
			},

			market_items.ProductRating : {
				'submitted_on' : self.datetime_format
			}
		}
		self.logger = logging.getLogger('DataFormatterPipeline')


	def process_item(self, item, spider):
		for item_type in self.filter_map:
			if isinstance(item, item_type):
				for key in self.filter_map[item_type]:
					if key in item:
						item[key] = self.filter_map[item_type][key].__call__(item[key])
		
		return item

	def normlaize_pgp_key(self, key):
		begin = '-----BEGIN PGP (PUBLIC|PRIVATE) KEY BLOCK-----'
		end = '-----END PGP (PUBLIC|PRIVATE) KEY BLOCK-----'
		m = re.search('(%s)(.+)(%s)' % (begin, end), key,re.S)
		if m:
			newlines = []
			for line in m.group(3).splitlines():
				if re.search('version', line, re.IGNORECASE):
					continue
				elif re.search('comment', line, re.IGNORECASE):
					continue
				newlines.append(line)
			content = ''.join(newlines)
			return '%s\n\n%s\n%s' % (m.group(1), content, m.group(4))
		
		self.logger.warning('Failed to clean PGP key. \n %s' % key)
		return key

	def bool_to_str(self, val):
		return str(val) if val in [True, False] else val

	def datetime_format(self, val):
		return val.strftime('%Y-%m-%d %H:%M:%S') if isinstance(val, datetime) else val
