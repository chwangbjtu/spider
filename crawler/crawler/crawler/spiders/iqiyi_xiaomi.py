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

class iqiyi_xiaomi(Spider):
    name = "iqiyi_xiaomi"
    pipelines = ['MysqlStorePipeline']
    spider_id = "65536"
    site_id = "5"   #iqiyi
    allowed_domains = ["list.iqiyi.com","www.iqiyi.com","cache.video.iqiyi.com"]
    url_prefix = 'http://list.iqiyi.com'
    playnum_url = 'http://cache.video.iqiyi.com/jp/pc/'
    playlength_url = "http://cache.video.iqiyi.com/a/"
    max_search_page = 1

    mgr = DbManager.instance()

    def __init__(self, *args, **kwargs):
        super(iqiyi_xiaomi, self).__init__(*args, **kwargs)
        self._cat_urls = [{'url': 'http://list.iqiyi.com/www/25/20031-------------4-1-2-iqiyi-1-.html', 'id': '10000', 'name': u'热点'}, 
                          {'url': 'http://list.iqiyi.com/www/25/21314-------------4-1-2-iqiyi-1-.html', 'id': '10000', 'name': u'新闻'},
                          {'url': 'http://list.iqiyi.com/www/25/21739-------------4-1-2-iqiyi-1-.html', 'id': '10000', 'name': u'新闻'},
                          {'url': 'http://list.iqiyi.com/www/25/21740-------------4-1-2-iqiyi-1-.html', 'id': '10000', 'name': u'新闻'},
                         ]


    def start_requests(self):
        try:
            items = []

            for cat in self._cat_urls:
                items.extend([Request(url=cat['url'], callback=self.parse_page,meta={'page': 1, 'cat_id': cat['id'], 'cat_name': cat['name']})])

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_page(self, response):
        try:
            #log.msg('parse page %s: %s' % (response.request.url, response.request.meta['page']))
            page = response.request.meta['page']
            cat_id = response.request.meta['cat_id']
            cat_name = response.request.meta['cat_name']
            if int(page) > int(self.max_search_page):
                return

            items = []

            #video items
            qy_v = response.xpath('//div[@class="wrapper-piclist"]/ul/li/div[1]')
            for v in qy_v:
                thumb = v.xpath('./a/img/@src').extract()
                url = v.xpath('./a/@href').extract()
                items.append(Request(url=url[0].strip(), callback=self.parse_episode, meta={'cat_id': cat_id, 'cat_name': cat_name, 'thumb': thumb}))

            #pages
            next_page = response.xpath("//div[@class='mod-page']/a[text()='%s']/@href" % u'下一页').extract()
            if next_page:
                items.append(Request(url=self.url_prefix+next_page[0], callback=self.parse_page, meta={'page': page+1, 'cat_id': cat_id, 'cat_name': cat_name}))

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_episode(self, response):
        try:
            log.msg('parse_episode %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            cat_name = response.request.meta['cat_name']
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
            #if category:
            #    ep_item['category'] = category[0].strip()
            if thumb_url:
                ep_item['thumb_url'] = thumb_url[0].strip()

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url
            ep_item['cat_id'] = cat_id
            ep_item['category'] = cat_name
            ep_item['format_id'] = '2'
            ep_item['audit'] = '0'
            ep_item['priority'] = '8'

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
                if int(plsylength) < 600:
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

