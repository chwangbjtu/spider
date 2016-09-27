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

class wasu_spider(Spider):
    name = "wasu"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    site_code = "wasu"
    site_id = ""   #wasu
    allowed_domains = ["www.wasu.cn","all.wasu.cn"]
    url_prefix = 'http://www.wasu.cn'
    site_name = Util.guess_site(url_prefix)
    
    mgr = DbManager.instance()
    os_id = mgr.get_os('web')["os_id"]
    site_id = str(mgr.get_site(site_code)["site_id"])
    channel_map = {}
    channel_map = mgr.get_channel_map()
    max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
    global_spider = True

    httpdownload = HTTPDownload()

    channel_info = {}
    test_page_url = None
    test_channel_id = None
    
    album_api = 'http://www.wasu.cn/Column/ajax_list?uid=%s&y=%s&mon=%s'

    def __init__(self, json_data=None, *args, **kwargs):
        super(wasu_spider, self).__init__(*args, **kwargs)
        cat_urls = []
        tasks = None
        if json_data:
            data = json.loads(json_data)
            if "type" in data:
                spider_type = data["type"]
                if spider_type != "global":
                    self.global_spider = False
            tasks=[]
            ttask={}
            if "id" in data and "url" in data:
                ttask["id"] = data["id"]
                ttask["url"] = data["url"]
                ttask["sid"] = ""
                ttask["untrack_id"] = ""
                cat_urls.append(ttask)

            cmd = data["cmd"]
            if cmd == "assign":
                tasks = data["task"]
            elif cmd == "trig":
                stat = data['stat'] if 'stat' in data else None
                tasks = self.mgr.get_untrack_url(self.site_code, stat)
            elif cmd == 'carpet':
                tasks = self.mgr.get_video_url(self.site_code)
            elif cmd == "test" and 'id' in data and 'url' in data:
                self.test_page_url = data["url"]
                self.test_channel_id = data["id"]
            if tasks:
                for task in tasks:
                    ttask={}
                    ttask["url"] = task["url"]
                    code = task["code"]
                    ttask["id"] = self.channel_map[code]
                    ttask["untrack_id"] = task["untrack_id"] if 'untrack_id' in task else None
                    ttask["sid"] = task["sid"] if 'sid' in task else None
                    ttask['mid'] = task['mid'] if 'mid' in task else None
                    cat_urls.append(ttask)

        self._cat_urls = []
        if cat_urls:
            self._cat_urls = cat_urls

    def start_requests(self):
        try:
            items = []

            self.movie_id = str(self.mgr.get_channel('电影')["channel_id"])
            self.tv_id = str(self.mgr.get_channel('电视剧')["channel_id"])
            self.variety_id = str(self.mgr.get_channel('综艺')["channel_id"])
            self.cartoon_id = str(self.mgr.get_channel('动漫')["channel_id"])

            self.channel_info = {self.movie_id:u"电影",self.tv_id:u"电视剧",self.variety_id:u"综艺",self.cartoon_id:u"动漫"}

            if self.test_page_url:
                turl = Util.normalize_url(self.test_page_url,"wasu")
                items.append(Request(url=self.test_page_url, callback=self.parse_page, meta={'cat_id': self.test_channel_id,'page':1}))
                return items

            if not self._cat_urls:
                if self.global_spider:
                    cat_urls = [{'url':'http://all.wasu.cn/index/cid/1','id':self.movie_id},
                            {'url':'http://all.wasu.cn/index/cid/11','id':self.tv_id},
                            {'url':'http://all.wasu.cn/index/cid/37','id':self.variety_id},
                            {'url':'http://all.wasu.cn/index/cid/19','id':self.cartoon_id}]
                for cat in cat_urls:
                    items.append(Request(url=cat['url'], callback=self.parse_type, meta={'cat_id': cat['id'],'page':1}))
            else:
                for cat in self._cat_urls:
                    turl = Util.normalize_url(cat['url'],"wasu")
                    items.append(Request(url=turl, callback=self.parse_single_episode, meta={'cat_id': cat["id"],'page':1,"poster_url":"","untrack_id":cat["untrack_id"],"sid":cat["sid"],"mid":cat["mid"]}))
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_type(self,response):
        items = []
        try:
            #logging.log(logging.INFO, 'parse_type: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="ws_all_span"]/ul/li[1]/a/@href').extract()
            for sub in subs:
                items.append(Request(url=sub, callback=self.parse_tag, meta={'cat_id': cat_id,'page':1}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_tag(self,response):
        items = []
        try:
            logging.log(logging.INFO, 'parse_tag: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="ws_all_span"]/ul/li[2]/a/@href').extract()
            for sub in subs:
                items.append(Request(url=sub, callback=self.parse_area, meta={'cat_id': cat_id,'page':1}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_area(self,response):
        items = []  
        try:
            logging.log(logging.INFO, 'parse_area: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="ws_all_span"]/ul/li[3]/a/@href').extract()
            for sub in subs:
                items.append(Request(url=sub, callback=self.parse_time, meta={'cat_id': cat_id,'page':1}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_time(self,response):
        items = []
        try:
            logging.log(logging.INFO, 'parse_time: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="ws_all_span"]/ul/li[4]/a/@href').extract()
            for sub in subs:
                items.append(Request(url=sub, callback=self.parse_sort, meta={'cat_id': cat_id,'page':1}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_sort(self,response):
        items = []
        # 默认最近更新
        time_url = response.request.url
        try:
            logging.log(logging.INFO, 'parse_sort: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="pxfs"]/div[@class="l"]/ul/li/a/@href').extract()
            # 优先爬取最近更新
            subs.insert(0, time_url)
            for sub in subs:
                items.append(Request(url=sub, callback=self.parse_page, meta={'cat_id': cat_id,'page':1}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_page(self,response):
        items = []
        try:
            cat_id = response.request.meta['cat_id']
            page = response.request.meta['page']
            logging.log(logging.INFO, 'parse_page: %s,%s' % (response.request.url,page)) 
            #if int(page) > int(self.max_update_page) and not self.global_spider:
            #    return
            
            items = []
            
            play_url = ""
            subs = response.xpath('//div[@class="ws_row mb25"]/div')
            #if not subs:
            #    subs = response.xpath('./div/div[@class="ws_row mb25"]/div[@class=" col2 mb20"]/div[@class="hezhip]')
            
            for sub in subs:
                play_urls = sub.xpath('./div/div[@class="v mb5"]/div[@class="v_link"]/a/@href').extract()
                pic_urls = sub.xpath('./div/div[@class="v mb5"]/div[@class="v_img"]/img/@src').extract()
                if not play_urls:
                    play_urls = sub.xpath('./div/div[@class="v mb5"]/div[@class="p_link"]/a/@href').extract()
                if not pic_urls:
                    pic_urls = sub.xpath('./div/div[@class="v mb5"]/div[@class="p_img"]/img/@src').extract()
                pic_url = ""
                if pic_urls:
                    pic_url = pic_urls[0]
                if play_urls:
                    rplay_url = play_urls[0].strip()
                    if '/Play/show' in rplay_url:
                    #if int(cat_id) == int(self.movie_id):
                        items.append(Request(url=rplay_url,callback=self.parse_single_episode,meta={'cat_id': cat_id,'poster_url':pic_url,'untrack_id':'','sid':''}))
                    else:
                        items.append(Request(url=rplay_url,callback=self.parse_episode_info,meta={'cat_id': cat_id,'poster_url':pic_url,'untrack_id':'','sid':''}))

            next_page = response.xpath('//div[@class="item_page"]/a[text()="%s"]/@href' % u'下一页').extract()
            page_prefix = "http://all.wasu.cn"
            if next_page:
                snext_page = next_page[0].strip()
                if snext_page.find(page_prefix) < 0:
                    snext_page = page_prefix + snext_page
                items.append(Request(url=snext_page, callback=self.parse_page, meta={'page': page+1, 'cat_id': cat_id}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_single_episode(self,response):
        items = []
        try:
            logging.log(logging.INFO, 'parse_single_episode: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            untrack_id = response.request.meta['untrack_id']
            sid = response.request.meta['sid']
            mid = response.request.meta['mid'] if 'mid' in response.request.meta else ""
            poster_url = response.request.meta['poster_url']
            #解析媒体页信息
            urls = response.xpath('//div[@class="play_site mb10"]/div[1]/h3/a/@href').extract()
            if not urls:
                #通过标题不能进入媒体页，要通过分级目录
                turls = response.xpath('//div[@class="play_site mb10"]/div[1]/div[@class="play_seat"]/a/@href').extract()
                for turl in turls:
                    tiurl = self.get_episode_url(turl)
                    if tiurl:
                        urls.append(tiurl)
            if urls:
                for iurl in urls:
                    if not Util.guess_site(iurl):
                        iurl = self.url_prefix + iurl
                    surl = Util.normalize_url(iurl,"wasu")
                    if surl and self.site_name == Util.guess_site(surl):
                        items.append(Request(url=surl, callback=self.parse_episode_info, meta={'cat_id': cat_id,'poster_url':poster_url,'page':1,"untrack_id":untrack_id,"sid":sid,"mid":mid}))
            else:
                #电影视频，没有媒体页，只有播放页
                #动漫电影，没有媒体页，只有播放页
                titems = self.parse_play_page(response)
                for item in titems:
                    if mid:
                        item['mid'] = mid
                    items.append(item)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_episode_info(self,response):
        items = []
        try:
            request_url = response.request.url
            logging.log(logging.INFO, 'parse_episode_info: %s' % request_url)
            cat_id = response.request.meta['cat_id']
            poster_url = response.request.meta['poster_url']
            untrack_id = ""
            sid = ""
            mid = ""
            if "untrack_id" in response.request.meta:
                untrack_id = response.request.meta['untrack_id']
            if "sid" in response.request.meta:
                sid = response.request.meta['sid']
            if "mid" in response.request.meta:
                mid = response.request.meta['mid']
                
            #此处因考虑不想过多改变原来的程序结构，其实这些属性可以通过接口获得
            #http://clientapi.wasu.cn/Phone/vodinfo/id/6786984
            title_list = response.xpath('//div[@class="cloudotm1"]/p[1]/a/text()').extract()
            if not title_list:
                title_list = response.xpath('//div[@class="tele_txts"]/h4[1]/a/text()').extract()
            
            director_list = response.xpath('//div[@class="right_fl"]//*[contains(text(),"%s")]/a/text()' % u'导演').extract()
            if not director_list:
                director_list = response.xpath('//div[@class="tele_txts"]//*[contains(text(),"%s")]/a/text()' % u'导演').extract()
            performer_list = response.xpath('//div[@class="right_fl"]//*[contains(text(),"%s")]/a/text()' % u'演员').extract()
            if not performer_list:
                performer_list = response.xpath('//div[@class="tele_txts"]//*[contains(text(),"%s")]/a/text()' % u'演员').extract()
            area_list = response.xpath('//div[@class="right_fl"]//*[contains(text(),"%s")]/a/text()' % u'地区').extract()
            if not area_list:
                area_list = response.xpath('//div[@class="tele_txts"]//*[contains(text(),"%s")]/a/text()' % u'地区').extract()
            tag_list = response.xpath('//div[@class="right_fl"]//*[contains(text(),"%s")]/a/text()' % u'标签').extract()
            if not tag_list:
                tag_list = response.xpath('//div[@class="right_fl"]//*[contains(text(),"%s")]/a/text()' % u'类型').extract()
            if not tag_list:
                tag_list = response.xpath('//div[@class="tele_txts"]//*[contains(text(),"%s")]/a/text()' % u'标签').extract()
            if not tag_list:
                tag_list = response.xpath('//div[@class="tele_txts"]//*[contains(text(),"%s")]/a/text()' % u'类型').extract()
            year_list = response.xpath('//div[@class="right_fl"]//*[contains(text(),"%s")]/a/text()' % u'年份').extract()
            if not year_list:
                year_list = response.xpath('//div[@class="tele_txts"]//*[contains(text(),"%s")]/a/text()' % u'年份').extract()
            pers = Util.join_list_safely(performer_list)
            dirs = Util.join_list_safely(director_list)
            areas = Util.join_list_safely(area_list)
            tags = Util.join_list_safely(tag_list)
            
            #text
            text = response.xpath('//div[@class="right_fl"]/p/span[@id="infoS"]/text()').extract()
            if text:
                text = response.xpath('//div[@class="tele_b_otm"]/p/span[@id="infoS"]/text()').extract()

            play_url = ""
            mvitem = self.compose_mvitem(response,title_list,pers,dirs,response.request.url,cat_id,poster_url,text)
            if mid:
                mvitem['mid'] = mid

            if mvitem and 'video' in mvitem and 'url' in mvitem['video'][0] and mvitem['video'][0]['url']:
                mvitem['media']['type'] = tags
                mvitem['media']['district'] = areas
                if year_list:
                    mvitem['media']['release_date'] = Util.str2date(year_list[0])
                tlen = len(mvitem['video'])
                logging.log(logging.INFO, "++++url: %s video len: %d " % (response.request.url,tlen))
                items.append(mvitem)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_play_page(self,response):
        items = []
        try:
            cat_id = response.request.meta['cat_id']
            poster_url = response.request.meta['poster_url']
            untrack_id = ""
            sid = ""
            if "untrack_id" in response.request.meta:
                untrack_id = response.request.meta['untrack_id']
            if "sid" in response.request.meta:
                sid = response.request.meta['sid']

            title_list = response.xpath('//div[@class="play_site mb10"]/div/h3/text()').extract()
            director_list  = response.xpath('//div[@class="play_information play_intro"]/div[@class="play_information_t"]/div[@class="r"]/div/span[text()="%s"]/../a/text()' % u'导演：').extract()
            performer_list  = response.xpath('//div[@class="play_information play_intro"]/div[@class="play_information_t"]/div[@class="r"]/div/div/span[text()="%s"]/../../div[@class="r"]/a/text()' % u'主演：').extract()
            tag_list = response.xpath('//div[@class="play_information play_intro"]/div[@class="play_information_t"]/div[@class="r"]/div/span[text()="%s"]/../a/text()' % u'类型：').extract()
            area_list = response.xpath('//div[@class="play_information play_intro"]/div[@class="play_information_t"]/div[@class="r"]/div/span[text()="%s"]/../a/text()' % u'地区：').extract()
            
            pers = Util.join_list_safely(performer_list)
            dirs = Util.join_list_safely(director_list)
            areas = Util.join_list_safely(area_list)
            tags = Util.join_list_safely(tag_list)
            
            text = response.xpath('//div[@class="play_information play_intro"]/div[@class="play_information_b intro_down"]/div[@class="one"]/b/text()').extract()
            
            mvitem = self.compose_mvitem(response,title_list,pers,dirs,response.request.url,cat_id,poster_url,text)
            if mvitem:
                mvitem['media']['type'] = tags
                mvitem['media']['district'] = areas
                items.append(mvitem)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_video_item(self,response,cat_id,url,title,playlistId):
        #logging.log(logging.INFO, 'parse_video_item , info url %s,paly_url: %s,cat id %s,title %s' % (response.request.url,url,cat_id,title))
        videoitems = []
        ep_item = MediaItem()
        item = MediaVideoItem();
        item["media"] = ep_item;
        item["video"] = videoitems
        try:
            if int(cat_id) == int(self.variety_id):
                tvideoitems = self.parse_variety(response)
                if tvideoitems:
                    for titem in tvideoitems:
                        videoitems.append(titem)
            elif '/Play/show' not in url:
            #if int(cat_id) != int(self.movie_id):
                #ul_list = response.xpath('//div[@class="teleplay_gather tab_box"]/div[@class="list_tabs_cont"]/ul/li')
                ul_list = response.xpath('//div[@class="teleplay_gather tab_box"]/div/ul/li')
                if ul_list:
                    #http://www.wasu.cn/Tele/index/id/6539647
                    for li in ul_list:
                        yugaopian = li.xpath('.//i[@class="yugao"]').extract()
                        if yugaopian:
                            continue
                        url = li.xpath('./a/@href').extract()
                        ttitle = li.xpath('./a/@title').extract()
                        snum = li.xpath('./a/text()').extract()
                        play_num = ""
                        if snum:
                            play_num = self.get_play_num(snum[0])
                        if int(cat_id) == int(self.variety_id):
                            play_num1 = self.getvnum(self.url_prefix + url[0])
                            if play_num1:
                                play_num = play_num1
                        if not ttitle:
                            ttitle = [play_num]
                        vitem = None
                        if self.site_name == Util.guess_site(url[0]):
                            vitem = self.compose_vitem([url[0]],[title[0].strip()],play_num)
                        else:
                            vitem = self.compose_vitem([self.url_prefix + url[0]],[title[0].strip()],play_num)
                        if 'url' in vitem:
                            videoitems.append(vitem)
                if not ul_list:
                    #http://www.wasu.cn/Tele/index/id/6786984
                    ul_list = response.xpath('//div[@class="tab_box"]//div[ends-with(@class, "col2")]')
                    for li in ul_list:
                        yugaopian = li.xpath('.//i[@class="yugao"]').extract()
                        if yugaopian:
                            continue
                        url = li.xpath('./div[@class="ws_des"]/p[1]/a/@href').extract()
                        ttitle = li.xpath('./div[@class="ws_des"]/p[2]/span/text()').extract()
                        snum = li.xpath('./div[@class="ws_des"]/p[1]/a/text()').extract()
                        play_num = ""
                        if snum:
                            play_num = self.get_play_num(snum[0])
                        if int(cat_id) == int(self.variety_id):
                            play_num1 = self.getvnum(self.url_prefix + url[0])
                            if play_num1:
                                play_num = play_num1
                        if not ttitle:
                            ttitle = [play_num]
                        vitem = None
                        if self.site_name == Util.guess_site(url[0]):
                            vitem = self.compose_vitem([url[0]],[title[0].strip()],play_num)
                        else:
                            vitem = self.compose_vitem([self.url_prefix + url[0]],[title[0].strip()],play_num)
                        if 'url' in vitem:
                            videoitems.append(vitem)
            else:
            #elif int(cat_id) == int(self.movie_id):
                #无媒体页的播放页
                if url:
                    vitem = self.compose_vitem([url],title,1)
                    if 'url' in vitem:
                        videoitems.append(vitem)
            if videoitems:
                item["video"] = videoitems
                item["media"]["url"] = response.request.url
                Util.set_ext_id(item["media"],item["video"])
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return item

    def compose_mvitem(self,response,title_list,pers,dirs,play_url,cat_id,poster_url,text):
        try:
            cat_id = response.request.meta['cat_id']
            poster_url = response.request.meta['poster_url']
            untrack_id = ""
            sid = ""
            if "untrack_id" in response.request.meta:
                untrack_id = response.request.meta['untrack_id']
            if "sid" in response.request.meta:
                sid = response.request.meta['sid']

            videoitems = []
            ep_item = MediaItem()
            if title_list:
                ep_item["title"] = title_list[0].strip()
            ep_item["actor"] = pers
            ep_item["director"] = dirs

            ep_item["site_id"] = self.site_id
            ep_item["channel_id"] = cat_id
            ep_item["poster_url"] = poster_url
            ep_item["url"] = Util.normalize_url(response.request.url,"wasu")

            if len(text) > 0:
                ep_item["intro"] = text[0].strip()

            mvitem = MediaVideoItem();
            mvitem["media"] = ep_item;

            mid = self.getshowid(response.request.url)
            mvitem["media"]["cont_id"] = mid
            ttvitem = {}
            if title_list:
                ttvitem = self.parse_video_item(response,cat_id,play_url,title_list,None)
            if ttvitem:
                if 'video' in ttvitem and len(ttvitem['video']) > 0:
                    mvitem['video'] = ttvitem['video']
                    mvitem["media"]["info_id"] = Util.md5hash(Util.summarize(mvitem["media"]))
                    Util.set_ext_id(mvitem["media"],mvitem["video"])
                    if untrack_id and sid:
                        mvitem["untrack_id"] = untrack_id
                        mvitem["sid"] = sid
                    res = self.check_url(mvitem)
                    if not res:
                        return None
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return mvitem

    def compose_vitem(self,url_list,title_list,vnum):
        vitem = VideoItem()
        try:
            if not url_list:
                return vitem
            if title_list:
                vitem["title"] = title_list[0].strip()
            turl = Util.normalize_url(url_list[0],"wasu")
            vitem["url"] = turl
            vitem["vnum"] = str(vnum)
            vitem["os_id"] = self.os_id
            vitem["ext_id"] = Util.md5hash(turl)
            vitem["site_id"] = self.site_id
            vitem["cont_id"] = self.getshowid(turl)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return vitem

    #解析娱乐频道的videos
    def parse_variety(self,response):
        videoitems = []
        try:
            #year list
            year_list = response.xpath('//div[@id="play_year"]/div[@id="divselect"]/div[@class="play_sel"]/p/a/text()').extract()
            uid = self.getuid(response.request.url)
            cid = None
            month_list = ["12","11","10","9","8","7","6","5","4","3","2","1"]
            cid_url_list = response.xpath('//div[@class="head1 mb10"]/a/@href').extract()
            for cid_url in cid_url_list:
                cid = self.getcid(cid_url)
                if cid:
                    break
            #http://www.wasu.cn/Column/ajax_list?uid=252&y=2015&mon=7&cid=39
            for year in year_list:
                for month in month_list:
                    if uid and year and month:
                        turl='http://www.wasu.cn/Column/ajax_list?uid=%s&y=%s&mon=%s&cid=%s' % (uid,year,month,cid)
                        info = self.httpdownload.get_data(turl)
                        if not info:
                            continue
                        jinfo = json.loads(info)
                        if "con" in jinfo and jinfo["con"]:
                            tinfo = jinfo["con"].replace("\/","/")
                            tsel = Selector(text=tinfo).xpath('//div[@id="itemContainer"]/div[@class="col2 play_love"]')
                            for isel in tsel:
                                title = isel.xpath('./div[@class="v"]/div[@class="v_link"]/a/@title').extract()
                                url = isel.xpath('./div[@class="v"]/div[@class="v_link"]/a/@href').extract()
                                vnum = isel.xpath('./div[@class="v"]/div[@class="v_meta"]/div[@class="meta_tr"]/text()').extract()
                                tvnum = vnum[0].strip()
                                svnum = tvnum.replace("-","")
                                titem = self.compose_vitem([self.url_prefix + url[0]],title,svnum)
                                if titem:
                                    videoitems.append(titem)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return videoitems

    def get_play_num(self,title):
        num = ""
        try:
            num_list = re.findall('([\d]+)',title)
            if num_list:
                num_size = len(num_list)
                num = num_list[num_size-1]
        except Exception as e:
            pass
        return num

    def check_url(self,mvitem):
        res = True
        try:
            if 'video' in mvitem:
                for video in mvitem['video']:
                    if 'url' in video:
                        if Util.guess_site(video['url']) != self.site_name:
                            res = False
                            break
        except Exception as e:
            pass 
        return res
            
    def is_same_site(self,url):
        res = True
        try:
            tsite = Util.guess_site(url)
            if tsite != self.site_name:
                res = False
        except Exception as e:
            pass
            res = False
        return res

    def getshowid(self,url):
        id = ""
        try:
            #http://www.wasu.cn/Play/show/id/5871821
            #http://www.wasu.cn/Tele/index/id/6786984
            #http://www.wasu.cn/Column/show/column/252
            r = re.compile(r'http://.*/id/(\d+)[\?]?.*')
            m = r.match(url)
            if m:
                return m.group(1)
            else:
                r = re.compile(r'http://.*/show/.*/(\d+)[\?]?.*')
                m = r.match(url)
                if m:
                    return m.group(1)
        except Exception as e:
            pass
        return id

    def getvnum(self,url):
        id = ""
        try:
            r = re.compile(r'http://.*-drama-(\d+).*')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return id 

    def getuid(self,url):
        uid = ""
        try:
            #http://www.wasu.cn/Column/show/column/252
            r = re.compile(r'.*/column/([\d]+)')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return uid

    def getcid(self,url):
        cid = ""
        try:
            #http://all.wasu.cn/index/cid/39
            r = re.compile(r'.*/cid/([\d]+)*')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return cid

    def getareaid(self,url):
        cid = ""
        try:
            #http://all.wasu.cn/index/cid/39
            r = re.compile(r'.*/area/([\d]+)*')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return cid

    def getyearid(self,url):
        cid = ""
        try:
            #http://all.wasu.cn/index/cid/39
            r = re.compile(r'.*/year/([\d]+)*')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return cid

    def get_episode_url(self,url):
        rurl = ""
        try:
            #http://www.wasu.cn/Play/show/id/5871821
            #http://www.wasu.cn/Column/show/column/252
            r = re.compile(r'(.*/show/.*/\d+)')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return rurl
