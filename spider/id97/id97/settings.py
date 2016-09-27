# -*- coding: utf-8 -*-

# Scrapy settings for id97 project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'id97'

SPIDER_MODULES = ['id97.spiders']
NEWSPIDER_MODULE = 'id97.spiders'

#MAX_SEARCH_PAGE
# 0:爬取全部
# N：增量更新前N页
MAX_UPDATE_PAGE = 0

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36'

COOKIES_ENABLED = False
DOWNLOAD_DELAY = 0.2
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_ITEMS = 400
CONCURRENT_REQUESTS = 64

CONCURRENT_REQUESTS_PER_DOMAIN = 256
CONCURRENT_REQUESTS_PER_IP = 32
DEPTH_LIMIT = 0
DEPTH_PRIORITY = 0

ITEM_PIPELINES = {
    'id97.pipelines.Id97Pipeline': 100,
}

LOG_LEVEL = 'INFO'


