# -*- coding:utf-8 -*-
import re
import time
import json
import traceback
import logging

from xvsync.common.util import Util
from xvsync.items import MediaItem, VideoItem

class kankan_extract(object):

    #list_channels = [u'综艺']
    list_channels = [u'电影', u'电视剧', u'综艺', u'动漫']
    list_channels_pinyin = {u'电影':'movie', u'电视剧':'teleplay', u'综艺':'tv', u'动漫':'anime'}

    @staticmethod
    def video_extract(response):
        items = []
        try:
            #list列表页
            #普通URL
            results = response.xpath('.//a/@href[re:test(., "http://vod\.kankan\.com/v/[\d]+/[\d]+\.shtml.*")]').extract()
            for item in results:
                videoItem = VideoItem()
                videoItem['url'] = item 
                items.append(videoItem)
            #vipURL
            results = response.xpath('.//a/@href[re:test(., "http://vip\.kankan\.com/vod/[\d]+\.html.*")]').extract()
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
            channel_name = videoItem['intro'] if 'intro' in videoItem else ''
            videoItem['intro'] = ''
            #媒体页
            sels = response.xpath('./a[@class="pic" or @class="foc"]') 
            if sels:
                urls = sels.xpath('./@href').extract()
                titles = sels.xpath('./@title').extract()
                cont_ids = sels.xpath('./@subid').extract()
                thumb_urls = sels.xpath('.//img/@_src').extract()
                if urls:
                    url = urls[0]
                    videoItem['url'] = url
                    #这里得区分综艺与其他，因为综艺跟其他刚好反过来
                    if channel_name == u'综艺':
                        intros = response.xpath('./*/a[@href="%s"]/text()' % url).extract() 
                        if intros:
                            videoItem['intro'] = intros[0]
                    else:
                        vnums = response.xpath('./*/a[@href="%s"]/text()' % url).extract()
                        if vnums:
                            vnums = re.findall(r'[\d]+', vnums[0]) 
                            vnum = ''.join(vnums)
                            if vnum:
                                videoItem['vnum'] = vnum 
                if titles:
                    videoItem['title'] = titles[0]
                if cont_ids:
                    videoItem['cont_id'] = cont_ids[0]
                if thumb_urls:
                    videoItem['thumb_url'] = thumb_urls[0]
            #这里得区分综艺与其他，因为综艺跟其他刚好反过来
            if channel_name == u'综艺':
                vnums = response.xpath('./h4/text()').extract()
                if vnums:
                    vnums = re.findall(r'[\d]+', vnums[0]) 
                    vnum = ''.join(vnums)
                    if vnum:
                        videoItem['vnum'] = vnum 
            else:
                intros = response.xpath('./h4/text()').extract()
                if intros:
                    videoItem['intro'] = intros[0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    @staticmethod
    def media_extract(response):
        items = []
        try:
            results = response.xpath('.//a/@href[re:test(., "http://movie\.kankan\.com/movie/[\d]+/introduction")]').extract()
            if results:
                #http://vip.kankan.com/vod/88169.html?fref=kk_search_sort_01#7927921
                #http://vip.kankan.com/vod/88365.html#7306075
                url = results[0]
                regex_pattern = re.compile('(http://movie\.kankan\.com/movie/[\d]+)')
                match_results = regex_pattern.search(url)
                if match_results:
                    mediaItem = MediaItem()
                    mediaItem['url'] = match_results.groups()[0]
                    items.append(mediaItem)
            else:
                #http://vod.kankan.com/v/86/86897.shtml#9895815
                results = response.xpath('.//a/@href[re:test(., "http://data\.movie\.kankan\.com/movie/[\d]+")]').extract()
                for item in results:
                    mediaItem = MediaItem()
                    mediaItem['url'] = item 
                    items.append(mediaItem)
                    break
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    @staticmethod
    def media_info_extract(response, mediaItem):
        try:
            if mediaItem == None:
                mediaItem = MediaItem()
            #list列表页
            sels = response.xpath('.//p[@class="movielist_tt"]')
            if sels:
                scores = sels.xpath('.//em[@class="score"]/text()').extract()
                latests = sels.xpath('.//em[@class="update"]/text()').extract()
                if scores:
                    mediaItem['score'] = scores[0]
                if latests:
                    latests = re.findall(r'[\d]+', latests[0]) 
                    if latests:
                        mediaItem['latest'] = latests[0]
            sels = response.xpath('.//a[@class="pic"]') 
            if sels:
                poster_urls = sels.xpath('./img/@_src').extract()
                if poster_urls:
                    mediaItem['poster_url'] = poster_urls[0]

            #播放页 - 普通版面
            sels = response.xpath('..//ul[@class="movieinfo"]/li')
            for sel in sels:
                labels = sel.xpath('./text()').extract()
                infos = sel.xpath('./*/text()').extract()
                kankan_extract.text_infos_resolve(labels, infos, mediaItem)
            intros = response.xpath('..//p[@id="movie_info_intro_l"]/text()').extract()
            if intros:
                mediaItem['intro'] = intros[0]

            #播放页 - vip
            #(1)http://vip.kankan.com/vod/88169.html?fref=kk_search_sort_01#7927921
            sels = response.xpath('..//div[@class="intro"]')
            if sels:
                url_sels = sels.xpath('.//dt/a/@href')
                if url_sels:
                    regex_express = '(http://movie\.kankan\.com/movie/[\d]+).*'
                    match_result = url_sels.re(regex_express)
                    if match_result:
                        mediaItem['url'] = match_result[0]
                sels = sels.xpath('.//dd') 
                for sel in sels:
                    labels = sel.xpath('./text()').extract()
                    infos = sel.xpath('./a/text()').extract()
                    kankan_extract.text_infos_resolve(labels, infos, mediaItem)            
                intros = sels.xpath('./dd[@class="intro_p"]/p').extract()
                mediaItem['intro'] = ''.join(intros)
            #(2)http://vip.kankan.com/vod/88365.html#7306075
            sels = response.xpath('..//div[@class="movie_info"]')
            if sels:
                url_sels = sels.xpath('.//dd') 
                for sel in url_sels:
                    labels = sel.xpath('./span/text()').extract()
                    infos = sel.xpath('./span/a/text()').extract()
                    if not labels:
                        labels = sel.xpath('./text()').extract()
                        infos = sel.xpath('./a/text()').extract()
                    kankan_extract.text_infos_resolve(labels, infos, mediaItem)            
                intros = sels.xpath('./dd/p[@class="intro_p"]').extract()
                mediaItem['intro'] = ''.join(intros)

            #媒体页
            sels = response.xpath('//head//script')
            if sels:
                regex_express = 'movieInfo\.movieid[ ]?=[ ]?(\d+)'
                match_result = sels.re(regex_express)
                if match_result:
                    mediaItem['cont_id'] = match_result[0]
                regex_express = 'movieInfo\.movie_title[ ]?=[ ]?\'(.*)\''
                match_result = sels.re(regex_express)
                if match_result:
                    mediaItem['title'] = match_result[0]
                regex_express = 'movieInfo\.poster[ ]?=[ ]?\'(.*)\''
                match_result = sels.re(regex_express)
                if match_result:
                    mediaItem['poster_url'] = match_result[0]
                regex_express = 'movieInfo\.movie_classify[ ]?=[ ]?(\{.*\})'
                match_result = sels.re(regex_express)
                if match_result:
                    content = match_result[0]
                    json_data = json.loads(content)
                    release_date = json_data['year'] if 'year' in json_data else ''
                    release_dates = re.findall(r'[\d]+', str(release_date)) 
                    release_date = ''.join(release_dates)
                    if release_date:
                        release_date = Util.str2date(release_date)
                        mediaItem['release_date'] = release_date
                regex_express = 'movieInfo\.episode[ ]?=[ ]?\'(.*)\''
                match_result = sels.re(regex_express)
                if match_result:
                    latests = match_result[0]
                    latests = latests.split('/')
                    #共N集/更新至N集
                    if len(latests) > 1:
                        latests = latests[1]
                    else:
                        latests = latests[0]
                    latests = re.findall(r'[\d]+', latests) 
                    mediaItem['latest'] = ''.join(latests)
                regex_express = 'movieInfo\.total_number[ ]?=[ ]?(\d+)'
                match_result = sels.re(regex_express)
                if match_result:
                    if int(match_result[0]) > 0:
                        mediaItem['vcount'] = match_result[0]
            sels = response.xpath('..//div[@class="info_list"]//li')
            for sel in sels:
                labels = sel.xpath('./text()').extract()
                if not labels:
                    labels = sel.xpath('./em/text()').extract()
                infos = sel.xpath('./a/text()').extract()
                if not infos:
                    infos = sel.xpath('./span/text()').extract()
                kankan_extract.text_infos_resolve(labels, infos, mediaItem)
            sels = response.xpath('..//ul[@class="detail_ul"]//li')
            for sel in sels:
                labels = sel.xpath('./text()').extract()
                infos = sel.xpath('./*/text()').extract()
                kankan_extract.text_infos_resolve(labels, infos, mediaItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    @staticmethod
    def next_page_extract(response):
        items = []
        try:
            next_pages = response.xpath('.//a[@id="pagenav_next"]/@href').extract()
            if next_pages:
                next_page = next_pages[0]
                items.append(next_page)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    @staticmethod
    def text_infos_resolve(labels, infos, mediaItem):
        try:
            if mediaItem == None:
                return
            if labels and infos:
                labels = str(labels[0]).splitlines()
                label = ''.join(labels)
                label = label.replace(' ','')
                if label.startswith(u'更新'): 
                    latest = infos[0]
                    latests = latest.split('/')
                    #共N集/更新至N集
                    if len(latests) > 1:
                        latest = latests[1]
                    else:
                        latest = latests[0]
                    latests = re.findall(r'[\d]+', latest) 
                    mediaItem['latest'] = ''.join(latests)
                elif label.startswith(u'导演'):
                    mediaItem['director'] = Util.join_list_safely(infos) 
                elif label.startswith(u'作者') or label.startswith(u'编剧'):
                    mediaItem['writer'] = Util.join_list_safely(infos) 
                elif label.startswith(u'主演') or label.startswith(u'配音') or label.startswith(u'主持'):
                    mediaItem['actor'] = Util.join_list_safely(infos) 
                elif label.startswith(u'地区'):
                    mediaItem['district'] = Util.join_list_safely(infos)
                elif label.startswith(u'类型'):
                    mediaItem['type'] = Util.join_list_safely(infos)
                elif label.startswith(u'年份') or label.startswith(u'上映'):
                    release_dates = re.findall(r'[\d]+', infos[0]) 
                    if release_dates:
                        release_date = ''.join(release_dates)
                        release_date = Util.str2date(release_date)
                        mediaItem['release_date'] = release_date 
                elif label.startswith(u'片长'):
                    durations = re.findall(r'[\d]+', infos[0]) 
                    if durations:
                        mediaItem['duration'] = durations[0] 
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
