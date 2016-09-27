# -*- coding: utf-8 -*-
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
import logging
import traceback
from douban.items import MediaItem
from douban.spiders.base.douban_common import common_parse_media
try:
    from douban.hades_db.db_mgr import DbManager
    #from douban.hades_db.mongo_mgr import MongoMgr
except ImportError:
    from hades_db.db_mgr import DbManager
    #from hades_db.mongo_mgr import MongoMgr

class DoubanSpread(CrawlSpider):
    name = 'douban_spread'
    site_code = 'douban'
    mgr = DbManager.instance()
    allowed_domains = ['movie.douban.com', 'www.douban.com']

    rules = (
            Rule(LinkExtractor(allow=r'https://movie.douban.com/subject/\d+/$', tags=('a',)), callback='parse_media', follow=True),
            Rule(LinkExtractor(allow=r'https://movie.douban.com/subject/\d+/\?from=.*', tags=('a',)), callback='parse_media', follow=True),
            Rule(LinkExtractor(allow=r'.*/doulist/.*', tags=('a',)), follow=True),
            Rule(LinkExtractor(allow=r'.*/celebrity/\d+/.*', tags=('a',)), follow=True), 
            Rule(LinkExtractor(allow=r'.*/typerank?.*', tags=('a',)), follow=True), 
            Rule(LinkExtractor(allow=r'.*/chart.*', tags=('a',)), follow=True), 
            Rule(LinkExtractor(allow=r'https://movie.douban.com/tag.*', tags=('a',)), follow=True), 
            Rule(LinkExtractor(allow=r'https://movie.douban.com/tv.*', tags=('a',)), follow=True), 
            Rule(LinkExtractor(allow=r'https://movie.douban.com/explore.*', tags=('a',)), follow=True), 
            Rule(LinkExtractor(allow=r'.*/awards.*', tags=('a',)), follow=True), 
            Rule(LinkExtractor(allow=r'.*/top250.*', tags=('a',)), follow=True), 
            Rule(LinkExtractor(allow=r'.*/annual2015.*', tags=('a',)), follow=True), 
            Rule(LinkExtractor(allow=r'.*/people/\w+/', tags=('a',)), follow=True), 
            Rule(LinkExtractor(allow=r'.*/people/\w+/do.*', tags=('a',)), follow=True), 
            Rule(LinkExtractor(allow=r'.*/people/\w+/wish.*', tags=('a',)), follow=True), 
            Rule(LinkExtractor(allow=r'.*/people/\w+/collect.*', tags=('a',)), follow=True), 
            Rule(LinkExtractor(allow=r'.*nowplaying.*', tags=('a',)), follow=True), 
    )

    start_urls = ['https://movie.douban.com/']

    def __init__(self, *args, **kwargs):
        super(DoubanSpread, self).__init__(*args, **kwargs)
        self.site_id = self.mgr.get_site_id_by_code(self.site_code)
        self.start_urls.extend(self.mgr.get_douban_media_urls())
        #self.start_urls = ['https://movie.douban.com/subject/1295644/']

    def parse_media(self, response):
        try:
            logging.log(logging.INFO, 'parse_media: %s' % response.request.url)
            mediaItem = common_parse_media(response)
            vcount = mediaItem['vcount'] if 'vcount' in mediaItem else 1
            mediaItem['site_id'] = self.site_id
            print mediaItem
            return mediaItem
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            return mediaItem

