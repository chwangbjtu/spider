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

class bilibili_cat(Spider):
    name = "bilibili_cat"
    pipelines = ['MysqlStorePipeline']
    spider_id = "5"
    site_id = "13"   
    max_search_page = 1
    url_prefix = "http://www.bilibili.com/index/tag/%s/default/1/%s.json"
    mgr = DbManager.instance()

    def __init__(self, *args, **kwargs):
        super(bilibili_cat, self).__init__(*args, **kwargs)
        self._cat_urls = []
        try:
            self._cat_urls = self.mgr.get_cat_url('bilibili')
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
            #video items
            id = response.xpath('//div[@class="fcname"]/ul/li[@class="on"]/@tid').extract()
            tag = response.xpath('//div[@class="fcname"]/ul/li[@class="on"]/a/text()').extract()
            if tag[0].strip() == u'全部':
                id = response.xpath('//div[@class="menu-wrapper"]/ul/li[@class="m-i  on"]/@data-tid').extract()
                tag = response.xpath('//div[@class="menu-wrapper"]/ul/li[@class="m-i  on"]/a/em/text()').extract()
            if id and tag:
                url = self.url_prefix % (id[0].strip(),tag[0].strip())
                print url
                items.append(Request(url=url, callback=self.parse_episode, meta={'cat_name': cat_name, 'audit':audit,'priority':priority}))
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
            items = []
            data = json.loads(response.body)
            list = data.get('list')
            for item in list:
                ep_item = EpisodeItem()
                ep_item['title'] = item.get('title')
                ep_item['show_id'] = item.get('aid')
                #ep_item['tag'] =  item.get()
                ep_item['thumb_url'] = item.get('pic')
                ep_item['spider_id'] = self.spider_id
                ep_item['site_id'] = self.site_id
                ep_item['url'] = "http://www.bilibili.com/video/av%s/" % item.get('aid')
                #ep_item['cat_id'] = cat_id
                ep_item['category'] = cat_name
                ep_item['description'] = item.get("description")
                ep_item['format_id'] = '2'
                ep_item['audit'] = audit
                ep_item['priority'] =priority
                ep_item['played'] = item.get('play')
                #ep_item['upload_time'] = item.get('create')
                duration = item.get('duration')
                if duration:
                    a,b=duration.split(':')
                    duration = int(a)*60+int(b)
                else:
                    duration = 0
                ep_item['duration'] = duration
                items.append(ep_item)
                
            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)


