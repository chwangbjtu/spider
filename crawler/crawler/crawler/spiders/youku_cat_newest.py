# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from scrapy.spider import Spider
from scrapy.http import Request
import logging
from scrapy.utils.project import get_project_settings
from crawler.common.util import Util
from crawler.items import EpisodeItem, UserItem
from crawler.db.db_mgr import DbManager
from datetime import datetime
import traceback
import re
import json

class YoukuCatNewestSpider(Spider):
    name = "youku_cat_newest"
    pipelines = ['MysqlStorePipeline']
    spider_id = "1"
    site_id = "1"
    format_id = 2
    #allowed_domains = ["www.youku.com", "v.youku.com", "i.youku.com", "index.youku.com", "play.youku.com"]
    url_prefix = 'http://www.youku.com'
    playlength_url = "http://play.youku.com/play/get.json?ct=10&vid="
    mgr = DbManager.instance()

    def __init__(self, *args, **kwargs):
        super(YoukuCatNewestSpider, self).__init__(*args, **kwargs)
        cat_urls = kwargs.get('cat_urls')
        if cat_urls:
            cat_urls = json.loads(cat_urls)
        else:
            cat_urls = self.mgr.get_cat_url("youku")
        if cat_urls:
            self._cat_urls = cat_urls 
        else:
            self._cat_urls = [] 

    def start_requests(self):
        try:
            items = []
            for cat in self._cat_urls:
                print cat
                items.append(Request(url=cat['url'], callback=self.parse_page, meta={'cat_id': cat['id'], 'cat_name': cat['cat_name'], 'audit': cat['audit'], 'priority': cat['priority']}))
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_page(self, response):
        try:
            logging.log(logging.INFO, 'page:%s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            audit = response.request.meta['audit']
            cat_name = response.request.meta['cat_name']
            priority = response.request.meta['priority']

            #page = response.request.meta['page']
            #if int(page) > int(self.max_search_page):
            #    return
            items = []
            #video items
            #yk_v = response.xpath('//div[@class="yk-col4"]')
            '''
            yk_v = response.xpath('//div[@id="getVideoList"]/div[@class="yk-row yk-v-90u"]/div[@class="yk-col4"]')
            for v in yk_v:
                url = v.xpath('./div/div[@class="v-link"]/a/@href').extract()
                thumb_urls = v.xpath('./div/div[@class="v-thumb"]/img/@src').extract()
            '''
            # 游戏、生活、旅游、搞笑
            yk_v = response.xpath('//div[@class="vaule_main"]/div[@class="box-video"]/div[@class="yk-row"]/div')
            for v in yk_v:
                url = v.xpath('./div/div/a/@href').extract()
                thumb_urls = v.xpath('./div/div/img/@src').extract()
                if thumb_urls:
                    thumb_url = thumb_urls[0]
                    if thumb_url == 'http://g1.ykimg.com/':
                        thumb_url = None
                else:
                    thumb_url = None
                    
                if url:
                    items.append(Request(url=url[0], callback=self.parse_episode, meta={'cat_id': cat_id, 'cat_name': cat_name, 'audit': audit, 'thumb_url':thumb_url, 'priority': priority}))
            # 资讯、母婴、军事
            yk_v2 = response.xpath('//div[@class="yk-box"]/div[@class="yk-body"]/div[@class="yk-row"]/div[@class="yk-col4"]')
            for v in yk_v2:
                url = v.xpath('./div/div[@class="v-link"]/a/@href').extract()
                thumb_urls = v.xpath('./div/div[@class="v-thumb"]/img/@src').extract()
                if thumb_urls:
                    thumb_url = thumb_urls[0]
                    if thumb_url == 'http://g1.ykimg.com/':
                        thumb_url = None
                else:
                    thumb_url = None
                if url:
                    items.append(Request(url=url[0], callback=self.parse_episode, meta={'cat_id': cat_id, 'cat_name': cat_name, 'audit': audit, 'thumb_url':thumb_url, 'priority': priority}))

            '''
            #pages
            next_page = response.xpath('//div[@class="yk-pager"]/ul/li[@class="next"]/a/@href').extract()
            if next_page:
                items.append(Request(url=self.url_prefix+next_page[0], callback=self.parse_page, meta={'page': page+1, 'cat_id': cat_id}))
            '''
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_episode(self, response):
        try:
            logging.log(logging.INFO, "episode:%s" % response.request.url)
            cat_id = response.request.meta['cat_id']
            cat_name = response.request.meta['cat_name']
            audit = response.request.meta['audit']
            thumb_url = response.request.meta['thumb_url']
            priority = response.request.meta['priority']

            items = []

            #owner
            owner = response.xpath('//div[@class="yk-userinfo"]/div[@class="user-name"]/a/@href').extract()
            owner_show_id = None
            if owner:
                owner_show_id = Util.get_owner(owner[0])
                items.append(Request(url=owner[0], callback=self.parse_owner))

            #video info
            title = response.xpath('//div[@class="base_info"]/h1/descendant-or-self::text()').extract()
            #category = response.xpath('//div[@class="base_info"]/div[@class="guide"]/div/a/text()').extract()
            scripts = response.xpath('//script[@type="text/javascript"]')
            video_id = scripts.re('videoId = \'(\d+)\'')
            tag = scripts.re('tags="(.+)"')
            upload = response.xpath('//div[@class="yk-videoinfo"]/div[@class="time"]/text()').extract()
            description = response.xpath('//div[@class="yk-videoinfo"]/div[@id="text_long"]/text()').extract()
            vp_url = response.xpath('//span[@id="videoTotalPV"]/../../@href').extract()

            ep_item = EpisodeItem()
            ep_item['show_id'] = Util.get_showid(response.request.url)
            if video_id:
                ep_item['video_id'] = video_id[0]
            if owner_show_id:
                ep_item['owner_show_id'] = owner_show_id
            if title:
                t = "".join(title)
                t = t.strip("\n").strip()
                ep_item['title'] = Util.strip_title(t)
            if tag:
                ep_item['tag'] = Util.unquote(tag[0]).rstrip('|')
            #if category:
            #    ep_item['category'] = category[0].replace(u'频道', '')
            ep_item['category'] = cat_name
            if upload:
                t = Util.get_upload_time(upload[0])
                if t:
                    ep_item['upload_time'] = Util.get_datetime_delta(datetime.now(), t)
            if description:
                ep_item['description'] = description[0]

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url
            ep_item['cat_id'] = cat_id
            ep_item['audit'] = audit
            ep_item['format_id'] = self.format_id
            ep_item['thumb_url'] = thumb_url
            ep_item['priority'] = priority

            if vp_url:
                items.append(Request(url=vp_url[0], callback=self.parse_vpaction, meta={'item':ep_item}))
            else:
                if ep_item['show_id']:
                    items.append(ep_item)

            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_vpaction(self, response):
        try:
            logging.log(logging.INFO, response.request.url)
            item = response.request.meta['item']
            vp = response.xpath('//ul[@class="player_info"]/li[@class="sum"]/text()').extract()
            if vp:
                item['played'] = Util.normalize_played(Util.normalize_vp(vp[0].replace('总播放:', '')))
            show_id = item['show_id']
            item = Request(url=self.playlength_url+show_id, callback=self.parse_playlength, meta={'item':item})
            return item
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_playlength(self,response):
        try:
            logging.log(logging.INFO, response.request.url)
            item = response.request.meta['item']
            showid = item["show_id"]

            msg = response.body
            jinfo = json.loads(msg)
            plsylength = str(int(float(jinfo["data"]["video"]["seconds"])))
            if plsylength:
                item['duration'] = int(plsylength)

            return item
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_owner(self, response):
        try:
            logging.log(logging.INFO, response.request.url)
            items = []

            user_item = UserItem()
            #owner id 
            script = response.xpath('/html/head/script')
            owner_id = script.re('ownerId = \"(\d+)\"')
            show_id = script.re('ownerEncodeid = \'(.+)\'')
            if owner_id:
                user_item['owner_id'] = owner_id[0]
            if show_id:
                user_item['show_id'] = show_id[0]
            else:
                return

            #user profile
            up = response.xpath('//div[@class="profile"]')
            if up:
                user_name = up.xpath('./div[@class="info"]/div[@class="username"]/a[1]/@title').extract()
                played = up.xpath('./div[@class="state"]/ul/li[@class="vnum"]/em/text()').extract()
                fans = up.xpath('./div[@class="state"]/ul/li[@class="snum"]/em/text()').extract()

                if user_name:
                    user_item['user_name'] = user_name[0]
                if played:
                    #user_item['played'] = Util.normalize_vp(played[0])
                    user_item['played'] = Util.normalize_played(Util.normalize_vp(played[0]))
                if fans:
                    user_item['fans'] = Util.normalize_vp(fans[0])

            #youku profile
            yp = response.xpath('//div[@class="YK-profile"]')
            if yp:
                intro = yp.xpath('./div[@class="userintro"]/div[@class="desc"]/p[2]/text()').extract()

                if intro:
                    user_item['intro'] = ''.join(intro)
            
            #count
            yh = response.xpath('//div[@class="YK-home"]')
            vcount = None
            if yh:
                video_count = yh.xpath('div[1]/div/div/div/div[@class="title"]/span/a/text()').re(u'\((\d+)\)')

                if video_count:
                    vcount = video_count[0]

            user_item['vcount'] = vcount

            user_item['spider_id'] = self.spider_id
            user_item['site_id'] = self.site_id
            user_item['url'] = response.request.url
            
            items.append(user_item)
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
