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
import urllib

import sys

reload(sys)
sys.setdefaultencoding( "utf-8" )

class ku6_search_video(Spider):
    name = "ku6_search_video"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    spider_id = "16384" #ku6_search_video
    site_id = "6"   #k6
    allowed_domains = ["so.ku6.com","v.ku6.com","v3.stat.ku6.com"]
    url_prefix = 'http://v.ku6.com/fetchVideo4Player/'
    url_playnum = 'http://v3.stat.ku6.com/dostatv.do?method=getVideoPlayCount&n=gotPlayCounts&v='
    #hottest_played_threshold = get_project_settings().get('ORDERED_PLAYED_THRESHOLD')

    mgr = DbManager.instance()

    def __init__(self, cat_ids=None, keywords=None, *args, **kwargs):
        super(ku6_search_video, self).__init__(*args, **kwargs)
        if keywords:
            keywords = json.loads(keywords)
            self.max_search_page = get_project_settings().get('MAX_MANUAL_SEARCH_PAGE')
        else:
            keywords = self.mgr.get_keywords(st='video', site_name='ku6')
            self.max_search_page = get_project_settings().get('MAX_SEARCH_PAGE')
        if keywords:
            self._keywords = keywords            
        else:
            self._keywords = []
    
    def start_requests(self):
        try:
            items = []

            for kw in self._keywords:
                kw_id = kw['id']
                word = kw['keyword']
                cat_id = kw['ext_cat_id']

                turl = 'http://so.ku6.com/search?q=' + word + '&categoryid=' + str(cat_id)
                items.append(Request(url=turl,callback=self.parse_page, meta={'page': 1,'kw_id': kw_id}))
                turl1 = str(turl) + u'&sort=uploadtime'
                items.append(Request(url=turl1,callback=self.parse_page, meta={'page': 1,'kw_id': kw_id}))
                turl2 = str(turl) + u'&sort=viewcount'
                items.append(Request(url=turl2,callback=self.parse_page, meta={'page': 1,'kw_id': kw_id}))

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_page(self,response):
        try:
            log.msg('parse_page: %s' % response.request.url)
            page = response.request.meta['page']
            kw_id = response.request.meta['kw_id']
            if int(page) > int(self.max_search_page):
                return

            items = []

            #video items
            titems = response.xpath('//div[@id="search_list"]/div[2]/div[2]/ul[1]/li')
            for item in titems:
                turl = item.xpath('./h3[1]/a/@href').extract()
                if turl:
                    show_id = Util.get_ku6_showid(turl[0])
                items.append(Request(url=turl[0].strip(), callback=self.parse, meta={'kw_id': kw_id, 'show_id': show_id}))

            #pages
            next_page = response.xpath("//div[@id='search_list']/div[2]/div[2]/div/a[text()='%s']/@href" % u'下一页').extract()
            if next_page:
                items.append(Request(url=next_page[0], callback=self.parse_page, meta={'page': page+1, 'kw_id': kw_id}))

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    #for each category parse all its sub-categories or types
    def parse(self, response):
        try:
            #log.msg('lev1: %s' % response.request.url)
            kw_id = response.request.meta['kw_id']
            show_id = response.request.meta['show_id']
            items = []
            sel = Selector(response)

            #category
            url1 = self.url_prefix + str(show_id) + ".html"
            items.extend([Request(url=url1, callback=self.parse_second, meta={'show_id': show_id,'kw_id':kw_id})])

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_second(self,response):
        try:
            #log.msg('lev2: %s' % response.request.url)
            kw_id = response.request.meta['kw_id']
            items = []
            sel = Selector(response)

            #info
            jinfo = json.loads(response.body)
            title = jinfo['data']['t']
            show_id = response.request.meta['show_id']
            tags = jinfo['data']['tag']
            tag = tags.replace(' ','|').replace(',','|').strip('|')

            tuploadtime = jinfo['data']['uploadtime']
            upload_time = Util.timestamp2datetime(tuploadtime)

            description = jinfo['data']['desc']
            thumb_url = jinfo['data']['picpath']

            tduration = str(jinfo['data']['vtime'])
            tduration1 = tduration.split(',')
            duration = tduration1[0]

            ep_item = EpisodeItem()
            if len(title) != 0:
                ep_item["title"] = title
            ep_item['show_id'] = response.request.meta['show_id']

            turl = "http://v.ku6.com/show/" + show_id + ".html"

            if len(tag) != 0:
                ep_item["tag"] = tag
            if len(upload_time) != 0:
                ep_item["upload_time"] = upload_time
            if len(turl) != 0:
                ep_item["url"] = turl
            if len(thumb_url) != 0:
                ep_item['thumb_url'] = thumb_url
            if len(duration) != 0:
                ep_item["duration"] = duration
            ep_item['kw_id'] = kw_id
            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id

            items.append(Request(url=turl, callback=self.parse_episode, meta={'item':ep_item}))

            return items
            
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_episode(self, response):
        try:
            log.msg('parse_episode %s' % response.request.url)
            item = response.request.meta['item']
            items = []

            sel = Selector(response)

            #category
            tcategory = sel.xpath('//div[@class="ckl_conleftop"]/div[1]/span[1]/a[1]/text()').extract()
            category = ""
            if len(tcategory) > 0:
                category = tcategory[0].strip()
            
            item['category'] = category

            #items.append(ep_item)
            turl = self.url_playnum + item['show_id']
            items.append(Request(url=turl, callback=self.parse_playnum, meta={'item':item}))

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_playnum(self,response):
        try:
            log.msg('parse_playnum %s' % response.request.url)
            items = []

            item = response.request.meta['item']
            sel = Selector(response)
            msg = response.body
            r = re.compile(',count:"(\d+)?')
            m = r.search(msg)
            if m:
                tinfo = m.groups(0)
                if len(tinfo) > 0:
                    playnum = tinfo[0]
                    item['played'] = str(playnum)
                    items.append(item)

        except Exception as e: 
            log.msg(traceback.format_exc(), level=log.ERROR)

        return items


