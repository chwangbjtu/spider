# -*- coding:utf-8 -*- 
from scrapy.spiders import CrawlSpider, Rule
from scrapy.http import Request
from scrapy.linkextractors import LinkExtractor
import logging
import traceback
import json
import re
from scrapy.utils.project import get_project_settings
from zimu.items import SubtitleItem
try:
    from zimu.hades_db.db_mgr import DbManager
except ImportError:
    from hades_db.db_mgr import DbManager

class ZimukuSpider(CrawlSpider):
    name = "zimuku_spread"
    allowed_domains = ["www.zimuku.net"]
    url_prefix = 'http://www.zimuku.net'
    site_code = "zimuku"
    mgr = DbManager.instance()
    site_id = str(mgr.get_site_by_code(site_code)["site_id"])
    
    rules = (Rule(LinkExtractor(allow=r'.*/detail/\d+.html'), callback='parse_media', follow=False),
            #Rule(LinkExtractor(allow=r'.*/shooter/\d+.html'), callback='parse_media', follow=False),
            Rule(LinkExtractor(allow=r'.*/newsubs.*', tags=('a',))),
            Rule(LinkExtractor(allow=r'.*/hotsubs.*', tags=('a',))),
            Rule(LinkExtractor(allow=r'.*/search.*', tags=('a',))),
            Rule(LinkExtractor(allow=r'.*/subs/\d+.html', tags=('a',))),
            )
    
    start_urls = [
                  'http://www.zimuku.net/'
                 ]
                 
    def __init__(self, *args, **kwargs):
        super(ZimukuSpider, self).__init__(*args, **kwargs)
        max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
        
    def parse_media(self, response, **kwargs):
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
        
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
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
            
            
