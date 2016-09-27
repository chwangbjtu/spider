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

class YoukuCatHottestSpider(Spider):
    name = "youku_cat_hottest"
    pipelines = ['HottestItemPipeline', 'CategoryPipeline', 'MysqlStorePipeline']
    spider_id = "2" #youku_cat_hottest
    site_id = "1"   #youku
    allowed_domains = ["www.youku.com", "v.youku.com", "i.youku.com", "index.youku.com", "play.youku.com"]
    url_prefix = 'http://www.youku.com'
    vpaction_url = "http://v.youku.com/v_vpactionInfo/id/"
    # playlength_url = "http://v.youku.com/player/getPlayList/VideoIDS/"
    playlength_url = "http://play.youku.com/play/get.json?ct=10&vid="
    hottest_played_threshold = get_project_settings().get('HOTTEST_PLAYED_THRESHOLD')

    mgr = DbManager.instance()
    channel_exclude = mgr.get_channel_exclude()

    def __init__(self, cat_urls=None, *args, **kwargs):
        super(YoukuCatHottestSpider, self).__init__(*args, **kwargs)
        if cat_urls:
            cat_urls = json.loads(cat_urls)
            self.max_search_page = get_project_settings().get('MAX_MANUAL_SEARCH_PAGE')
        else:
            cat_urls = self.mgr.get_cat_url("youku")
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
            sel = Selector(response)

            #category
            subs = sel.xpath('//div[@class="yk-filter-panel"]/div[2]/ul/li/a/@href').extract()
            items.extend([Request(url=url, callback=self.parse_most_played, meta={'cat_id': cat_id}) for url in subs])

            inh_item = self.parse_most_played(response)
            if inh_item:
                items.extend(inh_item)

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    #for each sub-category we get the most played
    def parse_most_played(self, response):
        try:
            #log.msg('lev2: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            items = []
            sel = Selector(response)

            #most played
            most_played = sel.xpath("//div[@class='yk-sort']/div[3]/div/div[@class='panel']/ul/li/a[text()='%s']/@href" % u'本周').extract()
            items.extend([Request(url=url, callback=self.parse_page, meta={'page': 1, 'cat_id': cat_id}) for url in most_played])

            '''
            inh_item = self.parse_page(response)
            if inh_item:
                items.extend(inh_item)
            '''

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_page(self, response):
        try:
            log.msg('%s: %s' % (response.request.url, response.request.meta['page']))
            cat_id = response.request.meta['cat_id']
            page = response.request.meta['page']
            if int(page) > int(self.max_search_page):
                return

            items = []
            sel = Selector(response)

            #video items
            yk_v = sel.xpath('//div[@class="yk-col4"]')
            for v in yk_v:
                url = v.xpath('./div/div[@class="v-link"]/a/@href').extract()
                pl = v.xpath('./div/div[@class="v-meta va"]/div[@class="v-meta-entry"]/span/text()').extract()
                if url and pl:
                    pld = Util.normalize_played(pl[0])
                    if int(pld) >= int(self.hottest_played_threshold):
                        items.append(Request(url=url[0], callback=self.parse_episode, meta={'cat_id': cat_id}))
                    #else:
                    #    log.msg('discard: %s' % url[0])

            #pages
            next_page = sel.xpath('//div[@class="yk-pager"]/ul/li[@class="next"]/a/@href').extract()
            if next_page:
                items.append(Request(url=self.url_prefix+next_page[0], callback=self.parse_page, meta={'page': page+1, 'cat_id': cat_id}))

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_episode(self, response):
        try:
            log.msg('%s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            items = []
            sel = Selector(response)

            #owner
            owner = sel.xpath('//div[@class="yk-userinfo"]/div[@class="user-name"]/a/@href').extract()
            owner_show_id = None
            if owner:
                owner_show_id = Util.get_owner(owner[0])
                if owner_show_id in self.channel_exclude:
                    log.msg("video owner excluded: %s" % owner_show_id)
                    return
                items.append(Request(url=owner[0], callback=self.parse_owner))

            #video info
            #title = sel.xpath('//div[@class="base_info"]/h1/descendant-or-self::*/text()').extract()
            title = sel.xpath('//div[@class="base_info"]/h1/descendant-or-self::text()').extract()
            category = sel.xpath('//div[@class="base_info"]/div[@class="guide"]/div/a/text()').extract()
            scripts = sel.xpath('//script[@type="text/javascript"]')
            video_id = scripts.re('videoId = \'(\d+)\'')
            tag = scripts.re('tags="(.+)"')
            upload = sel.xpath('//div[@class="yk-videoinfo"]/div[@class="time"]/text()').extract()
            description = sel.xpath('//div[@class="yk-videoinfo"]/div[@id="text_long"]/text()').extract()
            vp_url = sel.xpath('//span[@id="videoTotalPV"]/../../@href').extract()

            ep_item = EpisodeItem()
            ep_item['show_id'] = Util.get_showid(response.request.url)
            if video_id:
                ep_item['video_id'] = video_id[0]
            if owner_show_id:
                ep_item['owner_show_id'] = owner_show_id
            if title:
                t = "".join(title)
                t = t.strip("\n").strip()
                #ep_item['title'] = Util.strip_title("".join(title))
                ep_item['title'] = Util.strip_title(t)
            if tag:
                ep_item['tag'] = Util.unquote(tag[0]).rstrip('|')
            if category:
                ep_item['category'] = category[0].replace(u'频道', '')
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

            #if video_id:
            #    items.append(Request(url=self.vpaction_url+video_id[0], callback=self.parse_vpaction, meta={'item':ep_item}))
            if vp_url:
                items.append(Request(url=vp_url[0], callback=self.parse_vpaction, meta={'item':ep_item}))
            else:
                items.append(ep_item)

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_vpaction(self, response):
        try:
            #log.msg('%s' % response.request.url)
            item = response.request.meta['item']
            sel = Selector(response)

            #vp = sel.xpath('//div[@id="videodetailInfo"]/ul/li').re(u'<label>总播放数:</label><span.*>(.+)</span>')
            #vp = sel.xpath('//div[@class="info_num"]/span/text()').extract()
            vp = sel.xpath('//ul[@class="player_info"]/li[@class="sum"]/text()').extract()
            if vp:
                item['played'] = Util.normalize_played(Util.normalize_vp(vp[0].replace('总播放:', '')))

            show_id = item['show_id']
            item = Request(url=self.playlength_url+show_id, callback=self.parse_playlength, meta={'item':item})

            return item

        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_playlength(self,response):
        try:
            #log.msg('parse_playlength ,%s' % response.request.url)
            item = response.request.meta['item']
            showid = item["show_id"]
                    
            msg = response.body
            jinfo = json.loads(msg)
            # plsylength = str(int(float(jinfo["data"][0]["seconds"])))
            plsylength = str(int(float(jinfo["data"]["video"]["seconds"])))
            if plsylength:
                item['duration'] = str(plsylength)

            return item
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_owner(self, response):
        try:
            log.msg('%s' % response.request.url)
            items = []
            sel = Selector(response)

            user_item = UserItem()
            #owner id 
            script = sel.xpath('/html/head/script')
            owner_id = script.re('ownerId = \"(\d+)\"')
            show_id = script.re('ownerEncodeid = \'(.+)\'')
            if owner_id:
                user_item['owner_id'] = owner_id[0]
            if show_id:
                user_item['show_id'] = show_id[0]
            else:
                return

            #user profile
            up = sel.xpath('//div[@class="profile"]')
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
            yp = sel.xpath('//div[@class="YK-profile"]')
            if yp:
                intro = yp.xpath('./div[@class="userintro"]/div[@class="desc"]/p[2]/text()').extract()

                if intro:
                    user_item['intro'] = ''.join(intro)
            
            #count
            yh = sel.xpath('//div[@class="YK-home"]')
            vcount = '0'
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
            log.msg(traceback.format_exc(), level=log.ERROR)
