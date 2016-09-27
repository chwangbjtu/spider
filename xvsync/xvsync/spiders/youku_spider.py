# -*- coding:utf-8 -*-
from scrapy.spiders import Spider
from scrapy.selector import Selector
from scrapy.http import Request
from scrapy.http import HtmlResponse
import logging
from xvsync.common.util import Util
from xvsync.common.http_download import HTTPDownload
from xvsync.items import MediaItem
from xvsync.items import MediaVideoItem
from xvsync.items import VideoItem
from xvsync.db.db_mgr import DbManager
from scrapy.utils.project import get_project_settings
import traceback
import re
import json
import string
from datetime import datetime

class youku_spider(Spider):
    name = "youku"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    site_code = "youku"
    allowed_domains = ["youku.com","v.youku.com"]
    url_prefix = 'http://www.youku.com'
    ua='Mozilla/5.0 (iPod; U; CPU iPhone OS 4_3_2 like Mac OS X; zh-cn) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8H7 Safari/6533.18.5'    

    mgr = DbManager.instance()
    os_id = mgr.get_os('web')["os_id"]
    site_id = str(mgr.get_site(site_code)["site_id"])
    channel_map = mgr.get_channel_map() #code -> id
    channel_map_rev = dict([[str(v), k] for k, v in channel_map.items()]) #id -> code
    max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')

    httpdownload = HTTPDownload()
    cat_urls = []

    def __init__(self, json_data=None, *args, **kwargs):
        super(youku_spider, self).__init__(*args, **kwargs)

        if json_data:
            data = json.loads(json_data)
            tasks=[]
            cmd = data["cmd"]

            if cmd == "assign":
                #task from command
                tasks = data["task"]
            elif cmd == "trig":
                #task from untrack
                stat = data['stat'] if 'stat' in data else None
                tasks = self.mgr.get_untrack_url(self.site_code, stat)
            elif cmd == 'carpet':
                tasks = self.mgr.get_video_url(self.site_code)
            elif cmd == "test" and 'id' in data and 'url' in data:
                #assign task by channel_id and url
                self.cat_urls.append({'id': data["id"], 'url': data["url"], 'sid': '', 'untrack_id': ''})

            for task in tasks:
                ttask={}
                ttask["url"] = task["url"]
                code = task["code"]
                ttask["id"] = self.channel_map[code]
                ttask["untrack_id"] = task["untrack_id"] if 'untrack_id' in task else None
                ttask["sid"] = task["sid"] if 'sid' in task else None
                ttask['mid'] = task['mid'] if 'mid' in task else None
                self.cat_urls.append(ttask)

    def start_requests(self):
        try:
            items = []
            if not self.cat_urls:
                cat_urls = [{'url':'http://www.youku.com/v_olist/c_85', 'id': self.channel_map['variaty']}]
                ''' 
                cat_urls = [{'url':'http://www.youku.com/v_olist/c_96', 'id': self.channel_map['movie']},
                        {'url':'http://www.youku.com/v_olist/c_97', 'id': self.channel_map['tv']},
                        {'url':'http://www.youku.com/v_olist/c_85', 'id': self.channel_map['variaty']},
                        {'url':'http://www.youku.com/v_olist/c_100', 'id':self.channel_map['cartoon']}]
                '''
                for cat in cat_urls:
                    items.append(Request(url=cat['url'], callback=self.parse_list, meta={'cat_id': cat['id'],'page':1}))
            else:
                for cat in self.cat_urls:
                    turl = Util.normalize_url(cat['url'],"youku")
                    items.append(Request(url=turl, callback=self.parse_single_episode, meta={'cat_id': cat["id"],'page':1,"untrack_id":cat["untrack_id"],"sid":cat["sid"],"mid":cat["mid"]}))
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_single_episode(self,response):
        items = []
        try:
            logging.log(logging.INFO, 'parse_single_episode: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            untrack_id = ""
            sid = ""
            mid = ""
            if "untrack_id" in response.request.meta:
                untrack_id = response.request.meta['untrack_id']
            if "sid" in response.request.meta:
                sid = response.request.meta['sid']
            if "mid" in response.request.meta:
                mid = response.request.meta['mid']

            urls = response.xpath('//div[@class="base_info"]/h1[@class="title"]/a/@href').extract()
            if urls:
                for iurl in urls:
                    surl = Util.normalize_url(iurl,"youku")
                    if surl:
                        items.append(Request(url=surl, callback=self.parse_episode_info, meta={'cat_id': cat_id,'poster_url':'','page':1,"untrack_id":untrack_id,"sid":sid,"mid":mid}))
            else:
                logging.log(logging.INFO, 'miss media page: %s' % response.request.url)
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_list(self,response):
        items = []
        try:
            logging.log(logging.INFO, 'parse_list: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']

            area_list = response.xpath('//div[@class="yk-filter-panel"]/div/label[text()="%s"]/../ul/li/a/text() ' % u"地区").extract()
            type_list = response.xpath('//div[@class="yk-filter-panel"]/div/label[text()="%s"]/../ul/li/a/text() ' % u"类型").extract()
            year_list = response.xpath('//div[@class="yk-filter-panel"]/div/label[text()="%s"]/../ul/li/a/text() ' % u"时间").extract()
            s_list = ['1','2','4','5','6']
            d_list = ['1','2','4']
 
            for area in area_list:
                for type in type_list:
                    for s_sub in s_list:
                        url_pref = response.request.url + "_a_" + area + "_g_" + type + "_u_1" + "_s_" + s_sub +"_d_1"  + ".html"
                        items.append(Request(url=url_pref, callback=self.parse_page, meta={'cat_id': cat_id,'page':1}))
            
            titem = self.parse_page(response)
            if titem:
                items.extend(titem)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

        return items 

    def parse_page(self,response):
        items = []
        try:
            logging.log(logging.INFO, 'parse_page: %s' % response.request.url)

            page = response.request.meta['page']
            logging.log(logging.INFO, 'parse_page: %s,%s' % (str(page),response.request.url))
            #if int(page) > int(self.max_update_page) and self.global_spider:
            #    logging.log(logging.INFO, 'parse_page: %s,%s' % (str(page),response.request.url))
            #    return

            cat_id = response.request.meta['cat_id']
            page = response.request.meta['page']
            items = []

            subs = response.xpath('//div[@class="yk-row yk-v-80"]/div')

            for sub in subs:
                pic_urls = sub.xpath('./div[@class="p p-small"]/div[@class="p-thumb"]/img/@src').extract()
                play_url = sub.xpath('./div[@class="p p-small"]/div[@class="p-link"]/a/@href').extract()
                pic_url = ""
                if pic_urls:
                    pic_url = pic_urls[0]
                if play_url:
                    items.append(Request(url=play_url[0].strip(),callback=self.parse_episode_info,meta={'cat_id': cat_id,'poster_url':pic_url}))

            next_page = response.xpath("//div[@class='yk-pager']/ul[@class='yk-pages']/li[@title='%s']/a/@href" % u'下一页').extract()
            if next_page:
                snext_page = next_page[0].strip()
                if snext_page.find(self.url_prefix) < 0:
                    snext_page = self.url_prefix + snext_page
                items.append(Request(url=snext_page, callback=self.parse_page, meta={'page': page+1, 'cat_id': cat_id}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_episode_info(self,response):
        try:
            logging.log(logging.INFO, 'parse_episode_info: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            poster_url = response.request.meta['poster_url']
            page_id = self.get_youku_pageid(response.request.url)
            if not page_id:
                log.error('miss content id: %s' % response.request.url)
                return

            untrack_id = ""
            sid = ""
            mid = ""
            if "untrack_id" in response.request.meta:
                untrack_id = response.request.meta['untrack_id']
            if "sid" in response.request.meta:
                sid = response.request.meta['sid']
            if "mid" in response.request.meta:
                mid = response.request.meta['mid']
            items = []

            year_list = []

            title = self.parse_title(response,cat_id)
            performer_list = self.parse_actor(response)
            director_list = self.parse_director(response)
            district_list = response.xpath('//ul[@class="baseinfo"]/li/span/label[text()="%s"]/../a/text()'  % u'地区:').extract()
            type_list = response.xpath('//ul[@class="baseinfo"]/li/span/label[text()="%s"]/../a/text()'  % u'类型:').extract()
            play_date = self.parse_play_date(response)
            total_num = self.parse_total_num(response)

            year_list = response.xpath('//div[@class="mod plot"]/ul[@class="filter"]/li[@class="v-year"]/a/em/text()').extract()
            pers = Util.join_list_safely(performer_list)
            dirs = Util.join_list_safely(director_list)
            types = Util.join_list_safely(type_list)

            #text
            text = response.xpath('//div[@class="detail"]/span/text()').extract()

            videoitems = []

            ep_item = MediaItem()
            if title:
                ep_item["title"] = title[0].strip()
            if pers:
                ep_item["actor"] = pers
            if dirs > 0:
                ep_item["director"] = dirs
            if types:
                ep_item["type"] = types
            if district_list:
                ep_item["district"] = district_list[0].strip()
            if play_date:
                ep_item["release_date"] = Util.str2date(play_date)
            if total_num:
                ep_item["vcount"] = total_num

            ep_item["site_id"] = self.site_id
            ep_item["channel_id"] = cat_id
            ep_item["poster_url"] = poster_url
            ep_item["url"] = Util.normalize_url(response.request.url,"youku")
            if text:
                ep_item["intro"] = text[0].strip()
            ep_item["cont_id"] = page_id
            ep_item["info_id"] = Util.md5hash(Util.summarize(ep_item))

            mvitem = MediaVideoItem();
            if mid:
                mvitem['mid'] = mid
            mvitem["media"] = ep_item;
            if untrack_id:
                mvitem["untrack_id"] = untrack_id
            if sid:
                mvitem["sid"] = sid

            video_list = self.parse_video_item(response, cat_id, ep_item["title"], page_id)
            mvitem['video'] = video_list
            Util.set_ext_id(mvitem["media"], mvitem["video"])
            items.append(mvitem)

        except Exception as e: 
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_video_item_media(self,code,pn):
        videoitems = []
        try:
            getlist_url = "http://v.youku.com/x_getAjaxData?md=showlistnew&vid=%s&pl=100&pn=%d" % (code,pn)
            urllist_info = self.httpdownload.get_data(getlist_url,ua=self.ua)
            if urllist_info:
                try:
                    json_data = json.loads(urllist_info)
                except Exception as e:
                    return videoitems
                if json_data and "showlistnew" in json_data:
                    if json_data["showlistnew"]:
                        items = json_data["showlistnew"]["items"]
                        vnum_name = ""
                        if type(items)==list:
                            videoseq = set()
                            videostage = set()
                            for item in items:
                                if "preview" in item:
                                    continue
                                videoseq.add(item["show_videoseq"])
                                videostage.add(item["show_videostage"])
                            if len(videoseq)>len(videostage):
                                vnum_name = "show_videoseq"
                            else:
                                vnum_name = "show_videostage"
                            for item in items:
                                if "preview" in item:
                                    continue
                                if "videoid" not in item:
                                    continue
                                vitem = VideoItem()
                                vitem["url"] = "http://v.youku.com/v_show/id_%s.html" % item["videoid"]
                                vitem["vnum"] = item[vnum_name]
                                vitem["title"] = item["title"]
                                vitem["os_id"] = self.os_id
                                vitem["ext_id"] = Util.md5hash(vitem["url"])
                                vitem["site_id"] = self.site_id
                                vitem["cont_id"] = item["videoid"]
                                videoitems.append(vitem)
                        elif type(items)==dict:                    
                            videoseq = set()
                            videostage = set()
                            for k in items:
                                item = items[k] 
                                if "preview" in item:
                                    continue
                                videoseq.add(item["show_videoseq"])
                                videostage.add(item["show_videostage"])
                            if len(videoseq)>len(videostage):
                                vnum_name = "show_videoseq"
                            else:
                                vnum_name = "show_videostage"
                            for k in items:
                                item = items[k]
                                if "preview" in item:
                                    continue
                                if "videoid" not in item:
                                    continue
                                vitem = VideoItem()
                                vitem["url"] = "http://v.youku.com/v_show/id_%s.html" % item["videoid"]
                                vitem["vnum"] = item[vnum_name]
                                vitem["title"] = item["title"]
                                vitem["os_id"] = self.os_id
                                vitem["ext_id"] = Util.md5hash(vitem["url"])
                                vitem["site_id"] = self.site_id
                                vitem["cont_id"] = item["videoid"]
                                videoitems.append(vitem)
                        else:
                            logging.log(logging.ERROR, getlist_url)
                            pass
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return videoitems

    def parse_video_item(self, response, cat_id, title, media_page_id):
        videoitems = []
        try:
            play_url = self.parse_play_url(response)
            if play_url:
                url = Util.normalize_url(play_url[0], "youku")
                cont_id = self.get_youku_showid(url)
                i=1
                while True:
                    item = self.parse_video_item_media(cont_id,i)
                    if item:
                        videoitems = videoitems + item
                        i = i+1
                    else:
                        break
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return videoitems

    def parse_title(self,response,cat_id):
        title = []
        try:
            #title = response.xpath('//div[@id="title_wrap"]/div[@id="title"]/h1/span[@class="name"]/text()').extract()
            title = response.xpath('//div[@id="title_wrap"]/div[@id="title"]/div[@class="base"]/h1/span[@class="name"]/text()').extract()
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

        return title

    def parse_actor(self,response):
        performer_list = []
        try:
            performer_list = response.xpath('//ul[@class="baseinfo"]/li/span/label[text()="%s"]/../a/text()'  % u'主演:').extract()
            if not performer_list:
                performer_list = response.xpath('//ul[@class="baseinfo"]/li/span/label[text()="%s"]/../a/text()'  % u'主持人:').extract()
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return performer_list

    def parse_director(self,response):
        director_list = []
        try:
            director_list = response.xpath('//ul[@class="baseinfo"]/li/span/label[text()="%s"]/../a/text()'  % u'导演:').extract()
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

        return director_list

    def parse_play_url(self,response):
        play_list = []
        try:
            play_list = response.xpath("//div[@class='showInfo poster_w yk-interact']/ul[@class='baseaction']/li[@class='action']/a/em[text()='%s']/../@href" % u"播放正片").extract()
            if not play_list:
                play_list = response.xpath("//div[@class='showInfo poster_w yk-interact']/ul[@class='baseaction']/li[@class='action']/a/em[text()='%s']/../@href" % u"播放").extract()
            if not play_list:
                play_list = response.xpath("//div[@class='showInfo poster_w yk-interact']/ul[@class='baseaction']/li[@class='action']/a/em[text()='%s']/../@href" % u"免费试看").extract()
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return play_list

    def get_youku_pageid(self,url):
        id = ""
        try:
            #http://www.youku.com/show_page/id_zed6b4c7497b811e4b522.html
            r = re.compile(r'http://www.youku.com/show_page/id_([^_]+).*\.html')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return id

    def get_youku_showid(self,url):
        #http://v.youku.com/v_show/id_XNzUyMDUwOTAw.html
        id = ""
        try:
            r = re.compile(r'http://v.youku.com/v_show/id_([^/]+).*\.html')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return id

    def parse_play_date(self,response):
        res = []
        strdate = None
        try:
            res = response.xpath('//ul[@class="baseinfo"]/li/span/label[text()="%s"]/../text()'  % u'优酷上映:').extract()
            if not res:
                res = response.xpath('//ul[@class="baseinfo"]/li/span/label[text()="%s"]/../text()'  % u'优酷开播:').extract()
            if not res:
                res = response.xpath('//ul[@class="baseinfo"]/li/span/label[text()="%s"]/../text()'  % u'上映:').extract()
            if res:
                strdate = res[0]
        except Exception as e:
            pass
        return strdate

    def parse_total_num(self,response):
        res = None
        try:
            info_list = response.xpath('//div[@class="basenotice"]/text()').extract()
            for info in info_list:
                r = re.compile(ur'.*%s(\d+)%s.*' % (u'共',u'集'))
                m = r.search(info)
                if m:
                    return m.group(1)
        except Exception as e:
            pass
        return res
