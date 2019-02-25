import logging
from clint.textui import colored

###
# This class simply add color to a formatter without touching the other parameters.
# We do extreme monkey patching
class ColorFormatterWrapper(logging.Formatter):
	baseformatter = logging.Formatter()

	def __init__(self,base):
		self.baseformatter = base;

	def format(self, record):
		levelname = record.levelname
		message = self.baseformatter.format(record);

		if levelname == 'DEBUG':
			return colored.white(message)
		elif levelname == 'INFO':
			return colored.cyan(message)
		elif levelname == 'WARNING':
			return colored.yellow(message)
		elif levelname == 'ERROR':
			return colored.red(message)	
		elif levelname == 'CRITICAL':
			return colored.magenta(message)	

		return message

