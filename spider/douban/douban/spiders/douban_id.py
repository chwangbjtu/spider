# -*- coding:utf-8 -*-
import re
import json
import traceback
import logging
from itertools import product
from dateutil import parser
from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.selector import Selector
from douban.items import MediaItem
from douban.spiders.base.douban_common import common_parse_media_plus, get_cookie, common_parse_recommend
try:
    from douban.hades_db.db_mgr import DbManager
    from douban.hades_db.mongo_mgr import MongoMgr
except ImportError:
    from hades_db.db_mgr import DbManager
    from hades_db.mongo_mgr import MongoMgr

class DoubanId(Spider):
    '''
    '''
    name = 'douban_id'
    site_code = 'douban'
    dbmgr = DbManager.instance()
    mongomgr = MongoMgr.instance()

    def __init__(self, *args, **kwargs):
        super(DoubanId, self).__init__(*args, **kwargs)
        self.site_id = self.dbmgr.get_site_id_by_code(self.site_code)
        self._url_api = "https://movie.douban.com/subject/%s/"
        self.seen = set()

    def prepare_data(self):
        lst1 = self.mongomgr.get_recommend_rec()
        lst2 = self.mongomgr.get_user_douId()
        lst3 = self.dbmgr.get_media_dou_id()
        set1 = set(self.dbmgr.get_douban_media_dou_id())
        self.seen.update(map(int, lst1))
        self.seen.update(map(int, lst2))
        self.seen.update(map(int, lst3))
        self.seen = self.seen - set1
        self.seen.update()

    def start_requests(self):
        try:
            self.prepare_data()
            print len(self.seen)
            for dou_id in list(self.seen):
                yield Request(url=self._url_api % dou_id, callback=self.parse_media)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_media(self, response):
        try:
            items = []
            logging.log(logging.INFO, 'parse_media: %s' % response.request.url)
            mediaItem = common_parse_media_plus(response)
            vcount = mediaItem['vcount'] if 'vcount' in mediaItem else 1
            mediaItem['site_id'] = self.site_id
            items.append(mediaItem)
            recommendItem = common_parse_recommend(response)
            items.append(recommendItem)
            return mediaItem
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            return mediaItem

