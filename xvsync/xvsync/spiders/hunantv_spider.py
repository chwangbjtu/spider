# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re
import json
import traceback
import logging
from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.selector import Selector
from scrapy.utils.project import get_project_settings

from xvsync.items import MediaVideoItem, MediaItem, VideoItem
from xvsync.extract.hunantv_extract import hunantv_extract 
from xvsync.common.util import Util
from xvsync.db.db_mgr import DbManager
from xvsync.common.http_download import HTTPDownload

class hunantv_spider(Spider):
    '''
        hunantv爬虫流程：
        (1)list列表页 -> 播放页 -> 正片页[ -> 媒体页]
        (2)播放页 -> 正片页
        由于hunantv在list表页的全部即代表全部，所以无需每个标签都爬取
    '''
    site_code = 'hunantv'
    name = site_code
    mgr = DbManager.instance()
    max_number = 100000
    max_mark_depth = 10 
    #通过json传递的参数
    json_data = None
    httpdownload = HTTPDownload()
    media_info_url = "http://m.api.hunantv.com/video/getbyid?videoId=%s"
    video_list_url = "http://m.api.hunantv.com/video/getList?videoId=%s&pageNum=%s"

    def __init__(self, json_data=None, *args, **kwargs):
        super(hunantv_spider, self).__init__(*args, **kwargs)
        if json_data:
            self.json_data = json.loads(json_data)

    def start_requests(self):
        items = []
        try:
            self.load_member_variable()
            if self.json_data:
                items = items + self.load_video_urls()
            else:
                url = 'http://list.hunantv.com'
                items.append(Request(url=url, callback=self.list_parse, meta={'level':0}))
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
            for list_channel in hunantv_extract.list_channels:
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
                        items.append(Request(url=url, callback=self.play_parse, meta={'item':mediaVideoItem}))
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
                elif cmd == 'carpet':
                    res = self.mgr.get_video_url(self.site_code)
                    for item in res:
                        mediaVideoItem = MediaVideoItem()
                        mediaVideoItem['mid'] = item['mid']
                        mediaItem = MediaItem()
                        mediaItem['channel_id'] = item['name']
                        mediaVideoItem['media'] = mediaItem
                        url = item['url']
                        items.append(Request(url=url, callback=self.video_parse, meta={'item':mediaVideoItem}))
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
            if level == 0: 
                #第一次进入list页面
                sels = response.xpath('//div[@id="hony-searchtag-condition"]/p')
                for list_channel in hunantv_extract.list_channels:
                    list_postfix_urls = sels.xpath('.//a[normalize-space(text())="%s"]/@href' % list_channel).extract()
                    if list_postfix_urls:
                        list_postfix_url = list_postfix_urls[0]
                        url = Util.get_absolute_url(list_postfix_url, prefix_url)
                        items.append(Request(url=url, callback=self.list_parse, meta={'id':list_channel}))
            else:
                page = response.request.meta['page'] if 'page' in response.request.meta else 1
                channel_id  = response.request.meta['id'] if 'id' in response.request.meta else None
                if page > self.max_update_page:
                    return items
                #获取播放地址
                sels = response.xpath('//div[@class="play-index-con-box"]')
                results = hunantv_extract.video_extract(sels)
                for item in results:
                    mediaVideoItem = MediaVideoItem()
                    mediaItem = MediaItem()
                    mediaItem['channel_id'] = channel_id
                    video_sels = sels.xpath('.//a[@href="%s"]/..' % item['url'])
                    hunantv_extract.media_info_extract(video_sels, mediaItem)
                    mediaItem['poster_url'] = Util.get_absolute_url(mediaItem['poster_url'], prefix_url)
                    url = Util.get_absolute_url(item['url'], prefix_url)
                    mediaVideoItem['media'] = mediaItem
                    items.append(Request(url=url, callback=self.video_parse, meta={'item':mediaVideoItem}))
                #下一页
                results = hunantv_extract.next_page_extract(response)
                if results:
                    result = results[0]
                    result = Util.get_absolute_url(result, prefix_url)
                    page = page + 1
                    items.append(Request(url=result, callback=self.list_parse, meta={'page':page, 'id':channel_id}))
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
            mediaItem = mediaVideoItem['media'] if 'media' in mediaVideoItem else None
            #播放页获取详细信息
            sels = response.xpath('//script[@type="text/javascript"]')
            hunantv_extract.media_info_extract(sels, mediaItem)
            sels = response.xpath('//div[@class="play-xxmes clearfix"]')
            hunantv_extract.media_info_extract(sels, mediaItem)
            #获得媒体页地址
            url_express = '(http://www\.hunantv\.com/v/[\d]+/[\d]+)/[a-zA-Z]/[\d]+\.html'
            url_regex = re.compile(url_express)
            match_results = url_regex.search(request_url)
            if match_results:
                url_content = match_results.groups()[0]
                mediaItem['url'] = url_content
            #获取正片地址
            url_exist = False
            sels = response.xpath('//div[@class="play-index-con-til clearfix"]//*[@class="mppl-til"]')
            for sel in sels:
                results = hunantv_extract.album_extract(sel)
                if results:
                    item = results[0]
                    url = item['url']
                    url = Util.get_absolute_url(url, prefix_url)
                    mediaVideoItem['media'] = mediaItem
                    items.append(Request(url=url, callback=self.album_parse, meta={'url':request_url, 'item':mediaVideoItem}))
                    url_exist = True
                    break
            #不存在正在播放的链接，如“芒果捞星闻”
            if 'url' in mediaItem and not url_exist:
                year_api = mediaItem['url'] + '/s/json.year.js'
                mediaVideoItem['media'] = mediaItem
                items.append(Request(url=year_api, callback=self.album_json_parse, meta={'item':mediaVideoItem, 'url':year_api}))                
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'video url: %s' % request_url)
        finally:
            return items

    def play_parse(self, response):
        items = []
        try:
            request_url = response.request.url
            logging.log(logging.INFO, 'play url: %s' % request_url)
            mediaVideoItem = response.request.meta['item'] if 'item' in response.request.meta else MediaVideoItem()
            
            route_url_list = response.xpath('//div[@class="play-content"]//div[@class="v-panel-route"]/a/@href').extract()
            media_url = ''
            if route_url_list:
                media_url = route_url_list[-1]
            if media_url:
                # 有媒体页url，媒体页抓取媒体信息
                items.append(Request(url=media_url, callback=self.media_parse, meta={'url':request_url, 'item':mediaVideoItem}))
            else:
                # 电影没有媒体页，在播放页抓取媒体信息
                mediaItem = mediaVideoItem['media'] if 'media' in mediaVideoItem else MediaItem()
                title_class = "v-info v-info-film e-follow"
                div_class = "v-meta v-meta-film"
                v_title = '//div[@class="%s"]//h1[@class="title"]/text()'
                title_list = response.xpath(v_title % title_class).extract()
                title = Util.join_list_safely(title_list)
                if title:
                    mediaItem['title'] = title
                mediaItem = self.pack_media_info(response, mediaItem, title_class, div_class)
                # 没有媒体页，播放地址作为媒体地址
                mediaItem['url'] = Util.normalize_url(request_url, self.site_code)
                mediaVideoItem['media'] = mediaItem
                r = re.compile('.*/(\d+).html')
                m = r.match(mediaItem['url'])
                if m:
                    vid = m.group(1)
                    prefix_video_url = re.sub(vid, '%s', mediaItem['url'])
                    items.append(self.api_media_info(mediaVideoItem, vid, prefix_video_url))
                else:
                    items.append(mediaVideoItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'play url: %s' % request_url)
        finally:
            return items

    def media_parse(self, response):
        items = []
        try:
            media_url = response.request.url
            logging.log(logging.INFO, 'media url: %s' % media_url)
            
            mediaVideoItem = response.request.meta['item'] if 'item' in response.request.meta else MediaVideoItem()
            mediaItem = mediaVideoItem['media'] if 'media' in mediaVideoItem else MediaItem()
            # 媒体页获取媒体信息
            title_class = "v-info v-info-album "
            div_class = "v-meta v-meta-album"
            v_title = '//div[@class="%s"]//h1[@class="title"]/span/text()'
            title_list = response.xpath(v_title % title_class).extract()
            title = Util.join_list_safely(title_list)
            if title:
                mediaItem['title'] = title
            mediaItem = self.pack_media_info(response, mediaItem, title_class, div_class)
            mediaItem['url'] = Util.normalize_url(media_url, self.site_code)
            request_url = response.meta['url']
            request_url = Util.normalize_url(request_url, self.site_code)
            r = re.compile('.*/(\d+).html')
            m = r.match(request_url)
            if m:
                vid = m.group(1)
                prefix_video_url = re.sub(vid, '%s', request_url)
                items.append(self.api_media_info(mediaVideoItem, vid, prefix_video_url))
            else:
                pass
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'media url: %s' % request_url)
        finally:
            return items

    def pack_media_info(self, response, mediaItem, title_class="", div_class=""):
        v_meta = '//div[@class="%s"]/p/em[re:test(text(), ".*%s.*")]/../%s/text()'
        director_list = response.xpath(v_meta % (div_class, u'导演', 'a')).extract()
        actor_list = response.xpath(v_meta % (div_class, u'主演', 'a')).extract()
        district_list = response.xpath(v_meta % (div_class, u'地区', 'a')).extract()
        tag_list = response.xpath(v_meta % (div_class, u'类型', 'a')).extract()
        intro_list = response.xpath(v_meta % (div_class, u'简介', 'span')).extract()
        
        director = Util.join_list_safely(director_list)
        actor = Util.join_list_safely(actor_list)
        district = Util.join_list_safely(district_list)
        tag = Util.join_list_safely(tag_list)
        intro = Util.join_list_safely(intro_list)
        if director:
            mediaItem['director'] = director
        if actor:
            mediaItem['actor'] = actor
        if district:
            mediaItem['district'] = district
        if tag:
            mediaItem['type'] = tag
        if intro:
            mediaItem['intro'] = intro
        return mediaItem

    def api_media_info(self, mediaVideoItem, vid, prefix_video_url):
        mediaItem = mediaVideoItem['media'] if 'media' in mediaVideoItem else MediaItem()
        try:
            miu = self.media_info_url % vid 
            jdata = self.httpdownload.get_data(miu)
            if not jdata:
                pass
            else:
                ddata = json.loads(jdata)
                assert int(ddata.get('code', 202)) == 200, "接口获取媒体信息失败"
                detail =  ddata.get('data').get('detail')
                assert type(detail) == dict
                mediaItem['cont_id'] = str(detail.get('collectionId'))
                mediaItem['title'] = detail.get('collectionName')
                mediaItem['director'] = Util.join_list_safely(detail.get('director').split('/'))
                mediaItem['actor'] = Util.join_list_safely(detail.get('player').split('/'))
                mediaItem['release_date'] = Util.str2date(detail.get('publishTime'))
                mediaItem['vcount'] = int(detail.get('totalvideocount'))
                latest = detail.get('lastseries')
                m = re.compile('\D*(\d+)\D*').match(latest)
                if m:
                    mediaItem['latest'] = m.group(1)
                if mediaItem['vcount'] == 1:
                    mediaItem['latest'] =1
                mediaItem['paid'] = detail.get('isvip')
                mediaItem['intro'] = detail.get('desc')
                mediaItem['poster_url'] = detail.get('image')
                mediaItem['site_id'] = self.site_id
                mediaItem['channel_id'] = self.channels_name_id[mediaItem['channel_id']]
                info_id = Util.md5hash(Util.summarize(mediaItem))
                mediaItem['info_id'] = info_id

                vcount = mediaItem['vcount']
                if not vcount:
                    vcount = 1
                else:
                    vcount = int(vcount)
                video_list = self.api_video_list(vid, vcount, prefix_video_url,mediaItem['channel_id'])
                if video_list:
                     Util.set_ext_id(mediaItem, video_list)
                mediaVideoItem['video'] = video_list
                mediaVideoItem['media'] = mediaItem
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.ERROR,vid)
        finally:
            return mediaVideoItem

    def api_video_list(self, vid, vcount, prefix_video_url,channel):
        video_list = []
        try:
            max_page_num = vcount / 20 + 1
            for i in range(max_page_num):
                vlu = self.video_list_url % (vid, i)
                jdata = self.httpdownload.get_data(vlu)
                if not jdata:
                    break
                ddata = json.loads(jdata)
                code = int(ddata.get('code', 202))
                if code != 200:
                    break
                datal = ddata.get('data')
                if not datal:
                    break
                for data in datal:
                    videoItem = VideoItem()
                    if type(data) != dict:
                        continue
                    #videoItem['title'] = data.get('name')
                    videoItem['title'] = data.get('desc')
                    videoItem['thumb_url'] = data.get('image')
                    videoItem['vnum'] = data.get('videoIndex')
                    videoId = data.get('videoId')
                    #if int(videoItem['vnum']) == 0:
                    #    videoItem['vnum'] = self.get_vnum(data.get('name'))
                    turl = self.media_info_url % (videoId)
                    tjdata = self.httpdownload.get_data(turl)
                    if not tjdata:
                        continue
                    tdjdata = json.loads(tjdata)
                    tcode = int(tdjdata.get('code', 202))
                    if code != 200:
                        continue
                    tdatal = tdjdata.get('data')
                    if not tdatal:
                        continue
                    publish_time = tdatal.get('detail').get('publishTime')
                    if publish_time and channel == 2004:
                        videoItem['vnum'] = self.get_vnum(publish_time)
                    
                    tcode = int(ddata.get('code', 202))
                    videoItem['cont_id'] = data.get('videoId')
                    videoItem['url'] = Util.normalize_url(prefix_video_url % data.get('videoId'), self.site_code)
                    videoItem['os_id'] = self.os_id
                    videoItem['site_id'] = self.site_id
                    videoItem['ext_id'] = Util.md5hash(videoItem['url'])
                    video_list.append(videoItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return video_list

    def album_json_parse(self, response):
        items = []
        try:
            request_url = response.request.url
            logging.log(logging.INFO, 'json url: %s' % request_url)
            prefix_url = Util.prefix_url_parse(request_url)
            mediaVideoItem = response.request.meta['item'] if 'item' in response.request.meta else MediaVideoItem()
            mediaItem = mediaVideoItem['media'] if 'media' in mediaVideoItem else None
            url = response.request.meta['url'] if 'url' in response.request.meta else None
            if url != request_url:
                #被重定向，表明不存在
                return items
            year_express = '(\[.*\])'
            year_regex = re.compile(year_express)
            match_results = year_regex.search(response.body)
            if match_results:
                videoItems = []
                year_content = match_results.groups()[0]
                years = json.loads(year_content)
                for year in years:
                    video_url = mediaItem['url'] + '/s/json.%s.js' % year
                    result = Util.get_url_content(video_url)
                    videoItems = videoItems + self.album_tag_json_resolve(text=result, meta={'url':video_url})

                if videoItems:
                    Util.set_ext_id(mediaItem, videoItems)
                    #进入媒体页，获取相关信息
                    result = Util.get_url_content(mediaItem['url'])
                    if result:
                        mediaItem = self.media_resolve(text=result, meta={'item':mediaItem, 'url':mediaItem['url']})

                    self.set_media_info(mediaItem)
                    mediaVideoItem['media'] = mediaItem
                    mediaVideoItem['video'] = videoItems
                    items.append(mediaVideoItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'json url: %s' % request_url)
        finally:
            return items

    def album_tag_json_resolve(self, text, meta):
        items = []
        try:
            request_url = meta['url'] if 'url' in meta else None
            logging.log(logging.INFO, 'json url: %s' % request_url)
            prefix_url = Util.prefix_url_parse(request_url)
            video_express = '(\[\{.*\}\])'
            video_regex = re.compile(video_express)
            match_results = video_regex.search(text)
            if match_results:
                video_content = match_results.groups()[0]
                videos = json.loads(video_content)
                for video in videos:
                    videoItem = VideoItem()
                    ext_id = video['id']
                    title = video['title']
                    vnum = video['stitle']
                    img = video['img']
                    url = video['url']
                    videoItem['cont_id'] = ext_id 
                    videoItem['title'] = title 
                    vnum = str(vnum)
                    videoItem['vnum'] = filter(str.isalnum, vnum)
                    videoItem['thumb_url'] = img 
                    videoItem['url'] = Util.get_absolute_url(url, prefix_url)
                    self.set_video_info(videoItem)
                    items.append(videoItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'json url: %s' % request_url)
        finally:
            return items

    def album_parse(self, response):
        items = []
        try:
            request_url = response.request.url
            logging.log(logging.INFO, 'album url: %s' % request_url)
            prefix_url = Util.prefix_url_parse(request_url)
            video_url = response.request.meta['url'] if 'url' in response.request.meta else None 
            mediaVideoItem = response.request.meta['item'] if 'item' in response.request.meta else MediaVideoItem()
            mediaItem = mediaVideoItem['media'] if 'media' in mediaVideoItem else MediaItem() 
            videoItems = []
            sels = response.xpath('//div[@class="page-videolist-tag-main"]//p[@class="pa1-nav"]')
            if sels:
                #存在tag页
                #http://list.hunantv.com/album/56.html
                results = hunantv_extract.album_tag_extract(sels)
                for item in results:
                    url = Util.get_absolute_url(item['url'], prefix_url)
                    result = Util.get_url_content(url)
                    videoItems = videoItems + self.album_tag_resolve(text=result, meta={'url':url})
            else:
                #不存在tag页
                #http://list.hunantv.com/album/2905.html
                video_sels = response.xpath('//div[@class="page-videolist clearfix"]')
                if video_sels:
                    result = video_sels.extract()[0]
                    videoItems = videoItems + self.album_tag_resolve(text=result, meta={'url':request_url})
                else:
                    #无正片页地址
                    #http://www.hunantv.com/v/7/102831/f/1043648.html，有正片集的URL，但该URL是无效的
                    if video_url:
                        videoItem = VideoItem()
                        Util.copy_media_to_video(mediaItem, videoItem)
                        videoItem['url'] = video_url
                        Util.copy_media_to_video(mediaItem, videoItem)
                        video_url_express = 'http://www\.hunantv\.com/v/[\d]+/[\d]+/[a-zA-Z]/([\d]+)\.html'
                        video_url_regex = re.compile(video_url_express)
                        #获取视频id
                        match_results = video_url_regex.search(video_url)
                        if match_results:
                            id = match_results.groups()[0]
                            videoItem['cont_id'] = id
                        self.set_video_info(videoItem)
                        videoItems.append(videoItem)

            if videoItems:
                #设置ext_id
                Util.set_ext_id(mediaItem, videoItems)

                #进入媒体页，获取相关信息
                result = Util.get_url_content(mediaItem['url'])
                if result:
                    mediaItem = self.media_resolve(text=result, meta={'item':mediaItem, 'url':mediaItem['url']})

                self.set_media_info(mediaItem)
                mediaVideoItem['media'] = mediaItem
                mediaVideoItem['video'] = videoItems
                items.append(mediaVideoItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'album url: %s' % request_url)
        finally:
            return items

    def album_tag_resolve(self, text, meta):
        items = []
        try:
            request_url = meta['url'] if 'url' in meta else None
            logging.log(logging.INFO, 'album tag url: %s' % request_url)
            prefix_url = Util.prefix_url_parse(request_url)
            try:
                response = Selector(text=text)
            except Exception, e:
                logging.log(logging.ERROR, traceback.format_exc())
                logging.log(logging.INFO, 'text to be parsed is not xml or html')
                return items
            sels = response.xpath('//div[@class="play-index-con-box"]//ul[@class="clearfix ullist-ele"]/li')
            video_url_express = 'http://www\.hunantv\.com/v/[\d]+/[\d]+/[a-zA-Z]/([\d]+)\.html'
            video_url_regex = re.compile(video_url_express)
            for sel in sels:
                videoItem = VideoItem()
                hunantv_extract.video_info_extract(sel, videoItem)
                url = videoItem['url']
                url = Util.get_absolute_url(url, prefix_url)
                videoItem['url'] = url 
                #获取视频id
                match_results = video_url_regex.search(url)
                if match_results:
                    id = match_results.groups()[0]
                    videoItem['cont_id'] = id
                self.set_video_info(videoItem)
                items.append(videoItem)
            #下一页
            results = hunantv_extract.next_page_extract(response)
            if results:
                url = results[0]
                url = Util.get_absolute_url(url, prefix_url)
                result = Util.get_url_content(url)
                items = items + self.album_tag_resolve(text=result, meta={'url':url})
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'album tag url: %s' % request_url)
        finally:
            return items

    def media_resolve(self, text, meta):
        try:
            request_url = meta['url'] if 'url' in meta else None
            logging.log(logging.INFO, 'media url: %s' % request_url)
            mediaItem = meta['item'] if 'item' in meta else None
            prefix_url = Util.prefix_url_parse(request_url)
            try:
                response = Selector(text=text)
            except Exception, e:
                logging.log(logging.ERROR, traceback.format_exc())
                logging.log(logging.INFO, 'text to be parsed is not xml or html')
                return mediaItem
            sels = response.xpath('//script[@language="javascript"]')
            if sels:
                hunantv_extract.media_info_extract(sels, mediaItem)
            sels = response.xpath('//div[@class="mod-album-1-intro clearfix"]') 
            if sels:
                hunantv_extract.media_info_extract(sels, mediaItem)
            sels = response.xpath('//div[@class="mod-album-1 clearfix"]') 
            if sels:
                hunantv_extract.media_info_extract(sels, mediaItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'media url: %s' % request_url)
        finally:
            return mediaItem

    def set_media_info(self, mediaItem):
        mediaItem['site_id'] = self.site_id
        #由于之前的channel_id存放的是中文的频道名称,需要转换成真正的channel_id
        channel_name = mediaItem['channel_id']
        mediaItem['channel_id'] = self.channels_name_id[channel_name]
        #设置info_id
        mediaItem['info_id'] = Util.md5hash(Util.summarize(mediaItem))          

    def set_video_info(self, videoItem):
        videoItem['os_id'] = self.os_id
        videoItem['site_id'] = self.site_id
        url = videoItem['url']
        url = Util.normalize_url(url, self.site_code)
        videoItem['url'] = url
        videoItem['ext_id'] = Util.md5hash(url)            

    def get_vnum(self,publish_time):
        #2016-03-05
        id = ""
        try:
            id = publish_time.replace('-','')
        except Exception as e:
            pass
        return id

    #def template(self):
    #    items = []
    #    try:
    #        return items
    #    except Exception, e:
    #        logging.log(logging.ERROR, traceback.format_exc())
    #    finally:
    #        return items
