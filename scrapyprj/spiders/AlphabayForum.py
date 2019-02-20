#http://pwoah7foa6au2pul.onion

from __future__ import absolute_import
import scrapy
from scrapy.http import FormRequest,Request
from scrapy.shell import inspect_response
import scrapyprj.spider_folder.alphabay_forum.helpers.LoginQuestion as LoginQuestion
import scrapyprj.spider_folder.alphabay_forum.helpers.DatetimeParser as AlphabayDatetimeParser
from scrapyprj.spiders.ForumSpider import ForumSpider
from scrapyprj.database.orm import *
import scrapyprj.database.forums.orm.models as models
import scrapyprj.items.forum_items as items
from datetime import datetime
from urlparse import urlparse
import logging
import time
import hashlib 
import traceback
import re
import pytz

from IPython import embed

class AlphabayForum(ForumSpider):
    name = "alphabay_forum"
    handle_httpstatus_list = [403]

    custom_settings = {
            'RANDOMIZE_DOWNLOAD_DELAY' : True,
            'CONCURRENT_REQUESTS' : 16,
            'DOWNLOAD_TIMEOUT' : 20
        }
    
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(16)      # Scrapy config
        self.set_download_delay(0)              # Scrapy config
        self.set_max_queue_transfer_chunk(16)    # Custom Queue system
        self.logintrial = 0

        self.parse_handlers = {
                'index'          : self.parse_index,
                'threadlisting'  : self.parse_threadlisting,
                'userprofile'    : self.parse_userprofile,
                'threadpage'     : self.parse_threadpage
            }

    def start_requests(self):
        yield self.make_request('index')

    def make_request(self, reqtype,  **kwargs):
        
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        if reqtype == 'index':
            req = Request(self.make_url('index'))
            req.dont_filter=True
        
        elif reqtype == 'dologin':
           
            data = {
                'login' : self.login['username'],
                'register' : '0',
                'password' : self.login['password'],
                'cookie_check' : '1',
                '_xfToken': "",
                'redirect' : self.resource('index')
            }

            if 'captcha_question_hash' in kwargs:
                data['captcha_question_hash'] = kwargs['captcha_question_hash']

            if 'captcha_question_answer' in kwargs:
                data['captcha_question_answer'] = kwargs['captcha_question_answer']
           
            req = FormRequest(self.make_url('login-postform'), formdata=data, callback=self.handle_login_response, dont_filter=True)
            #req.method = 'POST' # Has to be uppercase !
            req.meta['req_once_logged'] = kwargs['req_once_logged']
            req.dont_filter=True

        elif reqtype in  ['threadlisting', 'userprofile']:
            req = Request(kwargs['url'])
            req.meta['shared'] = True

        elif reqtype == 'threadpage':
            req = Request(kwargs['url'])
            req.meta['threadid'] = kwargs['threadid']
            req.meta['shared'] = True
        else:
            raise Exception('Unsuported request type ' + reqtype)

        req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
        req.meta['proxy'] = self.proxy  #meta[proxy] is handled by scrapy.

        return req
   
    def parse(self, response):
        if not self.islogged(response):   
            self.logger.info("Trying to login.")        
            yield self.make_request(reqtype='dologin', req_once_logged=response.request);  # We try to login and save the original request
        else : 
            self.logintrial = 0
            it = self.parse_handlers[response.meta['reqtype']].__call__(response)
            if it:
                for x in it:
                    if x != None: yield x
                        
    def parse_index(self, response):
        links = response.css("li.forum h3.nodeTitle a::attr(href)").extract()
        for link in links:
            yield self.make_request(reqtype='threadlisting', url=link)

    def parse_threadlisting(self, response):
        threaddivs = response.css("li.discussionListItem")
        oldestthread_datetime = datetime.utcnow()
        for threaddiv in threaddivs:
            try:
                threaditem = items.Thread();
                last_message_datestr        = threaddiv.css(".lastPostInfo .DateTime::text").extract_first()
                threaditem['last_update']   = self.to_utc(AlphabayDatetimeParser.tryparse(last_message_datestr))
                oldestthread_datetime       = threaditem['last_update']  # We assume that threads are ordered by time.
            
                link                            = threaddiv.css(".title a.PreviewTooltip")
                threadurl                       = link.xpath("@href").extract_first()              
                threaditem['relativeurl']       = threadurl
                threaditem['fullurl']           = self.make_url(threadurl)
                threaditem['title']             = self.get_text_first(link)
                threaditem['author_username']   = self.get_text_first(threaddiv.css(".username"))
                threaditem['threadid']          = self.read_threadid_from_url(threadurl)
                
                author_url = threaddiv.css(".username::attr(href)").extract_first()

                yield self.make_request('userprofile',  url = author_url)
                yield self.make_request('threadpage',   url = threadurl, threadid=threaditem['threadid']) # First page of threa

                yield threaditem # sends data to pipelne
                
            except Exception as e:
                self.logger.error("Failed parsing response for threadlisting at %s. Error is %s.\n Skipping thread\n %s" % ( response.url, e.message, traceback.format_exc() ))
                continue
        
        # Parse next page.
        for link in response.css("div.PageNav nav a::attr(href)").extract():
            yield self.make_request(reqtype='threadlisting', url = link)  
        
    # Parse messages from a thread page.
    def parse_threadpage(self, response):   
        threadid = response.meta['threadid']

        for message in response.css(".messageList .message"):
            msgitem = items.Message();
            try:
                fullid                      = message.xpath("@id").extract_first()
                msgitem['postid']           = re.match("post-(\d+)", fullid).group(1)
                msgitem['author_username']  = self.get_text(message.css(".messageDetails .username"))
                msgitem['posted_on']        = self.read_datetime_div(message.css(".messageDetails .DateTime"))
                textnode                    = message.css(".messageContent")
                msgitem['contenthtml']      = textnode.extract_first()
                msgitem['contenttext']      = self.get_text(textnode)
                msgitem['threadid']         = threadid
            except Exception as e:
                self.logger.error("Failed parsing response for thread at %s. Error is %s.\n Skipping thread\n %s" % (response.url, e.message, traceback.format_exc()))

            yield msgitem


        for link in response.css("a.username::attr(href)").extract():           # Duplicates will be removed by dupefilter
            yield self.make_request('userprofile', url=self.make_url(link))

        #Start looking for previous page.
        for link in  response.css("div.PageNav nav a::attr(href)").extract():
            yield self.make_request("threadpage", url=link, threadid=threadid)

    def parse_userprofile(self, response):
        if response.status == 403:  #Unauthorized profile. Happen for private profiles
            return

        content = response.css(".profilePage")
        if content:
            content                 = content[0]
            useritem                = items.User()
            useritem['username']    = self.get_text_first(content.css(".username"))
            urlparsed               =  urlparse(response.url)
            useritem['relativeurl'] = "%s?%s" % (urlparsed.path, urlparsed.query)
            useritem['fullurl']     = response.url

            useritem['title']       = self.get_text_first(content.css(".userTitle"))
            useritem['banner']      = self.get_text_first(content.css(".userBanner"))

            try:
                m = re.match('members/([^/]+)', urlparse(response.url).query.strip('/'))
                m2 = re.match("(.+\.)?(\d+)$", m.group(1))
                useritem['user_id'] = m2.group(2)
            except:
                pass

            infos = content.css(".infoBlock dl")
            for info in infos:
                name = info.css('dt::text').extract_first().strip()
                try:
                    if name == 'Last Activity:':
                        useritem['last_activity'] = self.read_datetime_div(info.css('dd .DateTime'))
                    elif name == 'Joined:' :
                        useritem['joined_on'] = self.read_datetime_div(info.css('dd'))
                    elif name == 'Messages:':
                        numberstr = self.get_text_first(info.css('dd'))
                        useritem['message_count'] = int(numberstr.replace(',', ''))
                    elif name == 'Likes Received:':
                        numberstr = self.get_text_first(info.css('dd'))
                        useritem['likes_received'] = int(numberstr.replace(',', ''))
                except:
                    pass

            yield useritem


    def handle_login_response(self, response):
        if self.islogged(response):
            self.logger.info('Login success, continuing where we were.')
            if response.meta['req_once_logged']:
                yield response.meta['req_once_logged']
            else:
                self.logger.error("No request was given for when the login succeeded. Can't continue")
        else :   # Not logged, check for captcha
            self.logintrial +=1
            self.logger.info("Trying to login")
            if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                self.wait_for_input("Too many failed login trials. Giving up.", response.meta['req_once_logged'])
                self.logintrial=0
                return 


            loginform = response.css("form[id='pageLogin']")
            if loginform:
                captcha = loginform.css("#Captcha")
                if captcha:
                    question = captcha.css('label::text').extract_first()
                    qhash = captcha.css("input[name='captcha_question_hash']::attr(value)").extract_first()   # This hash is not repetitive
                    dbhash = hashlib.sha256(question).hexdigest() # This hash is reusable
                    self.logger.info('Login failed. A captcha question has been asked.  Question : "' + question + '"')  
                    db_question = self.dao.get_or_create(models.CaptchaQuestion, forum=self.forum, hash=dbhash)
                    answer = ""
                    if db_question.answer:
                        answer = db_question.answer
                        self.logger.info('Question was part of database. Using answer : ' + answer)
                    else:
                        if not db_question.question:
                            db_question.question = question
                            self.dao.enqueue(db_question)
                        answer = LoginQuestion.answer(question, self.login)
                        self.logger.info('Trying to guess the answer. Best bet is : "%s"' % answer)
                    yield self.make_request(reqtype='dologin', req_once_logged= response.meta['req_once_logged'], captcha_question_hash=qhash, captcha_question_answer=answer);  # We try to login and save the original request

                else : 
                    self.logger.warning("Login failed. A new login form has been given, but with no captcha. Trying again.")
                    yield self.make_request(reqtype='dologin', req_once_logged=response.meta['req_once_logged']);  # We try to login and save the original request
            else :
                self.logger.error("Login failed and no login form has been given. Retrying")
                yield self.make_request(reqtype='dologin', req_once_logged=response.meta['req_once_logged']);  # We try to login and save the original request
                
    def islogged(self, response):
        logged = False
        username = response.css(".accountUsername::text").extract_first()
        if username and username.strip() == self.login['username']:
            logged = True
        
        if not logged:
            self.logger.debug("Not Logged In")

        return logged

    def isloginpage(self, response):
        if response.css("form[id='pageLogin']"):
            return True

        return False

    def read_threadid_from_url(self, url):
        try:
            m = re.match('threads/([^/]+)(/page-\d+)?', urlparse(url).query.strip('/'))
            m2 = re.match("(.+\.)?(\d+)$", m.group(1))
            return m2.group(2)
        except Exception as e:
            raise Exception("Could not extract thread id from url : %s. \n %s " % (url, e.message))

    def read_datetime_div(self, div):
        title = div.xpath("@title")
        time = None
        if title:
            time = AlphabayDatetimeParser.tryparse(title.extract_first())

        datestring = div.xpath("@data-datestring").extract_first()
        timestring = div.xpath("@data-timestring").extract_first()

        if datestring and timestring:
            time = AlphabayDatetimeParser.tryparse("%s %s" % (datestring, timestring))

        text = self.get_text_first(div)
        if text:
            time = AlphabayDatetimeParser.tryparse(text)

        if time:
            return self.to_utc(time)

