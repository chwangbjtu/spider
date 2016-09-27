# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import logging
import traceback
from douban.items import MediaItem, RecommendItem, ReviewItem, UserInfoItem, ImdbChiefItem

try:
    from douban.hades_db.db_mgr import * 
    from douban.hades_db.mongo_mgr import MongoMgr
except ImportError:
    from hades_db.db_mgr import *
    from hades_db.mongo_mgr import MongoMgr

class DoubanPipeline(object):
    def __init__(self):
        #self.__db_mgr = DbManager.instance()
        self.__db_mgr = create_instance()
        self.__mongo_mgr = MongoMgr.instance()

    def process_item(self, item, spider):
        try:
            if isinstance(item, MediaItem):
                self.__db_mgr.insert_douban(item)
            elif isinstance(item, RecommendItem):
                self.__mongo_mgr.insert_update_recommend(item)
            elif isinstance(item, ReviewItem):
                self.__mongo_mgr.insert_update_review(item)
            elif isinstance(item, UserInfoItem):
                self.__mongo_mgr.insert_update_user(item)
            elif isinstance(item, ImdbChiefItem):
                self.__db_mgr.update_imdb_chief(item)
            else:
                pass
            return item
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

