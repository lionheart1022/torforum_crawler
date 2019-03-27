import numpy as np
import scipy.signal as signal
import io
from PIL import Image
import logging

class DreamMarketRectangleCropper(object):
	def __init__(self):
		self.logger = logging.getLogger('DreamMarketRectangleCropper')

	def process(self, data):
		img = Image.open(io.BytesIO(data))			# Read img
		npimg = np.asarray(img.convert('L'))		# Converts to numpy array

		npimg_thresh = (npimg < 100).astype(float)	# Threasshold the image
		h,w = npimg.shape
		vline = (np.ones([h//2,2])>0.5).astype(float) # Create lines for convolution
		hline = (np.ones([2,w//2])>0.5).astype(float)
		vconv = signal.correlate(npimg_thresh,vline)	# Do cross correlation with our lines. 
		hconv = signal.correlate(npimg_thresh,hline)	# Lines are symetrics, so it comes back to a 2D convolution

		vsumdiff = np.abs(np.diff( np.sum(hconv,1) ))		# Derivative of sum. Will make peaks where correlation changes quickly.
		hsumdiff = np.abs(np.diff( np.sum(vconv,0) ))

		# Finds peaks that are at least 20px appart
		hp1 = hsumdiff.argmax()			# Horizontal
		hsumdiff[hp1] = 0
		hp2 = hp1
		while abs(hp2-hp1) < 20:
		    hp2 = hsumdiff.argmax()
		    hsumdiff[hp2] = 0
		            
		vp1 = vsumdiff.argmax()		# Vertical
		vsumdiff[vp1] = 0
		vp2 = vp1
		while abs(vp2-vp1) < 20:
		    vp2 = vsumdiff.argmax()
		    vsumdiff[vp2] = 0

		#swap if reverse
		if hp1>hp2:
		    hp1,hp2 = hp2,hp1
		if vp1>vp2:
		    vp1,vp2=vp2,vp1

		self.logger.info("Cropping image from (%d,%d) to (%d, %d)" % (vp1, hp1, vp2, hp2))
		cropped = npimg[vp1:vp2, hp1:hp2]	# Crop the image

		# Converts to JPEG bytearray
		buf = io.BytesIO()	
		Image.fromarray(cropped).convert('RGB').save(buf, format='jpeg')
		buf.seek(0)
		data = bytearray(buf.read())

		return data
    