import database.settings
#from peewee import *
# -*- coding: utf-8 -*-

# Scrapy settings for scrapyprj project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'scrapyprj'

PROXIES = {	
	'debug' : "http://127.0.0.1:8118",
	#'debug' : 'http://127.0.0.1:8888'
	#"tor9050" : "http://127.0.0.1:8118",
	#"tor9051" : "http://127.0.0.1:8119",
	#"tor9052" : "http://127.0.0.1:8120",
	#"tor9053" : "http://127.0.0.1:8121"
}


SPIDER_MODULES = ['scrapyprj.spiders']
NEWSPIDER_MODULE = 'scrapyprj.spiders'

DEATHBYCAPTHA = {
	'username' : 'lemixtape',
	'password' : 'h3GnHQNxgdty'
}


MAX_LOGIN_RETRY = 5

MAIL_FROM = 'username@gmail.com'
MAIL_HOST = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USER = 'username@gmail.com'
MAIL_PASS = 'xxxxx'

MAIL_RECIPIENT = ['username@gmail.com']


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'scrapyprj (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
#DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
	'scrapyprj.middlewares.shared_queue_middleware.SharedQueueMiddleware' : 100,
	'scrapyprj.middlewares.replay_spider_middleware.ReplaySpiderMiddleware' : 101,
    'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 200,
    'scrapyprj.middlewares.reschedule_middleware.RescheduleMiddleware': 300,
	'scrapyprj.middlewares.feedback_buffer_middleware.FeedbackBufferMiddleware' : 301,
	'scrapyprj.middlewares.autoflush_middleware.AutoflushMiddleWare' :  302,
	'scrapyprj.middlewares.start_requests_cookie_middleware.StartRequestCookie' :  303
}

DOWNLOADER_MIDDLEWARES = {
	'scrapyprj.middlewares.replay_request_middleware.ReplayRequestMiddleware' : 1,
	'scrapyprj.middlewares.captcha_middleware.CaptchaMiddleware' : 200
}


#LOG_LEVEL = 'INFO'
USE_SCRAPY_LOGGING = False
LOG_SCREEN_MINMAX = ('INFO', 'WARNING')
LOG_FILE_MINMAX = ('WARNING', 'CRITICAL')
DISABLE_LOGGER  = []

CONCURRENT_REQUESTS = 16


# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    #'scrapyprj.middlewares.ProxyMiddleware': 1,
#}

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
#}

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
		'scrapyprj.pipelines.ImagePipelineFromRequest.ImagePipelineFromRequest' : 400,
		'scrapyprj.pipelines.data_formatter.DataFormatterPipeline' : 401,	# Alter some item data to make sure they are properly formatted
		'scrapyprj.pipelines.map2db.map2db': 402,    	# Convert from Items to Models
		'scrapyprj.pipelines.save2db.save2db': 403       # Sends models to DatabaseDAO. DatabaseDAO must be explicitly flushed from spider.  self.dao.flush(Model)
    }

# Enable and configure the AutoThrottle extension (disabled by default)
# See http://doc.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
