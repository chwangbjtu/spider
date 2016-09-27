# -*- coding:utf-8 -*-
import re
import json
import urllib
import traceback
import logging
from itertools import product
from dateutil import parser
from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.selector import Selector
from douban.items import MediaItem
from douban.spiders.base.douban_common import common_parse_media, common_parse_media_plus
try:
    from douban.hades_db.db_mgr import DbManager
    #from douban.hades_db.mongo_mgr import MongoMgr
except ImportError:
    from hades_db.db_mgr import DbManager
    #from hades_db.mongo_mgr import MongoMgr
class DoubanId(Spider):
    '''
    '''
    name = 'douban_search'
    site_code = 'douban'
    dbmgr = DbManager.instance()
    #pomgr = DbManager.dynamic_instance("192.168.16.165", "root", "funshion", "db_poseidon_media", 3306)

    def __init__(self, *args, **kwargs):
        super(DoubanId, self).__init__(*args, **kwargs)
        self.site_id = self.dbmgr.get_site_id_by_code(self.site_code)
        #self._search_api = "https://movie.douban.com/subject_search?search_text=%s"
        self._search_api = "https://www.douban.com/search?cat=1002&q=%s" # 更准确
        self._url_api = "https://movie.douban.com/subject/%s/"
        self.seen = set(self.dbmgr.get_douban_media_dou_id())
        #self.titles = self.pomgr.get_fm_media_title()
        self.titles = self.dbmgr.get_media_title()


    def start_requests(self):
        try:
            for title in self.titles:
                t = self.process_str(title)
                yield Request(url=self._search_api % title, callback=self.parse_search)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_search(self, response):
        try:
            logging.log(logging.INFO, 'parse_search: %s' % response.request.url)
            url_results = response.xpath('//div[@class="result"]/div[@class="pic"]/a/@href').extract()
            if url_results:
                dou_ids = filter(self.carry_on, map(self.get_dou_id, url_results))
                for dou_id in dou_ids:
                    yield Request(url=self._url_api % dou_id, callback=self.parse_media)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def process_str(self, title):
        try:
            # 去掉数字
            r = re.compile(u'^([\u4e00-\u9fa5]+).*')
            m = r.match(title)
            if m:
                t = m.groups()[0]
            else:
                t = re.sub(r'([_\d+])','', title)
                t = t.replace('Season', '')
            return t
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_media(self, response):
        try:
            logging.log(logging.INFO, 'parse_media: %s' % response.request.url)
            mediaItem = common_parse_media_plus(response)
            vcount = mediaItem['vcount'] if 'vcount' in mediaItem else 1
            mediaItem['site_id'] = self.site_id
            self.seen.add(mediaItem['dou_id'])
            return mediaItem
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_dou_id(self, url):
        try:
            # https://www.douban.com/link2/?url=https://movie.douban.com/subject/3035040/&query=红&cat_id=1002&type=search&pos=0
            url = urllib.unquote(url)
            return int(url.split('=')[1].split('/')[4])
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def carry_on(self, dou_id):
        return dou_id not in self.seen

