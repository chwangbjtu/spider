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

class Acfun_cat(Spider):
    name = "acfun_cat"
    pipelines = ['MysqlStorePipeline']
    spider_id = "3"
    site_id = "12"   
    max_search_page = 1
    request_url = "http://www.acfun.tv/dynamic/channel/1.aspx?channelId=%s&orderBy=0&pageSize=16"
    mgr = DbManager.instance()

    def __init__(self, *args, **kwargs):
        super(Acfun_cat, self).__init__(*args, **kwargs)
        self._cat_urls = []
        try:
            self._cat_urls = self.mgr.get_cat_url('acfun')
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def start_requests(self):
        try:
            items = []

            for cat in self._cat_urls:
                url = self.request_url % Util.get_acfun_showid(cat['url'])
                items.extend([Request(url=url, callback=self.parse_page,meta={'cat_name': cat['cat_name'],'audit':cat['audit'],'priority':cat['priority']})])

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
            qy_v = response.xpath('//body/div')
            for v in qy_v:
                thumb = v.xpath('./a[@class="thumb"]/img/@src').extract()
                url = v.xpath('./a[@class="thumb"]/@href').extract()
                lens = v.xpath('./a[@class="thumb"]/p/text()').extract()
                if lens:
                    try:
                        a,b=lens[0].strip().split(':')
                        lens = int(a)*60+int(b)
                    except Exception as e:
                        lens = 0
                else:
                    lens = 0
                if url:
                    items.append(Request(url=("http://www.acfun.tv%s" % url[0].strip()), callback=self.parse_episode, meta={'cat_name': cat_name, 'thumb': thumb,'audit':audit,'priority':priority,'lens':lens}))
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
            show_id = response.xpath('//div[@id="block-data-view"]/@data-aid').extract()
            title = response.xpath('//div[@id="block-data-view"]/@data-title').extract()
            tags = response.xpath('//div[@id="block-data-view"]/@data-tags').extract()
            if lens ==0:
                data_from = response.xpath('//div[@id="area-part-view"]/div/a/@data-from').extract()
                data_sid = response.xpath('//div[@id="area-part-view"]/div/a/@data-sid').extract()
                if data_sid:
                    second_request = "http://www.acfun.tv/video/getVideo.aspx?id=" + data_sid[0].strip()
                    items.append(Request(url=second_request, callback=self.parse_duration, meta={'cat_name': cat_name, 'thumb': thumb_url,'audit':audit,'priority':priority,'show_id':show_id,'title':title,'tags':tags,'url':response.request.url}))
                return items
                
            else:
                ep_item = EpisodeItem()
             
                if title:
                    ep_item['title'] = title[0].strip()
                if show_id:
                    ep_item['show_id'] = show_id[0].strip()
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
                ep_item['duration'] = lens
                items.append(ep_item)
                return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_duration(self, response):
        try:
            items = []
            cat_name = response.request.meta['cat_name']
            thumb_url = response.request.meta['thumb']
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']
            title = response.request.meta['title']
            show_id = response.request.meta['show_id']
            tags = response.request.meta['tags']
            url = response.request.meta['url']
            data = json.loads(response.body)
            success = data.get('success')
            if not success or success == 'false':
                return items
            duration = data.get('time')
            if not duration:
                return items 
            ep_item = EpisodeItem()
             
            if title:
                ep_item['title'] = title[0].strip()
            if show_id:
                ep_item['show_id'] = show_id[0].strip()
            if tags:
                ep_item['tag'] = tags[0].strip()
            if thumb_url:
                ep_item['thumb_url'] = thumb_url[0].strip()

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = url
            #ep_item['cat_id'] = cat_id
            ep_item['category'] = cat_name
            ep_item['format_id'] = '2'
            ep_item['audit'] = audit
            ep_item['priority'] =priority
            ep_item['duration'] = int(duration)
            items.append(ep_item)
            return items 
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)
