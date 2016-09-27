# -*- coding:utf-8 -*-

# Scrapy settings for crawler project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'crawler'

SPIDER_MODULES = ['crawler.spiders']
NEWSPIDER_MODULE = 'crawler.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'

COOKIES_ENABLED = False
DOWNLOAD_DELAY = 0.1
CONCURRENT_ITEMS = 400
CONCURRENT_REQUESTS = 64
#The maximum number of concurrent (ie. simultaneous) requests that will be performed to any single domain.
CONCURRENT_REQUESTS_PER_DOMAIN = 256
CONCURRENT_REQUESTS_PER_IP = 32
DEPTH_LIMIT = 0
DEPTH_PRIORITY = 0
DNSCACHE_ENABLED = True

NEWEST_TIME_THRESHOLD = 480 #2h, 120min
NEWEST_PLAYED_THRESHOLD = 200
HOTTEST_TIME_THRESHOLD = 10080 #7day, 10080min
HOTTEST_PLAYED_THRESHOLD = 2000
MAX_SEARCH_PAGE = 4 #max search page:no need to search all pages. but avaliable for auto spider
MAX_MANUAL_SEARCH_PAGE = 40 #max manual search page:no need to search all pages. but avaliable for manual spider
ORDERED_PLAYED_THRESHOLD = 1000

CATEGORY_FILTER_LIST = [u'新闻', u'资讯']

ITEM_PIPELINES = {
    'crawler.pipelines.NewestItemPipeline': 90,
    'crawler.pipelines.HottestItemPipeline': 91,
    'crawler.pipelines.CategoryFilterPipeline': 92,
    'crawler.pipelines.CategoryPipeline': 93,
    'crawler.pipelines.MysqlStorePipeline': 100,
}

EXTENSIONS = {
    'scrapy.contrib.feedexport.FeedExporter': None,
}

'''
#AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3.0
AUTOTHROTTLE_CONCURRENCY_CHECK_PERIOD = 10#How many responses should pass to perform concurrency adjustments.
'''

'''
RETRY_HTTP_CODES = [500, 502, 503, 504, 400, 403, 404, 408]
RETRY_TIMES = 5

PROXY_LIST = ['/tmp/proxies.txt', '/tmp/proxies.txt.bak']
USER_AGENTS_LIST_FILE = '/tmp/ua.txt'
DOWNLOADER_MIDDLEWARES = {
    'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware' : None,
    'crawler.middleware.ua_mw.RandomUserAgentMiddleware' :80,
    'scrapy.contrib.downloadermiddleware.retry.RetryMiddleware': 90,
    'crawler.middleware.proxy_mw.RandomProxy': 100,
    'scrapy.contrib.downloadermiddleware.httpproxy.HttpProxyMiddleware': 110,
}
'''

RETRY_HTTP_CODES = [500, 502, 503, 504, 400, 403, 404, 408]
RETRY_TIMES = 5

PROXY_HOST = 'http://125.88.157.200:40080'
DOWNLOADER_MIDDLEWARES = {
    'scrapy.contrib.downloadermiddleware.retry.RetryMiddleware': 90,
    'crawler.middleware.proxy_mw.SpecificProxy': 100,
    #'scrapy.contrib.downloadermiddleware.httpproxy.HttpProxyMiddleware': 110,
}



LOG_LEVEL = 'INFO'
'''
LOG_ENABLED = True
LOG_ENCODING = 'utf-8'
LOG_FILE = '/tmp/crawler.log'
LOG_STDOUT = True
'''
