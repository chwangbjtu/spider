# -*- coding:utf-8 -*- 
from scrapy.spiders import CrawlSpider, Rule
from scrapy.http import Request
from scrapy.linkextractors import LinkExtractor
import logging
import traceback
import json

from xvsync.db.db_mgr import DbManager
from xvsync.spiders.base.v360_base import *
from xvsync.common.util import *
from xvsync.items import MediaVideoItem


class H360Spider(CrawlSpider):
    name = "h360kan"
    site_name = "360kan"
    allowed_domains = ["v.360.cn", "www.360kan.com"]
    url_prefix = 'http://www.360kan.com'

    rules = (Rule(LinkExtractor(allow=r'/m/\w+.html', tags=('a',)), callback='parse_media', follow=False, cb_kwargs={'channel': 'movie'}),
             Rule(LinkExtractor(allow=r'/tv/\w+.html', tags=('a',)), callback='parse_media', follow=False, cb_kwargs={'channel': 'tv'}),
             Rule(LinkExtractor(allow=r'/ct/\w+.html', tags=('a',)), callback='parse_media', follow=False, cb_kwargs={'channel': 'cartoon'}),
             Rule(LinkExtractor(allow=r'/va/\w+.html', tags=('a',)), callback='parse_media', follow=False, cb_kwargs={'channel': 'variaty'}),
            )

    start_urls = ['http://www.360kan.com/dianying/index.html',
                  'http://www.360kan.com/dianshi/index.html',
                  'http://www.360kan.com/zongyi/index.html', 
                  'http://www.360kan.com/dongman/index.html',
                 ]

    def __init__(self, *args, **kwargs):
        super(H360Spider, self).__init__(*args, **kwargs)
        self.mgr = DbManager.instance()
        self.parser = {'movie': V360ParserMovie(), 'tv': V360ParserTv(), 'variaty': V360ParserVariaty(), 'cartoon': V360ParserCartoon()}

        self.site_id = self.mgr.get_site(site_code=self.site_name)['site_id']
        self.os_id = self.mgr.get_os(os_name='web')
        self.channel_map = self.mgr.get_channel_map()

    def parse_media(self, response, **kwargs):
        try:
            channel = kwargs['channel']
            logging.log(logging.INFO, response.request.url)
            items = []
            mv = MediaVideoItem();
            mv["video"] = []
            
            media_info = self.parser[channel].parse_media_info(response)
            #print media_info
            if media_info:
                media_info['site_id'] = self.site_id
                media_info['channel_id'] = self.channel_map[channel]
                media_info['url'] = Util.normalize_url(response.request.url)
                media_info['ext_id'] = Util.md5hash(media_info['url'])
                media_info['info_id'] = Util.md5hash(Util.summarize(media_info))
            mv["media"] = media_info

            ext_video = self.parser[channel].parse_video(response)
            #print ext_video
            if ext_video:
                mv["ext_video"] = {'site_id': self.site_id, 'channel_id': media_info['channel_id'], 'urls': ext_video, 'media_ext_id': media_info['ext_id']}

            reviews = self.parser[channel].parse_review(response)
            if reviews:
                mv["review"] = {'urls': reviews, 'media_ext_id': media_info['ext_id']}

            items.append(mv)
            return items

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

