from __future__ import absolute_import
import scrapy
from scrapy.http import FormRequest,Request
from scrapy.shell import inspect_response
from scrapyprj.spiders.ForumSpider import ForumSpider
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

class AeroForumSpider(ForumSpider):
    name = "aero_forum"
    

    custom_settings = {
        'MAX_LOGIN_RETRY' : 10,
        'RESCHEDULE_RULES' : {
            'The post table and topic table seem to be out of sync' : 60
        }
    }

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(0)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system

        self.logintrial = 0
        self.parse_handlers = {
                'index'         : self.parse_index,
                'dologin'       : self.parse_index,
                'threadlisting' : self.parse_thread_listing,
                'thread'        : self.parse_thread,
                'userprofile'   : self.parse_userprofile,
                'loginpage'     : self.parse_loginpage # void function
            }

    def start_requests(self):
        yield self.make_request('index')

    def make_request(self, reqtype,  **kwargs):
        
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        if reqtype == 'index':
            req = Request(self.make_url('index'), dont_filter=True)
        elif reqtype == 'loginpage':
            req = Request(self.make_url('loginpage'), dont_filter=True)
        elif reqtype == 'dologin':
            req = self.craft_login_request_from_form(kwargs['response'])
            req.dont_filter=True
        elif reqtype == 'captcha_img':
            req = Request(self.make_url(kwargs['url']), dont_filter=True)
        elif reqtype in ['threadlisting', 'thread', 'userprofile']:
            req = Request(self.make_url(kwargs['url']))
            req.meta['shared'] = True
            if 'relativeurl' in kwargs:
                req.meta['relativeurl'] = kwargs['relativeurl']
        else:
            raise Exception('Unsuported request type ' + reqtype)

        req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
        req.meta['proxy'] = self.proxy  #meta[proxy] is handled by scrapy.

        if 'req_once_logged' in kwargs:
            req.meta['req_once_logged'] = kwargs['req_once_logged']        

        return req
   
    def parse(self, response):
        if not self.islogged(response):
            if self.is_login_page(response):
                req_once_logged = response.meta['req_once_logged'] if 'req_once_logged'  in response.meta else response.request 
                
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    self.wait_for_input("Too many login failed", req_once_logged)
                    self.logintrial = 0
                    return
                self.logger.info("Trying to login.")
                self.logintrial += 1
                
                yield self.make_request(reqtype='dologin',response=response, req_once_logged=req_once_logged);  # We try to login and save the original request
            else:
                self.logger.info("Not logged, going to login page.")
                yield self.make_request(reqtype='loginpage', req_once_logged=response.request);

        else : 
            self.logintrial = 0
            it = self.parse_handlers[response.meta['reqtype']].__call__(response)
            if it:
                for x in it:
                    if x != None:
                        yield x

    def parse_loginpage(self, response):    # We should never be looking at a login page while we are logged in.
        pass

    def parse_index(self, response):
        if 'req_once_logged' in response.meta:
            yield response.meta['req_once_logged']

        for line in response.css("#brdmain tbody tr"):
            link = line.css("h3>a::attr(href)").extract_first()
            
            yield self.make_request('threadlisting', url=link)
    
    def parse_thread_listing(self, response):
        for line in response.css("#brdmain tbody tr"):
            threaditem = items.Thread()
            title =  self.get_text(line.css("td:first-child a"))

            last_post_time = self.parse_timestr(self.get_text(line.css("td:last-child a")))           

            threadlinkobj = next(iter(line.css("td:first-child a") or []), None) # First or None if empty

            if threadlinkobj:
                threadlinkhref = threadlinkobj.xpath("@href").extract_first() if threadlinkobj else None
                threaditem['title'] = self.get_text(threadlinkobj)
                threaditem['relativeurl'] = threadlinkhref
                threaditem['fullurl']   = self.make_url(threadlinkhref)
                
                threaditem['threadid'] = self.get_url_param(threaditem['fullurl'], 'id')

                byuser = self.get_text(line.css("td:first-child span.byuser"))
                m = re.match("by (.+)", byuser) # regex
                if m:
                    threaditem['author_username'] = m.group(1)
                
                threaditem['last_update'] = last_post_time
                
                threaditem['replies']   = self.get_text(line.css("td:nth-child(2)"))
                threaditem['views']     = self.get_text(line.css("td:nth-child(3)"))
                
                yield threaditem
                yield self.make_request('thread', url=threadlinkhref)

        for link in response.css("#brdmain .pagelink a::attr(href)").extract():
            yield self.make_request('threadlisting', url=link)

    def parse_thread(self, response):
        threadid =  self.get_url_param(response.url, 'id')
        posts = response.css("#brdmain div.blockpost")
        for post in posts:
            try:
                messageitem = items.Message()
                posttime = self.parse_timestr(self.get_text(post.css("h2 a")))

                userprofile_link = post.css(".postleft dt:first-child a::attr(href)").extract_first()
                messageitem['author_username'] = self.get_text(post.css(".postleft dt:first-child a"))
                messageitem['postid'] = post.xpath("@id").extract_first()
                messageitem['threadid'] = threadid
                messageitem['posted_on'] = posttime

                msg = post.css("div.postmsg")
                messageitem['contenttext'] = self.get_text(msg)
                messageitem['contenthtml'] = self.get_text(msg.extract_first())

                yield messageitem

                yield self.make_request('userprofile', url = userprofile_link, relativeurl=userprofile_link )
            except Exception as e:
                self.logger.warning("Invalid thread page. %s" % e)

        for link in response.css("#brdmain .pagelink a::attr(href)").extract():
            yield self.make_request('thread', url=link)

    def parse_userprofile(self, response):
        user = items.User()
        user['relativeurl'] = response.meta['relativeurl']
        user['fullurl'] = response.url

        dts = response.css("#viewprofile dl dt")
        
        for dt in dts:
            key = self.get_text(dt).lower()
            ddtext = self.get_text(dt.xpath('following-sibling::dd[1]'))

            if key == 'username':
                user['username'] = ddtext
            elif key == 'title':
                user['title'] = ddtext
            elif key == 'registered':
                user['joined_on'] = self.parse_timestr(ddtext)
            elif key == 'last post':
                user['last_post'] = self.parse_timestr(ddtext)
            elif key == 'posts':
                m = re.match("^(\d+).+", ddtext)
                if m:
                    user['post_count'] = m.group(1)
            elif key == 'signature':
                user['signature'] = ddtext
            elif key == 'location':
                user['location'] = ddtext
            elif key == 'jabber':
                user['jabber'] = ddtext
            elif key == 'icq':
                user['icq'] = ddtext
            elif key == 'real name':
                user['realname'] = ddtext
            elif key == 'microsoft account':
                user['microsoft_account'] = ddtext            
            elif key == 'yahoo! messenger':
                user['yahoo_messenger'] = ddtext
            elif key == 'website':
                user['website'] = ddtext
            elif key in ['avatar', 'email', 'pm']:
                pass
            else:
                self.logger.warning('New information found on use profile page : %s' % key)

        yield user

    def craft_login_request_from_form(self, response):
        data = {
            'req_username' : self.login['username'],
            'req_password' : self.login['password']
        }
        req = FormRequest.from_response(response, formdata=data)

        captcha_src = response.css("form#login img::attr(src)").extract_first()

        return req

    def parse_timestr(self, timestr):
        last_post_time = None
        try:
            timestr = timestr.lower()
            timestr = timestr.replace('today', str(self.localnow().date()))
            timestr = timestr.replace('yesterday', str(self.localnow().date() - timedelta(days=1)))
            last_post_time = self.to_utc(dateutil.parser.parse(timestr))
        except:
            if timestr:
                self.logger.warning("Could not determine time from this string : '%s'. Ignoring" % timestr)
        return last_post_time

    def islogged(self, response):
        contenttext = self.get_text(response.css("#brdwelcome"))
        if 'Logged in as' in contenttext:
            return True
        return False

    def is_login_page(self, response):
        if len(response.css("form#login")) > 0:
            return True
        return False
