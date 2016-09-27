# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from zimu.items import SubtitleItem
import logging
import traceback
try:
    from zimu.hades_db.db_mgr import DbManager
except ImportError:
    from hades_db.db_mgr import DbManager

class MysqlStorePipeline(object):
    def __init__(self):
        self.__db_mgr = DbManager.instance()

    def process_item(self, item, spider):
        try:
            if isinstance(item, SubtitleItem):
                item_dict = dict(item)
                self.__db_mgr.insert_subtitle(item_dict)

            return item
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            
            
            
