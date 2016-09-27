# -*- coding:utf-8 -*-
from scrapy.spider import Spider
from scrapy.selector import Selector
from scrapy.http import Request
from scrapy import log
from scrapy.utils.project import get_project_settings
from crawler.common.util import Util
from crawler.items import UserItem
import traceback
import re
from datetime import datetime
import json

class YoutubeChannelSpider(Spider):
    name = "youtube_channel"
    pipelines = ['MysqlStorePipeline']
    spider_id = "32"
    site_id = "2"
    allowed_domains = ["www.youtube.com"]
    url_prefix = 'https://www.youtube.com'
    start_urls = ('https://www.youtube.com/channels',
                    )

    def parse(self, response):
        try:
            log.msg(response.request.url, level=log.INFO)
            items = []

            categories = response.xpath('//div[@class="yt-gb-shelf"]/h3/span/a[@class="category-title-link"]/@href').extract()

            for c in categories:
                if c.find('paid') < 0:
                    items.append(Request(url=self.url_prefix+c, callback=self.parse_category))
                    items.append(Request(url=self.url_prefix+c+"?gl=HK", callback=self.parse_category))
                    items.append(Request(url=self.url_prefix+c+"?gl=TW", callback=self.parse_category))

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_category(self, response):
        try:
            log.msg(response.request.url, level=log.INFO)
            items = []

            channels = response.xpath('//div[@class="yt-gb-shelf"]/div/a/@href').extract()

            for c in channels:
                items.append(Request(url=self.url_prefix+c+"/about", callback=self.parse_about))

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

