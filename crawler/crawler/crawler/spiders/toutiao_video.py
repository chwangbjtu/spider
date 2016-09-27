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
import time

class toutiao_video(Spider):
    name = "toutiao_video"
    pipelines = ['MysqlStorePipeline']
    spider_id = "123456"
    site_id = "101"   #iqiyi
    #allowed_domains = ["list.iqiyi.com","www.iqiyi.com","cache.video.iqiyi.com"]
    #url_prefix = 'http://list.iqiyi.com'
    #playnum_url = 'http://cache.video.iqiyi.com/jp/pc/'
    #playlength_url = "http://cache.video.iqiyi.com/a/"
    url_first = "http://toutiao.com/api/article/recent/?source=2&category=video&as=A165771AD802ED5&cp=57A8D2FE6D658E1&_=%s"
    url_second = "http://toutiao.com/api/article/recent/?source=2&count=20&category=video&max_behot_time=%s&utm_source=toutiao&offset=0&as=A1A5A75A8882EDC&cp=57A852EE9D5C6E1&max_create_time=%s&_=%s"
    max_search_page = 1000

    mgr = DbManager.instance()

    def __init__(self, *args, **kwargs):
        super(toutiao_video, self).__init__(*args, **kwargs)
        self._cat_urls = []
        try:
            self._cat_urls = [""]
            #self._cat_urls = self.mgr.get_ordered_url(site_name='iqiyi')
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def start_requests(self):
        try:
            items = []
            #for cat in self._cat_urls:
            url = self.url_first % int(time.time())
            items.append(Request(url=url, callback=self.parse_first))
            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)
    def parse_first(self,response):
        try:
            items = []
            user_item = UserItem()
            data = json.loads(response.body)
            print data
            return items
            has_more = data.get("has_more")
            message = data.get("message")
            max_behot_time = data.get("max_behot_time")
            data = data.get("data")
            if data:
                for it in data:
                    ep_item = EpisodeItem()
                    ep_item['title'] = it["title"]
                ep_item['show_id'] = show_id
                ep_item['tag'] =  "|".join([t.strip() for t in tag])
                ep_item['upload_time'] = upload_time[0].strip()
            if category:
                ep_item['category'] = category[0].strip()
            if thumb_url:
                ep_item['thumb_url'] = thumb_url[0].strip()

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url
            #ep_item['cat_id'] = cat_id
            ep_item['category'] = cat_name
            ep_item['format_id'] = '2'
            ep_item['audit'] = audit
            ep_item['priority'] = priority

                
            print type(data)
            #items.append(Request(url=urls, callback=self.parse_page))
            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_page(self, response):
        try:
            items = []
            cat_name = response.request.meta['cat_name']
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']
            #video items
            qy_v = response.xpath('//div[@class="wrap-customAuto-ht "]/ul/li/div[1]')
            for v in qy_v:
                thumb = v.xpath('./a/img/@src').extract()
                url = v.xpath('./a/@href').extract()
                items.append(Request(url=url[0].strip(), callback=self.parse_episode, meta={ 'thumb': thumb,"cat_name":cat_name,'audit':audit,'priority':priority}))

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_episode(self, response):
        try:
            log.msg('parse_episode %s' % response.request.url)
            thumb_url = response.request.meta['thumb']
            cat_name = response.request.meta['cat_name']
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']
            items = []
            
            #show_id
            show_id = Util.get_iqiyi_showid(response.request.url)
            #print "show_id:    %s" % show_id
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
            #if category:
            #    ep_item['category'] = category[0].strip()
            if thumb_url:
                ep_item['thumb_url'] = thumb_url[0].strip()

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url
            #ep_item['cat_id'] = cat_id
            ep_item['category'] = cat_name
            ep_item['format_id'] = '2'
            ep_item['audit'] = audit
            ep_item['priority'] = priority

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
            #if plsylength:
                #if int(plsylength) < 600:
                    #item['duration'] = str(plsylength)
                    #items.append(Request(url=self.playnum_url+albumid+"/?qyid=", callback=self.parse_playnum, meta={'item':item}))
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
                item['played'] = str(playnum)
                items.append(item)

            return items
                
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

