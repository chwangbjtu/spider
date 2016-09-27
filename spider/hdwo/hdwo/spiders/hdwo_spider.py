# -*- coding:utf-8 -*-
from scrapy.spiders import Spider
from scrapy.http import Request
import logging
import traceback
import json
import re
from hades_common.util import Util
from hdwo.items import MediaItem
from hdwo.items import MediaVideoItem
from hdwo.items import VideoItem
try:
    from hdwo.hades_db.db_mgr import DbManager
except ImportError:
    from hades_db.db_mgr import DbManager


class HdwoSpider(Spider):
    name = "hdwo"
    site_code = "hdwo"
    pipelines = ['MysqlStorePipeline']
    mgr = DbManager.instance()
    site_id = str(mgr.get_site_by_code(site_code)["site_id"])
    protocol_code = 'bt'
    protocol_id = mgr.get_protocol_map().get(protocol_code)

    def __init__(self, *args, **kwargs):
        super(HdwoSpider, self).__init__(*args, **kwargs)
        self._start = [
                        'http://hdwo.net/720p',
                        'http://hdwo.net/1080p',
                        'http://hdwo.net/juqing',
                        'http://hdwo.net/dongzuo',
                        'http://hdwo.net/donghua',
                        'http://hdwo.net/xiju',
                        'http://hdwo.net/nvxia',
                        'http://hdwo.net/kongbu',
                        'http://hdwo.net/war',
                        'http://hdwo.net/zainan',
                        'http://hdwo.net/love',
                        'http://hdwo.net/fanzui',
                        'http://hdwo.net/kehuan'
                      ]
                      
    def start_requests(self):
        items = []
        try:
            for s in self._start:
                items.append(Request(url=s, callback=self.parse_list))
        
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
    def parse_list(self, response):
        items = []
        try:
            media_url_list = response.xpath('//ul[@id="post_container"]/li/div/div/a/@href').extract()
            if media_url_list:
                for media_url in media_url_list: 
                    items.append(Request(url=media_url, callback=self.parse_media))
                
            #get next page
            next_page_sel = response.xpath('//div[@class="pagination"]/a[@class="next"]/@href').extract()
            if next_page_sel:
                next_page = next_page_sel[0]
                items.append(Request(url=next_page, callback=self.parse_list))
                      
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items  
    
    def parse_media(self, response):
        items = []
        try:
            bt_file_sels = response.xpath('//div[@id="post_content"]/p/strong/a')
            if not bt_file_sels:
                return items
                
            ep_item = MediaItem()
            cont_id = self.get_cont_id(response.request.url)
            title_sel = response.xpath('//div[@class="mainleft"]/div/h1/text()').extract()
            if title_sel:
                ep_item["title"] = title_sel[0].encode("utf-8")
            
            ep_item["site_id"] = self.site_id            
            ep_item["cont_id"] = cont_id
            ep_item["url"] = response.request.url
            video_list = []
            for bt_file_sel in bt_file_sels:  
                vitem = VideoItem()
                vitem["url"] = bt_file_sel.xpath('./@href').extract()[0]
                vitem["title"] = bt_file_sel.xpath('./@title').extract()[0].encode("utf-8")
                vitem["cont_id"] = Util.md5hash(vitem["url"])
                vitem['protocol_id'] = self.protocol_id
                video_list.append(vitem)
                
            ep_item['vcount'] = len(video_list)
            mvitem = MediaVideoItem()
            mvitem["media"] = ep_item
            mvitem['video'] = video_list
            items.append(mvitem)  
            
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
    def get_cont_id(self, url):
        cont_id = ''
        r = re.compile(r'.*/(.*/\d+).html')
        m = r.match(url)
        if m:
            cont_id = m.group(1)
        return cont_id
            
            
