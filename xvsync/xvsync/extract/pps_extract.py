# -*- coding:utf-8 -*-
import re
import time
import urllib
import traceback
import logging

from xvsync.common.util import Util
from xvsync.items import MediaItem, VideoItem

class pps_extract(object):

    list_channels = [u'电影', u'电视剧', u'综艺', u'动漫']
    list_channels_url = {u'电影':'http://v.pps.tv/v_list/c_movie.html',
                        u'电视剧':'http://v.pps.tv/v_list/c_tv.html',
                        u'综艺':'http://v.pps.tv/v_list/c_zy.html', 
                        u'动漫':'http://v.pps.tv/v_list/c_anime.html'}

    @staticmethod
    def media_extract(response):
        items = []
        try:
            #list列表页
            sels = response.xpath('.//div[@class="content"]//ul[@class="p-list-syd"]//li[@class="p-item"]') 
            for sel in sels:
                mediaItem = MediaItem()
                #实际为播放地址，这里暂放在mediaItem中
                urls = sel.xpath('./a/@href').extract()
                poster_urls = sel.xpath('./a/img/@src').extract()
                scores = sel.xpath('./div[@class="score"]')
                if urls:
                    mediaItem['url'] = urls[0]
                if poster_urls:
                    mediaItem['poster_url'] = poster_urls[0]
                if scores:
                    mediaItem['score'] = scores[0]
                items.append(mediaItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    @staticmethod
    def media_info_extract(response, mediaItem):
        try:
            return
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
    
    @staticmethod
    def next_page_extract(response):
        items = []
        try:
            #list列表页
            results = response.xpath('.//div[@class="page-nav-sya"]//a[@class="next pn"]/@href').extract()
            if results:
                next_page = results[0]
                items.append(next_page)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items
