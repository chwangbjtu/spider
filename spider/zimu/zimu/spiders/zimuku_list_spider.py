# -*- coding:utf-8 -*-
from scrapy.spiders import Spider
from scrapy.utils.project import get_project_settings
from scrapy.http import Request
import logging
import traceback
import json
import re
import urlparse
from scrapy.utils.project import get_project_settings
from zimu.items import SubtitleItem
try:
    from zimu.hades_db.db_mgr import DbManager
except ImportError:
    from hades_db.db_mgr import DbManager
    
class ZimukuListSpider(Spider):
    name = "zimuku_list"
    allowed_domains = ["www.zimuku.net"]
    url_prefix = 'http://www.zimuku.net'
    site_code = "zimuku"
    mgr = DbManager.instance()
    site_id = str(mgr.get_site_by_code(site_code)["site_id"])
    
    def __init__(self, *args, **kwargs):
        super(ZimukuListSpider, self).__init__(*args, **kwargs)
        max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
        self._limit = max_update_page if max_update_page > 0 else None
        self._start = [
                        {'url':'http://www.zimuku.net/newsubs?t=mv&ad=1'},
                        {'url':'http://www.zimuku.net/newsubs?t=tv&ad=1'},
                      ]
                      
    def start_requests(self):
        items = []
        try:
            for s in self._start:
                items.append(Request(url=s['url'], callback=self.parse_list))
        
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
    def parse_list(self, response):
        items = []
        try:
            media_url_list = response.xpath('//tbody/tr/td[@class="first"]/a/@href').extract()
            if media_url_list:
                for media_url in media_url_list: 
                    media_url = self.url_prefix + media_url
                    items.append(Request(url=media_url, callback=self.parse_media))       

            next_page_sel = response.xpath('//div[@class="pagination l clearfix"]/div/a[@class="next"]/@href').extract()
            if next_page_sel:
                if self._limit and self.get_next_page_num(next_page_sel[0]) > self._limit:
                    return items
                next_page = self.url_prefix + next_page_sel[0]
                items.append(Request(next_page, callback=self.parse_list))       
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
    def parse_media(self, response):
        items = []
        try:
            sub_item = SubtitleItem()
            sels = response.xpath('//div[@class="md_tt prel"]/h1/text()').extract()
            if sels:
                sub_item['title'] = sels[0].encode("UTF-8")
                    
            sels = response.xpath('//ul[@class="l tb"]//a/@href[re:test(., "http://movie\.douban\.com/subject/[\d]+/$")]').extract() 
            if sels:
                douban_url = sels[0]
                douban_id = self.get_douid(douban_url)
                sub_item['dou_id'] = douban_id
                
            cont_id = self.get_contid(response.request.url)
            sub_item['cont_id'] = cont_id
            sub_item['site_id'] = self.site_id
            sub_item['url'] = response.request.url
            items.append(sub_item)
            logging.log(logging.INFO, "spider success, url:%s, cont_id:%s" % (response.request.url, cont_id))
            
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
    def get_next_page_num(self, url):
        query_str = urlparse.urlparse(url).query
        query_dict = urlparse.parse_qs(query_str)
        return int(query_dict['p'][0])
        
    def get_douid(self, url):
        id = ""
        try:
            r = re.compile(r'.*/subject/(\d+)/$')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return id
        
    def get_contid(self, url):
        id = ""
        try:
            r = re.compile(r'.*/(.*)/(\d+).html$')
            m = r.match(url)
            if m:
                return m.group(1) + m.group(2)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return id
        
        
        