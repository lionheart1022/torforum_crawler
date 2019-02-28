from peewee import *
from pytz import timezone
import os, time
import re
from datetime import datetime
import tzlocal
# Placeholder for the database connection. 
# Read peewee's documentation for more details.
proxy = Proxy()	


def set_timezone(tz=None):
	if not tz:
		tz = tzlocal.get_localzone()
	
	offset_hour = float(tz.localize(datetime.now()).utcoffset().total_seconds())/3600.0
	sign = '+' if offset_hour > 0 else '-'
	offset_hour = abs(offset_hour)
	offset = "%s%02d:%02d" % (sign, offset_hour, 60*(offset_hour % 1)  )
	
	proxy.execute_sql('set time_zone ="%s"' % offset) 

def init(dbsettings):
	db = MySQLDatabase(dbsettings['dbname'],host=dbsettings['host'], user=dbsettings['user'], password=dbsettings['password'], charset=dbsettings['charset'])
	proxy.initialize(db);
	if 'timezone' in dbsettings:
		set_timezone(dbsettings['timezone'])

