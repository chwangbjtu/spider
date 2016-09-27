# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from imdb.items import MediaVideoItem
from imdb.items import MediaItem
from imdb.items import ImdbMediaVideoItem
import logging
import traceback
from urllib import unquote
from scrapy.http import Request, FormRequest, HtmlResponse
try:
    from imdb.hades_db.db_mgr import DbManager
except ImportError:
    from hades_db.db_mgr import DbManager

class MysqlStorePipeline(object):
    def __init__(self):
        self.__db_mgr = DbManager.instance()

    def process_item(self, item, spider):
        try:
            if isinstance(item, MediaItem):
                #self.__db_mgr.insert_media_video(item)
                self.__db_mgr.insert_media(item)
                
            elif isinstance(item, ImdbMediaVideoItem):
                self.__db_mgr.insert_imdb_media_and_video(item)

            return item
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

class WebkitDownloader(object):
#class WebkitDownloader( DownloaderMiddleware ):
    def process_request( self, request, spider ):
        if spider.name == "qq":
            
            treq = Request(url=request.url)
            rindex =  request.url.rfind(".qq.com")
            lindex = request.url.find(".qq.com")
            #print "l and r",lindex,rindex,request.url
            if lindex != rindex:
                turl = None
                if rindex-1 > 0 and request.url[rindex-1] == 'v':
                    turl = request.url[rindex-1:]
                elif rindex-1 > 0 and request.url[rindex-1] == 'm':
                    turl = request.url[rindex-4:]
                turl1 = turl.replace("%5Cx2F","/")
                if turl1.find("http") < 0:
                    turl1 = "http://" + turl1
                treq = request.replace(url=turl1)
                return treq
            return None
