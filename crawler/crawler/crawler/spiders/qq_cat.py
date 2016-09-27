# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from scrapy.spider import Spider
from scrapy.http import Request
from scrapy.http import FormRequest
import logging
from scrapy.utils.project import get_project_settings
from crawler.common.util import Util
from crawler.items import EpisodeItem, UserItem
from crawler.db.db_mgr import DbManager
from datetime import datetime
import traceback
import re
import json

class QqCatSpider(Spider):
    name = "qq_cat"
    pipelines = ['MysqlStorePipeline']
    spider_id = "4194304"
    site_id = "16"
    format_id = 2
    mgr = DbManager.instance()

    def __init__(self, *args, **kwargs):
        super(QqCatSpider, self).__init__(*args, **kwargs)
        cat_urls = kwargs.get('cats')
        if cat_urls:
            cat_urls = json.loads(cat_urls)
        else:
            cat_urls = self.mgr.get_cat_url('qq')
        if cat_urls:
            self._cat_urls = cat_urls
        else:
            self._cat_urls = []

    def start_requests(self):
        try:
            items = []
            for cat in self._cat_urls:
                items.append(Request(url=cat['url'], callback=self.parse_page, meta={'cat_id': cat['id'], 'cat_name': cat['cat_name'], 'audit': cat['audit'], 'priority': cat['priority']}))
                url = cat.pop('url')
                r = Request(url=url, callback=self.parse_page)
                r.meta.update({'cat': cat})
                items.append(r)
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_page(self, response):
        try:
            logging.log(logging.INFO, 'page:%s' % response.request.url)
            cat = response.request.meta['cat']
            items = []

            qq_v = response.xpath('//div[@class="mod_cont"]/ul/li')
            for v in qq_v:
                urls = v.xpath('./h6/a/@href').extract()
                titles = v.xpath('./h6/a/@text').extract()
                thumb_urls = v.xpath('./a/img/@src').extract()
                durations = v.xpath('./a/div/span[@class="mod_version"]/text()').extract()
                playeds = v.xpath('./p/span/text()').extract()

                title = titles[0] if titles else None
                thumb_url = thumb_urls[0] if thumb_urls else None
                duration = Util.get_qq_duration(durations[0]) if durations else None
                played = Util.normalize_played(Util.normalize_vp(playeds[0])) if playeds else None
                if urls:
                    r = Request(url=urls[0], callback=self.parse_episode)
                    d = {'title': title, 'thumb_url': thumb_url, 'duration': duration,'played': played}
                    d.update(order)
                    r.meta.update({'order': d})
                    items.append(r)
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_episode(self, response):
        try:
            logging.log(logging.INFO, 'episode:%s' % response.request.url)
            order = response.request.meta['order']
            items = []

            #video info
            #tags = response.xpath('//p[@class="info_tags"]//a/@title').extract()
            #descriptions = response.xpath('//div[@class="info_summary cf"]/span/text()').extract()

            ep_item = EpisodeItem()
            ep_item['show_id'] = Util.get_qq_showid(response.request.url)
            #if tags:
            #    ep_item['tag'] = Util.unquote(tags[0]).rstrip('|')
            #if descriptions:
            #    ep_item['description'] = descriptions[0]
            for k, v in order.items():
                if k == 'user':
                    ep_item['category'] = v
                elif k == 'show_id':
                    ep_item['owner_show_id'] = v
                else:
                    ep_item[k] = v

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url
            ep_item['format_id'] = self.format_id
            items.append(ep_item)

            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

