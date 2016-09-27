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

class iqiyi_military_hottest(Spider):
    name = "iqiyi_military_hottest"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    spider_id = "512" #iqiyi_military_hottest
    site_id = "5"   #iqiyi
    allowed_domains = ["list.iqiyi.com","www.iqiyi.com","cache.video.iqiyi.com"]
    url_prefix = 'http://list.iqiyi.com'
    playnum_url = 'http://cache.video.iqiyi.com/jp/pc/'
    playlength_url = "http://cache.video.iqiyi.com/a/"
    hottest_played_threshold = get_project_settings().get('ORDERED_PLAYED_THRESHOLD')

    mgr = DbManager.instance()

    def __init__(self, cat_urls=None, *args, **kwargs):
        super(iqiyi_military_hottest, self).__init__(*args, **kwargs)
        if cat_urls:
            cat_urls = json.loads(cat_urls)
            self.max_search_page = get_project_settings().get('MAX_MANUAL_SEARCH_PAGE')
        else:
            cat_urls = self.mgr.get_cat_url("iqiyi")
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


    #for each category parse all its sub-categories or types
    def parse(self, response):
        try:
            #log.msg('lev1: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            items = []

            #category
            subs = response.xpath('//div[@class="mod_sear_menu mt20 mb30"]/div[2]/ul/li/a/@href').extract()
            for turl in subs:
                if turl != "#":
                    url = self.url_prefix+turl
                    items.extend([Request(url=url, callback=self.parse_second, meta={'cat_id': cat_id})])
                else:
                    items.extend([Request(url=response.request.url, callback=self.parse_most_played, meta={'cat_id': cat_id})])

            inh_item = self.parse_second(response)
            if inh_item:
                items.extend(inh_item)

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_second(self,response):
        try:
            #log.msg('lev2: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            items = []

            #category
            subs = response.xpath('//div[@class="mod_sear_menu mt20 mb30"]/div[3]/ul/li/a/@href').extract()
            for turl in subs:
                if turl != "#":
                    url = self.url_prefix+turl
                    items.extend([Request(url=url, callback=self.parse_most_played, meta={'cat_id': cat_id})])
                else:
                    items.extend([Request(url=response.request.url, callback=self.parse_most_played, meta={'cat_id': cat_id})])

            inh_item = self.parse_most_played(response)
            if inh_item:
                items.extend(inh_item)

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    #for each sub-category we get the most played
    def parse_most_played(self, response):
        try:
            #log.msg('lev3: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            items = []

            url = response.request.url
            suburl = "------------"
            index = url.rfind(suburl)
            #combine all sort types
            if index > 0:
                headurl =  url[0:index]
                url11 = headurl + suburl + "10-1-2--1-.html"
                items.extend([Request(url=url11, callback=self.parse_page,meta={'page': 1, 'cat_id': cat_id})])
                url12 = headurl + suburl + "10-1-2--2-.html"
                items.extend([Request(url=url12, callback=self.parse_page,meta={'page': 1, 'cat_id': cat_id})])
                url21 = headurl + suburl + "4-1-2--1-.html"
                items.extend([Request(url=url21, callback=self.parse_page,meta={'page': 1, 'cat_id': cat_id})])
                url22 = headurl + suburl + "4-1-2--2-.html"
                items.extend([Request(url=url22, callback=self.parse_page,meta={'page': 1, 'cat_id': cat_id})])

            #donnot forget parse current reponse's page
            response.request.meta.update({'page': 1})
            items.extend(self.parse_page(response))
                        
            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_page(self, response):
        try:
            #log.msg('parse page %s: %s' % (response.request.url, response.request.meta['page']))
            page = response.request.meta['page']
            cat_id = response.request.meta['cat_id']
            if int(page) > int(self.max_search_page):
                return

            items = []

            #video items
            qy_v = response.xpath('//div[@class="wrapper-piclist"]/ul/li/div[1]')
            for v in qy_v:
                thumb = v.xpath('./a/img/@src').extract()
                url = v.xpath('./a/@href').extract()
                items.append(Request(url=url[0].strip(), callback=self.parse_episode, meta={'cat_id': cat_id, 'thumb': thumb}))

            #pages
            next_page = response.xpath("//div[@class='mod-page']/a[text()='%s']/@href" % u'下一页').extract()
            if next_page:
                items.append(Request(url=self.url_prefix+next_page[0], callback=self.parse_page, meta={'page': page+1, 'cat_id': cat_id}))

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_episode(self, response):
        try:
            log.msg('parse_episode %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            thumb_url = response.request.meta['thumb']
            items = []

            #show_id
            show_id = Util.get_iqiyi_showid(response.request.url)

            #space maybe exist: "albumId:326754200" or "albumId: 326754200"
            albumid = response.selector.re(re.compile(r'albumId: ?(\d+)'))

            #video info
            title = response.xpath('//div[@class="play-tit-l"]/h2/descendant-or-self::*/text()').extract()
            if not title:
                title = response.xpath('//div[@class="play-tit-l"]/h1/descendant-or-self::*/text()').extract()
            if not title:
                title = response.xpath('//div[@class="mod-play-tits"]/h1/descendant-or-self::*/text()').extract()
            if not title:
                title = response.xpath('//div[@class="play-tit play-tit-oneRow play-tit-long"]/h1/descendant-or-self::*/text()').extract()

            category = response.xpath('//div[@class="crumb_bar"]/span[1]/span/a[2]/text()').extract()
            if not category:
                category = response.xpath('//div[@class="play-album-crumbs textOverflow"]/span[1]/a[2]/text()').extract()
            if not category:
                category = response.xpath('//div[@class="crumb_bar"]/span[1]/a[2]/text()').extract()
            if not category:
                category = response.xpath('//div[@class="mod-crumb_bar"]/span[1]/a[2]/text()').extract()

            upload_time = response.xpath('//div[@class="crumb_bar"]/span[3]/span/text()').extract()
            if not upload_time:
                upload_time = response.xpath('//div[@class="crumb_bar"]/span[2]/span/text()').extract()
            
            tag = response.xpath('//span[@id="widget-videotag"]/descendant::*/text()').extract()
            if not tag:
                tag = response.xpath('//span[@class="mod-tags_item vl-block"]/descendant::*/text()').extract()
            if not tag:
                tag = response.xpath('//div[@class="crumb_bar"]/span[2]/a/text()').extract()

            ep_item = EpisodeItem()
            
            if title:
                ep_item['title'] = "".join([t.strip() for t in title])
            if show_id:
                ep_item['show_id'] = show_id
            if tag:
                ep_item['tag'] =  "|".join([t.strip() for t in tag])
            if upload_time:
                ep_item['upload_time'] = upload_time[0].strip()
            if category:
                ep_item['category'] = category[0].strip()
            if thumb_url:
                ep_item['thumb_url'] = thumb_url[0].strip()

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url
            ep_item['cat_id'] = cat_id

            if albumid:
                items.append(Request(url=self.playlength_url+albumid[0], callback=self.parse_playlength, meta={'item':ep_item,'albumid':albumid[0]}))
            else:
                items.append(ep_item)

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_playlength(self,response):
        try:
            log.msg('parse_playlength ,%s' % response.request.url)
            item = response.request.meta['item']
            albumid = response.request.meta['albumid']

            items = []
            #sel = Selector(response)
            msg = response.body
            index = msg.find("AlbumInfo=") + len("AlbumInfo=")
            info = msg[index:]
            jinfo = json.loads(info)
            plsylength = jinfo["data"]["playLength"]
            if plsylength:
                item['duration'] = str(plsylength)
            
            items.append(Request(url=self.playnum_url+albumid+"/?qyid=", callback=self.parse_playnum, meta={'item':item}))

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_playnum(self, response):
        try:
            #log.msg('parse_playnum ,%s' % response.request.url)
            item = response.request.meta['item']

            items = []
            #sel = Selector(response)
            tplaynum = response.selector.re(re.compile(r':(\d+)'))
            #log.msg('play: %s, %s' % (tplaynum[0], response.request.url))
            if tplaynum:
                playnum = tplaynum[0]
                if int(playnum) > int(self.hottest_played_threshold):
                    item['played'] = str(playnum)
                    items.append(item)

            return items
                
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

