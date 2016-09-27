# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from scrapy.spiders import Spider
from scrapy.http import Request
import logging
import traceback
import json
import urlparse
import time
from crawler.db.db_mgr import DbManager
from crawler.items import EpisodeItem

class GameFySpider(Spider):
    name = "gamefy_athletic_mobile"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    mgr = DbManager.instance()
    
    def __init__(self, *args, **kwargs):
        super(GameFySpider, self).__init__(*args, **kwargs)
        self._host_name = "http://www.gamefy.cn/"
        self._category = "游戏"
        self._site_id = '11'
        self._spider_id = '131072'                      
        self._cat_urls = self.mgr.get_cat_url("gamefy")
                      
    def start_requests(self):
        items = []
        try:                
            for cat in self._cat_urls:
                items.append(Request(url=cat['url'], callback=self.parse_list, meta={'cat_id': cat['id']}))
        
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
    def parse_list(self, response):
        items = []
        try:
            cat_id = response.request.meta['cat_id']
            sels = response.xpath('//div[@class="con"]//div[@class="area-col min"]//div[@class="area-block"]//a')
            if sels:
                for sel in sels:
                    urls = sel.xpath('./@href').extract()
                    titles = sel.xpath('./@title').extract()
                    imgs = sel.xpath('.//img/@src').extract()

                    url = urls[0]
                    title = titles[0].encode("UTF-8")
                    img = imgs[0]           
                    items.append(Request(url=url, callback=self.parse_media, meta={'title': title, 'img': img, 'cat_id': cat_id}))
                
            #get next page
            next_page_sel = response.xpath('//div[@class="viciao"]/a[text()=">"]/@href').extract()
            if next_page_sel:
                next_page = next_page_sel[0]
                next_page = self._host_name + next_page
                items.append(Request(url=next_page, callback=self.parse_list, meta={'cat_id': cat_id}))          
                      
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
    def parse_media(self, response):
        items = []
        try:
            cat_id = response.request.meta['cat_id']
            title = response.request.meta['title']
            thumb_url = response.request.meta['img']
            url = response.request.url
            query = urlparse.urlparse(url).query
            query_dict = urlparse.parse_qs(query)
            show_id = query_dict['id'][0]   
            
            #get tags
            sels = response.xpath('//span[@class="c_org1"]/a/text()').extract()
            tag = ''
            if sels:
                tag = "|".join(sels).encode("UTF-8")
            
            #get release time
            upload_time = ''
            sels = response.xpath('//p[@class="c_gray0 lh3"]/span/text()').extract()
            if sels:
                time_times = sels[0].encode("UTF-8")
                upload_time = time_times[0:16]
                
            #get play times
            played = 0
            sels = response.xpath('//p[@class="c_gray0 lh3"]/span/a/text()').extract()
            if sels:
                played = sels[0].strip()
                
            ep_item = EpisodeItem()
            ep_item['title'] = title
            ep_item['show_id'] = show_id
            ep_item['tag'] = tag
            ep_item['upload_time'] = upload_time
            ep_item['category'] = self._category
            ep_item['thumb_url'] = thumb_url
            ep_item['spider_id'] = self._spider_id
            ep_item['site_id'] = self._site_id
            ep_item['url'] = url
            ep_item['played'] = played
            ep_item['cat_id'] = cat_id
            
            items.append(ep_item)
           
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
            
            