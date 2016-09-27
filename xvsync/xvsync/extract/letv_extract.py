# -*- coding:utf-8 -*-
import re
import time
import traceback
import logging

from xvsync.common.util import Util
from xvsync.items import MediaItem, VideoItem

class letv_extract(object):

    list_channels = [u'电影', u'电视剧', u'综艺', u'动漫']
    list_channels_pinyin = {u'电影':'movie', u'电视剧':'tv', u'综艺':'zongyi', u'动漫':'comic'}
    ignore_channels = [u'短片', u'片段', u'片花', u'预告']

    @staticmethod
    def video_extract(response):
        items = []
        try:
            #list列表页
            results = response.xpath('.//a/@href[re:test(., "http://www\.letv\.com/ptv/vplay/[\d]+\.html")]').extract()
            for item in results:
                videoItem = VideoItem()
                videoItem['url'] = item 
                items.append(videoItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    @staticmethod
    def video_info_extract(response, videoItem):
        try:
            if videoItem == None:
                videoItem = VideoItem()
            sels = response.xpath('.//dt[@data-statectn="n_w150_dt"]')
            if sels:
                #媒体页-电影
                results = sels.xpath('.//p[@class="p1"]//img/@src').extract()
                if results:
                    videoItem['thumb_url'] = results[0]
            else:
                class_names = response.xpath('./@class').extract()
                if class_names and 'w120' == class_names[0]:
                    #媒体页-电视剧，动漫
                    urls = response.xpath('.//p[@class="p1"]/a/@href').extract()
                    vnums = response.xpath('.//p[@class="p1"]/a/text()').extract()
                    titles = response.xpath('./dt/a/img/@title').extract()
                    thumb_urls = response.xpath('./dt/a/img/@src').extract()
                    if urls:
                        videoItem['url'] = urls[0]
                    if vnums:
                        vnums = re.findall(r'[\d]+', vnums[0]) 
                        vnum = ''.join(vnums)
                        if vnum:
                            videoItem['vnum'] = vnum 
                    if titles:
                        videoItem['title'] = titles[0]
                    if thumb_urls:
                        videoItem['thumb_url'] = thumb_urls[0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    @staticmethod
    def media_extract(response):
        items = []
        try:
            #播放页的详情部分
            #http://www.letv.com/ptv/vplay/20655099.html#vid=20061199
            #http://www.letv.com/ptv/vplay/22299495.html
            results = response.xpath('.//a[contains(text(), "%s")]/@href' % u'更多详情').extract()
            if not results:
                #http://www.letv.com/ptv/vplay/1609062.html
                results = response.xpath('.//a[contains(text(), "%s")]/@href' % u'影片详情').extract()
            if results:
                url = results[0]
                mediaItem = MediaItem()
                mediaItem['url'] = url
                items.append(mediaItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    @staticmethod
    def media_info_extract(response, mediaItem):
        try:
            if mediaItem == None:
                mediaItem = MediaItem()
            #播放页
            class_names = response.xpath('./@type').extract()
            if class_names and 'text/javascript' == class_names[0]:
                #媒体页
                titles = response.re('title[ ]?:[ ]?\"(.*)\"')
                if titles:
                    mediaItem['title'] = titles[0]
                #播放页
                pids = response.re('pid[ ]?:[ ]?(\d+)')
                totals = response.re('totalcount[ ]?:[ ]?(\d+)')
                trylooks = response.re('trylook[ ]?:[ ]?(\d*)')
                pPics = response.re('pPic[ ]?:[ ]?\"(.*)\"')
                if pids:
                    mediaItem['cont_id'] = pids[0]
                if totals:
                    mediaItem['vcount'] = totals[0]
                """
                if trylooks:
                    trylook = str(trylooks[0])
                    if trylook == '0':
                        mediaItem['paid'] = 0
                    else:
                        mediaItem['paid'] = 1
                """
                if pPics:
                    poster_url = pPics[0]
                    mediaItem['poster_url'] = poster_url 
                if u'电影' == mediaItem['channel_id']: 
                    #电影，获取时长 
                    durations = response.re('duration[ ]?:[ ]?\"(.*)\"')
                    if durations:
                        duration = durations[0]
                        durations = duration.split(':')
                        length = len(durations)
                        if length == 3:
                            duration = int(durations[0])*60 + int(durations[1])
                            duration = str(duration)
                        elif length == 2:
                            duration = durations[0]
                        mediaItem['duration'] = duration
            #媒体页
            results = response.xpath('.//span[@class="s-t"]/text()').extract()
            if results:
                latests = re.findall(r'[\d]+', results[0])
                if latests:
                    latest = ''.join(latests)
                    mediaItem['latest'] = latest
            #媒体页-综艺、动漫、电视剧
            sels = response.xpath('.//dd[@data-statectn="n_textInfo"]')
            if sels:
                results = sels.xpath('.//p[@class="p1"]//a/text()').extract()
                if results:
                    if u'综艺' == mediaItem['channel_id']: 
                        mediaItem['actor'] = Util.join_list_safely(results)
                    else:
                        mediaItem['director'] = Util.join_list_safely(results)
                results = sels.xpath('.//p[@class="p2"]//a/text()').extract()
                if results:
                    if u'综艺' != mediaItem['channel_id']: 
                        mediaItem['actor'] = Util.join_list_safely(results)
                results = sels.xpath('.//p[@class="p3"]//a/text()').extract()
                if results:
                    mediaItem['district'] = Util.join_list_safely(results)
                if 'release_date' not in mediaItem:
                    results = sels.xpath('.//p[@class="p4"]//a/text()').extract()
                    if results:
                        release_date = results[0]
                        release_date = Util.str2date(release_date)
                        mediaItem['release_date'] = release_date 
                results = sels.xpath('.//p[@class="p5"]//a/text()').extract()
                if results:
                    mediaItem['type'] = Util.join_list_safely(results)
                results = sels.xpath('.//p[@class="p7"]/text()').extract()
                if results:
                    intro = results[0].strip()
                    mediaItem['intro'] = intro
            else:
                #媒体页-电影
                sels = response.xpath('.//dd[@data-statectn="n_w150_dd"]')
                if sels:
                    results = sels.xpath('.//p[@class="p2"]//a/text()').extract()
                    if results:
                        mediaItem['director'] = Util.join_list_safely(results)
                    results = sels.xpath('.//p[@class="p3"]//a/text()').extract()
                    if results:
                        mediaItem['actor'] = Util.join_list_safely(results)
                    results = sels.xpath('.//span[@class="s4"]//a/text()').extract()
                    if results:
                        mediaItem['district'] = Util.join_list_safely(results)
                    results = sels.xpath('.//span[@class="s5"]//a/text()').extract()
                    if results:
                        for item in results:
                            if re.match(r"^[\d-]+$", item):
                                if 'release_date' not in mediaItem:
                                    release_date = Util.str2date(item)
                                    mediaItem['release_date'] = release_date
                                results.remove(item)
                                break
                        mediaItem['type'] = Util.join_list_safely(results)
                    results = sels.xpath('.//p[@class="p6"]/text()').extract()
                    if results:
                        intro = results[0].strip()
                        mediaItem['intro'] = intro 
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
