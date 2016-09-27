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

class sohu_cat(Spider):
    name = "sohu_cat"
    pipelines = ['MysqlStorePipeline']
    spider_id = "1048576"
    site_id = "3"   #iqiyi
    max_search_page = 1

    mgr = DbManager.instance()

    def __init__(self, *args, **kwargs):
        super(sohu_cat, self).__init__(*args, **kwargs)
        self._cat_urls = []
        try:
            self._cat_urls = self.mgr.get_cat_url('sohu')
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def start_requests(self):
        try:
            items = []

            for cat in self._cat_urls:
                items.append(Request(url=cat['url'], callback=self.parse_page,meta={'page': 1, 'cat_name': cat['cat_name'],'audit':cat['audit'],'priority':cat['priority']}))

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_page(self, response):
        try:
            log.msg('parse page %s: %s' % (response.request.url, response.request.meta['page']))
            page = response.request.meta['page']
            cat_name = response.request.meta['cat_name']
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']
            #if int(page) > int(self.max_search_page):
            #    return

            items = []
            #video items
            qy_v = response.xpath('//div[@class="column-bd wemd cfix"]/ul/li')
            if not qy_v:
                qy_v = response.xpath('//div[@class="column-bd cfix"]/ul/li')
            print len(qy_v)
            for v in qy_v:
                thumb = v.xpath('./div[@class="st-pic"]/a/img/@src').extract()
                url = v.xpath('./div[@class="st-pic"]/a/@href').extract()
                lens = v.xpath('./div[@class="st-pic"]/span[@class="maskTx"]/text()').extract()
                if not lens:
                    lens = v.xpath('./div[@class="st-pic"]/a/span[@class="maskTx"]/text()').extract()
                try:
                    lens = lens[0].strip()

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
            #cat_id = response.request.meta['cat_id']
            cat_name = response.request.meta['cat_name']
            thumb_url = response.request.meta['thumb']
            audit = response.request.meta['audit']
            lens = response.request.meta['lens']
            priority = response.request.meta['priority']
            items = []

            #space maybe exist: "albumId:326754200" or "albumId: 326754200"
            #albumid = response.selector.re(re.compile(r'pid: ?(\d+)'))
            #show_id
            show_id = Util.get_sohu_showid(response.request.url)
            #tag
            tag = response.xpath('//meta[@name="keywords"]/@content').extract()
            #video info
            title = response.xpath('//div[@id="crumbsBar"]/div/div[@class="left"]/h2/text()').extract()
            #played = response.xpath('//em[@id="video_playcount"]').extract()
            ep_item = EpisodeItem()
             
            if title:
                ep_item['title'] = title[0].strip()
            if show_id:
                ep_item['show_id'] = show_id
            if tag:
                ep_item['tag'] =  tag[0].strip()
            if thumb_url:
                ep_item['thumb_url'] = thumb_url[0].strip()

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url
            #ep_item['cat_id'] = cat_id
            ep_item['category'] = cat_name
            ep_item['format_id'] = '2'
            ep_item['audit'] = audit
            ep_item['priority'] = priority
            ep_item['duration'] = lens
            #if played:
            #    ep_item['played']=played
            #if albumid:
            #    items.append(Request(url=self.playlength_url+albumid[0], callback=self.parse_playlength, meta={'item':ep_item,'albumid':albumid[0]}))
            #else:
            items.append(ep_item)

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)


