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
from urllib import unquote
import traceback
import re
import json

class YoutubeSearchVideoSpider(Spider):
    name = "youtube_search_video"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    spider_id = "64"
    site_id = "2"
    allowed_domains = ["www.youtube.com"]
    url_prefix = 'https://www.youtube.com'

    mgr = DbManager.instance()
    
    def __init__(self, keywords=None, *args, **kwargs):
        super(YoutubeSearchVideoSpider, self).__init__(*args, **kwargs)
        if keywords:
            keywords = json.loads(keywords)
            self.max_search_page = get_project_settings().get('MAX_MANUAL_SEARCH_PAGE')
        else:
            keywords = self.mgr.get_keywords(st='video', site_name='youtube')
            self.max_search_page = get_project_settings().get('MAX_SEARCH_PAGE')
        if keywords:
            self._keywords = keywords
        else:
            self._keywords = []

    def start_requests(self):
        try:
            items = []
            for page in xrange(int(self.max_search_page)):
                items.extend([Request(url='https://www.youtube.com/results?filters=video%%2C+week&search_sort=video_view_count&search_query=%s&page=%s' % (k['keyword'], page + 1), callback=self.parse, meta={'category': k['user'], 'kw_id': k['id']}) for k in self._keywords])

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse(self, response):
        try:
            category = response.request.meta['category'] if 'category' in response.request.meta else 'other'
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else 1
            log.msg('%s: %s' % (response.request.url, category), level=log.INFO)

            items = []
            #videos
            videos = response.xpath('//ol[@class="item-section"]/li')
            for v in videos:
                url = v.xpath('./div/div/div[@class="yt-lockup-thumbnail"]/a/@href').extract()
                thumb_url = v.xpath('./div/div/div[@class="yt-lockup-thumbnail"]/a/div/img/@src').extract()
                views = v.xpath('./div/div/div[@class="yt-lockup-content"]/div[@class="yt-lockup-meta"]/ul/li/text()').re('([\d|,]*) views')
                upload_time = v.xpath('./div/div/div[@class="yt-lockup-content"]/div[@class="yt-lockup-meta"]/ul/li[2]/text()').extract()

                if url:
                    items.append(Request(url=self.url_prefix + url[0], callback=self.parse_episode, meta={'thumb_url': thumb_url, 'upload_time': upload_time, 'category': category, 'kw_id': kw_id}))
            
            return items

        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_episode(self, response):
        try:
            log.msg('%s' % response.request.url)
            thumb_url = response.request.meta['thumb_url']
            upload_time = response.request.meta['upload_time']
            category = response.request.meta['category']
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else 1
            items = []

            #owner
            owner = response.xpath('//div[@class="yt-user-info"]/a/@data-ytid').extract()
            owner_url = response.xpath('//div[@class="yt-user-info"]/a/@href').extract()
            owner_show_id = None
            if owner:
                owner_show_id = owner[0]
                items.append(Request(url=self.url_prefix + owner_url[0] + "/about", callback=self.parse_about))

            #video info
            title = response.xpath('//span[@id="eow-title"]/text()').extract()
            #category = response.xpath('//p[@id="eow-category"]/a/text()').extract()
            tag = response.xpath('./head/meta[@name="keywords"]/@content').extract()
            #upload = response.xpath('//p[@id="watch-uploader-info"]/strong/text()').extract()
            description = response.xpath('//p[@id="eow-description"]/descendant-or-self::*/text()').extract()
            played = response.xpath('//div[@class="watch-view-count"]/text()').extract()

            #other info
            sts = re.search(r'\"sts\": ?(\d+)', response.body)

            ep_item = EpisodeItem()
            ep_item['show_id'] = Util.get_youtube_showid(response.request.url)
            if owner_show_id:
                ep_item['owner_show_id'] = owner_show_id
            if title:
                ep_item['title'] = title[0].strip()
            if tag:
                ep_item['tag'] = tag[0].replace(', ', '|')
            if category:
                #ep_item['category'] = category[0].replace('&', '|')
                ep_item['category'] = category
            '''
            if upload:
                ptime = Util.get_youtube_publish(upload[0])
                if ptime:
                    ep_item['upload_time'] = ptime
            '''
            if upload_time:
                t = Util.get_youtube_upload_time(upload_time[0].strip())
                if t:
                    ep_item['upload_time'] = Util.get_datetime_delta(datetime.now(), t)
            if description:
                ep_item['description'] = "\n".join(description)
            if thumb_url:
                ep_item['thumb_url'] = thumb_url[0]
            if played:
                pld = Util.normalize_played(played[0])
                if pld:
                    ep_item['played'] = Util.normalize_played(played[0])
                else:
                    ep_item['played'] = '0'

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = Util.normalize_youtube_url(response.request.url)
            ep_item['kw_id'] = kw_id

            query = Util.encode({'video_id': ep_item['show_id'], \
                                 'eurl': 'https://youtube.googleapis.com/v/' + ep_item['show_id'], \
                                 'sts': sts.groups()[0] if sts else ''})
            items.append(Request(url='http://www.youtube.com/get_video_info?'+query, callback=self.parse_other_info, meta={'item': ep_item}))

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_other_info(self, response):
        try:
            log.msg('%s' % response.request.url)
            item = response.request.meta['item']
            items = []

            #duration
            duration = re.search(r'length_seconds=(\d+)', response.body)

            if duration:
                item['duration'] = duration.groups()[0]

            items.append(item)

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_about(self, response):
        try:
            log.msg(response.request.url, level=log.INFO)
            items = []

            show_id = response.xpath('//meta[@itemprop="channelId"]/@content').extract()
            user_name = response.xpath('//span[@class="qualified-channel-title-text"]/a/text()').extract()
            fans = response.xpath('//ul[@class="about-stats"]/li').re(re.compile(r'<li.*>.*<b>([\d|,]*)</b>.*subscribers.*</li>', re.S))
            played = response.xpath('//ul[@class="about-stats"]/li').re(re.compile(r'<li.*>.*<b>([\d|,]*)</b>.*views.*</li>', re.S))
            intro = response.xpath('//div[@class="about-description branded-page-box-padding"]/descendant-or-self::*/text()').extract()

            if show_id:
                user_item = UserItem()
                user_item['show_id'] = show_id[0]

                if user_name:
                    user_item['user_name'] = user_name[0]
                if fans:
                    user_item['fans'] = Util.normalize_played(fans[0])
                if played:
                    user_item['played'] = Util.normalize_played(played[0])
                if intro:
                    user_item['intro'] = "".join(intro).strip()

                user_item['spider_id'] = self.spider_id
                user_item['site_id'] = self.site_id
                user_item['url'] = response.request.url[:-len('/about')]

                items.append(user_item)

            return items

        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

