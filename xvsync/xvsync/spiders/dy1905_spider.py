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
from xvsync.extract.dy1905_extract import dy1905_extract 
from xvsync.common.util import Util
from xvsync.db.db_mgr import DbManager

class dy1905_spider(Spider):
    '''
        dy1905爬虫流程：
            (1)list列表页 -> 媒体页(无需进入播放页)
            (2)播放页->媒体页
        由于dy1905在list表页的全部即代表全部，所以无需每个标签都爬取
    '''
    site_code = '1905'
    name = site_code
    mgr = DbManager.instance()
    max_number = 100000
    vip_prefix_urls = ['http://vip.1905.com', 'http://vip.m1905.com']
    max_mark_depth = 10 
    #通过json传递的参数
    json_data = None
    
    #统计数据用
    #count = 0

    def __init__(self, json_data=None, *args, **kwargs):
        super(dy1905_spider, self).__init__(*args, **kwargs)
        if json_data:
            self.json_data = json.loads(json_data)
    
    def start_requests(self):
        items = []
        try:
            self.load_member_variable()
            if self.json_data:
                items = items + self.load_video_urls()
            else:
                for list_channel in dy1905_extract.list_channels:
                    if list_channel == u'电影':
                        url = 'http://www.1905.com/mdb/film/list'
                        items.append(Request(url=url, callback=self.list_parse, meta={'level':0, 'id':list_channel}))
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
            for list_channel in dy1905_extract.list_channels:
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
                    '''
                    #由于当前360爬取策略将m1905 -> 1905，故舍弃该方法
                    site_codes = ['1905', 'm1905']
                    for site_code in site_codes:
                        res = self.mgr.get_untrack_url(site_code=site_code)
                        for item in res:
                            mediaVideoItem = MediaVideoItem()
                            mediaVideoItem['sid'] = item['sid']
                            mediaVideoItem['untrack_id'] = item['untrack_id']
                            mediaItem = MediaItem()
                            mediaItem['channel_id'] = item['name']
                            mediaVideoItem['media'] = mediaItem
                            url = item['url']
                            items.append(Request(url=url, callback=self.video_parse, meta={'item':mediaVideoItem}))
                    '''
                    #由于电影网特别的site_code有:1905, m1905,舍弃原因的方式
                    if self.site_code:
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
                            level = self.max_mark_depth + 1
                            items.append(Request(url=url, callback=self.list_parse, meta={'level':level, 'id':list_channel}))
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
            level = response.request.meta['level'] if 'level' in response.request.meta else -1
            channel_id = response.request.meta['id'] if 'id' in response.request.meta else None
            if level == 0:
                urls = response.xpath('//div[@class="rightArea"]//dl[@class="srhGroup srhGroup85 clear"]//dd/a/@href').extract()
                for url in urls:
                    url = Util.get_absolute_url(url, prefix_url) 
                    items.append(Request(url=url, callback=self.list_parse, meta={'level':1, 'id':channel_id}))
            elif level == 1:
                urls = response.xpath('//div[@class="termsBox"]//*[starts-with(@class, "selectLine")]//a[text()="%s"]/@href' % u'可点播').extract() 
                if urls:
                    url = urls[0]
                    url = Util.get_absolute_url(url, prefix_url) 
                    items.append(Request(url=url, callback=self.list_parse, meta={ 'pre_url':url, 'id':channel_id}))
            else:
                page = response.request.meta['page'] if 'page' in response.request.meta else 1  
                if page > self.max_update_page:
                    return items
                #list列表 
                has_more = False
                sels = response.xpath('//ul[@class="inqList pt18"]')
                results = dy1905_extract.media_extract(sels)
                if results:
                    has_more = True
                for item in results:
                    mediaVideoItem = MediaVideoItem()
                    mediaItem = MediaItem()
                    mediaItem['channel_id'] = channel_id
                    mediaItem['poster_url'] = item['poster_url']
                    url = item['url']
                    url = Util.get_absolute_url(url, prefix_url)
                    mediaItem['url'] = url
                    mediaVideoItem['media'] = mediaItem
                    items.append(Request(url=url, callback=self.media_parse, meta={'item':mediaVideoItem}))
                #判断是否有下一页
                if has_more:
                    page = page + 1    
                    post_url = '/p%s.html'
                    post_url = post_url % str(page) 
                    pre_url = response.request.meta['pre_url'] if 'pre_url' in response.request.meta else ''
                    url = pre_url + post_url
                    items.append(Request(url=url, callback=self.list_parse, meta={'page':page, 'pre_url':pre_url, 'id':channel_id}))
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
            #播放页 - 普通电影
            sels = response.xpath('//div[@class="film-info clearfix"]//span[@class="summary"]/a/@href')
            if not sels:
                #播放页 - vip电影
                sels = response.xpath('//div[@class="f_song inner_resumeCon intro"]//div[@class="con"]/a/@href')
            if not sels:
                #播放页 - 预告片电影
                sels = response.xpath('//div[@class="related-film clear"]//a[@class="rel-film-img"]/@href')
            if sels:
                url = sels.extract()[0]
                url = Util.get_absolute_url(url, prefix_url) 
                mediaItem['url'] = url
                mediaVideoItem['media'] = mediaItem
                items.append(Request(url=url, callback=self.media_parse, meta={'item':mediaVideoItem}))
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
            #获取播放地址
            videoItems = []
            videoItem = VideoItem()
            Util.copy_media_to_video(mediaItem, videoItem)
            sels = response.xpath('//div[@class="laMovPIC fl pr22"]')
            dy1905_extract.video_info_extract(sels, videoItem)
            if 'url' not in videoItem:
                #如果videoItem['url']为空，则表示只有影片资料，无播放地址，直接扔掉
                logging.log(logging.INFO, '该影片找不到播放地址: %s' % request_url)
                return items
            url = videoItem['url']
            url = Util.get_absolute_url(url, prefix_url)
            videoItem['url'] = url
            self.set_video_info(videoItem)
            videoItems.append(videoItem)
            #媒体属性
            #设置媒体付费属性
            video_prefix_url = Util.prefix_url_parse(url)
            if video_prefix_url in self.vip_prefix_urls:
                mediaItem['paid'] = '1'
            else:
                mediaItem['paid'] = '0'

            sels = response.xpath('//div[@class="laMovPIC fl pr22"]')
            dy1905_extract.media_info_extract(sels, mediaItem)
            sels = response.xpath('//div[@class="laMovMAIN fl"]')
            dy1905_extract.media_info_extract(sels, mediaItem)

            #剧情与演职人员
            nav_sels = response.xpath('//ul[@class="navSMb"]//li[@class="mdbpLeft2"]//div[@class="nowDefLine DefBOttom"]//a')
            if nav_sels:
                for sel in nav_sels:
                    labels= sel.xpath('./text()').extract()
                    urls = sel.xpath('./@href').extract()
                    if labels and urls:
                        label = labels[0].strip()
                        if label.startswith(u'剧情') or label.startswith('演职人员'):
                            url = urls[0]
                            url = Util.get_absolute_url(url, prefix_url)
                            result = Util.get_url_content(url)
                            dy1905_extract.media_more_info_resolve(result, mediaItem)

            #设置绝对路径
            url = mediaItem['url']
            url = Util.get_absolute_url(url, prefix_url)
            mediaItem['url'] = url

            if videoItems:
                #设置ext_id
                Util.set_ext_id(mediaItem, videoItems)

                self.set_media_info(mediaItem)

                mediaVideoItem['media'] = mediaItem
                mediaVideoItem['video'] = videoItems
                items.append(mediaVideoItem)
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
        url = mediaItem['url']
        media_url_express = 'http://www.1905.com/mdb/film/([\d]+).*'
        media_url_regex = re.compile(media_url_express)
        match_results = media_url_regex.search(url)
        if match_results:
            id = match_results.groups()[0]
            mediaItem['cont_id'] = id
        #设置info_id
        mediaItem['info_id'] = Util.md5hash(Util.summarize(mediaItem)) 

    def set_video_info(self, videoItem):
        videoItem['os_id'] = self.os_id
        videoItem['site_id'] = self.site_id
        url = videoItem['url']
        url = Util.normalize_url(url, self.site_code)
        videoItem['url'] = url
        videoItem['ext_id'] = Util.md5hash(url)

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
