# -*- coding:utf-8 -*-
import re
import time
import json
import traceback
import logging

from xvsync.common.util import Util
from xvsync.common.util import URL_TYPE_MEDIA, URL_TYPE_PLAY
from xvsync.items import MediaItem, VideoItem

class iqiyi_extract(object):

    #list_channels = [u'电视剧']
    list_channels = [u'电影', u'电视剧', u'综艺', u'动漫']
    list_channels_id = {u'电影':'1', u'电视剧':'2', u'综艺':'6', u'动漫':'4'}

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
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    @staticmethod
    def media_extract(response):
        items = []
        try:
            #list播放页
            sels = response.xpath('.//div[@class="site-piclist_pic"]//a[@class="site-piclist_pic_link"]')
            if sels:
                mediaItem = MediaItem()
                urls = sels.xpath('./@href').extract()
                poster_urls = sels.xpath('./img/@src').extract()
                if urls:
                    mediaItem['url'] = urls[0].strip()
                if poster_urls:
                    mediaItem['poster_url'] = poster_urls[0].strip()
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
            #普通媒体页
            release_dates = response.xpath('./@data-qitancomment-tvyear').extract()
            if release_dates:
                release_dates = re.findall(r'[\d]+', release_dates[0]) 
                if release_dates:
                    release_date = ''.join(release_dates)
                    release_date = Util.str2date(release_date)
                    mediaItem['release_date'] = release_date 
            class_names = response.xpath('./@type').extract()
            if class_names and 'text/javascript' == class_names[0]:
                #视频类型 video:正片 trailer:片花
                regex_express = "vType[ ]?:[ ]?[']?(\w+)[']"
                match_result = response.re(regex_express)
                if match_result:
                   vType  = match_result[0]
                   if vType.strip() != 'video':
                        return
                regex_express = 'sourceId[ ]?:[ ]?["]?(\d+)'
                #默认采用的是sourceId
                cont_id = '0'
                regex_express = 'sourceId[ ]?:[ ]?["]?(\d+)'
                match_result = response.re(regex_express)
                if match_result:
                    cont_id = match_result[0]
                if cont_id == '0':
                    #其他采用的是albumId
                    regex_express = 'albumId[ ]?:[ ]?["]?(\d+)'
                    match_result = response.re(regex_express)
                    if match_result:
                        cont_id = match_result[0]
                        mediaItem['cont_id'] = '%s|album_id' % (cont_id)                    
                else:
                    mediaItem['cont_id'] = '%s|source_id' % (cont_id)                    
                regex_express = 'cid[ ]?:[ ]?(\d+)'
                match_result = response.re(regex_express)
                if match_result:
                    cid = match_result[0]
                    mediaItem['channel_id'] = cid                    
                regex_express = 'title[ ]?:[ ]?\"(.*)\"'
                match_result = response.re(regex_express)
                if match_result:
                    title = match_result[0]
                    mediaItem['title'] = title
                #特殊剧集页：http://www.iqiyi.com/dianshiju/18jbj.html#vfrm=2-4-0-1
                regex_express = 'albumInfo[ ]?=[ ]?(\{.*\})'
                match_result = response.re(regex_express)
                if match_result:
                    json_content = match_result[0]
                    try:
                        json_data = json.loads(json_content)
                        cont_ids = '0'
                        cont_ids = json_data['sourceId']
                        if cont_ids != '0':
                            cont_ids = '%s|source_id' % (cont_ids) 
                            mediaItem['cont_id'] = cont_ids
                        else:
                            cont_ids = json_data['albumId']
                            cont_ids = '%s|album_id' % (cont_ids) 
                            mediaItem['cont_id'] = cont_ids
                        districts = json_data['areas']
                        types = json_data['types']
                        directors = json_data['directors']
                        actors = json_data['mainActors']
                        writers = json_data['writer']
                        titles = json_data['tvName']
                        poster_urls = json_data['tvPictureUrl']
                        vcounts = json_data['episodeCounts'] 
                        latests = json_data['currentMaxEpisode']
                        release_dates = json_data['issueTime']
                        intros = json_data['tvDesc']
                        if districts:
                            districts_json = json.loads(districts)
                            districts = districts_json.values()
                            mediaItem['district'] = Util.join_list_safely(districts)
                        if types:
                            types_json = json.loads(types)
                            types = types_json.values()
                            mediaItem['type'] = Util.join_list_safely(types)
                        mediaItem['director'] = Util.join_list_safely(directors)
                        mediaItem['actor'] = Util.join_list_safely(actors)
                        mediaItem['writer'] = Util.join_list_safely(writers)
                        mediaItem['title'] = titles
                        mediaItem['poster_url'] = poster_urls
                        mediaItem['vcount'] = vcounts
                        mediaItem['latest'] = latests
                        release_dates = str(release_dates)
                        release_date = Util.str2date(release_dates)
                        mediaItem['release_date'] = release_date
                        mediaItem['intro'] = intros
                    except Exception, e:
                        logging.log(logging.ERROR, traceback.format_exc())
                        logging.log(logging.INFO, '=================json_content=================')
                        logging.log(logging.INFO, json_content)
            #普通媒体页 - 媒体信息域
            # (1) http://www.iqiyi.com/a_19rrgjaiqh.html#vfrm=2-4-0-1
            #   集数的情况很复杂，这里不予考虑
            sels = response.xpath('.//div[@class="result_pic pr"]')
            if sels:
                poster_urls = sels.xpath('.//a/img/@src').extract()
                if poster_urls:
                    mediaItem['poster_url'] = poster_urls[0]
            sels = response.xpath('.//div[@class="result_detail"]')
            if sels:
                titles = sels.xpath('.//h1[@class="main_title"]//a/text()').extract()
                scores = sels.xpath('.//div[@class="topic_item topic_item-rt"]//span[@class="score_font"]//span/text()').extract()
                scores = ''.join(scores)
                scores = re.findall(r'[\d.]+', scores) 
                if titles:
                    mediaItem['title'] = titles[0]
                if scores:
                    try:
                        mediaItem['score'] = float(scores[0])
                    except Exception, e:
                        pass
                msg_sels = sels.xpath('.//div[@class="topic_item clearfix"]')
                for msg_sel in msg_sels:
                    msg_more_sels = msg_sel.xpath('./div')
                    for sel in msg_more_sels:
                        labels = sel.xpath('.//em/text()').extract()
                        infos = sel.xpath('.//em/a/text()').extract()
                        iqiyi_extract.text_infos_resolve(labels, infos, mediaItem)
                intros = sels.xpath('.//div[@class="topic_item clearfix"]//span[@data-moreorless="moreinfo"]/span/text()').extract()
                if not intros:
                    intros = sels.xpath('.//div[@class="topic_item clearfix"]//span[@data-moreorless="lessinfo"]/span/text()').extract()
                if intros:
                    mediaItem['intro'] = intros[0]
            # (2) http://www.iqiyi.com/a_19rrhc1qy5.html#vfrm=2-4-0-1
            sels = response.xpath('.//div[@class="album-hdPic"]')
            if sels:
                scores = sels.xpath('.//div[@class="gx-con-r fr"]//span[@class="fenshu-r"]/text()').extract()
                titles = sels.xpath('.//div[@class="album-playArea clearfix"]//a[@class="white"]/text()').extract()
                latests = sels.xpath('.//div[@class="album-playArea clearfix"]//span[@class="qishuTxt"]/text()').extract()
                if scores:
                    scores = re.findall(r'[\d.]+', scores[0])
                    if scores:
                        try:
                            mediaItem['score'] = float(scores[0])
                        except Exception, e:
                            pass
                if titles:
                    mediaItem['title'] = titles[0]
                if latests:
                    latests = re.findall(r'[\d]+', latests[0])
                    latest = ''.join(latests)
                    mediaItem['latest'] = latest
            sels = response.xpath('.//div[@class="album-msg"]')
            if sels:
                msg_sels = sels.xpath('.//p[@class="li-mini" or @class="li-large"]')
                for sel in msg_sels:
                    labels = sel.xpath('./text()').extract()
                    infos = sel.xpath('./a/text()').extract()
                    iqiyi_extract.text_infos_resolve(labels, infos, mediaItem)
                intros = sels.xpath('.//div[@data-moreorless="moreinfo"]//span[@class="bigPic-b-jtxt"]/text()').extract()
                if not intros:
                    intros = sels.xpath('.//div[@data-moreorless="lessinfo"]//span[@class="bigPic-b-jtxt"]/text()').extract()
                if intros:
                    mediaItem['intro'] = intros[0]
            #特辑媒体页
            cids = response.xpath('//div[@data-widget-videolistbyyear="tab"]/@data-widget-videolistbyyear-categoryid').extract()
            titles = response.xpath('//meta[@name="irAlbumName"]/@content').extract()
            album_ids = response.xpath('//div[@class="flashArea"]//div/@data-player-albumid').extract()
            intros = response.xpath('//meta[@name="description"]/@content').extract()
            if cids:
                mediaItem['channel_id'] = cids[0]
            if titles:
                mediaItem['title'] = titles[0]
            if album_ids:
                cont_id = mediaItem['cont_id'] if 'cont_id' in mediaItem else None
                if not cont_id:
                    cont_id = '%s|album_id' % (album_ids[0])
                    mediaItem['cont_id'] = cont_id
            if intros:
                mediaItem['intro'] = intros[0]
            #播放页 - 电影
            sels = response.xpath('.//span[@id="datainfo-navlist" or @id="widget-videonav"]')
            if sels:
                urls = sels.xpath('./a[last()]/@href').extract()
                if urls:
                    mediaItem['url'] = urls[0]
            if u'电影' == mediaItem['channel_id']:
                titles = response.xpath('./meta[@itemprop="name"]/@content').extract()
                release_dates = response.xpath('./meta[@itemprop="datePublished"]/@content').extract()
                directors = response.xpath('./span[@itemprop="director"]//meta[@itemprop="name"]/@content').extract()
                types = response.xpath('./meta[@itemprop="genre"]/@content').extract()
                actors = response.xpath('./item[@itemprop="actor"]//meta[@itemprop="name"]/@content').extract()
                writers = response.xpath('./meta[@itemprop="author"]/@content').extract()
                intros = response.xpath('./meta[@itemprop="description"]/@content').extract() 
                poster_urls = response.xpath('./item/meta[@itemprop="image"]/@content').extract()
                durations = response.xpath('./item/meta[@itemprop="duration"]/@content').extract()
                vcounts = response.xpath('./meta[@itemprop="numberOfEpisodes"]/@content').extract()
                latests = response.xpath('./meta[@itemprop="newestEpisode"]/@content').extract()
                districts = response.xpath('./item/meta[@itemprop="contentLocation"]/@content').extract()
                scores = response.xpath('./item/div[@itemprop="aggregateRating"]/meta[@itemprop="ratingValue"]/@content').extract()
                if titles:
                    mediaItem['title'] = titles[0]
                if release_dates:
                    release_dates = re.findall(r'[\d]+', release_dates[0]) 
                    release_date = ''.join(release_dates)
                    release_date = Util.str2date(release_date)
                    mediaItem['release_date'] = release_date
                if directors:
                    mediaItem['director'] = Util.join_list_safely(directors)
                if types:
                    mediaItem['type'] = Util.join_list_safely(types)
                if actors:
                    mediaItem['actor'] = Util.join_list_safely(actors)
                if writers:
                    mediaItem['writer'] = Util.join_list_safely(writers)
                if intros:
                    mediaItem['intro'] = intros[0]
                if poster_urls:
                    mediaItem['poster_url'] = poster_urls[0]
                if durations:
                    durations = re.findall(r'[\d]+', durations[0])
                    if durations:
                        mediaItem['duration'] = durations[0]    
                if vcounts:
                    vcounts = re.findall(r'[\d]+', vcounts[0])
                    vcount = ''.join(vcounts)
                    mediaItem['vcount'] = vcount
                if latests:
                    latests = re.findall(r'[\d]+', latests[0])
                    latest = ''.join(latests)
                    mediaItem['latest'] = latest
                if districts:
                    mediaItem['district'] = Util.join_list_safely(districts)
                if scores:
                    mediaItem['score'] = scores[0]                    
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    @staticmethod
    def next_page_extract(response):
        items = []
        try:
            next_pages = response.xpath('..//div[@class="mod-page"]//a[text()="%s"]/@href' % u'下一页').extract()
            if next_pages:
                next_page = next_pages[0]
                items.append(next_page)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    @staticmethod
    def url_type_resolve(url):
        url_type = None
        try:
            regex_express = 'http://www.iqiyi.com/a_[\w]+\.html.*'
            regex_pattern = re.compile(regex_express)
            match_result = regex_pattern.search(url)
            if match_result:
                url_type = URL_TYPE_MEDIA
            #http://www.iqiyi.com/v_19rro48cw0.html
            regex_express = 'http://www.iqiyi.com/v_[\w]+\.html.*'
            regex_pattern = re.compile(regex_express)
            match_result = regex_pattern.search(url)
            if match_result:
                url_type = URL_TYPE_PLAY
            #http://www.iqiyi.com/dianshiju/20110608/d108470f067c02a7.html
            regex_express = 'http://www.iqiyi.com/[a-zA-Z]+/[\d]+/[\w]+\.html.*'
            regex_pattern = re.compile(regex_express)
            match_result = regex_pattern.search(url)
            if match_result:
                url_type = URL_TYPE_PLAY
            #http://www.iqiyi.com/dianshiju/18jbj.html#vfrm=2-4-0-1
            regex_express = 'http://www.iqiyi.com/[a-zA-Z]+/[^/]+\.html.*'
            regex_pattern = re.compile(regex_express)
            match_result = regex_pattern.search(url)
            if match_result:
                url_type = URL_TYPE_MEDIA
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return url_type

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
                    latests = re.findall(r'[\d]+', latest) 
                    latest = ''.join(latests) 
                    mediaItem['latest'] = latest
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
                '''
                #截取的情况较为复杂，此处忽略不取，直接采用api里的数据
                elif label.startswith(u'集数'):
                    vcount = ''
                    latest = infos[0]
                    latests = latest.split('/')
                    #更新至N集/共N集
                    if len(latests) > 1:
                        latest = latests[0]
                        vcount = latests[1]
                    else:
                        vcount = latests[0]
                    vcounts = re.findall(r'[\d]+', vcount) 
                    latests = re.findall(r'[\d]+', latest) 
                    mediaItem['vcount'] = ''.join(vcounts)
                    mediaItem['latest'] = ''.join(latests)
                '''
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
