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

class iqiyi_subject_history(Spider):
    name = "iqiyi_subject_history"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    spider_id = "4096" #iqiyi_order_history
    site_id = "5"   #iqiyi
    allowed_domains = ["list.iqiyi.com","www.iqiyi.com","cache.video.iqiyi.com", "cache.video.qiyi.com"]
    url_prefix = 'http://list.iqiyi.com'
    playnum_url = 'http://cache.video.iqiyi.com/jp/pc/'
    playlength_url = "http://cache.video.iqiyi.com/a/"
    hottest_played_threshold = get_project_settings().get('ORDERED_PLAYED_THRESHOLD')

    mgr = DbManager.instance()

    def __init__(self, cat_urls=None, *args, **kwargs):
        super(iqiyi_subject_history, self).__init__(*args, **kwargs)
        if cat_urls:
            cat_urls = json.loads(cat_urls)
            self.max_search_page = get_project_settings().get('MAX_MANUAL_SEARCH_PAGE')
        else:
            cat_urls = self.mgr.get_subjects("iqiyi")
            self.max_search_page = get_project_settings().get('MAX_SEARCH_PAGE')
        if cat_urls:
            self._cat_urls = cat_urls 
        else:
            self._cat_urls = [] 

    def start_requests(self):
        try:
            items = []

            for cat in self._cat_urls:
                items.append(Request(url=cat['url'], callback=self.parse, meta={'cat_id': cat['id']}))

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)


    #start_urls = ["http://www.iqiyi.com/a_19rrgubpsd.html"]
    #start_urls = ["http://www.iqiyi.com/a_19rrgiavst.html#vfrm=2-3-0-1"]
    #start_urls = mgr.get_cat_url("iqiyi")

    #for each category parse all its sub-categories or types
    def parse(self, response):
        try:
            #log.msg('lev1: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            items = []
            sel = Selector(response)

            #category
            albumId = response.selector.re(re.compile(r'albumId: ?(\d+)'))[0]
            sourceid = response.selector.re(re.compile(r'sourceId: ?(\d+)'))[0]
            cid = response.selector.re(re.compile(r'cid: ?(\d+)'))[0]

            years = []
            subs = sel.xpath('//div[@id="block-J"]/div[1]/div[1]/div[1]/div[2]/ul/li/a/@data-year').extract()
            i = 0
            for year in subs:
                sxpath = '//div[@id="block-J"]/div[1]/div[' + str(i+2) + ']/a/@data-month'
                subs1 = sel.xpath(sxpath).extract()
                #subs1 = sel.xpath('//div[@id="block-J"]/div[1]/div[2]/a/@data-month').extract()
                for month in subs1:
                    y_month = str(year)+str(month)
                    url1 = "http://cache.video.qiyi.com/jp/sdvlst/" + cid  + "/" + sourceid + "/" + y_month + "/?categoryId=" + cid +"&sourceId=" + sourceid + "&tvYear=" + y_month + "&callback=window"
                    items.extend([Request(url=url1, callback=self.parse_second,meta={'cat_id': cat_id})])
                i = i + 1

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_second(self,response):
        try:
            #log.msg('lev2: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            items = []
            sel = Selector(response)

            #category
            begin = response.body.find("try{window(")
            begin += len("try{window(")
            end = response.body.find(");}catch(e)")
            msg = response.body[begin:end]
            jmsg = json.loads(msg)
            num = len(jmsg["data"])
            for i in range(num):
                title = jmsg["data"][i]["aName"]
                play_num = "0"
                play_num = str(jmsg["data"][i]["disCnt"])
                upload_time = jmsg["data"][i]["tvYear"]
                turl = jmsg["data"][i]["vUrl"]
                timelength = str(jmsg["data"][i]["timeLength"])

                ep_item = EpisodeItem()
                if len(title) != 0:
                    ep_item["title"] = title
                ep_item["played"] = play_num
                if len(upload_time) != 0:
                    ep_item["upload_time"] = upload_time
                if len(turl) != 0:
                    ep_item["url"] = turl
                if len(timelength) != 0:
                    ep_item["duration"] = timelength
                ep_item['subject_id'] = cat_id

                items.append(Request(url=turl, callback=self.parse_episode, meta={'item':ep_item}))

            return items
            
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_episode(self, response):
        try:
            log.msg('parse_episode %s' % response.request.url)
            items = []

            item = response.request.meta['item']
            sel = Selector(response)

            #video info
            ttitle = sel.xpath('//div[@class="play-tit-l"]/h2/span/text()').extract()
            title = ""
            if len(ttitle) > 0:
                title = ttitle[0]

            if len(title) == 0:
                ttitle = sel.xpath('//div[@class="play-tit-l"]/h1/text()').extract()
                if len(ttitle) > 0:
                    title = ttitle[0]

            if len(title) == 0 and "title" in item:
                title = item["title"]

            index = response.request.url.rfind("#")
            surl = response.request.url[:index]

            show_id = ""
            r = re.compile(r'[vw]_[0-9a-zA-Z]*')
            m = r.search(surl)
            if m:
                show_id = m.group()

            category = None
            tcategory = sel.xpath('//div[@id="block-E"]/div[1]/div[1]/div[2]/div[1]/span[1]/a[2]/text()').extract()
            if len(tcategory) > 0:
                category = tcategory[0].strip()

            tcategory = sel.xpath('//div[@class="crumb_bar"]/span[1]/span/a[2]/text()').extract()#"channel"
            if len(tcategory) > 0 and not category:
                category = tcategory[0].strip()
            else:
                tcategory = sel.xpath('//div[@class="play-album-crumbs textOverflow"]/span[1]/a[2]/text()').extract()
                if len(tcategory) > 0 and not category:
                    category = tcategory[0].strip()
                else:
                    tcategory = sel.xpath('//div[@class="crumb_bar"]/span[1]/a[2]/text()').extract()#"channel"
                    if len(tcategory) > 0 and not category:
                        category = tcategory[0].strip()
                    #else:
                    #    log.msg("not find category,url is %s" % response.request.url, level=log.ERROR)

            #get upload time
            upload_time = ""
            tag = ""

            tupload_time = sel.xpath('//div[@class="crumb_bar"]/span[3]/span/text()').extract()
            if len(tupload_time) > 0:
                upload_time = tupload_time[0].strip()

            tupload_time = sel.xpath('//div[@class="crumb_bar"]/span[2]/span/text()').extract()
            if len(tupload_time) > 0:
                upload_time = tupload_time[0].strip()

            if len(upload_time) == 0:
                tupload_time = sel.xpath('//div[@class="movieMsg"]/div/p/text()').extract()
                if len(tupload_time) > 0:
                    r = re.compile(r'(\d+)[.-](\d+)[\d+].*')
                    m = r.search(tupload_time[0])
                    if m:   
                        ttupload_time = m.group()
                        upload_time = ttupload_time.replace(".","-")
                    #ttupload_time  = tupload_time.re(r'(\d+)[.-](\d+)[\d+].*')

            #get tags,two ways to get tags
            taglist = sel.xpath('//div[@class="crumb_bar"]/span[2]/a/text()').extract()
            if len(taglist) > 0:
                tag =  "|".join(taglist)

            if  not tag or len(tag) == 0:
                taglist = sel.xpath('//div[@class="crumb_bar"]/span[1]/a/text()').extract()
                if len(taglist) > 0:
                    tag =  "|".join(taglist)

            ep_item = response.request.meta['item']
            

            if title:
                ep_item['title'] = title
            if show_id:
                ep_item['show_id'] = show_id
            if tag:
                ep_item['tag'] = tag
            if upload_time:
                ep_item['upload_time'] = upload_time
            if category:
                ep_item['category'] = category

            if not title or not show_id or not category:
                #log.msg("title ,show_id,category is null ,url is %s" % response.request.url, level=log.ERROR)
                return 
            if len(title) == 0 or len(show_id) == 0 or len(category) == 0:
                #log.msg("title ,show_id,category is null ,url is %s" % response.request.url, level=log.ERROR)
                return 
            
            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url

            items.append(ep_item)

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)


