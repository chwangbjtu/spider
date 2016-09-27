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

class iqiyi_order(Spider):
    name = "iqiyi_order"
    pipelines = ['MysqlStorePipeline']
    spider_id = "131072"
    site_id = "5"   #iqiyi
    allowed_domains = ["list.iqiyi.com","www.iqiyi.com","cache.video.iqiyi.com"]
    url_prefix = 'http://list.iqiyi.com'
    playnum_url = 'http://cache.video.iqiyi.com/jp/pc/'
    playlength_url = "http://cache.video.iqiyi.com/a/"
    max_search_page = 1

    mgr = DbManager.instance()

    def __init__(self, *args, **kwargs):
        super(iqiyi_order, self).__init__(*args, **kwargs)
        self._cat_urls = []
        try:
            self._cat_urls = self.mgr.get_ordered_url(site_name='iqiyi')
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def start_requests(self):
        try:
            items = []

            #items.append(Request(url="http://www.iqiyi.com/u/1061614233", callback=self.parse_first,meta={'cat_name': u'生活','audit':1,'show_id':'1061614233'}))
            #'''
            for cat in self._cat_urls:
                #items.append(Request(url="http://www.iqiyi.com/u/1211677213", callback=self.parse_first))
                items.append(Request(url=cat['url'], callback=self.parse_first,meta={'cat_name': cat['user'],'audit':cat['audit'],'show_id':cat['show_id'],'priority':cat['priority']}))
            #'''
            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)
    def parse_first(self,response):
        try:
            items = []
            user_item = UserItem()
            cat_name = response.request.meta['cat_name']
            audit = response.request.meta['audit']
            show_id = response.request.meta['show_id']
            priority = response.request.meta['priority']

            #owner_id = response.xpath('//div[@class="top-yc_userCare fl"]/a/@data-userid')
            fans = response.xpath('//div[@class="info_connect"]//em/a[@data-fans="fans"]/text()')
            played = response.xpath('//div[@class="info_connect"]/span[@class="conn_type S_line1"]/em/a/text()')
            '''
            if owner_id:
                owner_id = owner_id.extract()[0].strip()
                #user_item['owner_id']=owner_id
                user_item['show_id']=owner_id
            else:
                owner_id = response.xpath('//span[@class="pc-btn pc-care-large pc-btn-reset"]/a[@class="btn-care btn-care-tocare"]/@data-userid')
                if owner_id:
                    owner_id = owner_id.extract()[0].strip()
                    #user_item['owner_id']=owner_id
                    user_item['show_id']=owner_id
            '''
            user_item['show_id'] = show_id
            if fans:
                fans = fans.extract()[0].strip()
                fans = fans.replace(',','')
                if fans.find(u'万'):
                    fans = float(fans[:fans.find(u'万')])
                    fans = fans*10000
                    user_item['fans']=int(fans)
                else:
                    user_item['fans']=int(fans)
            if played:
                played = played.extract()[0].strip()
                played = played.replace(',','')
                if played.find(u'万'):
                    played = float(played[:played.find(u'万')])
                    played = played*10000
                    user_item['played']=int(played)
                else:
                    user_item['played']=int(played)
                
            username = response.xpath('//div[@class="pf_username"]/span/text()')
            userinfo = response.xpath('//div[@class="pf_intro"]/a/text()')
            if username:
                username = username.extract()[0].strip()
                user_item['user_name']=username
            if userinfo:
                userinfo = userinfo.extract()[0].strip()
                user_item['intro']= userinfo

            user_item['spider_id'] = self.spider_id
            user_item['site_id'] = self.site_id
            user_item['url'] = response.request.url
            items.append(user_item) 

            title = u'视频'
            urls = ''
            u = response.xpath('//div[@class="qiyiSet-nav"]/ul[@class="qiyiNav-normal"]/li/a[@title="%s"]/@href' % title)
            if u:
                urls = u.extract()[0]
            else:
                u = response.xpath('//div[@class="pc-nav-title pc-item-box"]/ul[@class="pc-user-nav pc-user-nav-4 clearfix"]/li[@data-ugcguide-target ="2"]/a/@href')
                urls = u.extract()[0]
            items.append(Request(url=urls, callback=self.parse_page, meta={'cat_name': cat_name,'audit':audit,'priority':priority}))
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

            #pages
            #next_page = response.xpath("//div[@class='mod-page']/a[text()='%s']/@href" % u'下一页').extract()
            #if next_page:
            #    items.append(Request(url=self.url_prefix+next_page[0], callback=self.parse_page, meta={'page': page+1, 'cat_id': cat_id, 'cat_name': cat_name}))

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

