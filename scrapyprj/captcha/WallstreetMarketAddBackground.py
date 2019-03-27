import numpy as np
import scipy.signal as signal
import io
from PIL import Image
import logging
from IPython import embed

class WallstreetMarketAddBackground(object):
	def __init__(self):
		self.logger = logging.getLogger('WallstreetMarketAddBackground')

	def process(self, data):
		img = Image.open(io.BytesIO(data))			# Read img
		new_img = Image.new('RGB', img.size)
		new_img.paste(img)
		buf = io.BytesIO()	
		new_img.save(buf, format='png')
		buf.seek(0)
		data = bytearray(buf.read())

		return data
    