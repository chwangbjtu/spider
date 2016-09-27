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

class ifeng_cat(Spider):
    name = "ifeng_cat"
    pipelines = ['MysqlStorePipeline']
    spider_id = "9"
    site_id = "4"   
    max_search_page = 1
    mgr = DbManager.instance()

    def __init__(self, *args, **kwargs):
        super(ifeng_cat, self).__init__(*args, **kwargs)
        self._cat_urls = []
        try:
            self._cat_urls = self.mgr.get_cat_url('ifeng')
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def start_requests(self):
        try:
            items = []

            for cat in self._cat_urls:
                print cat
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
            qy_v = response.xpath('//div[@class="listwrap"]/div/ul/li')
            for v in qy_v:
                thumb = v.xpath('./div[@class="pic"]/a/img/@src').extract()
                url = v.xpath('./div[@class="pic"]/a/@href').extract()
                lens = v.xpath('./div[@class="pic"]/span[@class="sets"]/text()').extract()
                if lens:
                    try:
                        a,b=lens[0].strip().split(':')
                        lens = int(a)*60+int(b)
                    except Exception as e:
                        lens = 0
                else:
                    lens = 0
                if url:
                    items.append(Request(url=url[0].strip(), callback=self.parse_episode, meta={'cat_name': cat_name, 'thumb': thumb,'audit':audit,'priority':priority,'lens':lens}))
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
            lens = response.request.meta['lens']
            items = []
            
            show_id = Util.get_ifeng_showid(response.request.url)
            title = response.xpath('//head/meta[@property="og:title"]/@content').extract()
            tags = response.xpath('//div[@class="protag"]/a/text()').extract()
            upload_time = response.xpath('//div[@class="vTit_wrap"]/div/p/span[@class="data"]/text()').extract()
            #video info
            ep_item = EpisodeItem()
             
            if title:
                ep_item['title'] = title[0].strip()
            if show_id:
                ep_item['show_id'] = show_id
            if tags:
                ep_item['tag'] = '|'.join(tags)
            if thumb_url:
                ep_item['thumb_url'] = thumb_url[0].strip()
            if upload_time:
                ep_item['upload_time'] = upload_time[0]

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url
            #ep_item['cat_id'] = cat_id
            ep_item['category'] = cat_name
            ep_item['format_id'] = '2'
            ep_item['audit'] = audit
            ep_item['priority'] =priority
            ep_item['duration'] = lens
            items.append(ep_item)

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)


