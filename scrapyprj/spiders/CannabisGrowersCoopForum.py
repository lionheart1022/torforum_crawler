from __future__ import absolute_import
import scrapy
from scrapy.http import FormRequest,Request
from scrapy.shell import inspect_response
from scrapyprj.spiders.ForumSpiderV2 import ForumSpiderV2
from scrapyprj.database.orm import *
import scrapyprj.database.forums.orm.models as models
import scrapyprj.items.forum_items as items
from datetime import datetime, timedelta
from urlparse import urlparse, parse_qsl
import logging
import time
import hashlib 
import traceback
import re
import pytz
import dateutil
from IPython import embed
from random import randint


class CannabisGrowersCoopForum(ForumSpiderV2):
    name = "cgmc_forum"
    
    custom_settings = {
        'MAX_LOGIN_RETRY' : 10,
		'IMAGES_STORE' : './files/img/cgmc_forum',
		'RANDOMIZE_DOWNLOAD_DELAY' : True
    }

    
    def __init__(self, *args, **kwargs):
        super(CannabisGrowersCoopForum, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(12)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system
        self.statsinterval = 60 				# Custom Queue system

        self.logintrial = 0
    
    def parse_response(self, response):
        parser = None
        if self.is_logged(response):
            # we're logged in!
            if self.is_thread_listing(response):
                parser = self.parse_thread_listing
            elif self.is_thread(response):
                parser = self.parse_thread
            pass
        elif self.is_login_page(response):
            yield self.do_login(response)
        else:
            self.logger.warning('We are not logged in and we are not on the login page')
        
        if parser is not None:
            for x in parser(response):
                yield x

    def is_logged(self, response):
		logout_link = response.css('header nav div:last-child > a:last-child')
		if logout_link and logout_link.css("::text").extract_first() == "Log Out":
			return True

		return False

    def is_login_page(self, response):
        return response.css('form#login-form').extract_first() is not None
    
    def do_login(self, response):
        data = {
            'username' : self.login['username'],
            'password' : self.login['password'],
			'user_action' : 'login',
			'return' : 'login/'
        }

        req = FormRequest.from_response(response, formdata=data, formcss='form#login-form')
        req.dont_filter = True
        
        captcha_src = '/login/showCaptcha?' + str(randint(100000, 999999))

        req.meta['captcha'] = { 
            'request' : self.make_request(url = captcha_src, dont_filter = True),
            'name': 'captcha'
        }

        return req

    def is_thread_listing(self, response):
        return response.css('ul.row.big-list.zebra').extract_first() is not None

    def parse_thread_listing(self, response):
        topics = response.css('ul.row.big-list.zebra > li')
        for topic in topics:
            threaditem = items.Thread()
            threaditem['title'] =  self.get_text(topic.css("div.main > div > a"))

            href = topic.css("div.main > div > a::attr(href)").extract_first()
            threaditem['relativeurl'] = href
            threaditem['fullurl']   = self.make_url(href)
            threadid = self.get_thread_id(href)
            threaditem['threadid'] = threadid
            threaditem['author_username'] = topic.css("div.main > div > span a::text").extract_first()
            
            replies = self.get_text(topic.css("div.main > div > span strong:last-child"))
            if re.match(r'^\d+$', replies) is None:
                replies = 0
            threaditem['replies'] = replies
                        
            yield threaditem
    
    def is_thread(self, response):
        return response.css('ul.row.list-posts').extract_first() is not None

    def parse_thread(self, response):
        posts = response.css('ul.row.list-posts > li')
        for post in posts:
            messageitem = items.Message()

            messageitem['author_username'] = self.get_text(post.css('.post-header a.poster'))
            messageitem['postid'] = self.get_post_id(post.css('span:first-child::attr(id)').extract_first())
            messageitem['threadid'] = self.get_thread_id(response.url)
            messageitem['posted_on'] = dateutil.parser.parse(self.get_text(post.css('.footer .cols-10 .col-4:first-child strong')))

            msg = post.css("div.content")
            messageitem['contenttext'] = self.get_text(msg)
            messageitem['contenthtml'] = self.get_text(msg.extract_first())

            yield messageitem

    def get_thread_id(self, uri):
        match = re.search(r'/discussion/(\d+)/', uri)
        if match:
            return match.group(1)
        match = re.search(r'/post/(\d+)/', uri)
        if match:
            return match.group(1)
        return None
    
    def get_post_id(self, uri):
        match = re.search(r'post-(\d+)', uri)
        if match:
            return match.group(1)
        match = re.search(r'comment-(\d+)', uri)
        if match:
            return match.group(1)
        return None