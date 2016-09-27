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

class letv_cat(Spider):
    name = "letv_cat"
    pipelines = ['MysqlStorePipeline']
    spider_id = "524288"
    site_id = "15"   
    max_search_page = 1

    mgr = DbManager.instance()

    def __init__(self, *args, **kwargs):
        super(letv_cat, self).__init__(*args, **kwargs)
        self._cat_urls = []
        self._page_api = "http://list.le.com/apin/chandata.json?c=%s&d=%s&md=%s&o=%s&p=%s&t=%s"
        self._le_url = "http://www.le.com/ptv/vplay/%s.html"
        self._max_page = 5
        try:
            self._cat_urls = self.mgr.get_cat_url('letv')
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def start_requests(self):
        try:
            items = []

            for cat in self._cat_urls:   
                items.extend([Request(url=cat['url'], callback=self.parse_page,meta={'cat_name': cat['cat_name'],'audit':cat['audit'],'priority':cat['priority']})])
                ret = self.parse_info_from_url(cat['url'])
                for p in range(self._max_page):
                    url = self._page_api % (ret['c'], ret['d'], ret['md'], ret['o'], str(p+1), ret['t'])
                    items.extend([Request(url=url, callback=self.parse_page_json,meta={'cat_name': cat['cat_name'],'audit':cat['audit'],'priority':cat['priority']})])
                    
            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)
            
    def parse_page_json(self, response):
        try:
            cat_name = response.request.meta['cat_name']
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']
            items = []
            json_data = json.loads(response.body)
            for item in json_data['data_list']:
                vid = item['vid']
                url = self._le_url % (vid)
                lens = item['duration']
                images = item['images']
                if '180*135' in images:
                    thumb = images['180*135']
                    items.append(Request(url=url, callback=self.parse_episode, meta={'cat_name': cat_name, 'thumb': thumb,'audit':audit,'lens':lens,'priority':priority}))
            
            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_page(self, response):
        try:
            cat_name = response.request.meta['cat_name']
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']

            items = []
            #video items
            qy_v = response.xpath('//div[@class="layout"]/dl')
            for v in qy_v:
                thumb = v.xpath('./dt/a/img/@src').extract()
                url = v.xpath('./dt/a/@href').extract()
                lens = v.xpath('./dt/a/span[@class="number_bg"]/text()').extract()[0]
                try:
                    if not lens:
                        lens=0
                    else:
                        a,b=lens.split(':')
                        lens = int(a)*60+int(b)
                
                    items.append(Request(url=url[0].strip(), callback=self.parse_episode, meta={'cat_name': cat_name, 'thumb': thumb,'audit':audit,'lens':lens,'priority':priority}))
                except Exception as e:
                    continue
            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_episode(self, response):
        try:
            log.msg('parse_episode %s' % response.request.url)
            cat_name = response.request.meta['cat_name']
            thumb_url = response.request.meta['thumb']
            audit = response.request.meta['audit']
            lens = response.request.meta['lens']
            priority = response.request.meta['priority']
            items = []

            #show_id
            show_id = Util.get_letv_showid(response.request.url)
            albumid = response.selector.re(re.compile(r'pid: ?(\d+)'))
            #video info
            title = response.xpath('//meta[@name="irTitle"]/@content').extract()
            upload_time = response.xpath('//ul[@class="info_list"]//em[@id="video_time"]/text()').extract()
            tag_sel = response.xpath('//meta[@name="keywords"]/@content').extract()
            ep_item = EpisodeItem()
            if title:
                ep_item['title'] = title[0]
            if show_id:
                ep_item['show_id'] = show_id
            if tag_sel:
                tag_str = tag_sel[0][len(title[0]) + 1:]
                if tag_str:
                    tag_list = []
                    split_space = tag_str.split(' ')
                    for item_space in split_space:
                        split_comma = item_space.split(',')
                        for item_comma in split_comma:
                            tag_list.append(item_comma)
                    
                    ep_item['tag'] =  "|".join([t.strip() for t in tag_list])
            if upload_time:
                ep_item['upload_time'] = upload_time[0].strip()
            if thumb_url:
                ep_item['thumb_url'] = thumb_url[0].strip()

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url
            ep_item['category'] = cat_name
            ep_item['format_id'] = '2'
            ep_item['audit'] = audit
            ep_item['priority'] =priority
            ep_item['duration'] = lens
            items.append(ep_item)

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)
            
    def parse_info_from_url(self, url):
        result = {}
        keys = ['c', 't', 'md', 'o', 'd', 'p']
        info_str = url.split('/')[-1].split('.')[0]
        key_value = info_str.split('_')
        for item in key_value:
            for key in keys:
                if item[0:len(key)] == key:
                    result[key] = item[len(key):]
                    
        return result
                    


