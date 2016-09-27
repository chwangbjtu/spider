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
    
class ZimuzuListSpider(Spider):
    name = "zimuzu_list"
    allowed_domains = ["www.zimuzu.tv"]
    url_prefix = 'http://www.zimuzu.tv'
    site_code = "zimuzu"
    mgr = DbManager.instance()
    site_id = str(mgr.get_site_by_code(site_code)["site_id"])
    
    def __init__(self, *args, **kwargs):
        super(ZimuzuListSpider, self).__init__(*args, **kwargs)
        max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
        self._limit = max_update_page if max_update_page > 0 else None
        self._start = [
                        {'url':'http://www.zimuzu.tv/esubtitle'},
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
            media_url_list = response.xpath('//div[@class="box subtitle-list"]/ul/li//strong/a/@href').extract()
            if media_url_list:
                for media_url in media_url_list: 
                    media_url = self.url_prefix + media_url
                    items.append(Request(url=media_url, callback=self.parse_media))       

            next_page_sel = response.xpath(u'//div[@class="pages"]/div/a[text()="下一页"]/@href').extract()
            if next_page_sel:
                if self._limit and self.get_next_page_num(next_page_sel[0]) > self._limit:
                    return items
                next_page = self.url_prefix + '/esubtitle' + next_page_sel[0]
                items.append(Request(next_page, callback=self.parse_list))       
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
    def parse_media(self, response, **kwargs):
        items = []
        try:
            sub_item = SubtitleItem()
            sels = response.xpath('//ul[@class="subtitle-info"]/li/text()').extract()
            if sels:
                for sel in sels:
                    text_regex = re.compile('%s(.+?)%s(.*)' % (u'【',u'】'))
                    match_results = text_regex.search(sel)
                    if match_results:
                        key = match_results.groups()[0]
                        value = match_results.groups()[1]
                        if key == u"中文":
                            sub_item['title'] = value.encode("UTF-8")
                                         
            sub_item["cont_id"] = self.get_contid(response.request.url)
            sub_item["url"] = response.request.url
            sub_item['site_id'] = self.site_id
            items.append(sub_item)
            logging.log(logging.INFO, "spider success, url:%s, cont_id:%s" % (response.request.url, sub_item["cont_id"]))
        
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
    def get_next_page_num(self, url):
        query_str = urlparse.urlparse(url).query
        query_dict = urlparse.parse_qs(query_str)
        return int(query_dict['page'][0])
    
    def get_contid(self, url):
        id = ""
        try:
            r = re.compile(r'.*/subtitle/(\d+)$')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return id
    
    