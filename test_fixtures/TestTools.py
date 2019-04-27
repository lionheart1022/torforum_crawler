import random
import string
from datetime import datetime, timedelta

def round_microseconds(dt):
	if dt.microsecond >= 500000:
		dt += timedelta(seconds = 1);

	return dt.replace(microsecond=0)

def random_datetime():
	year = random.randint(1970, 2017)
	month = random.randint(1, 12)
	day = random.randint(1, 28)
	hours = random.randint(0,23)
	minutes = random.randint(0,59)
	seconds = random.randint(0,59)
	return datetime(year, month, day, hours, minutes, seconds)

def randstring(length):
	return ''.join(random.choice(string.ascii_uppercase  + string.digits) for _ in range(length))
	
def delete_all(self, *args, **kwargs):
	for m in args:
		try:
			m.delete_instance()
		except:
			if 'silent' in kwargs and kwargs['silent']:
				pass
			else:
				raise