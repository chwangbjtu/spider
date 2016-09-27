# -*- coding:utf-8 -*-
# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from crawler.db.db_mgr import DbManager
from crawler.items import EpisodeItem
from crawler.items import UserItem
from scrapy import log
from scrapy.exceptions import DropItem
from crawler.common.util import Util
from datetime import datetime, timedelta
import traceback

class NewestItemPipeline(object):

    @classmethod
    def from_crawler(cls, crawler):
        up_thres = crawler.settings.get("NEWEST_TIME_THRESHOLD")
        pl_thres = crawler.settings.get("NEWEST_PLAYED_THRESHOLD")
        return cls(up_thres, pl_thres)

    def __init__(self, up_thres, pl_thres):
        self._up_thres = up_thres
        self._pl_thres = pl_thres

    def process_item(self, item, spider):
        if not item or 'NewestItemPipeline' not in getattr(spider, 'pipelines', []):
            return item
        if isinstance(item, EpisodeItem):
            if 'upload_time' in item and item['upload_time']:
                delta = Util.get_delta_minutes(datetime.now(), item['upload_time'])
                if delta >= self._up_thres:
                    log.msg("Drop late upload item: %s" % item['show_id'])
                    return
            else:
                log.msg("Drop null upload item: %s" % item['show_id'])
                return

            if 'played' in item and item['played']:
                if int(item['played']) < int(self._pl_thres):
                    log.msg("Drop less played item: %s" % item['show_id'])
                    return
            else:
                log.msg("Drop null played item: %s" % item['show_id'])
                return

            return item
        else:
            return item

class HottestItemPipeline(object):

    @classmethod
    def from_crawler(cls, crawler):
        up_thres = crawler.settings.get("HOTTEST_TIME_THRESHOLD")
        pl_thres = crawler.settings.get("HOTTEST_PLAYED_THRESHOLD")
        return cls(up_thres, pl_thres)

    def __init__(self, up_thres, pl_thres):
        self._up_thres = up_thres
        self._pl_thres = pl_thres

    def process_item(self, item, spider):
        if not item or 'HottestItemPipeline' not in getattr(spider, 'pipelines', []):
            return item
        if isinstance(item, EpisodeItem):
            '''
            if 'upload_time' in item and item['upload_time']:
                delta = Util.get_delta_minutes(datetime.now(), item['upload_time'])
                if delta >= self._up_thres:
                    log.msg("Drop late upload item: %s" % item['show_id'])
                    return
            else:
                log.msg("Drop null upload item: %s" % item['show_id'])
                return
            '''
        
            if 'played' in item and item['played']:
                if int(item['played']) < int(self._pl_thres):
                    log.msg("Drop less played item: %s" % item['show_id'])
                    return
            else:
                log.msg("Drop null played item: %s" % item['show_id'])
                return

            return item
        else:
            return item

class CategoryFilterPipeline(object):

    @classmethod
    def from_crawler(cls, crawler):
        cat_list = crawler.settings.get("CATEGORY_FILTER_LIST")
        return cls(cat_list)

    def __init__(self, cat_list):
        self._cat_list = cat_list

    def process_item(self, item, spider):
        if not item or 'CategoryFilterPipeline' not in getattr(spider, 'pipelines', []):
            return item
        if isinstance(item, EpisodeItem):
            if 'category' not in item:
                log.msg("Drop null category item: %s" % item['show_id'])
                return
            elif item['category'] in self._cat_list:
                log.msg("Drop category: %s, item: %s" % (item['category'], item['show_id']))
                return

            return item
        else:
            return item

class CategoryPipeline(object):
    def __init__(self):
        self.__db_mgr = DbManager.instance()
        self.__cdict = {}
        self.__cdict[u'电影'] = u'电影片花'
        self.__cdict[u'电视剧'] = u'电视片花'
        self.__cdict[u'综艺'] = u'综艺片花'
        self.__cdict[u'动漫'] = u'动漫片花'
        self.__cdict[u'自拍'] = u'其他'
        self.__cdict[u'创意视频'] = u'其他'
        self.__cdict[u'网剧'] = u'搞笑'
        self.__cdict[u'拍客'] = u'搞笑'
        self.__cdict[u'亲子'] = u'母婴'
        self.__cdict[u'教育'] = u'公开课'
        self.__cdict[u'原创'] = u'其他'

        #self.__ddict = {}
        #self.__ddict['资讯'] = u'del'
        #self.__ddict['微电影'] = u'del'
        self.__dlist = [u'资讯',u'微电影']
        
    def process_item(self, item, spider):
        if not item or "CategoryPipeline" not in getattr(spider, 'pipelines', []):
            return item
        try:
            if isinstance(item, EpisodeItem):
                if 'category' in item:
                    catgory = item['category']
                    if catgory in self.__dlist:
                        #print "catgory in dlist",catgory
                        return
                    if catgory in self.__cdict:
                        #print "find catgory",catgory,self.__cdict[catgory]
                        item['category'] = self.__cdict[catgory]
                if 'title' in item and item['title'].find(u'广场舞') != -1:
                    item['category'] = u'广场舞'
                if 'tag' in item and  item['tag'].find(u'汽车') != -1:
                    item['category'] = u'汽车'
                return item
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

class MysqlStorePipeline(object):
    def __init__(self):
        self.__db_mgr = DbManager.instance()

    def process_item(self, item, spider):
        if not item or 'MysqlStorePipeline' not in getattr(spider, 'pipelines', []):
            return item
        try:
            if isinstance(item, EpisodeItem):
                self.__db_mgr.insert_episode(item)
            elif isinstance(item, UserItem):
                self.__db_mgr.insert_user(item)

            return item
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
