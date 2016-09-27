# -*- coding:utf-8 -*-
import re
import time
import urllib
import traceback
import logging

from xvsync.common.util import Util
from xvsync.items import MediaItem, VideoItem

class pptv_extract(object):
    #list_channels = [u'综艺']
    list_channels = [u'电影', u'电视剧', u'综艺', u'动漫']
    ignore_channels = [u'花絮', u'预告']

    @staticmethod
    def media_info_extract(response, mediaItem):
        try:
            if mediaItem == None:
                mediaItem = MediaItem()
            #list api页面
            results = response.xpath('.//p[@class="ui-pic"]//img/@data-src2').extract()
            if results:
                mediaItem['poster_url'] = results[0]
            results = response.xpath('.//p[@class="ui-txt"]//span[@class="main-tt"]/text()').extract()
            if results:
                mediaItem['title'] = results[0]
            results = response.xpath('.//p[@class="ui-txt"]//em/text()').extract()
            if results:
                mediaItem['score'] = results[0]

            #普通播放页
            sel = response.xpath('.//script[@type="text/javascript"]')
            if sel:
                cont_ids = sel.re('\"id\"[ ]?:[ ]?(\d+)')  
                if cont_ids:
                    mediaItem['cont_id'] = cont_ids[0]
            sel = response.xpath('.//div[@id="mainContent"]')
            if sel:
                titles = sel.xpath('.//*[@class="tit"]/text()').extract()
                scores = sel.xpath('.//div[@id="scoremark"]//em[@class="score"]/text()').extract()
                intros = sel.xpath('.//p[@class="longinfo"]/text()').extract()
                if titles:
                    title = titles[0].strip()
                    match_result = None
                    #电影
                    if u'电影' == mediaItem['channel_id']:
                        match_result = None
                    #综艺
                    #都来爱梦-20121215     时尚健康-20150430-包贝尔分享包氏火锅哲学
                    elif u'综艺' == mediaItem['channel_id']:
                        regex_express = r'(.+)-[\d]+[-].+'
                        regex_pattern = re.compile(regex_express)
                        match_result = regex_pattern.search(title)
                        if not match_result:
                            regex_express = r'(.+)-[\d]+' 
                            regex_pattern = re.compile(regex_express)
                            match_result = regex_pattern.search(title)
                        if not match_result:
                            regex_express = u'(.+)[(（]第[\d]+集[)）]'
                            regex_pattern = re.compile(regex_express)
                            match_result = regex_pattern.search(title)
                    #电视剧，动漫
                    else:
                        regex_express = u'(.+)[(（]第[\d]+集[)）]'
                        regex_pattern = re.compile(regex_express)
                        match_result = regex_pattern.search(title)
                    if match_result:
                        mediaItem['title'] = match_result.groups()[0] 
                    else:
                        mediaItem['title'] = title
                if scores:
                    score = scores[0].strip()
                    mediaItem['score'] = score
                if intros:
                    intro = intros[0].strip()
                    mediaItem['intro'] = intro
                msg_sels = sel.xpath('.//div[@class="intro-content intro-short"]//li')
                for sel in msg_sels:
                    labels = sel.xpath('./span/text()').extract()
                    infos = sel.xpath('./a/text()').extract()
                    if not infos:
                        infos = sel.xpath('./text()').extract()
                    pptv_extract.text_infos_resolve(labels, infos, mediaItem)

            #vip播放页
            sel = response.xpath('.//script[@type="text/javascript"]')
            if sel:
                cont_ids = sel.re('vid[ ]?:[ ]?["]?(\d+)')
                if cont_ids:
                    mediaItem['cont_id'] = cont_ids[0]
            sel = response.xpath('.//div[@class="ptxt"]')    
            if sel:
                titles = sel.xpath('./*/@title').extract()
                intros = sel.xpath('.//span[@class="thenext"]/text()').extract()
                if titles:
                    mediaItem['title'] = titles[0].strip()
                if intros:
                    mediaItem['intro'] = intros[0].strip() 
                msg_sels = sel.xpath('./p') 
                for sel in msg_sels:
                    labels = sel.xpath('./em/text()').extract()
                    infos = sel.xpath('.//tt/text()').extract()
                    pptv_extract.text_infos_resolve(labels, infos, mediaItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    @staticmethod
    def text_infos_resolve(labels, infos, mediaItem):
        try:
            if mediaItem == None:
                return
            if labels and infos:
                labels = str(labels[0]).splitlines()
                label = ''.join(labels)
                label = label.replace(' ','')
                if label.startswith(u'导演'):
                    mediaItem['director'] = Util.join_list_safely(infos) 
                elif label.startswith(u'主演'):
                    mediaItem['actor'] = Util.join_list_safely(infos) 
                elif label.startswith(u'类型'):
                    mediaItem['type'] = Util.join_list_safely(infos) 
                elif label.startswith(u'地区'):
                    mediaItem['district'] = Util.join_list_safely(infos) 
                elif label.startswith(u'上映'):
                    release_date = ''.join(infos) 
                    release_dates = re.findall(r'[\d]+', release_date)
                    release_date = ''.join(release_dates) 
                    release_date = Util.str2date(release_date)
                    mediaItem['release_date'] = release_date
                elif label.startswith(u'片长'):
                    duration = ''.join(infos) 
                    durations = re.findall(r'[\d]+', duration)
                    duration = ''.join(durations) 
                    mediaItem['duration'] = duration
                elif label.startswith(u'人气'):
                    score = ''.join(infos) 
                    scores = re.findall(r'[\d]+', score)
                    score = ''.join(scores) 
                    mediaItem['score'] = score 
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    '''
    Author: yuxj
    Email: yuxj@fun.tv
    Description:
        (1)由于pptv的链接大量采用这种方式:http://list.pptv.com?type=3&sort=1;而scrapy对于这种地址刚好存在一个bug
        (2)修改该bug,将地址由http://list.pptv.com?type=3&sort=1 -> http://list.pptv.com/?type=3&sort=1
    '''
    @staticmethod
    def normalize_url(url):
        fix_url = ''
        try:
            protocol, rest = urllib.splittype(url)
            domain, rest = urllib.splithost(rest)
            if not rest.startswith('/'):
                fix_url = '%s://%s/%s' % (protocol, domain, rest)
            else:
                fix_url = url
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return fix_url
