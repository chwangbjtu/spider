# -*- coding:utf-8 -*-
import re
import time
import traceback
import logging

from xvsync.common.util import Util
from xvsync.items import MediaItem, VideoItem

class hunantv_extract(object):
    
    #list_channels = [u'综艺']
    list_channels = [u'电影', u'电视剧', u'综艺', u'动漫']

    @staticmethod
    def video_extract(response):
        items = []
        try:
            #list列表页、正片页
            results = response.xpath('.//a/@href[re:test(., "http://www\.hunantv\.com/v/[\d]+/[\d]+/[a-zA-Z]/[\d]+\.html")]').extract()
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
            #正片页
            vnums = response.xpath('.//span[@class="a-pic-t1"]/text()').extract()
            titles = response.xpath('.//span[@class="a-pic-t2"]/text()').extract()
            urls = response.xpath('.//a/@href').extract()
            thumb_urls = response.xpath('.//img[@class="lazy"]/@data-original').extract()
            if vnums:
                vnums = re.findall(r'[\d]+', vnums[0])
                if vnums:
                    vnum = ''.join(vnums)
                    videoItem['vnum'] = vnum
            if titles:
                videoItem['title'] = titles[0]
            if thumb_urls:
                videoItem['thumb_url'] = thumb_urls[0]
            if urls:
                videoItem['url'] = urls[0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    @staticmethod
    def media_extract(response):
        items = []
        try:
            results = response.xpath('.//a/@href[re:test(., "http://www\.hunantv\.com/v/[\d]+/[\d]+")]').extract()
            for item in results:
                mediaItem = MediaItem()
                mediaItem['url'] = item 
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
            #媒体页
            sels = response.xpath('.//dt[@class="album-info"]//p')
            for sel in sels:
                labels = sel.xpath('./em[@class="label"]/text()').extract()
                if not labels:
                    continue
                label = labels[0]
                text_regex = re.compile('(%s.*%s.*)' % (u'简',u'介'))
                match_results = text_regex.search(label)
                if match_results:
                    infos = sel.xpath('./span/text()').extract()
                    if not infos:
                        continue
                    mediaItem['intro'] = infos[0]
                else:
                    infos = sel.xpath('./a/text()').extract()
                    if not infos:
                        continue
                    text_regex = re.compile('(%s.*%s.*)' % (u'导',u'演'))
                    match_results = text_regex.search(label)
                    if match_results:
                        mediaItem['director'] = Util.join_list_safely(infos) 
                    else: 
                        text_regex = re.compile('(%s.*%s.*)' % (u'主',u'演'))
                        match_results = text_regex.search(label)
                        if match_results:
                            mediaItem['actor'] = Util.join_list_safely(infos) 
                        else:
                            text_regex = re.compile('(%s.*%s.*%s.*)' % (u'主',u'持',u'人'))
                            match_results = text_regex.search(label)
                            if match_results:
                                mediaItem['actor'] = Util.join_list_safely(infos) 
                            else:
                                text_regex = re.compile('(%s.*%s.*)' % (u'类',u'型'))
                                match_results = text_regex.search(label)
                                if match_results:
                                    mediaItem['type'] = Util.join_list_safely(infos) 
                                else:
                                    text_regex = re.compile('(%s.*%s.*)' % (u'地',u'区'))
                                    match_results = text_regex.search(label)
                                    if match_results:
                                        mediaItem['district'] = Util.join_list_safely(infos) 
            sels = response.xpath('.//div[@class="mod-album-1-intro-til"]')
            if sels:
                titles = sels.xpath('.//span[@class="dd-pic-til"]/text()').extract()
                vcounts = sels.xpath('.//span[@class="update-info-series"]//em/text()').extract()
                if titles:
                    mediaItem['title'] = titles[0]
                if vcounts:
                    vcount = vcounts[0]
                    mediaItem['vcount'] = int(vcount)
            #媒体页
            class_names = response.xpath('./@language').extract()
            if class_names and 'javascript' == class_names[0]:
                cids = response.re('cid[ ]?:[ ]?(\d+)')
                is_fulls = response.re('\"isfull\"[ ]?:[ ]?(\d+)')
                latest = mediaItem['latest'] if 'latest' in mediaItem else None
                if cids:
                    cid = cids[0]
                    mediaItem['cont_id'] = cid
                if is_fulls:
                    is_full = is_fulls[0]
                    if is_full == '0':
                        latest = '0'
                    else:
                        latests = response.re('\"lastseries\"[ ]?:[ ]?\"([\d-]+)\"')
                        if latests:
                            latest = latests[0]
                            latest = filter(str.isalnum, str(latest))
                mediaItem['latest'] = latest

            #播放页（电影）
            sels = response.xpath('..//div[@class="play-xxmes clearfix"]//p')
            for sel in sels:
                labels = sel.xpath('./span[@class="px-l"]/text()').extract()
                if not labels:
                    continue
                label = labels[0]
                text_regex = re.compile('(%s.*%s.*)' % (u'简',u'介'))
                match_results = text_regex.search(label)
                if match_results:
                    infos = sel.xpath('./span[@class="px-r"]/text()').extract()
                    if not infos:
                        continue
                    mediaItem['intro'] = infos[0]
                else:
                    infos = sel.xpath('./span[@class="px-r"]/a/text()').extract()
                    if not infos:
                        continue
                    text_regex = re.compile('(%s.*%s.*)' % (u'导',u'演'))
                    match_results = text_regex.search(label)
                    if match_results:
                        mediaItem['director'] = Util.join_list_safely(infos) 
                    else: 
                        text_regex = re.compile('(%s.*%s.*)' % (u'主',u'演'))
                        match_results = text_regex.search(label)
                        if match_results:
                            mediaItem['actor'] = Util.join_list_safely(infos) 
                        else:
                            text_regex = re.compile('(%s.*%s.*)' % (u'类',u'型'))
                            match_results = text_regex.search(label)
                            if match_results:
                                mediaItem['type'] = Util.join_list_safely(infos)
                            else:
                                text_regex = re.compile('(%s.*%s.*)' % (u'地',u'区'))
                                match_results = text_regex.search(label)
                                if match_results:
                                    mediaItem['district'] = Util.join_list_safely(infos)
            #播放页
            class_names = response.xpath('./@type').extract()
            if class_names and 'text/javascript' == class_names[0]:
                titles = response.re('title[ ]?:[ ]?\"(.*)\"')
                cids = response.re('cid[ ]?:[ ]?(\d+)')
                release_dates = response.re('release_date[ ]?:[ ]?\"([\d-]+)\"')
                if titles:
                    mediaItem['title'] = titles[0]
                if cids:
                    mediaItem['cont_id'] = cids[0]
                if release_dates:
                    release_date = release_dates[0]
                    release_date = Util.str2date(release_date)
                    mediaItem['release_date'] = release_date 

            #list列表页
            poster_urls = response.xpath('.//img[@class="lazy"]/@data-original').extract()
            members = response.xpath('.//span[@class="member-ico"]').extract()
            if poster_urls:
                mediaItem['poster_url'] = poster_urls[0]
            if members:
                mediaItem['paid'] = '1'
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    @staticmethod
    def album_extract(response):
        items = []
        try:
            results = response.xpath('.//a/@href[re:test(., "http://list\.hunantv\.com/album/[\d]+\.html")]').extract()
            for item in results:
                mediaItem = MediaItem()
                mediaItem['url'] = item 
                items.append(mediaItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    @staticmethod
    def album_tag_extract(response):
        items = []
        try:
            results = response.xpath('.//a/@href[re:test(., "http://list\.hunantv\.com/album/[\d-]+\.html")]').extract()
            for item in results:
                mediaItem = MediaItem()
                mediaItem['url'] = item 
                items.append(mediaItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    @staticmethod
    def next_page_extract(response):
        items = []
        try:
            next_pages = response.xpath('.//div[normalize-space(@class)="mgtv-page clearfix"]//a[@title="%s"]/@href' % u'下一页').extract()
            if next_pages:
                next_page = next_pages[0]
                items.append(next_page)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items
