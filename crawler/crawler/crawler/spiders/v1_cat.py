# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from scrapy.spider import Spider
from scrapy.selector import Selector
from scrapy.http import Request
from scrapy import log
from scrapy.utils.project import get_project_settings
from crawler.common.util import Util
from crawler.items import EpisodeItem, UserItem
from crawler.db.db_mgr import DbManager
from datetime import datetime
import traceback
import re
import json

class v1_cat(Spider):
    name = "v1_cat"
    pipelines = ['MysqlStorePipeline']
    spider_id = "10"
    site_id = "17"   
    max_search_page = 1
    mgr = DbManager.instance()

    def __init__(self, *args, **kwargs):
        super(v1_cat, self).__init__(*args, **kwargs)
        self._cat_urls = []
        try:
            self._cat_urls = self.mgr.get_cat_url('v1')
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def start_requests(self):
        try:
            items = []

            for cat in self._cat_urls:
                items.extend([Request(url=cat['url'], callback=self.parse_page,meta={'cat_name': cat['cat_name'],'audit':cat['audit'],'priority':cat['priority']})])

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_page(self, response):
        try:
            #log.msg('parse page %s: %s' % (response.request.url, response.request.meta['page']))
            cat_name = response.request.meta['cat_name']
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']
            items = []
            qy_v = response.xpath('//div[@id="addMore"]/ul/li')
            print len(qy_v)
            for v in qy_v:
                thumb = v.xpath('./div[@class="lists"]/a/img/@src').extract()
                url = v.xpath('./div[@class="lists"]/a/@href').extract()
                if url:
                    items.append(Request(url=url[0].strip(), callback=self.parse_episode, meta={'cat_name': cat_name, 'audit':audit,'priority':priority,'thumb':thumb}))
            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_episode(self, response):
        try:
            log.msg('parse_episode %s' % response.request.url)
            #cat_id = response.request.meta['cat_id']
            cat_name = response.request.meta['cat_name']
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']
            thumb = response.request.meta['thumb']
            items = []

            show_id = Util.get_v1_showid(response.request.url)
            title = response.xpath('//meta[@name="title"]/@content').extract()
            tags = response.xpath('//meta[@name="keywords"]/@content').extract()
            ep_item = EpisodeItem()
            if title:
                ep_item['title'] = title[0].strip()
            if show_id:
                ep_item['show_id'] = show_id
            if tags:
                ep_item['tag'] =  tags[0].strip()

            ep_item['thumb_url'] = thumb[0].strip()
            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url
            #ep_item['cat_id'] = cat_id
            ep_item['category'] = cat_name
            #ep_item['description'] = item.get("description")
            ep_item['format_id'] = '2'
            ep_item['audit'] = audit
            ep_item['priority'] =priority
            #ep_item['played'] = item.get('play')
            #ep_item['upload_time'] = item.get('create')
            #duration = item.get('duration')
            #if duration:
            #    a,b=duration.split(':')
            #    duration = int(a)*60+int(b)
            #else:
            #    duration = 0
            #ep_item['duration'] = duration
            items.append(ep_item)
                
            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)


