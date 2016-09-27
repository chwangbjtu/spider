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

class ZimuzuSpider(CrawlSpider):
    name = "zimuzu_spread"
    allowed_domains = ["www.zimuzu.tv"]
    url_prefix = 'http://www.zimuzu.tv/'
    site_code = "zimuzu"
    mgr = DbManager.instance()
    site_id = str(mgr.get_site_by_code(site_code)["site_id"])
    
    rules = (Rule(LinkExtractor(allow=r'.*/subtitle/\d+', tags=('a',)), callback='parse_media', follow=False),
            Rule(LinkExtractor(allow=r'.*/esubtitle\?.*', tags=('a',))),
            )
    
    start_urls = [
                  'http://www.zimuzu.tv/esubtitle'
                 ]
                 
    def __init__(self, *args, **kwargs):
        super(ZimuzuSpider, self).__init__(*args, **kwargs)
        max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
        
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
        
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
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
            
            
