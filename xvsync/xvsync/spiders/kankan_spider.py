# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re
import time
import json
import traceback
import logging
from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.utils.project import get_project_settings

from xvsync.items import MediaVideoItem, MediaItem, VideoItem
from xvsync.extract.kankan_extract import kankan_extract 
from xvsync.common.util import Util
from xvsync.db.db_mgr import DbManager

class kankan_spider(Spider):
    '''
        kankan爬虫流程：
            (1)list列表页 -> 播放页 -> 媒体页
            (2)播放页 -> 媒体页
        由于kankan在list表页的全部即代表全部，所以无需每个标签都爬取
    '''
    site_code = 'kankan'
    name = site_code
    mgr = DbManager.instance()
    max_number = '100000'
    vip_prefix_url = 'http://vip.kankan.com'
    #通过json传递的参数
    json_data = None
    #统计数据用
    #count = 0

    #忽略类型：预告片
    skip_types = {'pre':u'预告片'}

    def __init__(self, json_data=None, *args, **kwargs):
        super(kankan_spider, self).__init__(*args, **kwargs)
        if json_data:
            self.json_data = json.loads(json_data)
    
    def start_requests(self):
        items = []
        try:
            self.load_member_variable()
            if self.json_data:
                items = items + self.load_video_urls()
            else:
                list_prefix_url = 'http://movie.kankan.com/type/%s/' 
                for list_channel in kankan_extract.list_channels:
                    list_channel_pinyin = kankan_extract.list_channels_pinyin[list_channel]
                    url = list_prefix_url % list_channel_pinyin
                    items.append(Request(url=url, callback=self.list_parse, meta={'first':True, 'id':list_channel}))
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    def load_member_variable(self):
        try:
            self.site_id = None 
            self.os_id = None
            self.channels_name_id = {}
            self.max_update_page = self.max_number
            res = self.mgr.get_site(self.site_code)
            if res:
                self.site_id = res['site_id']
            res = self.mgr.get_os(os_name='web')
            if res:
                self.os_id = res['os_id'] 
            for list_channel in kankan_extract.list_channels:
                res = self.mgr.get_channel(channel_name=list_channel)
                self.channels_name_id[list_channel] = res['channel_id']
            max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
            if max_update_page and max_update_page > 0:
                self.max_update_page = max_update_page
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def load_video_urls(self):
        items = []
        try:
            if self.json_data:
                cmd = self.json_data['cmd'] if 'cmd' in self.json_data else None 
                if cmd == 'trig':
                    stat = self.json_data['stat'] if 'stat' in self.json_data else None 
                    res = self.mgr.get_untrack_url(self.site_code, stat)
                    for item in res:
                        mediaVideoItem = MediaVideoItem()
                        mediaVideoItem['sid'] = item['sid']
                        mediaVideoItem['untrack_id'] = item['untrack_id']
                        mediaItem = MediaItem()
                        mediaItem['channel_id'] = item['name']
                        mediaVideoItem['media'] = mediaItem
                        url = item['url']
                        items.append(Request(url=url, callback=self.video_parse, meta={'item':mediaVideoItem}))
                elif cmd == 'assign':
                    tasks = self.json_data['task'] if 'task' in self.json_data else None 
                    for task in tasks: 
                        mediaVideoItem = MediaVideoItem()
                        mediaVideoItem['sid'] = task['sid'] if 'sid' in task else None
                        mediaVideoItem['untrack_id'] = task['untrack_id'] if 'untrack_id' in task else None
                        mediaItem = MediaItem()
                        mediaItem['channel_id'] = task['name'] 
                        mediaVideoItem['media'] = mediaItem
                        url = task['url']
                        items.append(Request(url=url, callback=self.video_parse, meta={'item':mediaVideoItem}))
                elif cmd == 'test':
                    channel_id = self.json_data['id'] if 'id' in self.json_data else None 
                    url = self.json_data['url'] if 'url' in self.json_data else None 
                    if url and channel_id:
                        list_channel = self.mgr.get_channel_name(channel_id)
                        if list_channel:
                            list_channel = list_channel['name']
                            items.append(Request(url=url, callback=self.list_parse, meta={'first':False, 'id':list_channel}))
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    def list_parse(self, response):
        items = []
        try:
            request_url = response.request.url
            logging.log(logging.INFO, 'url: %s' % request_url)
            prefix_url = Util.prefix_url_parse(request_url)
            first = response.request.meta['first'] if 'first' in response.request.meta else False
            channel_id = response.request.meta['id'] if 'id' in response.request.meta else None  
            if first:
                sels = response.xpath('//div[@class="tab_box"]//a')
                for sel in sels:
                    texts = sel.xpath('.//span/text()').extract()
                    if texts:
                        text = texts[0].replace(' ', '')
                        if text == u'最新':
                            urls = sel.xpath('./@href').extract()
                            url = urls[0]
                            items.append(Request(url=url, callback=self.list_parse, meta={'id':channel_id}))
                            break
            else:
                page = response.request.meta['page'] if 'page' in response.request.meta else 1  
                if page > self.max_update_page:
                    return items
                #list列表
                sels = response.xpath('//ul[@class="movielist"]/li')
                for sel in sels:
                    results = kankan_extract.video_extract(sel)
                    for item in results:
                        mediaVideoItem = MediaVideoItem()
                        mediaItem = MediaItem()
                        mediaItem['channel_id'] = channel_id
                        kankan_extract.media_info_extract(sel, mediaItem)
                        mediaVideoItem['media'] = mediaItem
                        items.append(Request(url=item['url'], callback=self.video_parse, meta={'item':mediaVideoItem}))
                        break
                #下一页
                sels = response.xpath('//p[@class="list-pager-v2"]')
                results = kankan_extract.next_page_extract(sels)
                page = page + 1
                for item in results:
                    url = Util.get_absolute_url(item, prefix_url) 
                    items.append(Request(url=url, callback=self.list_parse, meta={'page':page, 'id':channel_id}))
                    break
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'url: %s' % request_url)
        finally:
            return items

    def video_parse(self, response):
        items = []
        try:
            request_url = response.request.url
            logging.log(logging.INFO, 'video url: %s' % request_url)
            prefix_url = Util.prefix_url_parse(request_url)
            mediaVideoItem = response.request.meta['item'] if 'item' in response.request.meta else MediaVideoItem()
            mediaItem = mediaVideoItem['media'] if 'media' in mediaVideoItem else MediaItem()
            if prefix_url == self.vip_prefix_url:
                mediaItem['paid'] = '1'
            else:
                mediaItem['paid'] = '0'
            #http://vod.kankan.com/v/87/87998.shtml
            sels = response.xpath('//ul[@class="movieinfo"]')
            if sels:
                kankan_extract.media_info_extract(sels, mediaItem)
            sels = response.xpath('//p[@id="movie_info_intro_l"]')
            if sels:
                kankan_extract.media_info_extract(sels, mediaItem)
            #普通电影，电视剧，综艺，动漫
            sels = response.xpath('//div[@class="header_title"]')
            if sels:
                results = kankan_extract.media_extract(sels)
            else:
                #http://vip.kankan.com/vod/88365.html
                sels = response.xpath('//div[@class="movie_info"]')
                if sels:
                    kankan_extract.media_info_extract(sels, mediaItem)
                    results = kankan_extract.media_extract(sels)
                else:
                    #http://vip.kankan.com/vod/88169.html?fref=kk_search_sort_01
                    sels = response.xpath('//div[@class="aside"]//div[@class="intro"]')
                    results = kankan_extract.media_extract(sels)
            for item in results:
                mediaItem['url'] = item['url']
                mediaVideoItem['media'] = mediaItem
                items.append(Request(url=item['url'], callback=self.media_parse, meta={'item':mediaVideoItem}))
                break
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'video url: %s' % request_url)
        finally:
            return items

    def media_parse(self, response):
        items = []
        try:
            request_url = response.request.url
            logging.log(logging.INFO, 'media url: %s' % request_url)
            prefix_url = Util.prefix_url_parse(request_url)
            mediaVideoItem = response.request.meta['item'] if 'item' in response.request.meta else MediaVideoItem()
            mediaItem = mediaVideoItem['media'] if 'media' in mediaVideoItem else MediaItem()
            #过滤掉skip_types类型的影片
            sels = response.xpath('//head//script')
            if sels:
                regex_express = 'movieInfo\.play_type[ ]?=[ ]?\'(.*)\''
                match_result = sels.re(regex_express)
                if match_result:
                    play_type = match_result[0]
                    if play_type in self.skip_types:
                        return items
            #由于某些URL会有跳转，所以应保存真是的URL
            #http://movie.kankan.com/movie/88365 ->  http://data.movie.kankan.com/movie/88365
            mediaItem['url'] = request_url
            sels = response.xpath('//head')
            kankan_extract.media_info_extract(sels, mediaItem)
            sels = response.xpath('//div[@class="info_list"]')
            if sels:
                kankan_extract.media_info_extract(sels, mediaItem)
            sels = response.xpath('//ul[@class="detail_ul"]')
            if sels:
                kankan_extract.media_info_extract(sels, mediaItem)

            #获取媒体的剧集信息
            videoItems = []
            if u'综艺' == mediaItem['channel_id']:
                #综艺
                sels = response.xpath('//div[@id[re:test(., "fenji_[\d]+_[\d]+")]]')
                for sel in sels:
                    video_sels = sel.xpath('.//li')
                    for video_sel in video_sels:
                        videoItem = VideoItem()
                        videoItem['intro'] = mediaItem['channel_id']
                        kankan_extract.video_info_extract(video_sel, videoItem)
                        if 'url' in videoItem:
                            url = videoItem['url']
                            url = Util.get_absolute_url(url, prefix_url)
                            videoItem['url'] = url
                            self.set_video_info(videoItem, mediaItem['channel_id'])
                            videoItems.append(videoItem)
            elif u'电影' == mediaItem['channel_id']:
                #电影，从立即观看中获取
                videoItem = VideoItem()
                Util.copy_media_to_video(mediaItem, videoItem)
                sels = response.xpath('//div[@class="section clearfix s2"]')
                if sels:
                    urls = sels.xpath('.//a[starts-with(@class, "foc")]/@href').extract()
                    thumb_urls = sels.xpath('.//a[@class="foc"]/img/@src').extract()
                    if urls:
                        url = urls[0]
                        url = Util.get_absolute_url(url, prefix_url)
                        videoItem['url'] = url
                    if thumb_urls:
                        videoItem['thumb_url'] = thumb_urls[0]
                    self.set_video_info(videoItem, mediaItem['channel_id'])
                    videoItems.append(videoItem)
            else:
                #电视剧
                sels = response.xpath('//div[@id[re:test(., "fenji_[\d]+_asc")]]')
                if not sels:
                    #动漫,电视剧
                    sels = response.xpath('//ul[@id[re:test(., "fenji_[\d]+_asc")]]')
                for sel in sels:
                    video_sels = sel.xpath('.//li')
                    for video_sel in video_sels:
                        videoItem = VideoItem()
                        videoItem['intro'] = mediaItem['channel_id']
                        kankan_extract.video_info_extract(video_sel, videoItem)
                        if 'url' in videoItem:
                            url = videoItem['url']
                            url = Util.get_absolute_url(url, prefix_url)
                            videoItem['url'] = url
                            self.set_video_info(videoItem, mediaItem['channel_id'])
                            videoItems.append(videoItem)
            if videoItems:
                #设置ext_id
                Util.set_ext_id(mediaItem, videoItems)

                self.set_media_info(mediaItem)

                mediaVideoItem['media'] = mediaItem
                mediaVideoItem['video'] = videoItems
                items.append(mediaVideoItem)
                #self.count = self.count + 1
                #logging.log(logging.INFO, 'count: %s' % str(self.count))
            else:
                logging.log(logging.INFO, '%s: no videos' % request_url)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'media url: %s' % request_url)
        finally:
            return items

    def set_media_info(self, mediaItem):
        mediaItem['site_id'] = self.site_id
        #由于之前的channel_id存放的是中文的频道名称,需要转换成真正的channel_id
        channel_name = mediaItem['channel_id']
        mediaItem['channel_id'] = self.channels_name_id[channel_name]
        #设置info_id
        mediaItem['info_id'] = Util.md5hash(Util.summarize(mediaItem))          
            
    def set_video_info(self, videoItem, channel_name):
        videoItem['os_id'] = self.os_id
        videoItem['site_id'] = self.site_id
        url = videoItem['url']
        if u'电影' == channel_name:
            channel_name = kankan_extract.list_channels_pinyin[channel_name]
            url = Util.normalize_url(url, self.site_code, channel_name)
        else:
            url = Util.normalize_url(url, self.site_code)
        videoItem['url'] = url
        videoItem['ext_id'] = Util.md5hash(url)            
        video_url_express = 'http://[^/]*.kankan.com.+?/([\d]+).[s]?html'
        video_url_regex = re.compile(video_url_express)
        match_results = video_url_regex.search(url)
        if match_results:
            id = match_results.groups()[0]
            videoItem['cont_id'] = id

    '''
    def template(self, response):
        items = []
        try:
            return items
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items
    '''
