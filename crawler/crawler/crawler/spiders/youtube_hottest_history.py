# -*- coding:utf-8 -*-
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
    name = "youtube_hottest_history"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    spider_id = "4"
    site_id = "2"
    allowed_domains = ["www.youtube.com"]
    url_prefix = 'https://www.youtube.com'
    max_search_page = get_project_settings().get('MAX_SEARCH_PAGE')
    hottest_played_threshold = get_project_settings().get('HOTTEST_PLAYED_THRESHOLD')
    hottest_time_threshold = get_project_settings().get('HOTTEST_TIME_THRESHOLD')

    mgr = DbManager.instance()
    #orders = mgr.get_ordered_url(site_name='youtube')
    orders = [{"url": "https://www.youtube.com/channel/UC87tyACMd1KkeQAGVqVV-8Q", "user": u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCCyGXp9QJjnb144yMDkVfCg", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCfmenbM9GiyBe-1mqIL04zw", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCknIagYAYBWMQoi-bZe837w", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCLSMkVmeUS9zh3QV7cmyLcQ", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCmrvMnOXdSCJobSFbwXsupA", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCorOG0mIAkUii9WPJfuIlqA", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCs2mgdP22G07gw4Kg_oHgTg", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCOuQbxT3ChGo6B_cJz9InRg", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCsUe_Tm_BvNmw9oz4UVVwDg", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCCtW5W39Wm1UUfYfg5Togvw", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCuETX7HT959-oS2h2QY6bNg", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCsjyZN9CL9lyt4vFHfXypSQ", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCr67Kfo61QXJ2fVVbd9R5zQ", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCAamGYSv7_GviMf7EaCEGHA", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UC57A2kvwlPUCKzdAe9kpcew", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UC3ICcukYYeSn26KlCRnhOhA", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCJ5nhMUn7yfAqy8bcVYMjxA", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCk_YsHnf9-eEo9MP4qDuoHQ", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UC4Kw2IKCl6Bg3Bb66Di9_1g", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCjwmbv6NE4mOh8Z8VhPUx1Q", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UC_tl_KpH_fwqrE98HOnQ-8g", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCDHR5IsDMjaksuKItrtVDMw", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UC_7E_ls1UMGuXfyKMQkGczQ", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCZnk70gBD8P6mPe9PDkj-eg", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCOpTxvjaO7Sk0VYQUgV8xCA", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCctVKh07hVAyQtqpl75pxYA", "user":u'生活百科'},
                {"url": "https://www.youtube.com/channel/UCgMBvUmA-4nidyz5UyciBEw", "user":u'生活百科'},
                ]
    start_urls = [r['url'] for r in orders]

    def parse(self, response):
        try:
            log.msg(response.request.url, level=log.INFO)
            category = [r['user'] for r in self.orders if r['url'] == response.request.url]
            if not category:
                category = ['other']

            items = []
            items.append(Request(url=response.request.url+"/videos", callback=self.parse_video, meta={'category': category[0]}))

            return items

        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_video(self, response):
        try:
            log.msg(response.request.url, level=log.INFO)
            category = response.request.meta['category']
            items = []

            #content
            #content = response.xpath('//div[@id="video-page-content"]/ul/li')
            content = response.xpath('//ul[@id="channels-browse-content-grid"]/li')
            self.parse_page_content(items, content, category)

            #next page
            #next_page = response.xpath('//div[@id="video-page-content"]/button/@data-uix-load-more-href').extract()
            next_page = response.xpath('//button/@data-uix-load-more-href').extract()
            if next_page:
                items.append(Request(url=self.url_prefix + next_page[0], callback=self.parse_more_video, meta={'page': 2, 'category': category}))

            return items

        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_more_video(self, response):
        try:
            log.msg(response.request.url, level=log.INFO)
            page = response.request.meta['page']
            category = response.request.meta['category']
            '''
            if page > self.max_search_page:
                return
            '''

            items = []

            body = json.loads(response.body)
            self.parse_page_content(items, Selector(text=body['content_html']).xpath('./body/li'), category)

            #next page
            next_page = Selector(text=body['load_more_widget_html']).xpath('//button/@data-uix-load-more-href').extract()
            if next_page:
                items.append(Request(url=self.url_prefix + next_page[0], callback=self.parse_more_video, meta={'page': page+1, 'category': category}))

            return items

        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_page_content(self, items, content, category):
        try:
            for s in content:
                url = s.xpath('./div/div/div[@class="yt-lockup-thumbnail"]/a/@href').extract()
                thumb_url = s.xpath('./div/div/div[@class="yt-lockup-thumbnail"]/a/span/span/span/img/@src').extract()
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
                    items.append(Request(url=self.url_prefix + url[0], callback=self.parse_episode, meta={'thumb_url': thumb_url, 'upload_time': upload_time, 'category': category}))

        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_episode(self, response):
        try:
            log.msg('%s' % response.request.url)
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

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = Util.normalize_youtube_url(response.request.url)
            ep_item['stash'] = '1'

            items.append(ep_item)

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

