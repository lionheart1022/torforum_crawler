import sys, os
import random
import string
import unittest
from datetime import datetime, timedelta
from IPython import embed
import scrapy
from scrapy.http import Request, Response, HtmlResponse, TextResponse
from scrapyprj.replay.ReplayStorage import ReplayStorage
from TestTools import *
import struct
import base64

class MockedSpider(scrapy.Spider):
	name = 'mocked_spider'

class TestReplayStorage(unittest.TestCase):

	def make_response(self, **kwargs):
		return Response(url='http://127.0.0.1/'+randstring(20), body=randstring(50), headers={'Header1' : 'val1', 'Header2' : 'val2'}, status=200, flags=['aaa', 'bbb', 'ccc'], **kwargs)
	
	def make_request(self, **kwargs):
		return Request(url='http://127.0.0.1/'+randstring(20), body=randstring(50), headers={'Header9' : 'val9', 'header8' : 'val8'}, flags=['qqq', 'www', 'eee'], **kwargs)

	def make_request_utf8(self, **kwargs):
		return Request(url='http://127.0.0.1/\xc3\xa9\xc3\xa9', body='\xc3\xa9\xc3\xa9', headers={'Header9' : 'val9', 'header8' : 'val8'}, flags=['qqq', 'www', 'eee'], **kwargs)

	def assertRequestEqualNoMeta(self, req1, req2):
		self.assertEquals(req1.url, req2.url)
		self.assertEquals(req1.headers, req2.headers)
		self.assertEquals(req1.body, req2.body)
		self.assertEquals(req1.flags, req2.flags)

	def assertResponseEqualNoMeta(self, resp1, resp2):
		self.assertEquals(resp1.url, resp2.url)
		self.assertEquals(resp1.headers, resp2.headers)
		self.assertEquals(resp1.body, resp2.body)
		self.assertEquals(resp1.flags, resp2.flags)
		self.assertEquals(resp1.status, resp2.status)

	def setUp(self):
		self.spider = MockedSpider()
		self.storage = ReplayStorage(self.spider, 'teststorage')
		self.storage.make_dir()

	def tearDown(self):
		self.storage.delete_dir()
		os.rmdir('teststorage')

	def test_save(self):
		response = Response(url='http://127.0.0.1/aaa')
		self.storage.save(response)

	def test_basic_reload(self):
		response = Response(url='http://127.0.0.1/aaa')
		filename = self.storage.save(response)
		response2 = self.storage.load(filename)
		self.assertEquals(response.url, response2.url)

	def test_working_selector_after_reload(self):
		response = HtmlResponse(url='http://127.0.0.1/aaa', body='<html><body><h1>test</h1></body></html>')
		response.css('h1')
		filename = self.storage.save(response)
		response2 = self.storage.load(filename)
		response2.css('h1')

	def test_binary_body(self):
		response = Response(url='http://127.0.0.1/aaa', body=struct.pack('B'*255, *range(0,255)))
		filename = self.storage.save(response)
		response2 = self.storage.load(filename)
		self.assertEquals(response.url, response2.url)

	def test_utf8_body(self):
		response = Response(url='http://127.0.0.1/aaa', body='\xc3\xa9')
		filename = self.storage.save(response)
		response2 = self.storage.load(filename)
		self.assertEquals(response.url, response2.url)

	def test_utf8_url(self):
		response = Response(url='http://127.0.0.1/aaa\xc3\xa9', body='asd')
		filename = self.storage.save(response)
		response2 = self.storage.load(filename)
		self.assertEquals(response.url, response2.url)

	def test_response_to_dict(self):
		response = self.make_response()
		d = self.storage.response_to_dict(response)
		self.assertTrue(isinstance(d, dict))

	def test_response_from_dict(self):
		response1 = self.make_response()
		data = self.storage.response_to_dict(response1)
		response2 = self.storage.response_from_dict(data)
		self.assertIsInstance(response2, Response)

		self.assertEquals(response1.body, response2.body)
		self.assertEquals(response1.headers, response2.headers)
		self.assertEquals(response1.flags, response2.flags)
		self.assertEquals(response1.status, response2.status)
		self.assertEquals(response1.url, response2.url)

	def test_complex_reload(self):
		response = self.make_response()
		filename = self.storage.save(response)
		response2 = self.storage.load(filename)
		self.assertResponseEqualNoMeta(response, response2)

	def test_reload_with_request(self):
		response = self.make_response()
		request = self.make_request()
		response.request = request
		filename = self.storage.save(response)
		response2 = self.storage.load(filename)
		self.assertResponseEqualNoMeta(response, response2)
		self.assertRequestEqualNoMeta(response.request, response2.request)

	def test_reload_with_utf8_request(self):
		response = self.make_response()
		request = self.make_request_utf8()
		response.request = request
		filename = self.storage.save(response)
		response2 = self.storage.load(filename)
		self.assertResponseEqualNoMeta(response, response2)
		self.assertRequestEqualNoMeta(response.request, response2.request)

	
	def test_reload_with_request_meta(self):
		response = self.make_response()
		request = self.make_request()
		request.meta[randstring(10)] = randstring(10)
		response.request = request
		filename = self.storage.save(response)
		response2 = self.storage.load(filename)
		self.assertResponseEqualNoMeta(response, response2)
		self.assertRequestEqualNoMeta(response.request, response2.request)

		for k in response.meta:
			self.assertEquals(response.meta[k], response2.meta[k])

	def test_reload_with_request_meta_utf8(self):
		response = self.make_response()
		request = self.make_request()
		request.meta[randstring(10)] = randstring(10)
		request.meta[randstring(10)] = '\xc3\xa9'
		response.request = request
		filename = self.storage.save(response)
		response2 = self.storage.load(filename)
		self.assertResponseEqualNoMeta(response, response2)
		self.assertRequestEqualNoMeta(response.request, response2.request)

		for k in response.meta:
			self.assertEquals(response.meta[k], response2.meta[k])

	def test_reload_with_request_recursive_meta(self):
		response = self.make_response()
		request1 = self.make_request()
		request1.meta[randstring(10)] = randstring(10)
		request2 = self.make_request()
		request2.meta[randstring(10)] = randstring(10)
		request3 = self.make_request()
		request3.meta[randstring(10)] = randstring(10)
		request2.meta['request3'] = request3
		request1.meta['request2'] = request2

		response.request = request1
		filename = self.storage.save(response)
		response2 = self.storage.load(filename)

		self.assertResponseEqualNoMeta(response, response2)
		self.assertRequestEqualNoMeta(response.request, response2.request)

		for k in response.meta:
			if not isinstance(response.meta[k], Request):
				self.assertEquals(response.meta[k], response2.meta[k])

		self.assertTrue(isinstance(response.meta['request2'], Request))
		self.assertRequestEqualNoMeta(response.meta['request2'], request2)
		for k in response.meta['request2'].meta:
			if not isinstance(response.meta['request2'].meta, Request):
				self.assertEquals(response.meta['request2'].meta[k], request2.meta[k])


		self.assertTrue(isinstance(response.meta['request2'].meta['request3'], Request))
		self.assertRequestEqualNoMeta(response.meta['request2'].meta['request3'], request3)
		for k in response.meta['request2'].meta['request3'].meta:
			if not isinstance(response.meta['request2'].meta['request3'].meta, Request):
				self.assertEquals(response.meta['request2'].meta['request3'].meta[k], request3.meta[k])


	def test_reload_with_request_looping_reference(self):
		response = self.make_response()
		request1 = self.make_request()
		request1.meta[randstring(10)] = randstring(10)
		request2 = self.make_request()
		request2.meta[randstring(10)] = randstring(10)
		request2.meta['request'] = request1
		request1.meta['request'] = request2

		response.request = request1
		filename = self.storage.save(response)
		response2 = self.storage.load(filename)

		self.assertResponseEqualNoMeta(response, response2)
		self.assertRequestEqualNoMeta(response.request, response2.request)

		for k in response.meta:
			if not isinstance(response.meta[k], Request):
				self.assertEquals(response.meta[k], response2.meta[k])

		self.assertTrue(isinstance(response.meta['request'], Request))
		self.assertRequestEqualNoMeta(response.meta['request'], request2)

		for k in response.meta['request'].meta:
			if not isinstance(response.meta['request'].meta, Request):
				self.assertEquals(response.meta['request'].meta[k], request2.meta[k])

		self.assertIsNone(response2.meta['request'].meta['request'])	# Loops are broken avoiding infinite recursion

		

