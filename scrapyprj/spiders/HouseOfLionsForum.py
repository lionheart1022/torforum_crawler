#http://pwoah7foa6au2pul.onion

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

class HouseOfLionsSpider(ForumSpider):
    name = "houseoflions_forum"    

    custom_settings = {
        'MAX_LOGIN_RETRY' : 10
    }

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.logintrial = 0
        self.set_max_concurrent_request(16)      # Scrapy config
        self.set_download_delay(0)              # Scrapy config
        self.set_max_queue_transfer_chunk(16)    # Custom Queue system

        self.parse_handlers = {
                'index'         : self.parse_index,
                'dologin'       : self.parse_index,
                'loginpage'     : self.parse_loginpage,
                'board'         : self.parse_board,
                'thread'        : self.parse_thread,
                'userprofile'   : self.parse_userprofile,
                
            }

    def start_requests(self):
        yield self.make_request('loginpage')

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
        elif reqtype in ['board', 'userprofile', 'thread']:
            req = Request(kwargs['url'])
            req.meta['shared'] = True

            if 'threadid' in kwargs:
                req.meta['threadid'] = kwargs['threadid']
            
            if 'relativeurl' in kwargs:
                req.meta['relativeurl'] = kwargs['relativeurl']
        else:
            raise Exception('Unsuported request type %s ' % reqtype)

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
        yield self.make_request('index')

    def parse_index(self, response):
        for link in response.css("a.subject::attr(href)").extract():
            yield self.make_request('board', url=link)

    def parse_board(self, response):
        for threadline in response.css('#messageindex table tbody tr'):
            try:
                threaditem = items.Thread()

                threadcell = threadline.css(".subject")
                authorlink = threadcell.xpath(".//p[contains(., 'Started by')]").css('a')
                threadlink = threadcell.xpath('.//span[contains(@id, "msg_")]/a')

                threaditem['author_username'] = self.get_text_first(authorlink)
                threadurl = threadlink.xpath("@href").extract_first()
                
                m = re.search("\?topic=(\d+)", threadurl)
                if m:
                    threaditem['threadid'] = m.group(1).strip()
                threaditem['title'] = self.get_text(threadlink)
                threaditem['relativeurl'] = threadurl
                threaditem['fullurl'] = self.make_url(threadurl)

                #Last update
                lastpost_str = self.get_text(threadline.css(".lastpost"))
                m = re.search("(.+) by (.+)", lastpost_str)
                if m:
                    threaditem['last_update'] = self.parse_timestr(m.group(1))

                #Stats cell
                statcellcontent = self.get_text(threadline.css("td.stats"))
                m = re.search("(\d+) Replies [^\d]+(\d+) Views", statcellcontent)
                if m :
                    threaditem['replies'] = m.group(1)
                    threaditem['views'] = m.group(2)

                yield threaditem
                
                for pagelink in response.css(".pagelinks a.navPages"):
                    yield self.make_request('board', url = pagelink.xpath("@href").extract_first() )

                for userlink in threadline.xpath('.//a[contains(@href, "action=profile")]'):
                    u = userlink.xpath("@href").extract_first()
                    yield self.make_request('userprofile', url = u, relativeurl=u )

                for threadlink in threadline.xpath('.//a[contains(@href, "?topic=") and not(contains(@href, "#new"))]'):
                    yield self.make_request('thread', url = threadlink.xpath("@href").extract_first(), threadid=threaditem['threadid'] )
            except Exception as e:
                self.logger.error("Cannot parse thread item : %s" % e)
                raise

    def parse_thread(self, response):
        for postwrapper in response.css(".post_wrapper"):
            try:
                msgitem = self.get_message_item_from_postwrapper(postwrapper, response)
                useritem = self.get_user_item_from_postwrapper(postwrapper, response)

                yield msgitem
                yield useritem

                for pagelink in response.css(".pagelinks a.navPages"):
                    yield self.make_request('thread', url = pagelink.xpath("@href").extract_first(), threadid=msgitem['threadid'] )

                for userlink in postwrapper.css(".poster h4").xpath(".//a[not(contains(@href, 'action=pm'))]"):
                    u = userlink.xpath("@href").extract_first();
                    yield self.make_request('userprofile', url = u, relativeurl=u)
            except Exception as e:
                self.logger.error("Cannot parse Message item : %s" % e)
                raise


    def get_message_item_from_postwrapper(self, postwrapper, response):
        msgitem = items.Message()
        postmeta = self.get_text(postwrapper.css(".flow_hidden .keyinfo div"))
        postmeta_ascii = re.sub(r'[^\x00-\x7f]',r'', postmeta).strip()
        m = re.search('on:\s*(.+)', postmeta_ascii)
        if m:
            msgitem['posted_on'] = self.parse_timestr(m.group(1))
            
        postcontent = postwrapper.css(".postarea .post").xpath("./div[contains(@id, 'msg_')]")

        m = re.search('msg_(\d+)', postcontent.xpath('@id').extract_first())
        if m:
            msgitem['postid'] = m.group(1)

        msgitem['threadid']         = response.meta['threadid']
        msgitem['author_username']  = self.get_text(postwrapper.css(".poster h4"))  
        msgitem['contenthtml']      = self.get_text(postcontent.extract_first())
        msgitem['contenttext']      = self.get_text(postcontent)

        return msgitem

    def get_user_item_from_postwrapper(self, postwrapper, response):
        useritem = items.User()
        profilelink = postwrapper.css(".poster h4").xpath(".//a[not(contains(@href, 'action=pm'))]")
        useritem['username'] = self.get_text(postwrapper.css(".poster h4"))
        useritem['relativeurl'] = profilelink.xpath("@href").extract_first()
        useritem['fullurl'] = self.make_url(useritem['relativeurl'])

        extrainfo = postwrapper.css(".poster ul")
        useritem['postgroup'] = self.get_text(extrainfo.css("li.postgroup"))
        useritem['membergroup'] = self.get_text(extrainfo.css("li.membergroup"))
        m = re.search('(\d+)', self.get_text(extrainfo.css("li.postcount")))
        if m:
            useritem['post_count'] = m.group(1)       

        useritem['signature'] = self.get_text(postwrapper.css(".signature"))

        useritem['karma'] = self.get_text(extrainfo.css("li.karma"))
        useritem['stars'] = str(len(extrainfo.css("li.stars img")))
        useritem['icq'] = self.extract_icq(postwrapper.css("a.icq"))
        useritem['msn'] = self.extract_msn(postwrapper.css("a.msn"))

        return useritem

    def parse_userprofile(self, response):
        user = items.User()
        user['username'] = self.get_text(response.css("#basicinfo .username h4::text").extract_first())
        user['relativeurl'] = response.meta['relativeurl']
        user['fullurl'] = response.url
        user['membergroup'] = self.get_text(response.css("#basicinfo .username h4 span.position"))

        user['icq'] = self.extract_icq(response.css("#basicinfo a.icq"))
        user['msn'] = self.extract_msn(response.css("#basicinfo a.msn"))
        signature = self.get_text(response.css("#detailedinfo .signature"))
        user['signature'] = self.get_text(re.sub("^Signature:", "", signature))

        dts = response.css("#detailedinfo .content dl dt")
        
        for dt in dts:
            key = self.get_text(dt).lower().rstrip(':')
            ddtext = self.get_text(dt.xpath('following-sibling::dd[1]'))

            if key == 'posts':
                m = re.search('(\d+)\s*\((.+) per day\)', ddtext)
                if m:
                    user['post_count'] = m.group(1)
                    user['post_per_day'] = m.group(2)
                else:
                    user['post_count'] = ddtext
            elif key == 'karma':
                user['karma'] = ddtext
            elif key == 'age':
                user['age'] = ddtext
            elif key == 'position 1':
                user['group'] = ddtext
            elif key == 'gender':
                user['gender'] = ddtext
            elif key == 'personal text':
                user['personal_text'] = ddtext
            elif key == 'date registered':
                try:
                    user['joined_on'] = self.parse_timestr(ddtext)
                except:
                    user['joined_on'] = ddtext
            elif key == 'last active':
                try:
                    user['last_active'] = self.parse_timestr(ddtext)
                except :
                    user['last_active'] = ddtext            
            elif key == 'location':
                user['location'] = ddtext
            elif key == 'custom title':
                user['custom_title'] = ddtext
            elif key in ['local time']:
                pass
            else:
                self.logger.warning('New information found on user profile page : %s. (%s)' % (key, response.url))

        yield user

    def parse_timestr(self, timestr):
        timestr = timestr.lower()
        try:
            timestr = timestr.replace('today at', str(self.localnow().date()))
            return self.to_utc(dateutil.parser.parse(timestr))
        except:
            self.logger.warning("Cannot parse timestring %s " % timestr)


    def craft_login_request_from_form(self, response):
        sessionid = response.css('#frmLogin::attr(onsubmit)').re("'(.+)'")
        if len(sessionid) > 0:
            sessionid = sessionid[0]
            self.logger.debug("Session ID : %s" % sessionid)
        else:
            sessionid = ''
            self.logger.warning("Cannot determine session id from form")

        data = {
            'user' : self.login['username'],
            'passwrd' : self.login['password'],
            'cookielength' : '12000',
            'cookieneverexp' : 'On',
            'hash_passwrd' : self.make_hash(self.login['username'], self.login['password'], sessionid)
        }

        req = FormRequest.from_response(response, formid='frmLogin', formdata=data)

        return req

    def islogged(self, response):
        return True if len(response.css("#button_logout")) > 0 else False

    def is_login_page(self, response):
        return  True if len(response.css("#frmLogin")) > 0 else False

    #So there's a simili-protection on the login page where we need to submit a hash of the password salted with the session id.
    def make_hash(self, u, p, sessid):
        return hashlib.sha1(hashlib.sha1(u.encode('utf8')+p.encode('utf8')).hexdigest()+sessid).hexdigest()

    def extract_icq(self, a):
        if a:
            href = a.xpath("@href").extract_first()
            m  = re.search("uin=(\d+)", href)
            if m:
                return m.group(1)

    def extract_msn(self, a):
        if a:
            href = a.xpath("@href").extract_first()
            m  =re.search("members.msn.com/(.+)", href)
            if m:
                return m.group(1)

