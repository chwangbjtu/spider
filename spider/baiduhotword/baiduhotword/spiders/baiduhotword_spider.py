# -*- coding:utf-8 -*-
from scrapy.spiders import Spider
from scrapy.selector import Selector
from scrapy.http import Request
from scrapy.http import HtmlResponse
import logging
from hades_common.util import Util
from baiduhotword.items import BaidutopwordItem
from scrapy.utils.project import get_project_settings
import traceback
import re
import json
import string 
from datetime import datetime
try:
    from baiduhotword.hades_db.db_mgr import DbManager
except ImportError:
    from hades_db.db_mgr import DbManager

class baiduhotword_spider(Spider):
    name = "baiduhotword"
    site_code = "baidu"
    site_id = ""   #baidu
    allowed_domains = ["top.baidu.com"]
    url_prefix = 'http://top.baidu.com'
    #site_name = Util.guess_site(url_prefix)
    
    mgr = DbManager.instance()
    site_id = mgr.get_site_by_code(site_code)["site_id"]
    channel_map = {}
    channel_map = mgr.get_channel_map()

    channel_info = {}
    test_page_url = None
    test_channel_id = None

    def __init__(self, json_data=None, *args, **kwargs):
        super(baiduhotword_spider, self).__init__(*args, **kwargs)
        cat_urls = []
        tasks = None
        if json_data:
            data = json.loads(json_data)
            if "type" in data:
                spider_type = data["type"]
                if spider_type != "global":
                    self.global_spider = False
            tasks=[]
            ttask={}
            if "id" in data and "url" in data:
                ttask["id"] = data["id"]
                ttask["url"] = data["url"]
                ttask["sid"] = ""
                ttask["untrack_id"] = ""
                cat_urls.append(ttask)

            cmd = data["cmd"]
            if cmd == "assign":
                tasks = data["task"]
            elif cmd == "trig":
                stat = data['stat'] if 'stat' in data else None
                tasks = self.mgr.get_untrack_url(self.site_code, stat)
            elif cmd == "test" and 'id' in data and 'url' in data:
                self.test_page_url = data["url"]
                self.test_channel_id = data["id"]

            if tasks:
                for task in tasks:
                    ttask={}
                    ttask["url"] = task["url"]
                    code = task["code"]
                    ttask["id"] = self.channel_map[code]
                    ttask["untrack_id"] = task["untrack_id"]
                    ttask["sid"] = task["sid"]
                    cat_urls.append(ttask)

        self._cat_urls = []
        if cat_urls:
            self._cat_urls = cat_urls

    def start_requests(self):
        try:
            items = []

            #self.movie_id = str(self.mgr.get_channel('电影')["channel_id"])
            #self.tv_id = str(self.mgr.get_channel('电视剧')["channel_id"])
            #self.variety_id = str(self.mgr.get_channel('综艺')["channel_id"])
            #self.cartoon_id = str(self.mgr.get_channel('动漫')["channel_id"])

            #self.channel_info = {self.movie_id:u"电影",self.tv_id:u"电视剧",self.variety_id:u"综艺",self.cartoon_id:u"动漫"}

            if not self._cat_urls:
                cat_urls = [{'url':'http://top.baidu.com/category?c=1&fr=topcategory_c1','id':self.channel_map["movie"]},
                        {'url':'http://top.baidu.com/category?c=2&fr=topcategory_c1','id':self.channel_map["tv"]},
                        {'url':'http://top.baidu.com/category?c=3&fr=topcategory_c2','id':self.channel_map["variaty"]},
                        {'url':'http://top.baidu.com/category?c=5&fr=topcategory_c3','id':self.channel_map["cartoon"]}
                    ]
                for cat in cat_urls:
                    items.append(Request(url=cat['url'], callback=self.parse_block, meta={'cat_id': cat['id'],'page':1}))
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_block(self,response):
        items = []  
        try:            
            #logging.log(logging.INFO, 'parse_area: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            #subs = response.xpath('//div[@class="selecter"]/div[1]/div[@class="clearfix rp"]/a/@href').extract()
            subs = response.xpath('//div[@class="hblock"]/ul/li')
            for sub in subs:
                title = sub.xpath("./a/@title").extract()
                if  title and (title[0].find(u"全部") >= 0 or title[0].find(u"首页") >= 0):
                    continue
                turl = sub.xpath("./a/@href").extract()
                t = turl[0].strip()
                if t.find("http") < 0:
                    t1 = t.replace(".","")
                    t = self.url_prefix + t1
                block_id = self.mgr.get_top_block_id(cat_id,title[0])
                #print t,title[0],block_id
                items.append(Request(url=t, callback=self.parse_list, meta={'cat_id': cat_id,'block_id':block_id,'page':1}))
                #items.append(Request(url=self.url_prefix+sub, callback=self.parse_type, meta={'cat_id': cat_id,'page':1}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_list(self,response):
        items = []
        try:
            logging.log(logging.INFO, 'parse_list: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            block_id = response.request.meta['block_id']
            subs = response.xpath('//div[@class="grayborder"]/table/tr')
            for sub in subs:
                title = sub.xpath("./td[@class='keyword']/a[@class='list-title']/text()").extract()
                hot_num = sub.xpath("./td[@class='last']/span/text()").extract()
                if hot_num:
                    bditem = BaidutopwordItem()
                    bditem["block_id"] = block_id
                    bditem["word"] = title[0]
                    bditem["hot"] = hot_num[0]
                    #print "bditem",title,block_id,hot_num
                    items.append(bditem)
            
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        #print items
        return items

