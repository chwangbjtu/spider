# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from scrapy.spider import Spider
from scrapy.http import Request
from scrapy.http import FormRequest
from scrapy import log
from scrapy.utils.project import get_project_settings
from crawler.common.util import Util
from crawler.items import EpisodeItem, UserItem
from crawler.db.db_mgr import DbManager
from datetime import datetime
import traceback
import re
import json


class YoukuOrderSpider(Spider):
    name = "youku_order_all"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    spider_id = "256"
    site_id = "1"
    allowed_domains = ["i.youku.com", "www.youku.com", "v.youku.com"]
    url_prefix = 'http://i.youku.com'
    vpaction_url = "http://v.youku.com/v_vpactionInfo/id/"
    playlength_url = "http://v.youku.com/player/getPlayList/VideoIDS/"
    forbidden_author_list = set()

    mgr = DbManager.instance()

    def __init__(self, orders=None, *args, **kwargs):
        super(YoukuOrderSpider, self).__init__(*args, **kwargs)
        self._orders = [
                           {'url': 'http://i.youku.com/u/UMjk3OTcyMTM2/', 'cust_para': {'category': u'音乐', 'priority': '3', 'need_check': '1'}},
                       ]

        with open('./crawler/data/blacklist', 'r') as f:
            for line in f.readlines():
                self.forbidden_author_list.add(line.strip().decode('utf-8'))

    def start_requests(self):
        try:
            items = []

            for order in self._orders:
                cust_para = order['cust_para'] if 'cust_para' in order else {}
                items.append(Request(url=order['url'], callback=self.parse, meta={'cust_para': cust_para}))

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse(self, response):
        try:
            log.msg(response.request.url, level=log.INFO)
            cust_para = response.request.meta['cust_para']
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
                    user_item['played'] = Util.normalize_vp(played[0])
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
            vcount = '0'
            if yh:
                video_count = yh.xpath('div[1]/div/div/div/div[@class="title"]/span/a/text()').re(u'\((\d+)\)')

                if video_count:
                    vcount = video_count[0]

            user_item['vcount'] = vcount
            user_item['spider_id'] = self.spider_id
            user_item['site_id'] = self.site_id
            
            items.append(user_item)

            #videos
            items.append(Request(url=response.request.url+"videos", callback=self.parse_video_page, meta={'page':1, 'cust_para': cust_para}))

            return items

        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_video_page(self, response):
        try:
            page = response.request.meta['page']
            cust_para = response.request.meta['cust_para']
            log.msg('%s: %s' % (response.request.url, page))

            items = []

            #get videos
            yk_v = response.xpath('//div[@class="yk-col4"]/div')
            for v in yk_v:
                url = v.xpath('./div[@class="v-link"]/a/@href').extract()
                if url:
                    items.append(Request(url=url[0], callback=self.parse_episode, meta={'cust_para': cust_para}))

            #get last_str and ajax_url
            last_str= response.selector.re(u'\'last_str\':\'([^\']*)\'')
            ajax_url = response.selector.re(u'\'ajax_url\':\'([^\']*)\'')

            #reqest sibling page
            if ajax_url:
                sibling_page = (3 * page - 1, 3 * page)
                for p in sibling_page:
                    s = last_str[0] if last_str else u''
                    para = {"v_page":str(page), "page_num":str(p), "page_order":"1", "last_str":s}
                    items.append(FormRequest(url=self.url_prefix + ajax_url[0] + "fun_ajaxload/",
                                formdata=para,
                                method='GET',
                                callback=self.parse_video_page,
                                meta={'page': page, 'cust_para': cust_para}))

            #request next page
            next_page = response.xpath('//ul[@class="YK-pages"]/li[@class="next"]/a/@href').extract()
            if next_page:
                items.append(Request(url=self.url_prefix+next_page[0], callback=self.parse_video_page, meta={'page':page+1, 'cust_para': cust_para}))

            return items

        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def content_is_forbidden(self, content):
        for keyword in self.forbidden_author_list:
            if content.find(keyword) == -1:
                pass
            else:
                return True
        return False

    def parse_episode(self, response):
        try:
            cust_para = response.request.meta['cust_para']
            log.msg('%s: %s' % (response.request.url, cust_para))
            items = []

            #owner
            owner = response.xpath('//div[@class="yk-userinfo"]/div[@class="user-name"]/a/@href').extract()
            owner_show_id = None
            if owner:
                owner_show_id = Util.get_owner(owner[0])

            #video info
            title = response.xpath('//div[@class="base_info"]/h1/descendant-or-self::*/text()').extract()
            category = response.xpath('//div[@class="base_info"]/div[@class="guide"]/div/a/text()').extract()
            scripts = response.xpath('//script[@type="text/javascript"]')
            video_id = scripts.re('videoId = \'(\d+)\'')
            tag = scripts.re('tags="(.+)"')
            upload = response.xpath('//div[@class="yk-videoinfo"]/div[@class="time"]/text()').extract()
            description = response.xpath('//div[@class="yk-videoinfo"]/div[@id="text_long"]/text()').extract()

            ep_item = EpisodeItem()
            ep_item['show_id'] = Util.get_showid(response.request.url)
            if video_id:
                ep_item['video_id'] = video_id[0]
            if owner_show_id:
                ep_item['owner_show_id'] = owner_show_id
            if title:
                ep_item['title'] = Util.strip_title("".join(title))
                if 'need_check' in cust_para:
                    if self.content_is_forbidden(ep_item['title']):
                        log.msg('video [ %s ] is in blacklist!' % ep_item['show_id'])
                        return items
                    else:
                        pass
                else:
                    pass
                    
            if tag:
                ep_item['tag'] = Util.unquote(tag[0]).rstrip('|')
            if 'category' in cust_para:
                ep_item['category'] = cust_para['category']
            elif category:
                ep_item['category'] = category[0].replace(u'频道', '')
            if upload:
                t = Util.get_upload_time(upload[0])
                if t:
                    ep_item['upload_time'] = Util.get_datetime_delta(datetime.now(), t)
            if description:
                ep_item['description'] = description[0]

            if 'priority' in cust_para:
                ep_item['priority'] = cust_para['priority']

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url


            if video_id:
                items.append(Request(url=self.vpaction_url+video_id[0], callback=self.parse_vpaction, meta={'item':ep_item}))
            else:
                items.append(ep_item)

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)


    def parse_vpaction(self, response):
        try:
            #log.msg('%s' % response.request.url)
            item = response.request.meta['item']

            vp = response.xpath('//div[@id="videodetailInfo"]/ul/li').re(u'<label>总播放数:</label><span.*>(.+)</span>')
            if vp:
                item['played'] = Util.normalize_vp(vp[0])

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
            plsylength = str(int(float(jinfo["data"][0]["seconds"])))
            if plsylength:
                item['duration'] = str(plsylength)
                
            return item
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)
