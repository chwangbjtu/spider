# -*- coding: utf-8 -*-

# Scrapy settings for ncar project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'ncar'

SPIDER_MODULES = ['ncar.spiders']
NEWSPIDER_MODULE = 'ncar.spiders'

#MAX_SEARCH_PAGE
# 0:爬取全部
# N：增量更新前N页
MAX_UPDATE_PAGE = 0

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36'

COOKIES_ENABLED = False
DOWNLOAD_DELAY = 0.2
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_ITEMS = 400
CONCURRENT_REQUESTS = 400

CONCURRENT_REQUESTS_PER_DOMAIN = 256
CONCURRENT_REQUESTS_PER_IP = 32
DEPTH_LIMIT = 0
DEPTH_PRIORITY = 0

ITEM_PIPELINES = {
    'ncar.pipelines.NcarPipeline': 100,
}

LOG_LEVEL = 'INFO'

# 要爬取的频道
# 欧美剧集 129
# 欧美影音 76
# 日韩剧集 130
# 日韩影音 77
# 港台国产影音 121
# 港台国产连续剧 131
# 亲子早教视频 160
# 动漫大陆 78
CHANNEL_SWITCH = [129]
