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

class tucao_cat(Spider):
    name = "tucao_cat"
    pipelines = ['MysqlStorePipeline']
    spider_id = "7"
    site_id = "14"   
    max_search_page = 1
    #request_url = "http://www.acfun.tv/dynamic/channel/1.aspx?channelId=%s&orderBy=0&pageSize=16"
    mgr = DbManager.instance()

    def __init__(self, *args, **kwargs):
        super(tucao_cat, self).__init__(*args, **kwargs)
        self._cat_urls = []
        try:
            self._cat_urls = self.mgr.get_cat_url('tucao')
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
            
            #file = open('tucao.html','w')
            #file.write(response.body)
            #file.close()
            #video items
            qy_v = response.xpath('//div[@class="list"]/ul/li')
            for v in qy_v:
                thumb = v.xpath('./div/a[@class="pic"]/img/@src').extract()
                url = v.xpath('./div/a[@class="pic"]/@href').extract()
                if url:
                    items.append(Request(url=url[0].strip(), callback=self.parse_episode, meta={'cat_name': cat_name, 'thumb': thumb,'audit':audit,'priority':priority}))
            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_episode(self, response):
        try:
            log.msg('parse_episode %s' % response.request.url)
            #cat_id = response.request.meta['cat_id']
            cat_name = response.request.meta['cat_name']
            thumb_url = response.request.meta['thumb']
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']
            items = []
            show_id = Util.get_tucao_showid(response.request.url)
            title = response.xpath('//h1[@class="show_title"]/text()').extract()
            tags = response.xpath('//meta[@name="keywords"]/@content').extract()
            #video info
            ep_item = EpisodeItem()
             
            if title:
                ep_item['title'] = title[0].strip()
            if show_id:
                ep_item['show_id'] = show_id
            if tags:
                ep_item['tag'] = tags[0].strip()
            if thumb_url:
                ep_item['thumb_url'] = thumb_url[0].strip()

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url
            #ep_item['cat_id'] = cat_id
            ep_item['category'] = cat_name
            ep_item['format_id'] = '2'
            ep_item['audit'] = audit
            ep_item['priority'] =priority
            #ep_item['duration'] = lens
            items.append(ep_item)

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)


