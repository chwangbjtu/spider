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
from xvsync.extract.letv_extract import letv_extract 
from xvsync.common.util import Util
from xvsync.db.db_mgr import DbManager

class letv_spider(Spider):
    '''
        letv爬虫流程：
        (1)list列表页 -> 播放页 -> 媒体页
        (2)播放页 -> 媒体页
        注意：乐视需要分标签进行爬取
    '''
    site_code = 'letv'
    name = site_code
    mgr = DbManager.instance()
    max_mark_depth = 5 
    max_number = 100000
    list_json_prefix_url = 'http://list.letv.com/apin/chandata.json'
    zongyi_album_api = 'http://api.letv.com/mms/out/albumInfo/getVideoListByIdAndDate?&year=%s&month=%s&id=%s'
    # other_album_api = 'http://api.mob.app.letv.com/play/vlist?pid=%s&pagenum=%s'
    other_album_api = 'http://api.mob.app.letv.com/play/cards?pid=%s&version=6.2.2&pagenum=%s'
    #通过json传递的参数
    json_data = None

    def __init__(self, json_data=None, *args, **kwargs):
        super(letv_spider, self).__init__(*args, **kwargs)
        if json_data:
            self.json_data = json.loads(json_data)

    def start_requests(self):
        items = []
        try:
            self.load_member_variable()
            if self.json_data:
                items = items + self.load_video_urls()
            else:
                url = 'http://list.letv.com'
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
            for list_channel in letv_extract.list_channels:
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
            channel_id = response.request.meta['id'] if 'id' in response.request.meta else None
            if level == 0:
                #当前处在第一频道层，只提取电影、电视剧、动漫、综艺频道
                sels = response.xpath('.//div[normalize-space(@class)="column_menu"]/*[@class="channel_tit"]//li[@data-channel]')
                level = level + 1
                for list_channel in letv_extract.list_channels:
                    urls = sels.xpath('.//a[text()="%s"]/@href' % list_channel).extract()
                    if urls:
                        url = urls[0]
                        url = Util.get_absolute_url(url, prefix_url)
                        items.append(Request(url=url, callback=self.list_parse, meta={'level':level, 'id':list_channel}))
            else:
                #对当前层再进行细分
                sels = response.xpath('.//div[normalize-space(@class)="column_menu"]/ul[@data-statectn="left-biaoqian"]/li')
                if self.max_mark_depth > 0:
                    size = self.max_mark_depth if self.max_mark_depth < len(sels) else len(sels)
                else:
                    size = len(sels)
                if level <= size:
                    sel = sels[level - 1]
                    level = level + 1
                    url_sels = sel.xpath('.//dd/a') 
                    for url_sel in url_sels:
                        labels = url_sel.xpath('./b/text()').extract()
                        if not labels:
                            continue
                        label = labels[0]
                        if label in letv_extract.ignore_channels:
                            continue
                        urls = url_sel.xpath('./@href').extract()
                        if not urls:
                            continue
                        url = urls[0]
                        url = Util.get_absolute_url(url, prefix_url)
                        items.append(Request(url=url, callback=self.list_parse, meta={'level':level, 'id':channel_id}))
                #获取当前层的所有list数据
                #在URL中提取之前勾选的过滤条件
                regex_pattern = re.compile('http://list.letv.com/listn/(.*)\.html')
                match_result = regex_pattern.search(request_url)
                filter_str = ''
                if match_result:
                    filter_str = match_result.groups()[0]
                list_json_postfix_url = '?'
                regex_pattern = re.compile('([a-zA-Z]+)([\d,]+)')
                filters = regex_pattern.findall(filter_str)
                for item in filters:
                    if item[0] != 'o':
                        list_json_postfix_url = list_json_postfix_url + '%s=%s&' % (item[0], item[1])
                #按照排序方式再进行细分一次
                page = response.request.meta['page'] if 'page' in response.request.meta else 1  
                if self.max_update_page == self.max_number:
                    sels = response.xpath('//div[@class="sort_navy"]//a/@data-order')
                else:
                    sels = response.xpath('//div[@class="sort_navy"]//a[normalize-space(text())="%s"]/@data-order' % u'最新更新')
                for sel in sels:
                    list_json_postfix_url_temp = list_json_postfix_url
                    filters = regex_pattern.findall(sel.extract())
                    for item in filters:
                        list_json_postfix_url_temp = list_json_postfix_url_temp + '%s=%s&' % (item[0], item[1])
                    if list_json_postfix_url_temp != '?':
                        url = self.list_json_prefix_url + list_json_postfix_url_temp + 'p=%s' % page
                        items.append(Request(url=url, callback=self.list_json_parse, meta={'page':page, 'id':channel_id, 'postfix_url':list_json_postfix_url_temp, 'url':url}))
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'url: %s' % request_url)
        finally:
            return items

    def list_json_parse(self, response):
        items = []
        try:
            origin_url = response.request.meta['url']
            request_url = response.request.url
            logging.log(logging.INFO, 'json api url: %s' % request_url)
            page = response.request.meta['page'] if 'page' in response.request.meta else 1
            if page > self.max_update_page:
                return items
            channel_id = response.request.meta['id'] if 'id' in response.request.meta else None
            list_json_postfix_url = response.request.meta['postfix_url'] if 'postfix_url' in response.request.meta else None
            json_datas = json.loads(response.body)
            videos = []
            if json_datas:
                videos = json_datas['data_list'] if 'data_list' in json_datas else []
            if videos:
                #表明仍有下一页
                video_url = 'http://www.letv.com/ptv/vplay/%s.html'
                for item in videos:
                    mediaVideoItem = MediaVideoItem()
                    mediaItem = MediaItem()
                    mediaItem['channel_id'] = channel_id
                    if 'rating' in item and item['rating']:
                        mediaItem['score'] = item['rating']
                    subCategoryName = item['subCategoryName']
                    mediaItem['type'] =subCategoryName.replace(',', ';') 
                    mediaVideoItem['media'] = mediaItem
                    release_date = item['releaseDate']
                    if release_date:
                        release_date = float(release_date)
                        if release_date > 0:
                            release_date = release_date / 1000
                            release_date = time.localtime(release_date)
                            release_date = '%s-%s-%s' % (release_date.tm_year, release_date.tm_mon, release_date.tm_mday)
                            mediaItem['release_date'] = Util.str2date(release_date) 
                    vid = ''
                    if 'vids' in item:
                        vids = item['vids']
                        vids = vids.split(',')
                        vid = vids[0]
                    elif 'vid' in item:
                        vid = item['vid']
                    if vid:
                        url = video_url % vid 
                        items.append(Request(url=url, callback=self.video_parse, meta={'item':mediaVideoItem}))

                #下一页
                page = page + 1
                url = self.list_json_prefix_url + list_json_postfix_url + 'p=%s' % page
                items.append(Request(url=url, callback=self.list_json_parse, meta={'page':page, 'id':channel_id, 'postfix_url':list_json_postfix_url, 'url':url}))
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'json api url: %s' % request_url)
            logging.log(logging.INFO, 'origin url: %s' % origin_url)
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
            sels = response.xpath('//script[@type="text/javascript"]')
            letv_extract.media_info_extract(sels, mediaItem)
            
            sels = None
            if not sels:
                #Detail电视剧、综艺、动漫
                sels = response.xpath('//div[@data-statectn="play_info"]//ul[@class="intro_box"]')
            if not sels:
                #Info:普通影片,动漫
                sels = response.xpath('//div[@data-statectn="newplay_info"]//ul[@class="info_list"]')
            if not sels:
                #收费影片
                sels = response.xpath('//div[@class="Player"]//span[@class="video_info"]')
            
            if sels:
                results = letv_extract.media_extract(sels)
                if results:
                    item = results[0]
                    url = Util.get_absolute_url(item['url'], prefix_url)
                    mediaItem['url'] = url
                    mediaVideoItem['media'] = mediaItem
                    items.append(Request(url=url, callback=self.media_parse, meta={'item':mediaVideoItem}))
            
            if not items:
                #视频播放页找不到媒体页地址,尝试直接采用接口爬取
                if 'cont_id' in mediaItem:
                    self.api_parse(mediaVideoItem)
                else:
                    logging.log(logging.INFO, '该视频播放页找不到媒体页地址,也无法直接采用接口: %s' % request_url)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'video url: %s' % request_url)
        finally:
            return items

    def api_parse(self, mediaVideoItem):
        items = []
        try:
            mediaItem = mediaVideoItem['media']
            logging.log(logging.INFO, 'api parse pid: %s' % mediaItem['cont_id'])
            self.api_media_info(mediaItem)
            if 'title' in mediaItem:
                videoItems = []
                pagenum = 1
                while True:
                    videos_url = self.other_album_api % (mediaItem['cont_id'], pagenum)
                    result = Util.get_url_content(videos_url)
                    page_items = self.other_album_resolve(text=result, meta={'url':videos_url, 'pagenum':pagenum})
                    if not page_items:
                        break
                    videoItems = videoItems + page_items
                    pagenum = pagenum + 1
                if videoItems:
                    if 'url' not in mediaItem:
                        mediaItem['url'] = videoItems[0]['url']
                    Util.set_ext_id(mediaItem, videoItems)
                    self.set_media_info(mediaItem)
                    mediaVideoItem['media'] = mediaItem
                    mediaVideoItem['video'] = videoItems
                    items.append(mediaVideoItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    def api_media_info(self, mediaItem):
        try:
            api_url = self.other_album_api % (mediaItem['cont_id'], 1)
            result = Util.get_url_content(api_url)
            if not result:
                return
            json_result = json.loads(result)
            desc = json_result['body']['intro']['desc']
            mediaItem['title'] = desc['nameCn']
            if 'directory' in desc:
                director_list = desc['directory'].split("，")
                mediaItem['director'] = Util.join_list_safely(director_list)
            if 'starring' in desc:
                actor_list = desc['starring'].split("，")
                mediaItem['actor'] = Util.join_list_safely(actor_list)
            if 'subCategory' in desc:
                type_list = desc['subCategory'].split("，")
                desc['type'] = Util.join_list_safely(type_list)
            if 'area' in desc:
                district_list = desc['area'].split("，")
                mediaItem['district'] = Util.join_list_safely(district_list)
            if 'releaseDate' in desc:
                mediaItem['release_date'] = Util.str2date(str(desc['releaseDate']))

        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())


    def media_parse(self, response):
        items = []
        try:
            request_url = response.request.url
            logging.log(logging.INFO, 'media url: %s' % request_url)
            prefix_url = Util.prefix_url_parse(request_url)
            mediaVideoItem = response.request.meta['item'] if 'item' in response.request.meta else None
            mediaItem = mediaVideoItem['media'] if 'media' in mediaVideoItem else MediaItem()
            sels = response.xpath('//script[@type="text/javascript"]')
            letv_extract.media_info_extract(sels, mediaItem)
            sels = response.xpath('//div[@class="play"]')
            letv_extract.media_info_extract(sels, mediaItem)

            sels = response.xpath('//dl[@class="textInfo"]') 
            if sels:
                #电视剧、综艺、动漫
                letv_extract.media_info_extract(sels, mediaItem)
            else:
                #电影
                sels = response.xpath('//div[@class="detail"]') 
                letv_extract.media_info_extract(sels, mediaItem)

            #获取正片的url
            videoItems = []
            if u'电影' == mediaItem['channel_id']:
                pagenum = 1
                videos_url = self.other_album_api % (mediaItem['cont_id'], pagenum)
                result = Util.get_url_content(videos_url)
                page_items = self.other_album_resolve(text=result, meta={'url':videos_url, 'pagenum':pagenum})
                videoItems = page_items
            #综艺
            elif u'综艺' == mediaItem['channel_id']:
                sels = response.xpath('//div[@class="listTab"]//div[@data-statectn="n_click"]')
                if sels:
                    year_month_sels = sels.xpath('.//a')
                    for year_month_sel in year_month_sels:
                        years = year_month_sel.xpath('./@list-year').extract()
                        months = year_month_sel.xpath('./@list-month').extract()
                        year = None
                        month = None
                        if years:
                            year = years[0]
                        if months:
                            month = months[0]
                        if year and month:
                            videos_url = self.zongyi_album_api % (year, month, mediaItem['cont_id']) 
                            result = Util.get_url_content(videos_url)
                            videoItems = videoItems + self.zongyi_album_resolve(text=result, meta={'url':videos_url, 'year':year, 'month':month})
            elif mediaItem['channel_id'] in [u'电视剧', u'动漫']:
                pagenum = 1 
                while True:
                    videos_url = self.other_album_api % (mediaItem['cont_id'], pagenum)
                    result = Util.get_url_content(videos_url)
                    page_items = self.other_album_resolve(text=result, meta={'url':videos_url, 'pagenum':pagenum})
                    if not page_items:
                        break
                    videoItems = videoItems + page_items
                    pagenum = pagenum + 1

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

    def zongyi_album_resolve(self, text, meta):
        items = []
        try:
            if not text:
                return items
            request_url = meta['url'] if 'url' in meta else None
            logging.log(logging.INFO, 'json url: %s' % request_url)
            prefix_url = Util.prefix_url_parse(request_url)
            year = meta['year'] if 'year' in meta else None
            month = meta['month'] if 'month' in meta else None
            if year and month:
                videos_json = json.loads(text)
                videos = videos_json['data']
                if year in videos:
                    videos = videos[year]
                    if month in videos:
                        videos = videos[month]
                        video_url = 'http://www.letv.com/ptv/vplay/%s.html' 
                        for video in videos:
                            videoItem = VideoItem()
                            videoItem['cont_id'] = video['id']
                            videoItem['title'] = video['subTitle']
                            if video['issue']:
                                videoItem['vnum'] = video['issue']
                            videoItem['thumb_url'] = video['pic']
                            url = video_url % videoItem['cont_id']
                            videoItem['url'] = url
                            self.set_video_info(videoItem)
                            items.append(videoItem)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'json url: %s' % request_url)
            logging.log(logging.INFO, '===================content===================') 
            logging.log(logging.INFO, text)
        finally:
            return items

    def other_album_resolve(self, text, meta):
        items = []
        try:
            if not text:
                return items
            request_url = meta['url'] if 'url' in meta else None
            logging.log(logging.INFO, 'json url: %s' % request_url)
            prefix_url = Util.prefix_url_parse(request_url)
            video_url = 'http://www.letv.com/ptv/vplay/%s.html' 
            videos_json = json.loads(text)
            videos = videos_json['body']['videoList']['videoList']['videoInfo'] 
            for video in videos:
                try:
                    videoItem = VideoItem()
                    videoItem['cont_id'] = video['vid']
                    if video['episode']:
                        try:
                            vnum = int(float(video['episode']))
                            videoItem['vnum'] = vnum
                        except Exception, e:
                            vnum = int(float(video['porder']))
                            videoItem['vnum'] = vnum
                    videoItem['title'] = video['subTitle']
                    if not videoItem['title']:
                        videoItem['title'] = '第%s集' % videoItem['vnum']
                    for key in video['picAll']:
                        thumb_url = video['picAll'][key]
                        videoItem['thumb_url'] = thumb_url
                        break
                    url = video_url % videoItem['cont_id']
                    videoItem['url'] = url
                    self.set_video_info(videoItem)
                    items.append(videoItem)
                except Exception, e:
                    continue
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, 'json url: %s' % request_url)
            logging.log(logging.INFO, '===================content===================') 
            logging.log(logging.INFO, text)
        finally:
            return items

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

    #def template(self):
    #    items = []
    #    try:
    #        return items
    #    except Exception, e:
    #        logging.log(logging.ERROR, traceback.format_exc())
    #    finally:
    #        return items
