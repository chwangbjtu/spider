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

class YoutubeHottestSpider(Spider):
    name = "youtube_hottest"
    pipelines = ['MysqlStorePipeline']
    spider_id = "4"
    site_id = "2"
    allowed_domains = ["www.youtube.com"]
    url_prefix = 'https://www.youtube.com'
    hottest_played_threshold = get_project_settings().get('HOTTEST_PLAYED_THRESHOLD')
    hottest_time_threshold = get_project_settings().get('HOTTEST_TIME_THRESHOLD')

    mgr = DbManager.instance()

    def __init__(self, orders=None, *args, **kwargs):
        super(YoutubeHottestSpider, self).__init__(*args, **kwargs)
        if orders:
            orders = json.loads(orders)
            self.max_search_page = get_project_settings().get('MAX_MANUAL_SEARCH_PAGE')
        else:
            orders = self.mgr.get_ordered_url(site_name='youtube')
            self.max_search_page = get_project_settings().get('MAX_SEARCH_PAGE')
        if orders:
            self._orders = orders
        else:
            self._orders = []
        
    def start_requests(self):
        try:
            items = []
            for i in self._orders:
                items.append(Request(url=i['url'], callback=self.parse, meta={'audit': i['audit'], 'priority': i['priority']}))
            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse(self, response):
        try:
            log.msg(response.request.url, level=log.INFO)
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']
            category = [r['user'] for r in self._orders if r['url'] == response.request.url]
            if not category:
                category = ['other']

            items = []
            items.append(Request(url=response.request.url+"/videos", callback=self.parse_video, meta={'category': category[0], 'audit': audit, 'priority': priority}))

            return items

        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_video(self, response):
        try:
            log.msg(response.request.url, level=log.INFO)
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']
            category = response.request.meta['category']
            items = []

            #content
            #content = response.xpath('//div[@id="video-page-content"]/ul/li')
            content = response.xpath('//ul[@id="channels-browse-content-grid"]/li')
            self.parse_page_content(items, content, category, audit, priority)

            #next page
            #next_page = response.xpath('//div[@id="video-page-content"]/button/@data-uix-load-more-href').extract()
            next_page = response.xpath('//button/@data-uix-load-more-href').extract()
            if next_page:
                items.append(Request(url=self.url_prefix + next_page[0], callback=self.parse_more_video, meta={'page': 2, 'category': category, 'audit': audit, 'priority': priority}))

            return items

        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_more_video(self, response):
        try:
            log.msg(response.request.url, level=log.INFO)
            page = response.request.meta['page']
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']
            category = response.request.meta['category']
            if page > self.max_search_page:
                return

            items = []

            body = json.loads(response.body)
            self.parse_page_content(items, Selector(text=body['content_html']).xpath('./body/li'), category, audit, priority)

            #next page
            next_page = Selector(text=body['load_more_widget_html']).xpath('//button/@data-uix-load-more-href').extract()
            if next_page:
                items.append(Request(url=self.url_prefix + next_page[0], callback=self.parse_more_video, meta={'page': page+1, 'category': category, 'audit': audit, 'priority': priority}))

            return items

        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_page_content(self, items, content, category, audit, priority):
        try:
            for s in content:
                url = s.xpath('./div/div/div[@class="yt-lockup-thumbnail"]/span/a/@href').extract()
                thumb_url = s.xpath('./div/div/div[@class="yt-lockup-thumbnail"]/span/a/span/span/span/img/@src').extract()
                views = s.xpath('./div/div/div[@class="yt-lockup-content"]/div[@class="yt-lockup-meta"]/ul/li/text()').re('([\d|,]*) views')
                upload_time = s.xpath('./div/div/div[@class="yt-lockup-content"]/div[@class="yt-lockup-meta"]/ul/li[@class="yt-lockup-deemphasized-text"]/text()').extract()
                '''
                if not views or int(Util.normalize_played(views[0])) < int(self.hottest_played_threshold):
                    #log.msg('discard played: %s' % url[0])
                    continue
                if not upload_time or Util.get_youtube_upload_time(upload_time[0].strip()) >= int(self.hottest_time_threshold):
                    #log.msg('discard upload_time: %s' % url[0])
                    continue
                '''

                if url:
                    items.append(Request(url=self.url_prefix + url[0], callback=self.parse_episode, meta={'thumb_url': thumb_url, 'upload_time': upload_time, 'category': category, 'audit': audit, 'priority': priority}))

        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_episode(self, response):
        try:
            log.msg('%s' % response.request.url)
            audit = response.request.meta['audit']
            priority = response.request.meta['priority']
            thumb_url = response.request.meta['thumb_url']
            upload_time = response.request.meta['upload_time']
            category = response.request.meta['category']
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
                ep_item['played'] = Util.normalize_played(played[0])
                
            if audit:
                ep_item['audit'] = audit
                
            if priority:
                ep_item['priority'] = priority

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['format_id'] = 2
            ep_item['url'] = Util.normalize_youtube_url(response.request.url)

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
            fans = response.xpath('//span[@class="about-stat"]').re(re.compile(r'<span.*>.*<b>([\d|,]*)</b>.*subscribers.*</span>', re.S))
            played = response.xpath('//span[@class="about-stat"]').re(re.compile(r'<span.*>.*<b>([\d|,]*)</b>.*views.*</span>', re.S))
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

