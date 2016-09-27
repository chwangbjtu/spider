# -*- coding:utf-8 -*-
import re
import traceback
import logging
from scrapy.spiders import Spider
from scrapy.http import Request
from douban.items import ImdbChiefItem
from douban.spiders.base.douban_common import get_imdb_chief
try:
    from douban.hades_db.db_mgr import DbManager
    #from douban.hades_db.mongo_mgr import MongoMgr
except ImportError:
    from hades_db.db_mgr import DbManager
    #from hades_db.mongo_mgr import MongoMgr

class ImdbChief(Spider):
    '''
    '''
    name = 'imdb_chief'
    site_code = 'douban'
    dbmgr = DbManager.instance()

    def __init__(self, *args, **kwargs):
        super(ImdbChief, self).__init__(*args, **kwargs)
        self._imdb_api = "http://www.imdb.com/title/%s/"
        self.seen = set(self.dbmgr.get_douban_media_imdbs())

    def start_requests(self):
        try:
            for imdb in self.seen:
                yield Request(url=self._imdb_api % imdb, callback=self.parse_chief_imdb, meta={'imdb': imdb})
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_chief_imdb(self, response):
        try:
            items = []
            logging.log(logging.INFO, 'parse_chief_imdb: %s' % response.request.url)
            imdb_chief = get_imdb_chief(response)

            if not imdb_chief:
                imdb_chief = response.request.meta['imdb']

            icItem = ImdbChiefItem()
            icItem['imdb'] = response.request.meta['imdb']
            icItem['imdb_chief'] = imdb_chief

            return icItem
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

