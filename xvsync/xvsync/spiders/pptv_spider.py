# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re
import time
import json
from lxml import etree
import traceback
import logging
import random
from lxml import etree
from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.utils.project import get_project_settings

from xvsync.items import MediaVideoItem, MediaItem, VideoItem
from xvsync.extract.pptv_extract import pptv_extract 
from xvsync.common.util import Util
from xvsync.db.db_mgr import DbManager
from xvsync.common.http_download import HTTPDownload

class pptv_spider(Spider):
    '''
        pptv爬虫流程：
        (1)list列表页 -> 播放页
        (2)播放页

    '''
    site_code = 'pptv'
    name = site_code
    mgr = DbManager.instance()
    max_mark_depth = 6 
    max_number = 100000
    list_prefix_url = 'http://list.pptv.com/channel_list.html'
    vip_prefix_url = 'http://ddp.vip.pptv.com'
    #老api,已经被放弃
    #album_api = 'http://v.pptv.com/show/videoList?&cb=videoList&pid=%s&cid=%s&page=%s'
    #该接口时常不稳定
    album_api = 'http://v.pptv.com/show/videoList?&cb=videoList&pid=%s&cat_id=%s&highlight=%s&page=%s'
    #当album_api不稳定时，利用下一个接口：该接口需要auth,一个跟设备绑定的参数
    auths = ["d410fafad87e7bbf6c6dd62434345818"]
    auth_album_api = "http://epg.api.pptv.com/detail.api?vid=%s&auth=%s"
    #通过json传递的参数
    json_data = None
    httpcli = HTTPDownload()
    app_api = "http://epg.api.pptv.com/detail.api?auth=%s&vid=%s"
    web_api = "http://v.pptv.com/show/videoList?&cb=videoList&pid=%s&page=%s"

    def __init__(self, json_data=None, *args, **kwargs):
        super(pptv_spider, self).__init__(*args, **kwargs)
        if json_data:
            self.json_data = json.loads(json_data)

    def start_requests(self):
        items = []
        try:
            self.load_member_variable()
            if self.json_data:
                items = items + self.load_video_urls()
            else:
                url = 'http://list.pptv.com'
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
            for list_channel in pptv_extract.list_channels:
                res = self.mgr.get_channel(channel_name=list_channel)
                if not res:
                    continue
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
                        items.append(Request(url=url, callback=self.api_parse, meta={'item':mediaVideoItem}))
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
                        items.append(Request(url=url, callback=self.api_parse, meta={'item':mediaVideoItem}))
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
            channel_id = response.request.meta['id'] if 'id' in response.request.meta else None
            if level == 0:
                #当前处在第一频道层，只提取电影、电视剧、动漫、综艺频道
                sels = response.xpath('//div[@class="detail_menu"]//li')
                level = level + 1
                for list_channel in pptv_extract.list_channels:
                    urls = sels.xpath('.//a[text()="%s"]/@href' % list_channel).extract()
                    if urls:
                        url = urls[0]
                        url = Util.get_absolute_url(url, prefix_url)
                        url = pptv_extract.normalize_url(url)
                        items.append(Request(url=url, callback=self.list_parse, meta={'level':level, 'id':list_channel}))
            else:
                #对当前层再进行细分
                sels = response.xpath('//div[@class="sear-menu"]//dl')
                if self.max_mark_depth > 0:
                    size = self.max_mark_depth if self.max_mark_depth < len(sels) else len(sels)
                else:
                    size = len(sels)
                if level <= size:
                    sel = sels[level -1]
                    level = level + 1
                    url_sels = sel.xpath('.//dd/a')
                    for url_sel in url_sels:
                        labels = url_sel.xpath('./text()').extract()
                        if not labels:
                            continue
                        label = labels[0]
                        if label in pptv_extract.ignore_channels:
                            continue
                        urls = url_sel.xpath('./@href').extract()
                        if not urls:
                            continue
                        url = urls[0]
                        url = Util.get_absolute_url(url, prefix_url)
                        url = pptv_extract.normalize_url(url)
                        items.append(Request(url=url, callback=self.list_parse, meta={'level':level, 'id':channel_id}))
                #获取当前层的所有list数据
                #按照排序方式再进行细分一次
                sels = response.xpath('//div[@class="sort-result-container"]//li/a/@href')
                regex_express = 'http://list\.pptv\.com\?(.*)'
                page = response.request.meta['page'] if 'page' in response.request.meta else 1  
                for sel in sels:
                    match_result = sel.re(regex_express)
                    if match_result:
                        postfix_url = match_result[0]
                        list_postfix_url = postfix_url + '&page=%s' % page
                        url = self.list_prefix_url + '?' + list_postfix_url
                        items.append(Request(url=url, callback=self.list_html_parse, meta={'page':page, 'id':channel_id, 'postfix_url':postfix_url}))
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'url: %s' % request_url)
        finally:
            return items

    def list_html_parse(self, response):
        items = []
        try:
            request_url = response.request.url
            logging.log(logging.INFO, 'list html url: %s' % request_url)
            page = response.request.meta['page'] if 'page' in response.request.meta else 1
            if page > self.max_update_page:
                return items
            channel_id = response.request.meta['id'] if 'id' in response.request.meta else None
            postfix_url = response.request.meta['postfix_url'] if 'postfix_url' in response.request.meta else None
            if u'电影' == channel_id:
                '''
                    is_hj:是否合集的标志，爬虫目前舍弃合集的链接
                    is_virtual:本站点是否存在
                '''
                sels = response.xpath('//a[@class="ui-list-ct" and @is_hj="0" and @is_virtual="0"]') 
            else:
                sels = response.xpath('//a[@class="ui-list-ct" and @is_virtual="0"]') 
            if sels:
                #表明仍有下一页
                for sel in sels:
                    mediaVideoItem = MediaVideoItem()
                    mediaItem = MediaItem()
                    mediaItem['channel_id'] = channel_id
                    urls = sel.xpath('./@href').extract() 
                    mediaItem['url'] = urls[0]
                    pptv_extract.media_info_extract(sel, mediaItem)
                    mediaVideoItem['media'] = mediaItem
                    items.append(Request(url=mediaItem['url'], callback=self.video_parse, meta={'item':mediaVideoItem}))
                #下一页
                page = page + 1
                url = self.list_prefix_url + '?' + postfix_url + '&page=%s' % page
                items.append(Request(url=url, callback=self.list_html_parse, meta={'page':page, 'id':channel_id, 'postfix_url':postfix_url}))
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
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
            mediaItem['url'] = request_url
            pptv_extract.media_info_extract(response, mediaItem)
            videoItems = []
            if u'电影' == mediaItem['channel_id']:
                if 'cont_id' not in mediaItem or not mediaItem['cont_id']:
                    return items
                videoItem = VideoItem()
                videoItem['url'] = mediaItem['url']
                videoItem['cont_id'] = mediaItem['cont_id']
                Util.copy_media_to_video(mediaItem, videoItem)
                self.set_video_info(videoItem)
                videoItems.append(videoItem)
            else:
                sel = response.xpath('//script[@type="text/javascript"]')
                #获取pid&cid用于获取电视剧，综艺，动漫的剧集信息
                if sel:
                    pids = sel.re('\"pid\"[ ]?:[ ]?(\d+)')
                    cids = sel.re('\"cat_id\"[ ]?:[ ]?(\d+)')
                    vids = sel.re('\"id\"[ ]?:[ ]?(\d+)')
                    if pids and cids and vids:
                        pid = pids[0]
                        cid = cids[0]
                        vid = vids[0]
                        page = 1
                        #给media的cont_id赋值
                        mediaItem['cont_id'] = pid
                        while True:
                            meta = {'pid':pid, 'cid':cid, 'vid':vid, 'page':page}
                            url = self.album_api % (pid, cid, vid, page) 
                            result = Util.get_url_content(url)
                            page_result = self.album_json_resolve(result, mediaItem, meta)
                            if not page_result['items']:
                                #该接口暂时由于获取不到video url，暂不提供
                                #for auth in self.auths:
                                #    url = self.auth_album_api % (pid, auth)
                                #    result = Util.get_url_content(url)
                                #    page_items = self.auth_album_xml_resolve(result, mediaItem, meta)
                                #    if page_items:
                                #        videoItems = page_items
                                #        break
                                break
                            else:
                                videoItems = videoItems + page_result['items']
                                page = page + 1
            if videoItems:
                #设置ext_id
                Util.set_ext_id(mediaItem, videoItems)
                
                self.set_media_info(mediaItem)

                mediaVideoItem['media'] = mediaItem
                mediaVideoItem['video'] = videoItems
                items.append(mediaVideoItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'video url: %s' % request_url)
        finally:
            return items

    def get_auth(self):
        arr = map(chr, range(48,58)+range(65,91)+range(97,123))
        auth = ''.join(random.sample(arr, random.randint(1,32)))
        return auth

    def api_parse(self, response):
        items = []
        try:
            request_url = response.request.url
            logging.log(logging.INFO, 'api prase url: %s' % request_url)
            mediaVideoItem = response.request.meta['item'] if 'item' in response.request.meta else MediaVideoItem()
            mediaItem = mediaVideoItem['media'] if 'media' in mediaVideoItem else MediaItem()
            mediaItem['url'] = request_url

            sel = response.xpath('.//script[@type="text/javascript"]')
            pidl = response.xpath('.//script[@type="text/javascript"]').re('\"pid\"\D?(\d+)')
            vidl = response.xpath('.//script[@type="text/javascript"]').re('\"id\"\D?(\d+)')
            if pidl and vidl:
                pid = pidl[0]
                vid = vidl[0]
                app_api = self.app_api % (self.get_auth(), pid)
                ismovie = False
                isvariaty = False
                if u'电影' == mediaItem['channel_id']:
                    ismovie = True
                    app_api = self.app_api % (self.get_auth(), vid)
                    mediaItem['cont_id'] = str(vid)
                elif u'综艺' == mediaItem['channel_id']:
                    isvariaty = True
                    app_api = self.app_api % (self.get_auth(), pid)
                    mediaItem['cont_id'] = str(pid)
                else:
                    app_api = self.app_api % (self.get_auth(), pid)
                    mediaItem['cont_id'] = str(pid)
                xpara = self.get_xdata(url=app_api)
                mediaItem = self.resolve_media_info(xpara, mediaItem, ismovie=ismovie)
                mediaItem['url'] = Util.normalize_url(request_url, self.site_code)
                mediaItem['site_id'] = self.site_id
                mediaItem['channel_id'] = self.channels_name_id[mediaItem['channel_id']]
                mediaItem['info_id'] = Util.md5hash(Util.summarize(mediaItem))
                
                max_page = self.get_max_page(xpara)
                video_list = []
                if ismovie:
                    videoItem = VideoItem()
                    videoItem['title'] = mediaItem['title'] if 'title' in mediaItem else None
                    videoItem['thumb_url'] = mediaItem['poster_url'] if 'poster_url' in mediaItem else None
                    videoItem['url'] = mediaItem['url'] if 'url' in mediaItem else None
                    videoItem['os_id'] = self.os_id
                    videoItem['site_id'] = self.site_id
                    videoItem['ext_id'] = Util.md5hash(mediaItem['url']) if 'url' in mediaItem else None
                    videoItem['vnum'] = mediaItem['vcount'] if 'vcount' in mediaItem else 1
                    videoItem['cont_id'] = mediaItem['cont_id'] if 'cont_id' in mediaItem else None
                    video_list.append(videoItem)
                else:
                    for i in range(1, max_page):
                        web_api = self.web_api % (pid, i)
                        dpara = self.get_ddata(url=web_api)
                        video_list += self.resolve_video_item(dpara, page_num=i, isvariaty=isvariaty)
                if isvariaty:
                   video_list = self.revise_video_item(video_list, xpara)
                if video_list:
                    Util.set_ext_id(mediaItem, video_list)
                    mediaVideoItem['media'] = mediaItem
                    mediaVideoItem['video'] = video_list
                    items.append(mediaVideoItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    def get_max_page(self, xpara):
        max_page = 1
        try:
            video_list_count = xpara.find('video_list_count')
            if video_list_count is not None and video_list_count.text is not None and video_list_count.text.isdigit():
                max_page = int(video_list_count.text)
            else:
                max_page = len(xpara.xpath('//video'))
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return max_page/100 + 2

    def resolve_media_info(self, xpara, mediaItem, ismovie=False):
        try:
            title = xpara.find('title')
            if title is not None:
                mediaItem['title'] = title.text
            tag = xpara.find('catalog')
            if tag is not None and tag.text is not None:
                mediaItem['type'] = Util.join_list_safely(tag.text.split(','))
            director = xpara.find('director')
            if director is not None and director.text is not None:
                mediaItem['director'] = Util.join_list_safely(director.text.split(','))
            actor = xpara.find('act')
            if actor is not None and actor.text is not None:
                mediaItem['actor'] = Util.join_list_safely(actor.text.split(','))
            district = xpara.find('area')
            if district is not None and district.text is not None:
                mediaItem['district'] = district.text
            release_date = xpara.find('year')
            if release_date is not None and release_date.text is not None:
                # 会有<year>0</year>的情况,导致release_date为空
                mediaItem['release_date'] = Util.str2date(release_date.text)
            if ismovie:
                duration = xpara.find('duration')
                if duration is not None and duration.text is not None:
                    mediaItem['duration'] = int(float(duration.text))
            paid = xpara.find('pay')
            if paid is not None and paid.text is not None:
                mediaItem['paid'] = int(float(paid.text))
            intro = xpara.find('content')
            if intro is not None and intro.text is not None:
                mediaItem['intro'] = intro.text
            poster_url = xpara.find('imgurl')
            if poster_url is not None and poster_url.text is not None:
                mediaItem['poster_url'] = poster_url.text
            score = xpara.find('mark')
            if score is not None and score.text is not None:
                mediaItem['score'] = float(score.text)
            latest = xpara.find('vsTitle')
            if latest is not None and latest.text is not None:
                l = re.findall(r'[\d+]', latest.text)
                if l:
                    mediaItem['latest'] = ''.join(l)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return mediaItem

    def resolve_video_item(self, dpara, page_num=1, isvariaty=False):
        videos = []
        page_num -= 1
        try:
            if dpara and int(dpara.get('err')) == 0 and 'data' in dpara and 'list' in dpara['data']:
                    lst = dpara['data'].get('list', [])
                    sameV = 1
                    for index, item in enumerate(lst):
                        videoItem = VideoItem()
                        videoItem['cont_id'] = item.get('id')
                        videoItem['url'] = Util.normalize_url(item.get('url'), self.site_code)
                        videoItem['thumb_url'] = item.get('capture')
                        videoItem['os_id'] = self.os_id
                        videoItem['site_id'] = self.site_id
                        videoItem['ext_id'] = Util.md5hash(videoItem['url'])
                        oep = item.get('epTitle', '')
                        nep = oep[::-1]
                        for i in [u'上', u'中', u'下']:
                            nep.replace(i, '', 1)
                        nep = nep[::-1]
                        if isvariaty and nep and nep.isdigit() and len(nep) == 8:
                            videoItem['vnum'] = str(index + 1 + page_num * 100)
                            videoItem['title'] = item.get('title', '') + str(videoItem['vnum'])
                        elif isvariaty:
                            videoItem['title'] = oep if oep else item.get('title', '')
                            # 对于date为空的情况，取下标作为剧集号
                            videoItem['vnum'] = str(index + 1 + page_num * 100)
                        elif nep and nep.isdigit():
                            # '01' --> '1'
                            videoItem['vnum'] = str(int(float(nep)))
                            videoItem['title'] = item.get('title', '') + oep
                        elif nep:
                            videoItem['vnum'] = str(index + 1 + page_num * 100)
                            videoItem['title'] = oep
                        elif not nep:
                            videoItem['vnum'] = str(index + 1 + page_num * 100)
                            videoItem['title'] = item.get('title', '') + str(videoItem['vnum']) + oep
                        videos.append(videoItem)
        except Exception, e:    
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return videos

    def resolve_epTitle(self, ep=''):
        vnum = None
        mark = ep
        r = re.compile('\D?(\d+)\D?')
        m = r.match(ep)
        if m:
            vnum = m.group(1)
            mark = re.sub(vnum, '', ep)
        return vnum, mark

    def revise_video_item(self, video_list, xml):
        try:
            for index, videoItem in enumerate(video_list):
                cont_id = videoItem['cont_id']
                vl = xml.xpath('//video[@id="%s"]' % cont_id)
                if vl:
                    v = vl[0]
                    attr = v.attrib
                    ovnum = videoItem.get('vnum') 
                    if ovnum and len(ovnum) < 8:
                        continue
                    else:
                        videoItem['vnum'] = str(attr.get('date', index+1))
                else:
                    videoItem['vnum'] = str(index+1)
            #video_list.reverse()
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return video_list

    def get_ddata(self, url, timeout=3):
        return self.html2dict(self.httpcli.get_data(url=url, timeout=timeout))

    def get_xdata(self, url, timeout=3):
        return self.html2xml(self.httpcli.get_data(url=url, timeout=timeout))

    def html2xml(self, html):
        x = etree.Element('error')
        try:
            x = etree.fromstring(html)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return x

    def html2dict(self, html):
        d = {}
        try:
            r = re.compile('.*videoList\((.*)\);')
            m = r.match(html)
            if m:
                jpara = m.group(1)
                d = json.loads(jpara)
            else:
                d = json.loads(html)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return d

    def album_json_resolve(self, text, mediaItem, meta):
        result = {'error':'0', 'items':[]}
        try:
            pid = meta['pid']
            cid = meta['cid']
            vid = meta['vid']
            page = meta['page']
            request_url = self.album_api % (pid, cid, vid, page)
            logging.log(logging.INFO, 'album json url: %s' % request_url)
            regex_express = '(\{.*\})'
            regex_pattern = re.compile(regex_express)
            match_results = regex_pattern.search(text)
            if match_results:
                content = match_results.groups()[0]
                json_content = json.loads(content)
                if json_content['err'] != 0:
                    result['error'] = '1'
                    return result
                mediaItem['latest'] = json_content['data']['total']
                datas = json_content['data']['list']
                items = []
                for data in datas:
                    #片花
                    is_trailer = data['isTrailer']
                    if is_trailer != False and str(is_trailer) != 'false':
                        continue
                    videoItem = VideoItem()
                    videoItem['title'] = data['title']
                    videoItem['cont_id'] = data['id']
                    videoItem['url'] = data['url']
                    videoItem['thumb_url'] = data['capture']
                    epTitle = data['epTitle']
                    vnums = re.findall(r'[\d]+', epTitle)
                    if vnums:
                        videoItem['vnum'] = vnums[0] 
                    self.set_video_info(videoItem)
                    items.append(videoItem)
                result['items'] = items
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'album json url: %s' % request_url)
            logging.log(logging.INFO, '================json content=================')
            logging.log(logging.INFO, text)
        finally:
            return result

    def auth_album_xml_resolve(self, text, mediaItem, meta):
        result = {'error':'0', 'items':[]}
        try:
            pid = meta['pid']
            request_url = self.auth_album_api % (pid)
            logging.log(logging.INFO, 'auth album xml url: %s' % request_url)
            xml_content = etree.fromstring(text)
            latests = xml_content.xpath("//video_list_count").extract()
            if latests:
                mediaItem['latest'] = latests[0]
            datas = xml_content.xpath("//video_list/video")
            items = []
            for data in datas:
                videoItem = VideoItem()
                ids = data.xpath('./@id').extract()
                if ids:
                    videoItem['cont_id'] = ids[0]
                vnums = data.xpath('./@title').extract() 
                if vnums:
                    vnums = re.findall(r'[\d]+', vnums[0])
                    if vnums:
                        videoItem['vnum'] = vnums[0] 
                        videoItem['title'] = '第%s集' % vnums[0] 
                thumb_urls = data.xpath('./@sloturl').extract() 
                if thumb_urls:
                    videoItem['thumb_url'] = thumb_urls[0] 
                self.set_video_info(videoItem)
                items.append(videoItem)
            result['items'] = items
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'auth album xml url: %s' % request_url)
            logging.log(logging.INFO, '================xml content=================')
            logging.log(logging.INFO, text)
        finally:
            return result

    def set_video_info(self, videoItem):
        videoItem['os_id'] = self.os_id
        videoItem['site_id'] = self.site_id
        url = videoItem['url']
        url = Util.normalize_url(url, self.site_code)
        videoItem['url'] = url
        videoItem['ext_id'] = Util.md5hash(url)            

    def set_media_info(self, mediaItem):
        mediaItem['site_id'] = self.site_id
        #由于之前的channel_id存放的是中文的频道名称,需要转换成真正的channel_id
        channel_name = mediaItem['channel_id']
        mediaItem['channel_id'] = self.channels_name_id[channel_name]
        #设置info_id
        mediaItem['info_id'] = Util.md5hash(Util.summarize(mediaItem))          
