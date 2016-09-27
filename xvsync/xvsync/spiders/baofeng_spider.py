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

class baofeng_spider(Spider):
    name = "baofeng"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    site_code = "baofeng"
    site_id = ""   #baofeng
    allowed_domains = ["www.baofeng.com","g.hd.baofeng.com"]
    url_prefix = 'http://www.baofeng.com'
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

    def __init__(self, json_data=None, *args, **kwargs):
        super(baofeng_spider, self).__init__(*args, **kwargs)
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
            elif cmd == "test" and 'id' in data and 'url' in data:
                self.test_page_url = data["url"]
                self.test_channel_id = data["id"]

            if tasks:
                for task in tasks:
                    ttask={}
                    ttask["url"] = task["url"]
                    code = task["code"]
                    ttask["id"] = self.channel_map[code]
                    ttask["untrack_id"] = task["untrack_id"]
                    ttask["sid"] = task["sid"]
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
                turl = Util.normalize_url(self.test_page_url,"baofeng")
                items.append(Request(url=self.test_page_url, callback=self.parse_page, meta={'cat_id': self.test_channel_id,'page':1}))
                return items

            if not self._cat_urls:
                if self.global_spider:
                    cat_urls = [{'url':'http://www.baofeng.com/movie/682/list-sid-1-p-1.shtml','id':self.movie_id},
                            {'url':'http://www.baofeng.com/tv/914/list-type-2-ishot-1-sid-1-p-1.shtml','id':self.tv_id},
                            {'url':'http://www.baofeng.com/enc/444/list-type-4-ishot-1-sid-1-p-1.shtml','id':self.variety_id},
                            {'url':'http://www.baofeng.com/comic/924/list-type-3-ishot-1-sid-1-p-1.shtml','id':self.cartoon_id}]
                    #cat_urls = [{'url':'http://www.baofeng.com/enc/444/list-type-4-ishot-1-sid-1-p-1.shtml','id':self.variety_id}]
                for cat in cat_urls:
                    items.append(Request(url=cat['url'], callback=self.parse_area, meta={'cat_id': cat['id'],'page':1}))
                    #items.append(Request(url=cat['url'], callback=self.parse_page, meta={'cat_id': cat['id'],'page':1}))
            else:
                for cat in self._cat_urls:
                    turl = Util.normalize_url(cat['url'],"baofeng")
                    items.append(Request(url=turl, callback=self.parse_single_episode, meta={'cat_id': cat["id"],'page':1,"poster_url":"","untrack_id":cat["untrack_id"],"sid":cat["sid"]}))
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_area(self,response):
        items = []  
        try:            
            #logging.log(logging.INFO, 'parse_area: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="selecter"]/div[1]/div[@class="clearfix rp"]/a/@href').extract()
            for sub in subs:
                items.append(Request(url=self.url_prefix+sub, callback=self.parse_type, meta={'cat_id': cat_id,'page':1}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_type(self,response):
        items = []
        try:
            #logging.log(logging.INFO, 'parse_type: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="selecter"]/div[2]/div[@class="clearfix rp"]/a/@href').extract()
            for sub in subs:
                items.append(Request(url=self.url_prefix+sub, callback=self.parse_time, meta={'cat_id': cat_id,'page':1}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_time(self,response):
        items = []
        try:
            #logging.log(logging.INFO, 'parse_time: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="selecter"]/div[3]/div[@class="clearfix rp"]/a/@href').extract()
            for sub in subs:
                items.append(Request(url=self.url_prefix+sub, callback=self.parse_page, meta={'cat_id': cat_id,'page':1}))
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
            subs = response.xpath('//div[@class="sort-list-r-mod02"]/ul[@class="sort-list-r-poster clearfix"]/li')
            
            for sub in subs:
                play_url = sub.xpath('./div[1]/p[1]/a/@href').extract()
                pic_urls = sub.xpath('./div[1]/p[1]/a/img/@src').extract()
                #pic_urls = sub.xpath('./div[@class="hot-pic-like js-collect  shadow-cut"]/p[1]/a/img/@src').extract()
                pic_url = ""
                if pic_urls:
                    pic_url = pic_urls[0]
                if play_url:
                    rplay_url = play_url[0].strip()
                    
                    items.append(Request(url=self.url_prefix+rplay_url,callback=self.parse_single_episode,meta={'cat_id': cat_id,'poster_url':pic_url,'untrack_id':'','sid':''}))

            next_page = response.xpath('//div[@class="sort-list-r-mod02"]/div[@class="pages"]/ul[@class="clearfix"]/li/a[text()="%s"]/@href' % u'下一页').extract()
            if next_page:
                snext_page = next_page[0].strip()
                if snext_page.find(self.url_prefix) < 0:
                    snext_page = self.url_prefix + snext_page
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
            poster_url = response.request.meta['poster_url']
            urls = response.xpath('//div[@class="play-nav-l-new"]/h1/a/@href').extract()
            if urls:
                for iurl in urls:
                    turl = self.url_prefix + iurl
                    surl = Util.normalize_url(turl,"baofeng")
                    if surl and self.site_name == Util.guess_site(surl):
                    #if turl and self.site_name == Util.guess_site(turl):
                        items.append(Request(url=surl, callback=self.parse_episode_info, meta={'cat_id': cat_id,'poster_url':poster_url,'page':1,"untrack_id":untrack_id,"sid":sid}))        
            #付费电影，不能跳转到媒体页
            else:       
                pass
                 
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
            if "untrack_id" in response.request.meta:
                untrack_id = response.request.meta['untrack_id']
            if "sid" in response.request.meta:
                sid = response.request.meta['sid']
                
            year_list = [] 
            lyears = [] 
                
            title_list = response.xpath('//div[@class="aboutThis clearfix"]/div[@class="makeup"]/h3/a/@title').extract()
            director_list  = response.xpath('//div[@class="info clearfix"]/span[text()="%s"]/a/text()' % u'导演：').extract()
            performer_list = response.xpath('//div[@class="info clearfix"]/span[text()="%s"]/a/text()' % u'主演：').extract()
            type_list = response.xpath('//div[@class="info clearfix"]/span[text()="%s"]/a/text()' % u'类型：').extract()
            district_list = response.xpath('//div[@class="info clearfix"]/span[text()="%s"]/a/text()' % u'地区：').extract()
            year_info = response.xpath('//div[@class="info clearfix"]/span[text()="%s"]/text()' % u'地区：').extract()
            year = None
            if len(year_info) >= 2:
                year = self.get_year(year_info[1])
            
            #year_list = response.xpath('//div[@class="mod plot"]/ul[@class="filter"]/li[@class="v-year"]/a/em/text()').extract()
            pers = Util.join_list_safely(performer_list)
            dirs = Util.join_list_safely(director_list)
            types = Util.join_list_safely(type_list)
            districts = Util.join_list_safely(district_list)
            
            #text
            text = response.xpath('//div[@class="juqing briefTab"]/div/text()').extract()
            #score
            score = response.xpath('//div[@class="aboutThis clearfix"]/div[@class="makeup"]/div[1]/div[@class="score"]/div[class="score-num"]/strong/text()').extract()
            
            play_url = ""
            tplay_url = response.xpath('//div[@class="aboutThis clearfix"]/div[@class="makeup"]/div[@class="sourcePlay"]/a[@id="moviePlayButton"]/@href').extract()
            if tplay_url:
                play_url = self.url_prefix + tplay_url[0].strip()
            videoitems = []
            
            ep_item = MediaItem()
            if title_list:
                ep_item["title"] = title_list[0]
                if ep_item["title"].find(u'预:') >= 0:
                    print "预告片，url",response.request.url
                    return items
            ep_item["actor"] = pers
            ep_item["director"] = dirs
            if types:
                ep_item["type"] = types
            if district_list:
                ep_item["district"] = districts
            if year:
                ep_item["release_date"] = Util.str2date(year)
            
            ep_item["site_id"] = self.site_id
            ep_item["channel_id"] = cat_id
            ep_item["poster_url"] = poster_url
            ep_item["url"] = Util.normalize_url(response.request.url,"baofeng")
            
            if len(text) > 0:
                ep_item["intro"] = text[0].strip()
            
            mvitem = MediaVideoItem();
            mvitem["media"] = ep_item;
            
            vurl = ""
            
            videoid = self.getshowid(response.request.url)
            mvitem["media"]["cont_id"] = videoid
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
                    #if self.check_url(mvitem):
                    if res:
                        items.append(mvitem)
                        pass
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
            if int(cat_id) != int(self.movie_id):
                ul_list = response.xpath('//div[@class="episodes clearfix "]/a')
                if not ul_list:
                    ul_list = response.xpath('//div[@class="episodes clearfix enc-episodes-detail"]/a')
                for li in ul_list:
                    url = li.xpath('./@href').extract()
                    ttitle = li.xpath('./@title').extract()
                    snum = li.xpath('./text()').extract()
                    if snum:
                        play_num = self.get_play_num(snum[0])
                    if int(cat_id) == int(self.variety_id):
                        play_num = self.getvnum(self.url_prefix + url[0])
                    if not ttitle:
                        ttitle = [play_num]
                    vitem = self.compose_vitem([self.url_prefix + url[0]],title,play_num)
                    if 'url' in vitem:
                        videoitems.append(vitem)
            elif int(cat_id) == int(self.movie_id):
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

    def compose_vitem(self,url_list,title_list,vnum):
        vitem = VideoItem()
        try:
            if not url_list:
                return vitem
            if title_list:
                vitem["title"] = title_list[0].strip()
            turl = Util.normalize_url(url_list[0],"baofeng")
            vitem["url"] = turl
            vitem["vnum"] = str(vnum)
            vitem["os_id"] = self.os_id
            vitem["ext_id"] = Util.md5hash(turl)
            vitem["site_id"] = self.site_id
            vitem["cont_id"] = self.getshowid(turl)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return vitem

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
            #http://www.baofeng.com/play/497/play-786997.html
            #r = re.compile(r'http://.+/id_([^_]+).*\.html')
            #r = re.compile(r'http://.*[]-([\d]+).html')
            #r = re.compile(r'http://.*[play|detail]-([\d]+).*html')
            r = re.compile(r'http://.*/\w+-(\d+).*')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return id

    def getvnum(self,url):
        id = ""
        try:
            #http://www.baofeng.com/play/363/play-786863-drama-10.html
            r = re.compile(r'http://.*-drama-(\d+).*')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return id 

    def get_year(self,info):
        year = None
        try:
            r = re.compile(ur'.*(\d+).*')
            m = r.search(info)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return year
