# -*- coding:utf-8 -*-
import re
import json
import traceback
import logging
from scrapy.spiders import Spider
from scrapy.http import Request
from douban.items import RecommendItem
from douban.spiders.base.douban_common import common_parse_recommend
try:
    from douban.hades_db.db_mgr import DbManager
    from douban.hades_db.mongo_mgr import MongoMgr
except ImportError:
    from hades_db.db_mgr import DbManager
    from hades_db.mongo_mgr import MongoMgr

class DoubanRecommend(Spider):
    '''
    '''
    name = 'douban_recommend'
    db_mgr = DbManager.instance()
    mongo_mgr = MongoMgr.instance()

    def __init__(self, *args, **kwargs):
        super(DoubanRecommend, self).__init__(*args, **kwargs)
        self.seen = set(self.db_mgr.get_douban_media_dou_id()) - set(self.mongo_mgr.get_recommend_dou_id())
        self._url_api = "https://movie.douban.com/subject/%s/"
        print len(self.seen)


    def start_requests(self):
        try:
            for dou_id in self.seen:
                url = self._url_api % dou_id
                yield Request(url=url, callback=self.parse_recommend)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_recommend(self, response):
        try:
            logging.log(logging.INFO, 'parse_recommend: %s' % response.request.url)
            recommendItem = common_parse_recommend(response)
            if self.check_item(recommendItem):
                return recommendItem
            else:
                return []
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def check_item(self, item):
        try:
            assert 'dou_id' in item, 'recommendItem miss dou_id'
            assert 'rec_lst' in item, 'recommendItem miss rec_lst'
            return True
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            return False
