# -*- coding:utf-8 -*-
import re
import time
import traceback
import logging
from scrapy.selector import Selector

from xvsync.common.util import Util
from xvsync.items import MediaItem, VideoItem

class dy1905_extract(object):

    list_channels = [u'电影', u'电视剧', u'综艺', u'动漫']

    @staticmethod
    def video_extract(response):
        items = []
        try:
            return items
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    @staticmethod
    def video_info_extract(response, videoItem):
        try:
            if videoItem == None:
                videoItem = VideoItem()
            #媒体页
            sels = response.xpath('.//dl[@class="imgBAyy db"]')
            urls = sels.xpath('./a/@href').extract()
            if urls:
                url = urls[0]
                #http://vip.1905.com/play/871039.shtml
                regex_express = 'http://[^/]*\.[m]?1905\.com/play/([\d]+)\.shtml.*'
                regex_pattern = re.compile(regex_express)
                match_result = regex_pattern.search(url) 
                if not match_result:
                    #http://www.1905.com/vod/info/404887.shtml
                    #http://www.1905.com/vod/play/361717.shtml
                    regex_express = 'http://[^/]*\.[m]?1905\.com/vod/.*/([\d]+)\.shtml.*'
                    regex_pattern = re.compile(regex_express)
                    match_result = regex_pattern.search(url) 
                if match_result:
                    #说明当前的URL是1905本站的url，可以赋值
                    videoItem['url'] = url
                    videoItem['cont_id'] = match_result.groups()[0]
                    thumb_urls = sels.xpath('./a/img/@src').extract()
                    titles = sels.xpath('./a/@title').extract()
                    if thumb_urls:
                        videoItem['thumb_url'] = thumb_urls[0]
                    if titles:
                        videoItem['title'] = titles[0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    @staticmethod
    def media_extract(response):
        items = []
        try:
            #list列表页
            sels = response.xpath('.//li[@class="fl line" or normalize-space(@class)="fl"]')
            for sel in sels:
                mediaItem = MediaItem()
                urls = sel.xpath('./a/@href').extract() 
                poster_urls = sel.xpath('./a/img/@src').extract()
                if urls:
                    mediaItem['url'] = urls[0]
                    mediaItem['poster_url'] = poster_urls[0]
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
            sels = response.xpath('.//div[@class="laMoCont"]')
            if sels:
                name_sels = sels.xpath('.//div[@class="laMovName"]')
                titles = name_sels.xpath('.//a[@class="laGrayS_f"]/text()').extract()
                if titles:
                    mediaItem['title'] = titles[0]
                property_sels = sels.xpath('.//ol[@class="movStaff line_BSld"]//li')
                ignore = True
                for sel in property_sels:
                    label_sels = sel.xpath('.//strong')
                    info_sels = sel.xpath('.//a')
                    dy1905_extract.text_infos_resolve(label_sels, info_sels, mediaItem, ignore)
            scores = response.xpath('.//div[@class="laMoOther"]//div[@class="rating-dt"]//span[@class="score"]/text()').extract()
            if scores:
                scores = re.findall(r'[\d.]+', scores[0]) 
                if scores:
                    mediaItem['score'] = scores[0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    @staticmethod
    def media_more_info_resolve(text, mediaItem):
        try:
            try:
                response = Selector(text=text)
            except Exception, e:
                logging.log(logging.INFO, 'text to be parsed is not xml or html')
                logging.log(logging.ERROR, traceback.format_exc())
            if mediaItem == None:
                mediaItem = MediaItem()
            #剧情页面
            intros = response.xpath('.//div[@class="conTABLE mt10"]//div[@class="w100d line_Slx pt15 dlP"]/text()').extract()
            if intros:
                mediaItem['intro'] = intros[0].strip()
            #演职人员页面
            label_sels = response.xpath('.//div[@class="conTABLE mt10"]//*[@class="now pr05 fb"]')
            info_sels = response.xpath('.//div[@class="conTABLE mt10"]//*[@class="laGrayQdd_f pt12 line_Sbotlx pb15"]')
            index = 0
            size = len(info_sels)
            for label_sel in label_sels:
                if index < size: 
                    info_sel = info_sels[index].xpath('.//a[@class="laBlueS_f" or @class="laBlueS_f fl"]')    
                    dy1905_extract.text_infos_resolve(label_sel, info_sel, mediaItem)
                    index = index + 1
                else:
                    break
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    @staticmethod
    def text_infos_resolve(label_sels, info_sels, mediaItem, ignore=False):
        try:
            if mediaItem == None:
                return
            if not label_sels or not info_sels:
                return
            labels = label_sels.xpath('./text()').extract()
            infos = info_sels.xpath('./text()').extract()
            if labels and infos:
                labels = str(labels[0]).splitlines()
                label = ''.join(labels)
                label = label.replace(' ','')
                if label.startswith(u'导演') and ignore==False:
                    mediaItem['director'] = Util.join_list_safely(infos)
                elif label.startswith(u'编剧') and ignore==False:
                    mediaItem['writer'] = Util.join_list_safely(infos)
                elif label.startswith(u'主演') and ignore==False:
                    mediaItem['actor'] = Util.join_list_safely(infos)
                elif label.startswith(u'类型'):
                    #类型/地区放在一块，特殊处理
                    type_infos = info_sels.xpath('./@href[re:test(., "/mdb/film/list/mtype-[\d]+.*")]/../text()').extract()
                    district_infos = info_sels.xpath('./@href[re:test(., "/mdb/film/list/country-[\w]+.*")]/../text()').extract()
                    mediaItem['type'] = Util.join_list_safely(type_infos)
                    mediaItem['district'] = Util.join_list_safely(district_infos)
                elif label.startswith(u'上映'):
                    info = ''.join(infos)
                    release_dates = re.findall(r'[\d]+', info) 
                    if release_dates:
                        release_date = ''.join(release_dates)
                        release_date = Util.str2date(release_date)
                        mediaItem['release_date'] = release_date 
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
