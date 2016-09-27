# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors import LinkExtractor
from scrapy.http import Request, HtmlResponse
from scrapy.http import FormRequest
from scrapy.selector import Selector
import logging
from scrapy.utils.project import get_project_settings
from crawler.common.util import Util
from crawler.items import EpisodeItem
from crawler.db.db_mgr import DbManager
from datetime import datetime
import traceback
import re
import json

class PageOrderSpider(CrawlSpider):
    name = 'page_order'
    pipelines = ['MysqlStorePipeline']
    spider_id = "2048"
    format_id = 2
    allowed_domains = ["youku.com", "www.youku.com", "www.iqiyi.com", "cache.video.iqiyi.com", "www.soku.com", "index.youku.com", "play.youku.com"]
    vpaction_url = "http://v.youku.com/v_vpactionInfo/id/"
    playnum_url = 'http://cache.video.iqiyi.com/jp/pc/'
    playlength_url = "http://cache.video.iqiyi.com/a/"
    youku_playlength_url = "http://play.youku.com/play/get.json?ct=10&vid="

    mgr = DbManager.instance()

    rules = (
        #Rule(LinkExtractor(allow=r'http://v.youku.com/v_show/id_.+\.html'), callback='parse_episode_youku'),
        Rule(LinkExtractor(allow=r'http://v.youku.com/v_show/id_.+\.html.*'), callback='parse_episode_youku'),
        Rule(LinkExtractor(allow=r'http://www.iqiyi.com/[vw]_.+\.html'), callback='parse_episode_iqiyi'),
    )

    def __init__(self, orders=None, *args, **kwargs):
        super(PageOrderSpider, self).__init__(*args, **kwargs)
        if orders:
            orders = json.loads(orders)
        else:
            orders = self.mgr.get_ordered_page(site_name=['iqiyi','youku'])
        if orders:
            self._orders = orders
        else:
            self._orders = [] 

    def _requests_to_follow(self, response):
        if not isinstance(response, HtmlResponse):
            return
        seen = set()
        for n, rule in enumerate(self._rules):
            links = [l for l in rule.link_extractor.extract_links(response) if l not in seen]
            if links and rule.process_links:
                links = rule.process_links(links)
            for link in links:
                seen.add(link)
                r = Request(url=link.url, callback=self._response_downloaded)
                r.meta.update(response.request.meta)
                r.meta.update(rule=n, link_text=link.text)
                yield rule.process_request(r)

    def start_requests(self):
        try:
            items = []
            for page in self._orders:
                items.append(Request(url=page['url'], meta={'pg_id': page['id'], 'cat_name': page['user'], 'site_id': page['site_id'], 'audit': page['audit'], 'priority': page['priority']}))
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_episode_youku(self, response):
        try:
            logging.log(logging.INFO, "episode_youku:%s" % response.request.url)
            pg_id = response.request.meta['pg_id']
            cat_name = response.request.meta['cat_name']
            site_id = response.request.meta['site_id']
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']

            items = []
            #owner
            owner = response.xpath('//div[@class="yk-userinfo"]/div[@class="user-name"]/a/@href').extract()
            owner_show_id = None
            if owner:
                owner_show_id = Util.get_owner(owner[0])

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
                #ep_item['title'] = Util.strip_title("".join(title))
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
            ep_item['site_id'] = site_id
            ep_item['url'] = response.request.url
            ep_item['pg_id'] = pg_id
            ep_item['audit'] = audit
            ep_item['format_id'] = self.format_id
            ep_item['priority'] = priority

            if vp_url:
                items.append(Request(url=vp_url[0], callback=self.parse_vpaction, meta={'item':ep_item}))
            else:
                items.append(ep_item)
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_vpaction(self, response):
        try:
            logging.log(logging.INFO, "parse_vpaction:%s" % response.request.url)
            item = response.request.meta['item']

            vp = response.xpath('//ul[@class="player_info"]/li[@class="sum"]/text()').extract()
            if vp:
                item['played'] = Util.normalize_played(Util.normalize_vp(vp[0].replace('总播放:', '')))

            show_id = item['show_id']
            item = Request(url=self.youku_playlength_url+show_id, callback=self.parse_youku_playlength, meta={'item':item})
            return item
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_youku_playlength(self,response):
        try:
            logging.log(logging.INFO, "parse_youku_playlength:%s" % response.request.url)
            item = response.request.meta['item']
            showid = item["show_id"]

            msg = response.body
            jinfo = json.loads(msg)
            playlength = str(int(float(jinfo["data"]["video"]["seconds"])))
            if playlength:
                item['duration'] = str(playlength)
            return item
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_episode_iqiyi(self, response):
        try:
            logging.log(logging.INFO, "parse_youku_playlength:%s" % response.request.url)
            pg_id = response.request.meta['pg_id']
            cat_name = response.request.meta['cat_name']
            site_id = response.request.meta['site_id']
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']

            items = []

            #show_id
            show_id = Util.get_iqiyi_showid(response.request.url)
            albumid = response.selector.re(re.compile(r'albumId: ?(\d+)'))

            #video info
            title = response.xpath('//div[@class="play-tit-l"]/h2/descendant-or-self::*/text()').extract()
            if not title:
                title = response.xpath('//div[@class="play-tit-l"]/h1/descendant-or-self::*/text()').extract()
            if not title:
                title = response.xpath('//div[@class="mod-play-tits"]/h1/descendant-or-self::*/text()').extract()
            if not title:
                title = response.xpath('//div[@class="play-tit play-tit-oneRow play-tit-long"]/h1/descendant-or-self::*/text()').extract()

            #category = response.xpath('//div[@class="crumb_bar"]/span[1]/span/a[2]/text()').extract()
            #if not category:
            #    category = response.xpath('//div[@class="play-album-crumbs textOverflow"]/span[1]/a[2]/text()').extract()
            #if not category:
            #    category = response.xpath('//div[@class="crumb_bar"]/span[1]/a[2]/text()').extract()
            #if not category:
            #    category = response.xpath('//div[@class="mod-crumb_bar"]/span[1]/a[2]/text()').extract()

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
            ep_item['category'] = cat_name
            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = site_id
            ep_item['pg_id'] = pg_id
            ep_item['audit'] = audit
            ep_item['url'] = response.request.url
            ep_item['format_id'] = self.format_id
            ep_item['priority'] = priority

            if albumid:
                items.append(Request(url=self.playlength_url+albumid[0], callback=self.parse_playlength, meta={'item':ep_item,'albumid':albumid[0]}))
            else:
                items.append(ep_item)

            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_playlength(self,response):
        try:
            logging.log(logging.INFO, "parse_playlength:%s" % response.request.url)
            item = response.request.meta['item']
            albumid = response.request.meta['albumid']
                    
            items = [] 
            msg = response.body
            index = msg.find("AlbumInfo=") + len("AlbumInfo=")
            info = msg[index:]
            jinfo = json.loads(info)
            playlength = jinfo["data"]["playLength"]
            if playlength:
                item['duration'] = str(playlength)

            items.append(Request(url=self.playnum_url+albumid+"/?qyid=", callback=self.parse_playnum, meta={'item':item}))
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_playnum(self, response):
        try:
            logging.log(logging.INFO, "parse_playnum:%s" % response.request.url)
            item = response.request.meta['item']

            items = []
            tplaynum = response.selector.re(re.compile(r':(\d+)'))
            if tplaynum:
                item['played'] = str(tplaynum[0])
                items.append(item)
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

