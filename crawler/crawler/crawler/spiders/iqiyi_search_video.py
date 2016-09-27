# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import traceback
import json
import re
import urllib2
from scrapy import log
from scrapy.spider import Spider
from crawler.db.db_mgr import DbManager
from scrapy.utils.project import get_project_settings
from crawler.items import EpisodeItem, UserItem
from scrapy.http import Request
from crawler.common.util import Util

class iqiyi_search_video(Spider):
    name = 'iqiyi_search_video'
    pipelines = ['MysqlStorePipeline']
    spider_id = '32768'
    site_id = '5'
    allowed_domain=["so.iqiyi.com", "www.iqiyi.com"]
    url_prefix = 'http://so.iqiyi.com'
    playnum_url = 'http://cache.video.iqiyi.com/jp/pc/'
    playlength_url = "http://cache.video.iqiyi.com/a/"
    hottest_played_threshold = get_project_settings().get('HOTTEST_PLAYED_THRESHOLD')
    
    mgr = DbManager.instance()
    channel_exclude = mgr.get_channel_exclude()
    
    def __init__(self, cat_ids=None, keywords=None, *args, **kwargs):
        super(iqiyi_search_video, self).__init__(*args, **kwargs)
        if keywords:
            keywords = json.loads(keywords)
            self.max_search_page = get_project_settings().get('MAX_MANUAL_SEARCH_PAGE')
        else:
            keywords = self.mgr.get_keywords(st='video', site_name='iqiyi')
            self.max_search_page = get_project_settings().get('MAX_SEARCH_PAGE')
        if keywords:
            self._keywords = keywords
        else:
            self._keywords = [] 

    def start_requests(self):
        try:
            items = []
            run_time = {'10min': 2, '30min': 3, '60min': 4, 'plus': 5, 'default': 0}
            pub_time = {'day': 1, 'week': 2, 'month': 3, 'default': 0}
            quality = {'high': 3, '720P': 4, 'super': 6, '1080P': 7, 'default': ''}
            sort = {'composite': 1, 'new': 4, 'played': 11}
            for kw in self._keywords:
                url = "%s/so/q_%s_ctg__t_%s_page_%s_p_%s_qc_%s_rd_%s_site_%s_m_%s_bitrate_%s" % \
                    (self.url_prefix, urllib2.quote(kw['keyword'].encode('utf8')), run_time['default'], 1, 1, 0, pub_time['default'], "iqiyi", sort['composite'], quality['default'])
                items.append(Request(url=url, callback=self.parse, meta={'page':1, 'kw_id': kw['id']}))
            return items
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse(self, response):
        try:
            page = response.request.meta['page'] if 'page' in response.request.meta else 1
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else 1
            log.msg('%s: %s' %(response.request.url, page))
            if int(page) > int(self.max_search_page):
                return
            items = []
            iqiyi_kvs = response.xpath('//div[@class="mod_search_result"]/div[1]/ul/li[@data-widget-searchlist-source=""]')
            for iqiyi_kv in iqiyi_kvs:
                search_page_size = iqiyi_kv.xpath('./@data-widget-searchlist-pagesize').extract()
                page_size = 0
                if search_page_size:
                    page_size = int(search_page_size[0])
                # video list:
                if page_size in [0, 1]:
                    thumb_url = iqiyi_kv.xpath('./a/img/@src').extract()
                    url = iqiyi_kv.xpath('./a/@href').extract()
                    if thumb_url and url:
                        items.append(Request(url=url[0], callback=self.parse_episode, meta={'kw_id':kw_id,'thumb_url':thumb_url[0]}))
                #play list,暂不支持（情况很多，待评估后完成）
                #else:
                #    url = iqiyi_kv.xpath('./@href').extract()
                #    items.append(Request(url=url[0], callback=self.parse_playlist, meta={'kw_id':kw_id, 'thumb_url':thumb_url[0]})) 
            #next page
            next_page = response.xpath("//div[@class='mod-page']/a[text()='%s']/@href" % u'下一页').extract()
            if next_page:
               items.append(Request(url=self.url_prefix+next_page[0], callback=self.parse, meta={'page': page+1, 'kw_id': kw_id})) 
            return items

        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_playlist(self, response):
        try:
            items = []
            return items
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_episode(self, response):
        try:
            #kw_id
            kw_id = response.request.meta['kw_id']
            #thumb_url
            thumb_url = response.request.meta['thumb_url']
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
                ep_item['thumb_url'] = thumb_url

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url
            ep_item['kw_id'] = kw_id

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
            if "data" in jinfo.keys():
                plsylength = jinfo["data"]
                if "playLength" in jinfo["data"].keys():
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

