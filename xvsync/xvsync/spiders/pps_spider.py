# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re
import time
import json
import traceback
import logging
from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.utils.project import get_project_settings

from xvsync.items import MediaVideoItem, MediaItem, VideoItem
from xvsync.extract.pps_extract import pps_extract 
from xvsync.common.util import Util
from xvsync.db.db_mgr import DbManager

class pps_spider(Spider):
    '''
        pps爬虫流程：
        (1)list列表页 -> 播放页 -> 媒体页(若存在)
        (2)播放页 -> 媒体页(若存在)
    '''
    site_code = 'pps'
    name = site_code
    mgr = DbManager.instance()
    max_mark_depth = 3 
    max_number = 100000

    #通过json传递的参数
    json_data = None

    def __init__(self, json_data=None, *args, **kwargs):
        super(pps_spider, self).__init__(*args, **kwargs)
        if json_data:
            self.json_data = json.loads(json_data)

    def start_requests(self):
        items = []
        try:
            logging.log(logging.INFO, '由于pps站点处于十分不稳定状态，所以放弃该站点的爬虫')
            '''
            for list_channel in pps_extract.list_channels_url:
                url = pps_extract.list_channels_url[list_channel]
                items.append(Request(url=url, callback=self.list_parse, meta={'level':1, 'id':list_channel}))
            '''
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items
    
    def load_member_variable(self):
        try:
            self.site_id = None 
            self.os_id = None
            self.channels_name_id = {}
            self.max_update_page = self.max_number
            res = self.mgr.get_site(self.site_code)
            if res:
                self.site_id = res['site_id']
            res = self.mgr.get_os(os_name='web')
            if res:
                self.os_id = res['os_id'] 
            for list_channel in pps_extract.list_channels:
                res = self.mgr.get_channel(channel_name=list_channel)
                if not res:
                    continue
                self.channels_name_id[list_channel] = res['channel_id']
            max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
            if max_update_page and max_update_page > 0:
                self.max_update_page = max_update_page
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def load_video_urls(self):
        items = []
        try:
            logging.log(logging.INFO, '由于pps站点处于十分不稳定状态，所以放弃该站点的爬虫')
            '''
            if self.json_data:
                cmd = self.json_data['cmd'] if 'cmd' in self.json_data else None 
                if cmd == 'trig':
                    stat = self.json_data['stat'] if 'stat' in self.json_data else None 
                    res = self.mgr.get_untrack_url(self.site_code, stat)
                    for item in res:
                        mediaVideoItem = MediaVideoItem()
                        mediaVideoItem['sid'] = item['sid']
                        mediaVideoItem['untrack_id'] = item['untrack_id']
                        mediaItem = MediaItem()
                        mediaItem['channel_id'] = item['name']
                        mediaVideoItem['media'] = mediaItem
                        url = item['url']
                        items.append(Request(url=url, callback=self.video_parse, meta={'item':mediaVideoItem}))
                elif cmd == 'assign':
                    tasks = self.json_data['task'] if 'task' in self.json_data else None 
                    for task in tasks: 
                        mediaVideoItem = MediaVideoItem()
                        mediaVideoItem['sid'] = task['sid'] if 'sid' in task else None
                        mediaVideoItem['untrack_id'] = task['untrack_id'] if 'untrack_id' in task else None
                        mediaItem = MediaItem()
                        mediaItem['channel_id'] = task['name'] 
                        mediaVideoItem['media'] = mediaItem
                        url = task['url']
                        items.append(Request(url=url, callback=self.video_parse, meta={'item':mediaVideoItem}))
            '''
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    def list_parse(self, response):
        try:
            request_url = response.request.url
            logging.log(logging.INFO, 'url: %s' % request_url)
            prefix_url = Util.prefix_url_parse(request_url)
            level = response.request.meta['level'] if 'level' in response.request.meta else -1
            channel_id = response.request.meta['id'] if 'id' in response.request.meta else None
            sels = response.xpath('//div[@class="retrieval"]//dl[@class="retrieval-dl"]')
            if self.max_mark_depth > 0:
                size = self.max_mark_depth if self.max_mark_depth < len(sels) else len(sels)
            else:
                size = len(sels)
            if level <= size:
                sel = sels[level - 1]
                level = level + 1
                urls = sel.xpath('.//ul[@class="retrieval-list"]//a/@href').extract()
                for url in urls:
                    url = Util.get_absolute_url(url, prefix_url)
                    items.append(Request(url=url, callback=self.list_parse, meta={'level':level, 'id':channel_id}))
            #获取当前层的所有list数据
            #按照排序方式再进行细分一次
            urls = response.xpath('//div[@class="filter"]//ul[@class="tab-sya"]//li/a/@href').extract()
            for url in urls:
                url = Util.get_absolute_url(url, prefix_url)
                items.append(Request(url=url, callback=self.list_html_parse, meta={'page':1, 'id':channel_id}))
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'url: %s' % request_url)
        finally:
            return items
  
    def list_html_parse(self, response):
        items = []
        try:
            request_url = response.request.url
            logging.log(logging.INFO, 'list html url: %s' % request_url)
            page = response.request.meta['page'] if 'page' in response.request.meta else 1
            if page > self.max_update_page:
                return items
            channel_id = response.request.meta['id'] if 'id' in response.request.meta else None
            results = pps_extract.media_extract(response)
            for item in results:
                mediaVideoItem = MediaVideoItem()
                item['channel_id'] = channel_id
                url = item['url']
                url = Util.get_absolute_url(url, request_url)
                item['url'] = url
                mediaVideoItem['media'] = item
                items.append(Request(url=url, callback=self.video_parse, meta={'item':mediaVideoItem}))
            #下一页
            page = page + 1
            results = pps_extract.next_page_extract(response)
            for item in results:
                url = Util.get_absolute_url(item, request_url)
                items.append(Request(url=url, callback=self.list_html_parse, meta={'page':page, 'id':channel_id}))
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    def video_parse(self, response):
        items = []
        try:
            request_url = response.request.url
            logging.log(logging.INFO, 'video url: %s' % request_url)
            prefix_url = Util.prefix_url_parse(request_url)
            mediaVideoItem = response.request.meta['item'] if 'item' in response.request.meta else MediaVideoItem()
            mediaItem = mediaVideoItem['media'] if 'media' in mediaVideoItem else MediaItem()
            pps_extract.media_extract(response, mediaItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'video url: %s' % request_url)
        finally:
            return items

    def media_parse(self, response):
        items = []
        try:
            return
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'media url: %s' % request_url)
        finally:
            return items
