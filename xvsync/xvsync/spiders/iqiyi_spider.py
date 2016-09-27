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
from xvsync.extract.iqiyi_extract import iqiyi_extract 
from xvsync.common.util import Util
from xvsync.common.util import URL_TYPE_MEDIA, URL_TYPE_PLAY
from xvsync.db.db_mgr import DbManager

class iqiyi_spider(Spider):
    '''
        iqiyi浏览流程：
         (1)从list进入
            电视剧, 综艺, ：list列表页 -> 媒体页
            电影：list列表页 -> 播放页
            动漫：
                (1)电影版：list列表页 -> 播放页
                (2)普通版：list列表页 -> 媒体页
         (2)从播放页进入
            (1)播放页 -> 媒体页
            (2)播放页
        iqiyi爬虫流程：
          (1)list列表页进入 -> (判断URL类型，确定媒体页还是播放页)获取本页的信息，结束
          (2)播放页进入 -> 获取播放页信息，判断是否存在媒体页 -> 媒体页 
        由于iqiyi在list表页的最多只能浏览到30页,所以采用如下策略爬取
          (1)按一级一级类别细分成各个分支
          (2)当细分的页小于30时，该分支停止细分
          (2)当分支细分结束，页数仍大于30，则再利用不同的排序，再遍历，以尽量减少因无法访问30页之后所带来的内容缺失
          ps.一直采用细分到叶子，感觉整个流程比较深，所以采用截枝的方式
    '''
    site_code = 'iqiyi'
    name = site_code
    mgr = DbManager.instance()
    max_number = 100000
    #因为在类别细分生成树，本爬虫为了提高效率，采用将当前分支的页面数小于max_broswe_page,就截枝(不在细分)的方法
    max_broswe_page = '30'
    list_prefix_url = 'http://list.iqiyi.com'
    #http://cache.video.qiyi.com/jp/sdlst/6/1300000156/
    source_year_api = 'http://cache.video.qiyi.com/jp/sdlst/%s/%s/'
    #http://cache.video.qiyi.com/jp/sdvlst/6/1300001662/2014/?categoryId=6&sourceId=1300001662&tvYear=2014
    source_media_api = 'http://cache.video.qiyi.com/jp/sdvlst/%s/%s/%s/?categoryId=%s&sourceId=%s&tvYear=%s'
    #http://cache.video.qiyi.com/jp/avlist/202321801/1/?albumId=202321801&pageNo=1
    album_media_api = 'http://cache.video.qiyi.com/jp/avlist/%s/%s/?albumId=%s&pageNo=%s'
    vip_api = 'http://serv.vip.iqiyi.com/pay/movieBuy.action?aid=%s'
    api_success_code = u'A00000'
    max_mark_depth = 10 
    #通过json传递的参数
    json_data = None

    #统计数据用
    #count = 0
    
    def __init__(self, json_data=None, *args, **kwargs):
        super(iqiyi_spider, self).__init__(*args, **kwargs)
        if json_data:
            self.json_data = json.loads(json_data)
    
    def start_requests(self):
        items = []
        try:
            self.load_member_variable()
            if self.json_data:
                items = items + self.load_video_urls()
            else:
                url = self.list_prefix_url
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
            for list_channel in iqiyi_extract.list_channels:
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
                #当前处在第一频道层，只提取电影、电视剧、动漫、综艺频道
                level = level + 1
                sels = response.xpath('//div[@class="mod_sear_menu mt20 mb30"]//div[@class="mod_sear_list"]//li')
                for list_channel in iqiyi_extract.list_channels:
                    urls = sels.xpath('.//a[text()="%s"]/@href' % list_channel).extract()
                    if urls:
                        url = urls[0]
                        url = Util.get_absolute_url(url, prefix_url)
                        items.append(Request(url=url, callback=self.list_parse, meta={'level':level, 'id':list_channel}))
            else:
                page = response.request.meta['page'] if 'page' in response.request.meta else 1  
                if page > self.max_update_page:
                    return items
                channel_id = response.request.meta['id'] if 'id' in response.request.meta else None  
                if page == 1:
                    #第一次进入该层级,即在第一页，根据需要确定是否细分，否则，直接抓取每一页的内容即可
                    max_broswe_pages = response.xpath('//div[@class="mod-page"]//a[@data-key="%s"]' % self.max_broswe_page)
                    if max_broswe_pages:
                        #当前页面数仍大于max_broswe_page，需要再一次细分
                        sels = response.xpath('//div[@class="mod_sear_menu mt20 mb30"]//div[starts-with(@class, "mod_sear_list")]')
                        size = len(sels)
                        if level < size - 1:
                            sel = sels[level]
                            urls = sel.xpath('.//ul[@class="mod_category_item"]//li[not(@class="selected")]//a/@href').extract()
                            level = level + 1
                            for url in urls:
                                url = Util.get_absolute_url(url, prefix_url)
                                items.append(Request(url=url, callback=self.list_parse, meta={'level':level, 'id':channel_id}))
                        elif level == size -1:
                            if self.max_update_page == self.max_number:
                                #细分到最后一层，仍大于max_broswe_page，则利用排序再进行遍历一次
                                #如果是增量更新，则只需按最新排序即可
                                urls = response.xpath('//div[@class="sort-result-container"]//div[starts-with(@class, "sort-result-l")]//a/@href').extract()
                            else:
                                urls = response.xpath('//div[@class="sort-result-container"]//div[starts-with(@class, "sort-result-l")]//a[contains(@title, "%s")]/@href' % u'更新时间').extract()
                            level = level + 1
                            for url in urls:
                                url = Util.get_absolute_url(url, prefix_url)
                                if url == request_url:
                                    #排除掉按默认排序的方式
                                    continue
                                items.append(Request(url=url, callback=self.list_parse, meta={'level':level, 'id':channel_id}))
                #遍历list列表
                sels = response.xpath('//div[@class="wrapper-piclist"]//li')
                for sel in sels:
                    mediaVideoItem = MediaVideoItem()
                    mediaItem = MediaItem()
                    mediaItem['channel_id'] = channel_id
                    #根据实际不同情况，可能有的是直接跳到媒体页，有的直接跳转到播放页
                    #为了简化问题，都作为媒体来获取结果，再对结果进行分析url,来确定跳转方向
                    results = iqiyi_extract.media_extract(sel)
                    for item in results:
                        url = item['url']
                        url = Util.get_absolute_url(url, prefix_url)
                        mediaItem['url'] = url
                        mediaItem['poster_url'] = item['poster_url'] if 'poster_url' in item else None
                        mediaVideoItem['media'] = mediaItem 
                        url_type = iqiyi_extract.url_type_resolve(url)
                        if url_type == URL_TYPE_MEDIA:
                            items.append(Request(url=url, callback=self.media_parse, meta={'item':mediaVideoItem}))
                        elif url_type == URL_TYPE_PLAY:
                            items.append(Request(url=url, callback=self.video_parse, meta={'item':mediaVideoItem}))
                        break
                #下一页
                sels = response.xpath('//div[@class="mod-page"]')
                results = iqiyi_extract.next_page_extract(sels)
                if results:
                    page = page + 1
                    url = results[0]
                    url = Util.get_absolute_url(url, prefix_url)
                    items.append(Request(url=url, callback=self.list_parse, meta={'page':page, 'id':channel_id}))
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
            channel_id_fun = mediaItem['channel_id']
            sels = response.xpath('//script[@type="text/javascript"]')
            iqiyi_extract.media_info_extract(sels, mediaItem)
            mediaItem['channel_id'] = channel_id_fun
            sels = response.xpath('//div[@itemtype="http://schema.org/ShowEpisode"]')
            iqiyi_extract.media_info_extract(sels, mediaItem)
            #播放页 - 用于直接从播放页进入
            sels = response.xpath('//div[@class="crumb_bar" or @class="mod-crumb_bar"]')
            iqiyi_extract.media_info_extract(sels, mediaItem)
            url = mediaItem['url'] if 'url' in mediaItem else ''
            url_type = iqiyi_extract.url_type_resolve(url)
            if url_type == URL_TYPE_MEDIA:
                mediaVideoItem['media'] = mediaItem
                url = mediaItem['url']
                items.append(Request(url=url, callback=self.media_parse, meta={'item':mediaVideoItem})) 
            else:
                cont_id = mediaItem['cont_id'] if 'cont_id' in mediaItem else None
                title = mediaItem['title'] if 'title' in mediaItem else None
                if cont_id and title:
                    cont_ids = cont_id.split('|')
                    cont_id = cont_ids[0]
                    cont_type = cont_ids[1]
                    '''
                    vip_url = self.vip_api % cont_id
                    try:
                        result = Util.get_url_content(vip_url)
                        if result:
                            json_data = json.loads(result)
                            if json_data['code'] == self.api_success_code:
                                mediaItem['paid'] = '1'
                            else:
                                mediaItem['paid'] = '0'
                    except Exception, e:
                        logging.log(logging.ERROR, traceback.format_exc())
                        logging.log(logging.INFO, 'vip url: %s' % vip_url)
                    '''
                    videoItems = []
                    if cont_type == 'source_id': 
                        #年份，都采用统一的api来获取
                        #years = response.xpath('//div[@data-widget="album-sourcelist"]//div[@data-widget-year="album-yearlist"]//a/@data-year').extract()
                        #快乐大本营，天天向上的等,提供的是接口
                        url = self.source_year_api % (channel_id_site, cont_id)
                        result = Util.get_url_content(url)
                        years = self.source_year_json_resolve(result, url) 
                        for year in years:
                            url = self.source_media_api % (channel_id_site, cont_id, year, channel_id_site, cont_id, year)
                            result = Util.get_url_content(url)
                            videoItems = videoItems + self.source_media_json_resolve(result, mediaItem, url)
                    elif cont_type == 'album_id':
                        #其他，其他的接口
                        page = 1
                        url = self.album_media_api % (cont_id, page, cont_id, page)
                        result = Util.get_url_content(url)
                        videoItems = videoItems + self.album_media_json_resolve(result, mediaItem, url)
                        if not videoItems:
                            #特殊节目暂时不爬取,http://www.iqiyi.com/yule/cjkgbj.html
                            #不作任何处理
                            videoItems = videoItems
                    if videoItems:
                        #设置ext_id
                        Util.set_ext_id(mediaItem, videoItems)
                        self.set_media_info(mediaItem)

                        mediaVideoItem['media'] = mediaItem
                        mediaVideoItem['video'] = videoItems
                        print mediaVideoItem
                        items.append(mediaVideoItem)
                        #self.count = self.count + 1
                        #logging.log(logging.INFO, 'count: %s' % str(self.count))             
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
            videoItems = []
            #普通媒体页
            channel_id_fun = mediaItem['channel_id']
            sels = response.xpath('//div[@id="qitancommonarea"]')
            iqiyi_extract.media_info_extract(sels, mediaItem)
            sels = response.xpath('//script[@type="text/javascript"]')
            iqiyi_extract.media_info_extract(sels, mediaItem)
            sels = response.xpath('//div[@class="mod_search_topic mb20"]')
            if not sels:
                sels = response.xpath('.//div[@id="block-B"]')
            iqiyi_extract.media_info_extract(sels, mediaItem)
            #特辑媒体页
            iqiyi_extract.media_info_extract(response, mediaItem)
            cont_id = mediaItem['cont_id'] if 'cont_id' in mediaItem else None
            title = mediaItem['title'] if 'title' in mediaItem else None
            if cont_id and title:
                cont_ids = cont_id.split('|')
                cont_id = cont_ids[0]
                cont_type = cont_ids[1]
                '''
                vip_url = self.vip_api % cont_id
                try:
                    result = Util.get_url_content(vip_url)
                    if result:
                        json_data = json.loads(result)
                        if json_data['code'] == self.api_success_code:
                            mediaItem['paid'] = '1'
                        else:
                            mediaItem['paid'] = '0'
                except Exception, e:
                    logging.log(logging.ERROR, traceback.format_exc())
                    logging.log(logging.INFO, 'vip url: %s' % vip_url)
                    logging.log(logging.INFO, '-------json data----------')
                    logging.log(logging.INFO, result)
                '''
                mediaItem['channel_id'] = channel_id_fun
                channel_id_site = iqiyi_extract.list_channels_id[channel_id_fun]
                if cont_type == 'source_id': 
                    #年份，都采用统一的api来获取
                    #years = response.xpath('//div[@data-widget="album-sourcelist"]//div[@data-widget-year="album-yearlist"]//a/@data-year').extract()
                    #快乐大本营，天天向上的等,提供的是接口
                    url = self.source_year_api % (channel_id_site, cont_id)
                    result = Util.get_url_content(url)
                    years = self.source_year_json_resolve(result, url) 
                    for year in years:
                        url = self.source_media_api % (channel_id_site, cont_id, year, channel_id_site, cont_id, year)
                        result = Util.get_url_content(url)
                        videoItems = videoItems + self.source_media_json_resolve(result, mediaItem, url)
                elif cont_type == 'album_id':
                    #其他，其他的接口
                    page = 1
                    url = self.album_media_api % (cont_id, page, cont_id, page)
                    result = Util.get_url_content(url)
                    videoItems = videoItems + self.album_media_json_resolve(result, mediaItem, url)
                    if not videoItems:
                        #特殊节目暂时不爬取,http://www.iqiyi.com/yule/cjkgbj.html
                        #不作任何处理
                        videoItems = videoItems
            if videoItems:
                #设置ext_id
                Util.set_ext_id(mediaItem, videoItems)
                
                self.set_media_info(mediaItem)

                mediaVideoItem['media'] = mediaItem
                mediaVideoItem['video'] = videoItems
                items.append(mediaVideoItem)
                #self.count = self.count + 1
                #logging.log(logging.INFO, 'count: %s' % str(self.count))    
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'media url: %s' % request_url)
        finally:
            return items
            
    def source_year_json_resolve(self, text, request_url):
        items = []
        try:
            logging.log(logging.INFO, 'source year json url: %s' % request_url)
            regex_express = '=(\{.*\})'
            regex_pattern = re.compile(regex_express)
            match_results = regex_pattern.search(text)
            if match_results:
                content = match_results.groups()[0]
                json_content = json.loads(content)
                data = json_content['data']
                if data:
                    items = items + data.keys()
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'source year json url: %s' % request_url)
            logging.log(logging.INFO, '================json content=================')
            logging.log(logging.INFO, text)
        finally:
            return items

    def source_media_json_resolve(self, text, mediaItem, request_url):
        items = []
        try:
            logging.log(logging.INFO, 'source media json url: %s' % request_url)
            regex_express = '=(\{.*\})'
            regex_pattern = re.compile(regex_express)
            match_results = regex_pattern.search(text)
            if match_results:
                content = match_results.groups()[0]
                json_content = json.loads(content)
                datas = json_content['data']
                for data in datas:
                    videoItem = VideoItem()
                    title = data['shortTitle'] if 'shortTitle' in data else None
                    if not title:
                        title = data['tvSbtitle'] if 'tvSbtitle' in data else None
                    if not title:
                        title = data['videoName']
                    videoItem['title'] = title
                    videoItem['intro'] = data['desc']
                    videoItem['url'] = data['vUrl']
                    videoItem['thumb_url'] = data['tvPicUrl']
                    videoItem['cont_id'] = data['tvId']
                    vnums = data['tvYear']
                    vnums = re.findall(r'[\d]+', vnums)
                    vnum = ''.join(vnums)
                    videoItem['vnum'] = vnum
                    self.set_video_info(videoItem)
                    items.append(videoItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'source media json url: %s' % request_url)
            logging.log(logging.INFO, '================json content=================')
            logging.log(logging.INFO, text)
        finally:
            return items
    
    def album_media_json_resolve(self, text, mediaItem, request_url):
        items = []
        content = ''
        try:
            logging.log(logging.INFO, 'album media json url: %s' % request_url)
            regex_express = '=(\{.*\})'
            regex_pattern = re.compile(regex_express)
            match_results = regex_pattern.search(text)
            if match_results:
                content = match_results.groups()[0]
                json_content = json.loads(content)
                if json_content['code'] != self.api_success_code:
                    return items
                mediaItem['vcount'] = json_content['data']['pm']
                mediaItem['latest'] = json_content['data']['ic']
                datas = json_content['data']['vlist']
                for data in datas:
                    #type:正片:1, 预告片:0
                    type = data['type']
                    if str(type) != '0':
                        videoItem = VideoItem()
                        videoItem['intro'] = data['vt']
                        videoItem['vnum'] = data['pd']
                        videoItem['thumb_url'] = data['vpic']
                        videoItem['title'] = data['vt']
                        if not videoItem['title']:
                            videoItem['title'] = data['vn']
                        videoItem['cont_id'] = data['id']
                        videoItem['url'] = data['vurl']
                        self.set_video_info(videoItem)
                        items.append(videoItem)
                #爬取下一页
                current_count = int(json_content['data']['pn'])
                page_count = int(json_content['data']['pp'])
                if current_count != 0 and current_count == page_count:
                    cont_id = json_content['data']['aid']
                    page = int(json_content['data']['pg']) + 1
                    url = self.album_media_api % (cont_id, page, cont_id, page)
                    result = Util.get_url_content(url)
                    items = items + self.album_media_json_resolve(result, mediaItem, url)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'album media json url: %s' % request_url)
            logging.log(logging.INFO, '================json content=================')
            logging.log(logging.INFO, text)
        finally:
            return items
            
    def set_media_info(self, mediaItem):
        #将cont_id中的id提取出来
        cont_id = mediaItem['cont_id']
        cont_ids = cont_id.split('|')
        cont_id = cont_ids[0]
        mediaItem['cont_id'] = cont_id
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
