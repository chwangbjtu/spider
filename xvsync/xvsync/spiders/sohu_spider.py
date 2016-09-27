# -*- coding:utf-8 -*-
from scrapy.spiders import Spider
from scrapy.selector import Selector
from scrapy.http import Request
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

class sohu_spider(Spider):
    name = "sohu"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    site_code = "sohu"   #sohu
    site_id = ""   #sohu
    allowed_domains = ["so.tv.sohu.com","tv.sohu.com"]
    url_prefix = 'http://so.tv.sohu.com'
    #used for guess_site
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
    movie_id = None
    tv_id = None
    variety_id = None
    cartoon_id = None

    test_page_url = None
    test_channel_id = None
    cmd_json = {}

    album_api = 'http://pl.hd.sohu.com/videolist?playlistid=%s&pagenum=%s'

    def __init__(self, json_data=None, *args, **kwargs):
        super(sohu_spider, self).__init__(*args, **kwargs)
        self._cat_urls = []
        tcat_urls = []
        if json_data:
            data = json.loads(json_data)
            if "type" in data:
                spider_type = data["type"]
                if spider_type != "global":
                    self.global_spider = False
            tasks=[]
            if "id" in data and "url" in data:
                ttask={}
                ttask["id"] = data["id"]
                ttask["url"] = data["url"]
                ttask["sid"] = ""
                ttask["untrack_id"] = ""
                self._cat_urls.append(ttask)
            
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
            elif cmd == "episode" and 'id' in data and 'url' in data:
                self.cmd_json = data
            elif cmd == "debug":
                #tasks = [{"mid":"503669", "url":"http://tv.sohu.com/20151204/n429762764.shtml", "name":"综艺", "code":"variaty"}]
                #tasks = [{"mid":"510798", "url":"http://tv.sohu.com/20090824/n266189779.shtml", "name":"综艺", "code":"variaty"}]
                tasks = [{"mid":"502525", "url":"http://tv.sohu.com/20110617/n310505202.shtml", "name":"综艺", "code":"variaty"}]

            for task in tasks:
                ttask= {}
                ttask["url"] = task["url"]
                code = task["code"]
                ttask["id"] = self.channel_map[code]
                ttask["untrack_id"] = task["untrack_id"] if 'untrack_id' in task else None
                ttask["sid"] = task["sid"] if 'sid' in task else None
                ttask['mid'] = task['mid'] if 'mid' in task else None
                self._cat_urls.append(ttask)

    def start_requests(self):
        try:
            items = []

            self.movie_id = str(self.mgr.get_channel('电影')["channel_id"])
            self.tv_id = str(self.mgr.get_channel('电视剧')["channel_id"])
            self.variety_id = str(self.mgr.get_channel('综艺')["channel_id"])
            self.cartoon_id = str(self.mgr.get_channel('动漫')["channel_id"])

            self.channel_info = {self.movie_id:u"电影",self.tv_id:u"电视剧",self.variety_id:u"综艺",self.cartoon_id:u"动漫"}
            if self.test_page_url:
                turl = Util.normalize_url(self.test_page_url,"sohu")
                items.append(Request(url=self.test_page_url, callback=self.parse_page, meta={'cat_id': self.test_channel_id,'page':1}))
                return items

            if self.cmd_json:
                items.append(Request(url=self.cmd_json['url'],callback=self.parse_episode_info,meta={'cat_id': self.cmd_json["id"],'poster_url':''}))
                return items

            if not self._cat_urls:
                #cat_urls = [{'url':'http://so.tv.sohu.com/list_p1106_p2_p3_p4_p5_p6_p73_p8_p9_p10_p11_p12_p13.html','id':self.variety_id}]
                cat_urls = [{'url':'http://so.tv.sohu.com/list_p1100_p2_p3_p4_p5_p6_p73_p80_p9_2d1_p10_p11_p12_p13.html','id':self.movie_id},
                        {'url':'http://so.tv.sohu.com/list_p1101_p2_p3_p4_p5_p6_p73_p8_p9_p10_p11_p12_p13.html','id':self.tv_id},
                        {'url':'http://so.tv.sohu.com/list_p1106_p2_p3_p4_p5_p6_p73_p8_p9_p10_p11_p12_p13.html','id':self.variety_id},
                       {'url':'http://so.tv.sohu.com/list_p1115_p2_p3_p4_p5_p6_p73_p8_p9_p10_p11_p12_p13.html','id':self.cartoon_id}]
                #cat_urls = [{'url':'http://so.tv.sohu.com/list_p1100_p2_p3_p4_p5_p6_p73_p80_p9_2d1_p10_p11_p12_p13.html','id':self.movie_id}]

                for cat in cat_urls:
                    items.append(Request(url=cat['url'], callback=self.parse_type, meta={'cat_id': cat['id'],'page':1}))
            else:
                for cat in self._cat_urls:
                    items.append(Request(url=cat['url'], callback=self.parse_single_episode, meta={'cat_id': cat["id"],'page':1,"untrack_id":cat["untrack_id"],"sid":cat["sid"],"mid":cat["mid"]}))
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_single_episode(self,response):
        items = []
        try:
            logging.log(logging.INFO, 'parse_single_episode: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            untrack_id = response.request.meta['untrack_id']
            sid = response.request.meta['sid']
            mid = response.request.meta['mid'] if 'mid' in response.request.meta else ""
            playtype_list = response.selector.re(re.compile(r'var pagetype = .*?(\D+)'))
            #发现新的类型页面，http://tv.sohu.com/20100804/n273985736.shtml
            #http://my.tv.sohu.com/us/49390690/29200993.shtml  该URL利用现有的逻辑无法爬取到
            urls = response.xpath('//div[@id="crumbsBar"]/div[@class="area cfix"]/div[@class="left"]/div[@class="crumbs"]/a[last()]')
            attributes = urls.xpath('./@*').extract()
            size = len(attributes)
            urls = urls.xpath('./@href').extract()
            if size==1 and urls and not playtype_list:
                for iurl in urls:
                    surl = Util.normalize_url(iurl,"sohu")
                    if surl and "http" in surl:
                        items.append(Request(url=surl, callback=self.parse_episode_info, meta={'cat_id': cat_id,'poster_url':'','page':1,"untrack_id":untrack_id,"sid":sid,"mid":mid}))
            #付费电影，不能跳转到媒体页
            else:
                mvitem = self.parse_episode_play(response,untrack_id,sid)
                if mid:
                    mvitem['mid'] = mid
                if mvitem and "media" in mvitem and  "url" in mvitem["media"] and "ext_id" in mvitem["media"]:
                    if self.check_url(mvitem):
                        items.append(mvitem)
                
            if not items:
                mvitem = MediaVideoItem()
                if mid:
                    mvitem['mid'] = mid
                if untrack_id and sid:
                    mvitem["untrack_id"] = untrack_id
                    mvitem["sid"] = sid
                ep_item = MediaItem()
                ep_item["site_id"] = self.site_id
                ep_item["channel_id"] = cat_id
                mvitem["media"] = ep_item

                playlistId = ""
                playlistId_list = response.selector.re(re.compile(r'var playlistId.*?(\d+)'))
                if not playlistId_list:
                    playlistId_list = response.selector.re(re.compile(r'var PLAYLIST_ID.*?(\d+)'))
                if not playlistId_list:
                    playlistId_list = response.selector.re(re.compile(r'= playlistId.*?(\d+)'))
                if playlistId_list:
                    playlistId = playlistId_list[0]
                    items += self.api_episode_info(mvItem=mvitem, playlistId=playlistId, cat_id=cat_id)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_type(self,response):
        items = []
        try:
            #logging.log(logging.INFO, 'parse_typ: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="sort-type"]/dl[1]/dd[@class="sort-tag"]/a/@href').extract()
            for sub in subs:
                items.append(Request(url=self.url_prefix+sub, callback=self.parse_area, meta={'cat_id': cat_id,'page':1}))

            titem = self.parse_page(response)
            if titem:
                items.extend(titem)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_area(self,response):
        items = []
        try:
            #logging.log(logging.INFO, 'parse_area: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="sort-type"]/dl[2]/dd[@class="sort-tag"]/a/@href').extract()
            for sub in subs:
                items.append(Request(url=self.url_prefix+sub, callback=self.parse_sort, meta={'cat_id': cat_id,'page':1}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_sort(self,response):
        items = []
        try:
            #logging.log(logging.INFO, 'parse_sort: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="sort-column area"]/div[@class="column-hd"]/p[@class="st-link"]/a/@href').extract() 
            for sub in subs:
                items.append(Request(url=self.url_prefix+sub, callback=self.parse_page, meta={'cat_id': cat_id,'page':1}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_page(self,response):
        try:
            cat_id = response.request.meta['cat_id']
            page = response.request.meta['page']
            #logging.log(logging.INFO, 'parse_page: %s,%s' % (response.request.url,page))

            #if int(page) > int(self.max_update_page) and not self.global_spider:
            #    return
            
            items = []
            
            play_url = ""
            subs = response.xpath('//div[@class="column-bd cfix"]/ul[1]/li')
            
            for sub in subs:
                play_url = sub.xpath('./div[@class="st-pic"]/a/@href').extract()
                pic_urls = sub.xpath('./div[@class="st-pic"]/a/img/@src').extract()
                pic_url = ""
                if pic_urls:
                    pic_url = pic_urls[0]
                if play_url:
                    items.append(Request(url=play_url[0].strip(),callback=self.parse_episode_info,meta={'cat_id': cat_id,'poster_url':pic_url}))
                
            next_page = response.xpath("//div[@class='column-bd cfix']/div[1]/a[@title='%s']/@href" % u'下一页').extract()
            if next_page:
                snext_page = next_page[0].strip()
                if snext_page.find(self.url_prefix) < 0:
                    snext_page = self.url_prefix + snext_page
                items.append(Request(url=snext_page, callback=self.parse_page, meta={'page': page+1, 'cat_id': cat_id}))

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_episode_info(self,response):
        items = []
        try:
            logging.log(logging.INFO, 'parse_episode_info: %s' % response.request.url)
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

            year_list = []
            lyears = []

            playlistId = ""
            playlistId_list = response.selector.re(re.compile(r'var playlistId.*?(\d+)'))
            if not playlistId_list:
                playlistId_list = response.selector.re(re.compile(r'var PLAYLIST_ID.*?(\d+)'))
            if not playlistId_list:
                playlistId_list = response.selector.re(re.compile(r'= playlistId.*?(\d+)'))
        
            if playlistId_list:
                playlistId = playlistId_list[0]
            if not playlistId:
                logging.log(logging.INFO, "parse_episode_info error,not find playlistid,url:%s " % response.request.url)
                return items

            title_list = self.parse_title(response,cat_id)
            performer_list = self.parse_actor(response)
            director_list = self.parse_director(response)
            district_list = self.parse_district(response)
            type_list = self.parse_type_list(response)
            #year_list = response.xpath('//div[@class="mod plot"]/ul[@class="filter"]/li[@class="v-year"]/a/em/text()').extract()
            year_list = self.parse_year(response)
            year = None
            if year_list:
                year = year_list[0]
            #pers = "|".join([t.strip() for t in performer_list])
            #dirs = "|".join([t.strip() for t in director_list])
            pers = Util.join_list_safely(performer_list)
            dirs = Util.join_list_safely(director_list)
            types = Util.join_list_safely(type_list)
            district = Util.join_list_safely(district_list)

            #text
            text = response.xpath('//div[@class="movieCont mod"]/p[1]/span[@class="full_intro"]/text()').extract()

            play_url = ""
            play_url = response.xpath('//div[@class="cfix movie-info"]/div[2]/div[@class="cfix bot"]/a[@class="btn-playFea"]/@href').extract()
            videoitems = []

            ep_item = MediaItem()
            if title_list:
                ep_item["title"] = title_list[0]
            ep_item["actor"] = pers
            ep_item["director"] = dirs
            if types:
                ep_item["type"] = types
            if district:
                ep_item["district"] = district
            if year:
                ep_item["release_date"] = Util.str2date(year)

            ep_item["site_id"] = self.site_id
            ep_item["channel_id"] = cat_id
            ep_item["poster_url"] = poster_url
            ep_item["url"] = Util.normalize_url(response.request.url,"sohu")
            playlistId = str(playlistId)
            ep_item["cont_id"] = playlistId
            
            if len(text) > 0:
                ep_item["intro"] = text[0].strip()

            mvitem = MediaVideoItem();
            if mid:
                mvitem['mid'] = mid
            if untrack_id and sid:
                mvitem["untrack_id"] = untrack_id
                mvitem["sid"] = sid
            mvitem["media"] = ep_item;
            vurl = ""
            ttvitem = []
            if title_list:
                ttvitem = self.parse_video_item(cat_id, playlistId)
            if ttvitem:
                    mvitem['video'] = ttvitem
                    mvitem["media"]["info_id"] = Util.md5hash(Util.summarize(mvitem["media"]))
                    Util.set_ext_id(mvitem["media"],mvitem["video"])
                    if self.check_url(mvitem):
                        items.append(mvitem)
            if not items and playlistId:
                items += self.api_episode_info(mvitem, playlistId, cat_id=cat_id)
        except Exception as e: 
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def api_episode_info(self, mvItem=None, playlistId='', cat_id=''):
        # 应该保证mvItem,playlistId不为空，且包含mid或者sid、untrack_id,包含channel_id、site_id
        items = []
        try:
            mvitem = mvItem
            ep_item = mvitem["media"]

            url = self.album_api % (playlistId, 1)
            logging.log(logging.INFO, 'api_episode_info, info url %s' % url)
            info = self.httpdownload.get_data(url)
            info = info.decode('gbk').encode('utf-8')
            info_json = json.loads(info)
            
            actor_list = info_json.get("mainActors")
            director_list = info_json.get("directors")
            type_list = info_json.get("categories")
            if "actor" not in ep_item and actor_list:
                ep_item["actor"] = Util.join_list_safely(actor_list)
            if "director" not in ep_item and director_list:
                ep_item["director"] = Util.join_list_safely(director_list)
            if "type" not in ep_item and type_list:
                ep_item["type"] = Util.join_list_safely(type_list)
            if "title" not in ep_item:
                ep_item["title"] = info_json.get("albumName")
            if "district" not in ep_item:
                ep_item["district"] = info_json.get("area")
            if "release_date" not in ep_item and info_json.get("publishYear"):
                ep_item["release_date"] = Util.str2date(str(info_json.get("publishYear")))
            if "intro" not in ep_item:
                ep_item["intro"] = info_json.get("albumDesc")
            if "poster_url" not in ep_item or not str.strip(str(ep_item["poster_url"])):
                ep_item["poster_url"] = info_json.get("pic240_330")
            if "cont_id" not in ep_item:
                ep_item["cont_id"] = playlistId
            
            ttvitem = []
            if ep_item['title']:
                mvitem['media'] = ep_item
                ttvitem = self.parse_video_item(cat_id, playlistId)
            if ttvitem:
                    mvitem['video'] = ttvitem
                    if "url" not in mvitem["media"]:
                        mvitem["media"]["url"] = ttvitem[0]['url']
                    mvitem["media"]["info_id"] = Util.md5hash(Util.summarize(mvitem["media"]))
                    Util.set_ext_id(mvitem["media"], mvitem["video"])
                    if self.check_url(mvitem):
                        items.append(mvitem)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_episode_play(self,response,untrack_id,sid):
        mvitem = None
        try:
            logging.log(logging.INFO, 'parse_episode_play: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            #vip
            title_list = response.xpath('//div[@id="crumbsBar"]/div[@class="area cfix"]/div[@class="left"]/h2/@title').extract()
            director_list = response.xpath('//div[@class="info info-con"]/ul/li[text()="%s"]/a/text()' % u'导演：').extract()
            performer_list = response.xpath('//div[@class="info info-con"]/ul/li[text()="%s"]/a/text()' % u'主演：').extract()
            text = response.xpath('//div[@class="info info-con"]/p[@class="intro"]/text()').extract()
            pers = "|".join([t.strip() for t in performer_list])
            dirs = "|".join([t.strip() for t in director_list])
            playlistId = ""
            playlistId_list = response.selector.re(re.compile(r'var playlistId.*?(\d+)'))
            if not playlistId_list:
                playlistId_list = response.selector.re(re.compile(r'var PLAYLIST_ID.*?(\d+)'))
            if not playlistId_list:
                playlistId_list = response.selector.re(re.compile(r'= playlistId.*?(\d+)'))

            if playlistId_list:
                playlistId = playlistId_list[0]
            vid = ""
            vid_list = response.selector.re(re.compile(r'var vid.*?(\d+)'))
            if vid_list:
                vid = vid_list[0]
            if not playlistId or not vid:
                return mvitem

            ep_item = MediaItem()
            ep_item["cont_id"] = playlistId
            if title_list:
                ep_item["title"] = title_list[0]
            ep_item["actor"] = pers
            ep_item["director"] = dirs
            ep_item["site_id"] = self.site_id
            ep_item["channel_id"] = cat_id
            ep_item["url"] = Util.normalize_url(response.request.url,"sohu")
            
            if text:
                ep_item["intro"] = text[0].strip()

            mvitem = MediaVideoItem();
            mvitem["media"] = ep_item;
            if untrack_id:
                mvitem["untrack_id"] = untrack_id
            if sid:
                mvitem["sid"] = sid
            vitem = VideoItem()
            vitem["title"] = ep_item["title"] if 'title' in ep_item else None
            vitem["url"] = ep_item["url"]
            vitem["vnum"] = "1"
            vitem["os_id"] = self.os_id
            vitem["ext_id"] = Util.md5hash(ep_item["url"])
            vitem["site_id"] = self.site_id
            vitem["cont_id"] = vid 
            videoitems = []
            videoitems.append(vitem)
            mvitem["video"] = videoitems
            mvitem["media"]["info_id"] = Util.md5hash(Util.summarize(mvitem["media"]))

            Util.set_ext_id(mvitem["media"],mvitem["video"])
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return mvitem

    def parse_title(self,response,cat_id):
        gtitle = []
        title = []
        try:
            title = response.xpath('//div[@class="wrapper"]/div[1]/h2/text()').extract()
            gtitle = self.strip_title(cat_id,title)
            if not gtitle:
                title = response.xpath('//div[@class="wrapper"]/div[1]/h2/text()').extract()
                gtitle = self.strip_title(cat_id,title)
            if not gtitle:
                title = response.xpath('//div[@id="contentA"]/div[@class="right"]/div[@class="blockRA bord clear"]/h2/span/text()').extract()
                gtitle = self.strip_title(cat_id,title)
            if not gtitle:
                title = response.xpath('//div[@class="wrapper"]/div[1]/h2/span/text()').extract()
                gtitle = self.strip_title(cat_id,title)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

        return gtitle

    def strip_title(self,cat_id,title):
        gtitle = []
        try:
            if len(title):
                ttitle = title[0].strip()
                index = ttitle.find(self.channel_info[str(cat_id)])
                len1 = 0
                if index >= 0:
                    len1 = len(self.channel_info[str(cat_id)]) + 1
                else:  
                    index = 0
                tinfo = ttitle[index+len1:]
                if len(tinfo) > 0:
                    gtitle.append(tinfo)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return gtitle

    def parse_actor(self,response):
        performer_list = []
        try:
            performer_list = response.xpath('//div[@class="movie-infoR"]/ul[@class="cfix mB20"]/li/span[text()="%s"]/../a/text()' % u'主演：').extract()
            if not performer_list:
                performer_list = response.xpath('//div[@class="infoR"]/ul/li/span[text()="%s"]/../a/text()' % u'主持人：').extract()
            if not performer_list:
                performer_list = response.xpath('//div[@id="contentA"]/div[@class="right"]/div[@class="blockRA bord clear"]/div[@class="cont"]/p[text()="%s"]/a/text()' % u'配音：').extract()
            if not performer_list:
                performer_list = response.xpath('//div[@id="contentA"]/div[@class="right"]/div[@class="blockRA bord clear"]/div[@class="cont"]/p[text()="%s"]/a/text()' % u'声优：').extract()
            if not performer_list:
                performer_list = response.xpath('//div[@id="contentA"]/div[@class="right"]/div[@class="blockRA bord clear"]/div[@class="cont"]/p[text()="%s"]/a/text()' % u'主演：').extract()
            if not performer_list:
                performer_list = response.xpath('//div[@class="drama-infoR"]/ul[@class="cfix"]/li/span[text()="%s"]/../a/text()' % u'主演：').extract()
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return performer_list

    def parse_type_list(self,response):
        type_list = []
        try:
            type_list = response.xpath('//div[@class="movie-infoR"]/ul[@class="cfix mB20"]/li/span[text()="%s"]/../a/text()' % u'类型：').extract()
            if not type_list:
                type_list = response.xpath('//div[@id="contentA"]/div[@class="right"]/div[@class="blockRA bord clear"]/div[@class="cont"]/p[text()="%s"]/a/text()' % u'类型：').extract()
            if not type_list:
                type_list = performer_list = response.xpath('//div[@class="drama-infoR"]/ul[@class="cfix"]/li/span[text()="%s"]/../a/text()' % u'类型：').extract()
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return type_list

    def parse_district(self,response):
        type_list = []
        try:
            type_list = response.xpath('//div[@class="movie-infoR"]/ul[@class="cfix mB20"]/li/span[text()="%s"]/../a/text()' % u'地区：').extract()
            if not type_list:
                type_list = response.xpath('//div[@id="contentA"]/div[@class="right"]/div[@class="blockRA bord clear"]/div[@class="cont"]/p[text()="%s"]/a/text()' %u'地区：').extract()
            if not type_list:
                type_list = performer_list = response.xpath('//div[@class="drama-infoR"]/ul[@class="cfix"]/li/span[text()="%s"]/../a/text()' % u'地区：').extract()
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return type_list
    
    def parse_year(self,response):
        type_list = []
        try:
            type_list = response.xpath('//div[@class="movie-infoR"]/ul[@class="cfix mB20"]/li/span[text()="%s"]/../a/text()' % u'上映时间：').extract()
            if not type_list:
                type_list = response.xpath('//div[@id="contentA"]/div[@class="right"]/div[@class="blockRA bord clear"]/div[@class="cont"]/p[text()="%s"]/a/text()' %u'上映时间：').extract()
            if not type_list:
                type_list = response.xpath('//div[@class="drama-infoR"]/ul[@class="cfix"]/li/span[text()="%s"]/../text()' % u'上映时间：').extract()
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return type_list

    def parse_director(self,response):
        director_list = []
        try:
            director_list = response.xpath('//div[@class="movie-infoR"]/ul[@class="cfix mB20"]/li/span[text()="%s"]/../a/text()' % u'导演：').extract()
            if not director_list:
                director_list = response.xpath('//div[@id="contentA"]/div[@class="right"]/div[@class="blockRA bord clear"]/div[@class="cont"]/p[text()="%s"]/a/text()' % u'导演：').extract()
            if not director_list:
                director_list = response.xpath('//div[@id="contentA"]/div[@class="right"]/div[@class="blockRA bord clear"]/div[@class="cont"]/p[text()="%s"]/a/text()' % u'监督：').extract()
            if not director_list:
                director_list=response.xpath('//div[@class="drama-infoR"]/ul[@class="cfix"]/li/span[text()="%s"]/../a/text()' % u'导演：').extract()
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

        return director_list

    def parse_video_item(self, cat_id, playlistId):
        logging.log(logging.INFO, 'parse_video_item , playlistId %s' % playlistId)
        videoitems = []
        try:
            #新接口代码
            page = 1
            while True:
                page_items = self.parse_videos_info(cat_id, playlistId, page)
                if not page_items:
                    break
                videoitems = videoitems + page_items
                page = page + 1

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return videoitems

    def parse_videos_info(self, cat_id, playlistId, page):
        videoitems = []
        try:
            url = self.album_api % (playlistId, page)
            logging.log(logging.INFO, 'parse_videos_info, info url %s' % url)
            info = self.httpdownload.get_data(url)
            info = info.decode('gbk').encode('utf-8')
            info_json = json.loads(info)
            videos = info_json['videos']
            if int(cat_id) == int(self.variety_id):
                for video in videos:
                    tvSType = str(video['tvSType']) if 'tvSType' in video else '-1'
                    if tvSType != '1' and tvSType != '36':
                        continue
                    #综艺采用日期
                    play_num = self.get_play_num(video['showDate'])
                    if not play_num:
                        play_num = self.get_play_num_date(video['publishTime'])
                    vitem = self.compose_vitem([video['pageUrl']],[video['name']],play_num)
                    vitem['cont_id'] = video['vid']
                    vitem['thumb_url'] = video['smallPicUrl']
                    videoitems.append(vitem)
            else: 
                for video in videos:
                    tvSType = str(video['tvSType']) if 'tvSType' in video else '-1'
                    if tvSType != '1' and tvSType != '36':
                        continue
                    #非综艺采用order
                    play_num = self.get_play_num(video['order'])
                    vitem = self.compose_vitem([video['pageUrl']],[video['name']],play_num)
                    vitem['cont_id'] = video['vid']
                    vitem['thumb_url'] = video['smallPicUrl']
                    videoitems.append(vitem)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return videoitems

    def parse_variety_info(self,playlistId,response):
        logging.log(logging.INFO, 'parse_variety_info, info url %s' % response.request.url)
        videoitems = []
        try:
            year_list = response.xpath('//div[@class="mod plot"]/ul[@class="filter"]/li[@class="v-year"]/a/em/text()').extract()
            if not year_list:
                year_list = ["2015","2014","2013","2012","2011","2010"]
            for year in year_list:
                turl1 = "http://tv.sohu.com/item/VideoServlet?source=sohu&id=" + str(playlistId) + "&year=" + year + "&month=0&page=1"
                info = self.httpdownload.get_data(turl1)
                videolist = self.parse_play_list(info)
                if videolist:
                    for titem in videolist:
                        videoitems.append(titem)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return videoitems

    def parse_play_list(self,info):
        videoitems = []
        try:
            if not info or len(info) < len("{pageTotal: 1,videos:[]"):
                return None
            jinfo = {}
            try:
                jinfo = json.loads(info)
            except Exception as e:
                logging.log(logging.ERROR, traceback.format_exc())
            if "videos" not in jinfo:
                return videoitems

            itemlist = jinfo["videos"]
            for titem in itemlist:
                vitem = self.compose_vitem([titem["url"]],[titem["title"]],titem["showDate"])
                vitem['cont_id'] = titem['id']
                videoitems.append(vitem)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return videoitems

    def get_carton_list(self,response):
        videoitems = []
        try:
            ul_list=response.xpath('//div[@id="blockA"]/div[@id="allist"]/div[@id="list_asc"]/div[@class="pp similarLists"]/ul')
            for ul in ul_list:
                li_list = ul.xpath('./li')
                for li in li_list:
                    url = li.xpath('./a/@href').extract()
                    ttitle = li.xpath('./span/strong/a/text()').extract()
                    play_num = self.get_play_num(ttitle[0])
                    vitem = self.compose_vitem(url,ttitle,play_num)
                    if 'url' in vitem:
                        videoitems.append(vitem)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

        return videoitems

    def compose_vitem(self,url_list,title_list,vnum):
        vitem = VideoItem()
        try:
            if not url_list:
                return vitem
            if title_list:
                vitem["title"] = title_list[0].strip()
            turl = Util.normalize_url(url_list[0],"sohu")
            vitem["url"] = turl
            vitem["vnum"] = str(vnum)
            vitem["os_id"] = self.os_id
            vitem["ext_id"] = Util.md5hash(turl)
            vitem["site_id"] = self.site_id
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return vitem

    def get_sohu_showid(self,url):
        id = ""
        try:
            #http://tv.sohu.com/item/MTE4NTk2MA==.html
            #http://tv.sohu.com/item/MTE0NjQwNg==.html
            #r = re.compile(r'http://tv.sohu.com.+?/[^/]*./([^/]*)\.html')
            r = re.compile(r'http://tv.sohu.com/[^/].*/([^/].*)\.[s]?html')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return id

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

    def get_play_num_date(self, title):
        num = ""
        try:
            num_list = re.findall('([\d]+)',title)
            if num_list:
                num = "".join(num_list)
        except Exception as e:
            pass
        return num

    def check_url(self,mvitem):
        res = True
        try:
            if 'video' in mvitem:
                for video in mvitem['video']:
                    if 'url' in video:
                        tres = self.is_same_site(video['url'])
                        if not tres:
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

    def get_year(self,info):
        year = None
        try:
            r = re.compile(ur'.*%s.*(\d+).*' % (u'上映时间'))
            m = r.search(info)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return year
