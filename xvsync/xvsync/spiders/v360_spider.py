# -*- coding:utf-8 -*- 
from scrapy.spiders import Spider
from scrapy.http import Request
import logging
import traceback
import json
import hashlib

from xvsync.db.db_mgr import DbManager
from xvsync.spiders.base.v360_base import *
from xvsync.common.util import *
from xvsync.items import MediaVideoItem

class V360Spider(Spider):
    name = "360kan"
    allowed_domains = ["v.360.cn", "www.360kan.com"]
    url_prefix = 'http://www.360kan.com'

    def __init__(self, *args, **kwargs):
        super(V360Spider, self).__init__(*args, **kwargs)
        self.mgr = DbManager.instance()
        self.parser = {'movie': V360ParserMovie(), 'tv': V360ParserTv(), 'variaty': V360ParserVariaty(), 'cartoon': V360ParserCartoon()}

        self.poster_filter_md5 = self.mgr.get_poster_filter_md5()
        '''
        if 'json_data' in kwargs:
            data = json.loads(kwargs['json_data'])
            task = []
            if data['cmd'] == 'trig':
                stat = data['stat'] if 'stat' in data else None
                task = self.mgr.get_untrack_url('360kan', stat)
            elif data['cmd'] == 'assign':
                task = data['task']
            self.start = [{'channel': t['code'], 'url': t['url'], 'type': URL_TYPE_PLAY} for t in task]
        else:
        '''
        self.start = [{'channel': 'movie', 'url': 'http://www.360kan.com/dianying/list.php', 'type': URL_TYPE_MAIN}, \
                      {'channel': 'tv', 'url': 'http://www.360kan.com/dianshi/list.php', 'type': URL_TYPE_MAIN}, \
                      {'channel': 'variaty', 'url': 'http://www.360kan.com/zongyi/list.php', 'type': URL_TYPE_MAIN}, \
                      {'channel': 'cartoon', 'url': 'http://www.360kan.com/dongman/list.php', 'type': URL_TYPE_MAIN}, \
                      #{'channel': 'variaty', 'url': 'http://www.360kan.com/va/Zsgoa6dv7JM8ED.html', 'type': URL_TYPE_MEDIA}, \
                      #  {'channel': 'movie', 'url': 'http://www.360kan.com/m/f6bkZkUqcHr4TR.html', 'type': URL_TYPE_MEDIA}
                     ]

    def start_requests(self):
        try:
            #logging.log(logging.INFO, '%s' % json.dumps(self.start))
            self.site_id = self.mgr.get_site(site_code=self.name)['site_id']
            self.os_id = self.mgr.get_os(os_name='web')
            self.channel_map = self.mgr.get_channel_map()

            items = []
            for s in self.start:
                if s['type'] == URL_TYPE_MAIN:
                    items.append(Request(url=s['url'], callback=self.parse_main, meta={'channel': s['channel']}))
                elif s['type'] == URL_TYPE_MEDIA:
                    items.append(Request(url=s['url'], callback=self.parse_media, meta={'channel': s['channel']}))
                elif s['type'] == URL_TYPE_PLAY:
                    pass
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_main(self, response):
        try:
            channel = response.request.meta['channel']
            logging.log(logging.INFO, response.request.url)
            items = []
            
            sub_options = self.parser[channel].parse_options(response)
            
            for url in sub_options:
                items.append(Request(url=url, callback=self.parse_page_list, meta={'channel':channel, 'page':1}))
            #items.append(Request(url='http://www.360kan.com/dongman/list.php?cat=all&year=all&area=all&rank=rankhot', callback=self.parse_page_list, meta={'channel':channel, 'page':1}))

            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_page_list(self, response):
        try:
            channel = response.request.meta['channel']
            page = int(response.request.meta['page'])
            logging.log(logging.INFO, response.request.url)
            items = []

            page_list = self.parser[channel].parse_page_list(response)

            if page_list['urls']:
                items.extend([Request(url=self.url_prefix+url, callback=self.parse_media, meta={'channel': channel}) for url in page_list['urls']])
            if page_list['next_page']:
                items.append(Request(url=page_list['next_page'][0], callback=self.parse_page_list, meta={'channel': channel, 'page': page+1}))

            return items
                
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_media(self, response):
        try:
            channel = response.request.meta['channel']
            logging.log(logging.INFO, response.request.url)
            items = []

            mv = MediaVideoItem();
            mv["video"] = []

            media_info = self.parser[channel].parse_media_info(response)
            if 'poster_url' in media_info:
                poster_url_md5 = hashlib.md5(media_info['poster_url']).hexdigest()
                if poster_url_md5 in self.poster_filter_md5:
                    media_info['poster_url'] = None
            print media_info
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

