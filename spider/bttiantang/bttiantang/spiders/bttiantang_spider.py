# -*- coding:utf-8 -*-
from scrapy.spiders import Spider
from scrapy.http import Request
import logging
import traceback
import json
import urlparse
import time
import re
from scrapy.utils.project import get_project_settings
from hades_common.http_client import HttpDownload
from hades_common.util import Util
from bttiantang.items import MediaItem
from bttiantang.items import MediaVideoItem
from bttiantang.items import VideoItem
try:
    from bttiantang.hades_db.db_mgr import DbManager
except ImportError:
    from hades_db.db_mgr import DbManager

class BtTianTangSpider(Spider):
    name = "bttiantang"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    site_code = "bttiantang"
    mgr = DbManager.instance()
    site_id = str(mgr.get_site_by_code(site_code)["site_id"])
    protocol_code = 'bt'
    protocol_id = mgr.get_protocol_map().get(protocol_code)
    max_number = 10000
    def __init__(self, *args, **kwargs):
        super(BtTianTangSpider, self).__init__(*args, **kwargs)
        self._host_name = "http://www.bttiantang.com"
        self._start = [
                        {'url': 'http://www.bttiantang.com/?PageNo=1'},
                      ]
        self._http_client = HttpDownload()
        self._timeout = 5
        
    def start_requests(self):
        items = []
        try:
            self.load_member_variable()
            for s in self._start:
                items.append(Request(url=s['url'], callback=self.parse_list))
        
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
    def load_member_variable(self):
        try:
            max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
            if max_update_page and max_update_page > 0:
                self.max_number = max_update_page
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
    def parse_list(self, response):
        items = []
        try:
            page = response.request.meta['page'] if 'page' in response.request.meta else 1
            media_url_list = response.xpath('//div[@class="mb cl"]//div[@class="item cl"]//p[@class="tt cl"]/a/@href').extract()
            if media_url_list:
                for media_url in media_url_list: 
                    media_url = self._host_name + media_url
                    items.append(Request(url=media_url, callback=self.parse_media))
                
            #get next page
            if page < self.max_number:
                next_page_sel = response.xpath(u'//ul[@class="pagelist"]/li/a[text()="下一页"]/@href').extract()
                if next_page_sel:
                    next_page = next_page_sel[0]
                    next_page = self._host_name + next_page
                    items.append(Request(url=next_page, callback=self.parse_list,meta={'page':page+1}))           
                      
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
    def parse_media(self, response):
        items = []
        try:
            bt_file_sels = response.xpath('//div[@class="sl cl"]/div[@class="tinfo"]/a')
            if not bt_file_sels:
                return items
                
            name_sel = response.xpath('//div[@class="title"]/h2/descendant-or-self::text()').extract()
            alias_sel = response.xpath(u'//ul[@class="moviedteail_list"]/li[text()="又名:"]/a/text()').extract()
            tag_sel = response.xpath(u'//ul[@class="moviedteail_list"]/li[text()="标签:"]/a/text()').extract()
            district_sel = response.xpath(u'//ul[@class="moviedteail_list"]/li[text()="地区:"]/a/text()').extract()
            director_sel = response.xpath(u'//ul[@class="moviedteail_list"]/li[text()="导演:"]/a/text()').extract()
            writer_sel = response.xpath(u'//ul[@class="moviedteail_list"]/li[text()="编剧:"]/a/text()').extract()
            actor_sel = response.xpath(u'//ul[@class="moviedteail_list"]/li[text()="主演:"]/a/text()').extract() 
            imdb_sel = response.xpath('//ul[@class="moviedteail_list"]/li/a[@title="imdb"]/text()').extract()
            
            ep_item = MediaItem()
            if name_sel:
                ep_item["title"] = ""
                for item in name_sel:
                    ep_item["title"] += item.encode("utf-8")

            if alias_sel:
                ep_item["alias"] = alias_sel[0].encode("utf-8")
            if tag_sel:
                tag = Util.join_list_safely(tag_sel)
                tag = tag.encode("utf-8")
                ep_item["tag"] = tag
                if len(tag) > 128:
                    #to do,get last |
                    tag = tag[0:127]
                    fan_tag = tag[::-1]
                    pos = fan_tag.find('|')
                    if pos != -1:
                        ep_item["tag"] = tag[0:127-pos-1]               
                    
            if district_sel:
                district = Util.join_list_safely(district_sel)
                ep_item["district"] = district.encode("utf-8")
            if director_sel:
                director = Util.join_list_safely(director_sel)
                ep_item["director"] = director.encode("utf-8")
            if writer_sel:
                writer = Util.join_list_safely(writer_sel)
                ep_item["writer"] = writer.encode("utf-8")
            if actor_sel:
                actor = Util.join_list_safely(actor_sel)
                ep_item["actor"] = actor.encode("utf-8")
            if imdb_sel:
                ep_item["imdb"] = imdb_sel[0].encode("utf-8")
                
            #get douban id
            # douban_index_sel = response.xpath(u'//ul[@class="moviedteail_list"]/li[text()="详情:"]/a/@href').extract() 
            # if douban_index_sel:
                # douban_index_url = self._host_name + douban_index_sel[0]
                # res = self._http_client.get_data(douban_index_url, timeout=self._timeout)
                # r = re.compile(r'.*/subject/(\d+)/')
                # m = r.match(res)
                # if m:
                    # dou_id = m.group(1)
                    # ep_item['dou_id'] = dou_id
                
            ep_item["site_id"] = self.site_id
            #todo,now 2001
            #ep_item["channel_id"] = 2001
            ep_item["url"] = response.request.url
            cont_id = response.request.url.split('/')[-1]
            cont_id = cont_id.split('.')[0]
            ep_item["cont_id"] = cont_id
            
            video_list = []
            for bt_file_sel in bt_file_sels:  
                vitem = VideoItem()
                bt_file_address = bt_file_sel.xpath('./@href').extract()
                bt_file_title = bt_file_sel.xpath('./p/descendant-or-self::text()').extract()
                vitem["url"] = self._host_name + bt_file_address[0]
                vitem["title"] = "".join(bt_file_title).encode("utf-8")
                vitem["cont_id"] = Util.md5hash(vitem["url"])
                vitem['protocol_id'] = self.protocol_id
                video_list.append(vitem)
                
            ep_item['vcount'] = len(video_list)
            mvitem = MediaVideoItem()
            mvitem["media"] = ep_item
            mvitem['video'] = video_list
            items.append(mvitem)  
       
        except Exception as e:
            logging.log(logging.ERROR, response.request.url)
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
        
