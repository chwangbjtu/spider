# -*- coding:utf-8 -*-
from scrapy.spider import Spider
from scrapy.selector import Selector
from scrapy.http import Request
from scrapy import log
from crawler.common.util import Util
from crawler.items import EpisodeItem
import traceback
import re
from datetime import datetime

class SohuYuleNewestSpider(Spider):
    name = "sohu_yule_newest"
    pipelines = ['NewestItemPipeline', 'MysqlStorePipeline']
    spider_id = "8"
    site_id = "3"
    allowed_domains = ["tv.sohu.com"]
    start_urls = (
        'http://so.tv.sohu.com/list_p1112_p20_p3_p40_p5_p6_p73_p8_p9.html',
        )
    url_prefix = 'http://so.tv.sohu.com'

    def parse(self, response):
        try:
            log.msg(response.request.url, level=log.INFO)
            items = []
            sel = Selector(response)

            #video items
            videos = sel.xpath('//div[@class="column-bd clear"]/ul/li')
            for v in videos:
                thumb = v.xpath('div[@class="show-pic"]/a/img/@src').extract()
                played = v.xpath('div[@class="show-txt"]/div/p/a[@class="acount"]/text()').extract()
                href = v.xpath('div[@class="show-pic"]/a/@href').extract()

                if href:
                    items.append(Request(url=href[0], callback=self.parse_episode, meta={'thumb': thumb, 'played': played}))

            #pages
            next_page = sel.xpath('//div[@class="page"]/a[@class="next"]/@href').extract()
            if next_page:
                items.append(Request(url=self.url_prefix+next_page[0], callback=self.parse))

            return items

        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def parse_episode(self, response):
        try:
            log.msg('%s' % response.request.url)
            thumb = response.request.meta['thumb']
            played = response.request.meta['played']
            items = []
            sel = Selector(response)

            #video info
            title = sel.xpath('//div[@id="crumbsBar"]/div/div[@class="left"]/h2/text()').extract()
            #category= sel.xpath('//div[@id="crumbsBar"]/div/div[@class="left"]/div/descendant-or-self::*/text()').extract()
            category = sel.xpath('//head/meta[@name="category"]/@content').extract()
            scripts = sel.xpath('//script[@type="text/javascript"]')
            video_id = scripts.re('vid=\"(\d+)\"')
            show_id = scripts.re('nid = \"(\d+)\"')
            tag = scripts.re('tag = \"(.*?)\"')
            upload = sel.xpath('//div[@class="info info-con"]/ul').re(re.compile(u'<li.*>发布：(.*?)</li>', re.S))
            description = sel.xpath('//div[@class="info info-con"]/p[@class="intro"]/text()').extract()

            ep_item = EpisodeItem()
            if title:
                ep_item['title'] = "".join(title).strip()
            if video_id:
                ep_item['video_id'] = video_id[0]
            if show_id:
                ep_item['show_id'] = show_id[0]
            if tag:
                ep_item['tag'] = tag[0].strip().replace(' ', '|')
            if upload:
                ep_item['upload_time'] = Util.get_datetime(upload[0].strip())
            if description:
                ep_item['description'] = description[0].strip()
            if category:
                ep_item['category'] = category[0]

            if thumb:
                ep_item['thumb_url'] = thumb[0]
            if played:
                ep_item['played'] = Util.normalize_played(played[0])

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url

            items.append(ep_item)

            return items
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)

