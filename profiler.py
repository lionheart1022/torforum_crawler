# Custom profiler class by Pier-Yves Lessard
# simply call profiler.start('name_of_measurement'). Then profiler.top('name_of_measurement').
# Do that as much as you want. 
# Then profiler.get_report().
# Easy way to track RAM. Only tested on windows, should support Linux

import logging
import hashlib
import os
import platform

_global_enabled = True

class Profiler(object):
	def __init__(self):
		global _global_enabled
		self.perf_dict = {}
		self.active_measurements = {}
		self.ready = True
		self.supported_platform = ['Windows', 'Linux']
		self.logger = logging.getLogger('profiler')
		self.enabled = True

		self.logger.debug("Initializing profiler.")
		if len(self.logger.handlers) == 0:
			self.logger.addHandler(logging.StreamHandler())
			self.logger.setLevel('INFO')

		self.platform = platform.system() 
		if self.platform not in self.supported_platform:
			self.logger.warning("Cannot run profiler. Unsupported Platform : %s" % self.platform)
			self.ready = False

		if self.platform == 'Linux':
			try:
				globals()['psutil'] = __import__('psutil')
			except Exception as e:
				self.ready = False
				self.logger.warning("Cannot run profiler. memusage module is missing. %s" % e)
		elif self.platform == 'Windows':
			try:
				globals()['wmi'] = __import__('wmi')
			except Exception as e:
				self.ready = False
				self.logger.warning("Cannot run profiler. wmi module is missing. %s" % e)

		try:
			if self.canrun():
				self.get_usage()
		except Exception as e:
			self.ready = False
			self.logger.warning("Cannot run profiler. Unable to get memory usage. %s " % e)	
		
		self.enabled = _global_enabled
		self.logger.debug("Profiler initialized")	


	def start(self, name):
		if not self.canrun():
			return

		usage = self.get_usage();

		if name not in self.active_measurements:
			self.active_measurements[name] = usage
		else:
			self.logger.debug("Measurement for %s started but was already active." % name)


	def stop(self, name):
		if not self.canrun():
			return

		usage = self.get_usage();

		if name in self.active_measurements:
			if name not in self.perf_dict:
				self.perf_dict[name] = 0
			self.perf_dict[name] += usage - self.active_measurements[name]
		else:
			self.logger.debug("Stopped measurement for %s without previously starting it" % name)

	def reset(self,name):
		self.perf_dict[name] = 0

	def get_report(self):
		report = {}
		if not self.canrun():
			return report

		total = self.get_usage()
		report['actual_usage'] = total
		report['measurements'] = {}
		for k in self.perf_dict:
			report['measurements'][k] = {
				'usage' 	: self.perf_dict[k],
				'percent' 	: float(self.perf_dict[k])/float(total) * 100.0
			}
		return report

	def get_usage(self):
		if not self.canrun():
			return
		
		if self.platform=='Linux':
			return psutil.Process(os.getpid()).memory_info().vms
			
		elif self.platform == 'Windows':
			w = wmi.WMI('.')
			result = w.query("SELECT WorkingSet FROM Win32_PerfRawData_PerfProc_Process WHERE IDProcess=%d" % os.getpid())
			return int(result[0].WorkingSet)


	def canrun(self):
		return self.ready and self.enabled

	def enable(self, val=True):
		self.enabled=val


_profilers = {'root' : Profiler()}

def get_profiler(name=None):
	global _profilers
	if name == None:
		return _profilers['root']
	elif name not in _profilers:
		_profilers[name] = Profiler()
	return _profilers[name]



def enable_all(val=True):
	global _profilers
	global _global_enabled
	_global_enabled = val
	for k in _profilers:
		_profilers[k].enable(val)

def disable_all():
	enable_all(False)

def start(name):
	return get_profiler().start(name)

def stop(name):
	return get_profiler().stop(name)

def get_report():
	return get_profiler().get_report()

def get_usage():
	return get_profiler().get_usage()	

def reset(name):
	return get_profiler().reset(name)		
