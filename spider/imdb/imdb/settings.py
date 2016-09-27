# -*- coding: utf-8 -*-

# Scrapy settings for crawler project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'imdb'

SPIDER_MODULES = ['imdb.spiders']
NEWSPIDER_MODULE = 'imdb.spiders'

#MAX_SEARCH_PAGE
# 0:爬取全部
# N：增量更新前N页
MAX_UPDATE_PAGE = 0

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36'

COOKIES_ENABLED = False
#DOWNLOAD_DELAY = 0.1
CONCURRENT_ITEMS = 400
CONCURRENT_REQUESTS = 64
#The maximum number of concurrent (ie. simultaneous) requests that will be performed to any single domain.
CONCURRENT_REQUESTS_PER_DOMAIN = 256
CONCURRENT_REQUESTS_PER_IP = 32
DEPTH_LIMIT = 0
#DEPTH_PRIORITY = 0
#DNSCACHE_ENABLED = True

DEPTH_PRIORITY = 1
#SCHEDULER_DISK_QUEUE = 'scrapy.squeue.PickleFifoDiskQueue'
#SCHEDULER_MEMORY_QUEUE = 'scrapy.squeue.FifoMemoryQueue'


'''
#AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_CONCURRENCY_CHECK_PERIOD = 10#How many responses should pass to perform concurrency adjustments.
'''

ITEM_PIPELINES = {
    'imdb.pipelines.MysqlStorePipeline': 100,
}

if False:
    SCHEDULER = "scrapy_redis.scheduler.Scheduler"
    SCHEDULER_PERSIST = True
    REDIS_URL = 'redis://tt:funshion@127.0.0.1:6379'
    SCHEDULER_IDLE_BEFORE_CLOSE = 10

'''
LOG_ENABLED = True
LOG_ENCODING = 'utf-8'
LOG_FILE = '/tmp/crawler.log'
LOG_STDOUT = True
'''
 
DOWNLOADER_MIDDLEWARES = {
    'imdb.pipelines.WebkitDownloader': 551
}

LOG_LEVEL = 'INFO'
