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

class qq_spider(Spider):
    name = "qq"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    site_code = "qq"
    site_id = ""   #qq
    allowed_domains = ["v.qq.com","film.qq.com","s.video.qq.com"]
    url_prefix = 'http://v.qq.com'
    #used for guess_site
    site_name = Util.guess_site(url_prefix)

    mgr = DbManager.instance()
    os_id = mgr.get_os('web')["os_id"]
    site_id = str(mgr.get_site(site_code)["site_id"])
    #site_code = str(mgr.get_site(site_name)["site_code"])
    channel_map = {}
    channel_map = mgr.get_channel_map()
    max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
    global_spider = True
    httpdownload = HTTPDownload()

    channel_info = {}

    movie_id = ""
    tv_id = ""
    variety_id = ""
    cartoon_id = ""

    test_page_url = None 
    test_channel_id = None
    

    def __init__(self, json_data=None, *args, **kwargs):
        super(qq_spider, self).__init__(*args, **kwargs)
        cat_urls = []
        tasks = None
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
        items = []
        try:
            cat_urls = []

            self.movie_id = self.mgr.get_channel('电影')["channel_id"]
            self.tv_id = self.mgr.get_channel('电视剧')["channel_id"]
            self.variety_id = self.mgr.get_channel('综艺')["channel_id"]
            self.cartoon_id = self.mgr.get_channel('动漫')["channel_id"]

            self.channel_info = {self.movie_id:u"电影",self.tv_id:u"电视剧",self.variety_id:u"综艺",self.cartoon_id:u"动漫"}

            if self.test_page_url:
                turl = Util.normalize_url(self.test_page_url,"qq")
                items.append(Request(url=self.test_page_url, callback=self.parse_single_episode, meta={'cat_id': self.test_channel_id,'page':1}))
                return items

            if not self._cat_urls:
                #cat_urls = [{'url':'http://v.qq.com/list/2_-1_-1_-1_0_1_1_10_-1_-1_0.html','id':self.tv_id}]
                cat_urls = [{'url':'http://v.qq.com/movielist/10001/0/0/1/0/10/1/0.html','id':self.movie_id},
                        {'url':'http://v.qq.com/list/2_-1_-1_-1_0_1_1_10_-1_-1_0.html','id':self.tv_id},
                        {'url':'http://v.qq.com/variety/type/list_-1_0_0.html','id':self.variety_id},
                        {'url':'http://v.qq.com/cartlist/0/3_-1_-1_-1_-1_1_0_1_10.html','id':self.cartoon_id}]

                for cat in cat_urls:
                    items.append(Request(url=cat['url'], callback=self.parse_type, meta={'cat_id': cat['id'],'page':1}))
            else:
                for cat in self._cat_urls:
                    channel_id = str(cat["id"])
                    items.append(Request(url=cat['url'], callback=self.parse_single_episode, meta={'cat_id': channel_id,'page':1,"untrack_id":cat["untrack_id"],"sid":cat["sid"]}))

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_single_episode(self,response):
        items = []
        try:
            logging.log(logging.INFO, 'parse_single_episode: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            untrack_id = ""
            sid = ""
            if "untrack_id" in response.request.meta:
                untrack_id = response.request.meta['untrack_id']
            if "sid" in response.request.meta:
                sid = response.request.meta['sid']

            urls = response.xpath('//div[@class="breadcrumb"]/a[@class="breadcrumb_item"]/@href').extract()
            #carton is different
            if not urls:
                turls = response.xpath('//div[@class="mod_player_head cf"]/div[1]/div[1]/a/@href').extract()
                if turls:
                    tlen = len(turls)
                    urls = [turls[tlen-1]]

            if urls:
                turl = self.url_prefix + urls[0]
                #print "turl",turl
                #turl = "http://v.qq.com/p/tv/detail/hqg/index.html"
                items.append(Request(url=turl, callback=self.parse_episode_info, meta={'cat_id': cat_id,'poster_url':'','page':1,"untrack_id":untrack_id,"sid":sid}))
            else:
                ttitem = self.parse_episode_play(response)
                if ttitem and self.check_url(ttitem):
                    items.append(ttitem)

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_type(self,response):
        items = []
        try:
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="mod_indexs bor"]/div[@class="mod_cont"]/ul[1]/li/a/@href').extract()
            for sub in subs:
                items.append(Request(url=sub, callback=self.parse_area, meta={'cat_id': cat_id,'page':1}))

            titem = self.parse(response)
            if titem:
                items.extend(titem)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_area(self,response):
        items = []
        try:
            logging.log(logging.INFO, 'parse_area: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="mod_indexs bor"]/div[@class="mod_cont"]/ul[2]/li/a/@href').extract()
            for sub in subs:
                items.append(Request(url=sub, callback=self.parse_year, meta={'cat_id': cat_id,'page':1}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_year(self,response):
        items = []
        try:
            logging.log(logging.INFO, 'parse_year: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="mod_indexs bor"]/div[@class="mod_cont"]/ul[3]/li/a/@href').extract()
            for sub in subs:
                items.append(Request(url=sub, callback=self.parse_sort, meta={'cat_id': cat_id,'page':1}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_sort(self,response):
        items = []
        try:
            logging.log(logging.INFO, 'parse_sort: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            subs = response.xpath('//div[@class="mod_tab_sort"]/ul/li/a/@href').extract() 
            for sub in subs:
                items.append(Request(url=sub, callback=self.parse, meta={'cat_id': cat_id,'page':1}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    #for each category parse all its sub-categories or types,called by parse_sort
    def parse(self, response):
        items = []
        try:
            page = response.request.meta['page']
            logging.log(logging.INFO, 'lev1: %s,%s' % (str(page),response.request.url))
            #if int(page) > int(self.max_update_page) and not self.global_spider:
            #    return

            cat_id = response.request.meta['cat_id']
            page = response.request.meta['page']

            play_url = ""
            subs = response.xpath('//div[@class="grid_18"]/div[2]/div[@class="mod_cont"]/div[@class="mod_item"]')
            # 综艺页面不统一
            if not subs:
                subs = response.xpath('//div[@class="grid_18"]/div[2]/div[@class="mod_cont"]/div[@class="mod_item pic_160"]')

            for sub in subs:
                play_url = sub.xpath('./div[@class="mod_txt"]/div[@class="mod_operate"]/a/@href').extract()
                if not play_url:
                    play_url = sub.xpath('./div[@class="mod_txt"]/div[@class="mod_item_tit"]/h6/a/@href').extract()
                pic_urls = sub.xpath('./div[@class="mod_pic"]/a/img/@src').extract()
                pic_url = ""
                if pic_urls:
                    pic_url = pic_urls[0]
                items.append(Request(url=play_url[0].strip(),callback=self.parse_episode,meta={'cat_id': cat_id,'poster_url':pic_url}))

            next_page = response.xpath("//div[@class='mod_pagenav']/p/a[@title='%s']/@href" % u'下一页').extract()
            if next_page:
                snext_page = next_page[0].strip()
                if snext_page.find("v.qq.com") < 0:
                    snext_page = "http://v.qq.com" + snext_page
                items.append(Request(url=snext_page, callback=self.parse, meta={'page': page+1, 'cat_id': cat_id}))

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_episode_play(self,response):
        mvitem = None
        try:
            logging.log(logging.INFO, 'parse_episode_play: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            poster_url = ""
            untrack_id = ""
            sid = ""
            if "untrack_id" in response.request.meta:
                untrack_id = response.request.meta['untrack_id']
            if "sid" in response.request.meta:
                sid = response.request.meta['sid']
            #items = []

            #title
            title_list = response.xpath('//div[@class="movie_info"]/div[@class="title_wrap"]/h3/a/@title').extract()
            if not title_list:
                title_list = response.xpath('//div[@class="intro_lt"]/div[@class="intro_title cf"]/p[@class="title_cn"]/text()').extract() 
            #performer
            performer_list = response.xpath('//div[@class="movie_info"]/div[@class="movie_detail"]/dl[@class="detail_list"]/dd[@class="actor"]/a/text()').extract()
            #director
            director_list = response.xpath('//div[@class="movie_info"]/div[@class="movie_detail"]/dl[@class="detail_list"]/dd[@class="type"]/span[text()="%s"]/a/text()' % u'导演：').extract()
            #type_list = response.xpath('//div[@class="movie_info"]/div[@class="movie_detail"]/dl[@class="detail_list"]/dd[@class="type"]/span[text()="%s"]/a/text()' % u'导演：').extract()

            pers = Util.join_list_safely(performer_list)
            dirs = Util.join_list_safely(director_list)

            #text
            text = response.xpath('//div[@class="movie_info_wrap"]/div[1]/d1[1]/dd[3]/p[@class="detail_all"]/text()').extract()

            ep_item = MediaItem()
            videoitems = []

            #not film
            if int(cat_id) != int(self.movie_id):
                #video list
                #video_list = response.xpath('//div[@class="mod_player_side_inner"]/div[2]/div[1]/div[1]/div[1]/div[1]/ul[1]/li')
                video_list = response.xpath('//div[@class="tabcont_warp tabcont_warp_yespadding"]/div[@class="tabcont_album"]/ul[@class="album_list cf"]/li')
                i = 0
                for tvideo in video_list:
                    lurl = tvideo.xpath('./a/@href').extract()
                    surl = ""
                    #lnum = tvideo.xpath('./a/@title').extract()
                    lnum = tvideo.xpath('./a/span/text()').extract()

                    vitem = VideoItem()
                    if lnum and lurl:
                        vitem["vnum"] = lnum[0]
                        surl = "http://film.qq.com" + lurl[0]
                        vitem["os_id"] = self.os_id
                        vitem["site_id"] = self.site_id
                        #vitem["cont_id"] = self.get_vid(response.body,surl)
                        turl = ""
                        if cat_id == self.tv_id:
                            turl = Util.normalize_url(surl,"qq","tv")
                        if cat_id == self.cartoon_id:
                            turl = Util.normalize_url(surl,"qq","cartoon")
                        else:
                            turl = Util.normalize_url(surl,"qq")
                        if turl:
                            vitem["ext_id"] = Util.md5hash(turl)
                            vitem["url"] = turl
                        vitem["cont_id"] = self.get_qq_showid(vitem["url"])
                    else:
                        continue

                    videoitems.append(vitem)
            else:
                vitem = VideoItem()
                if title_list:
                    vitem["title"] = title_list[0]
                vitem["vnum"] = "1"
                vitem["os_id"] = self.os_id
                vitem["site_id"] = self.site_id
                #vitem["cont_id"] = self.get_vid(response.body,response.request.url)
                turl = Util.normalize_url(response.request.url,"qq")
                vitem["url"] = turl
                vitem["ext_id"] = Util.md5hash(turl)
                vitem["cont_id"] = self.get_qq_showid(vitem["url"])
                videoitems.append(vitem)

            if len(title_list) > 0:
                ep_item["title"] = title_list[0]
            if len(pers) > 0:
                ep_item["actor"] = pers
            if len(dirs) > 0:
                ep_item["director"] = dirs
            if len(text) > 0:
                ep_item["intro"] = text[0]
            ep_item["site_id"] = self.site_id
            ep_item["channel_id"] = cat_id
            ep_item["poster_url"] = poster_url

            videoid = self.get_qq_showid(response.request.url)
            #videoid = self.get_vid(response.body,response.request.url)
            ep_item["cont_id"] = videoid
            
            mvitem = MediaVideoItem();
            mvitem["media"] = ep_item;
            mvitem["video"] = videoitems
            #mvitem["media"]["url"] = response.request.url
            mvitem["media"]["url"] = Util.normalize_url(response.request.url,"qq")
            #mvitem["ext_id"] = Util.md5hash(mvitem["media"]["url"])
            
            if untrack_id:
                 mvitem["untrack_id"] = untrack_id
            if sid:
                mvitem["sid"] = sid
            mvitem["media"]["info_id"] = Util.md5hash(Util.summarize(mvitem["media"]))
            Util.md5hash(Util.summarize(mvitem["media"])) 
            Util.set_ext_id(mvitem["media"],mvitem["video"])
            #items.append(mvitem)
            
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return mvitem

    #先进入播放页，再进入媒体页，判断是否能进入媒体页，如果不能进入，就直接解析播放页信息
    def parse_episode(self,response):
        items = []
        try:
            logging.log(logging.INFO, 'lev2: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            poster_url = response.request.meta['poster_url']

            urls = response.xpath('//div[@class="breadcrumb"]/a[@class="breadcrumb_item"]/@href').extract()
            #carton is different
            if not urls:
                turls = response.xpath('//div[@class="mod_player_head cf"]/div[1]/div[1]/a/@href').extract()
                if turls:
                    tlen = len(turls)
                    urls = [turls[tlen-1]]
            if urls:
                turl = self.url_prefix + urls[0]
                items.append(Request(url=turl, callback=self.parse_episode_info, meta={'cat_id': cat_id,'poster_url':poster_url}))
            #不就跳转到媒体页
            else:
                print "2-----------------------not jump to episode ,",response.request.url
                titem = self.parse_episode_play(response)
                if titem and self.check_url(titem):
                    items.append(titem)

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

            #title
            title = response.xpath('//div[@class="mod_video_intro mod_video_intro_rich"]/div[@class="video_title"]/strong/a/text()').extract()
            if not title or not title[0]:
                title = response.xpath('//div[@class="mod_box mod_video_info"]/div[@class="mod_hd mod_hd_border"]/h1/strong/@title').extract()
                if not title or not title[0]:
                    title = response.xpath('//div[@class="mod_box mod_video_info"]/div[@class="mod_hd mod_hd_border"]/h2/strong/@title').extract()
                    if not title or not title[0]:
                        title = response.xpath('//div[@class="mod_page_banner"]/div[@class="banner_pic"]/a/@title').extract()
            #performer
            #performer_list = response.xpath('//div[@class="mod_video_intro mod_video_intro_rich"]/div[2]/div[2]/div[1]/a/span/text()').extract()
            performer_list = response.xpath('//div[@class="mod_video_intro mod_video_intro_rich"]/div[@class="video_info cf"]/div[@class="info_line cf"]/div[@class="info_cast"]/a/span/text()').extract()
            if not performer_list:
                performer_list = response.xpath('//div[@class="video_info cf"]/div[@class="info_line cf"]/p/span[text()="%s"]/../span[@class="content"]/a/span/text()' % u'主演：' ).extract()
            #director
            #director_list=response.xpath('//div[@class="mod_video_intro mod_video_intro_rich"]/div[2]/div[3]/div[1]/a/span/text()').extract()
            director_list = response.xpath('//div[@class="mod_video_intro mod_video_intro_rich"]/div[@class="video_info cf"]/div[@class="info_line cf"]/div[@class="info_director"]/a/span/text()').extract()
            if not director_list:
                director_list = response.xpath('//div[@class="video_info cf"]/div[@class="info_line cf"]/p/span[text()="%s"]/../span[@class="content"]/a/span/text()' % u'导演：' ).extract()
            #text
            text = response.xpath('//div[@class="movie_info_wrap"]/div[1]/d1[1]/dd[3]/p[@class="detail_all"]/text()').extract()
            if not text:
                response.xpath('//div[@class="mod_video_focus"]/div[@class="info_desc"]/span[@class="desc"]/text()').extract() 
            type_list = response.xpath('//div[@class="mod_video_intro mod_video_intro_rich"]/div[@class="video_info cf"]/div[@class="info_line info_line_tags cf"]/div[@class="info_tags"]/a/span/text()').extract()
            if not type_list:
                type_list = response.xpath('//div[@class="video_info cf"]/div[@class="info_line cf"]/p/span[text()="%s"]/../span[@class="content"]/a/text()' % u'类型：' ).extract()
            year_info = response.xpath('//div[@class="mod_video_intro mod_video_intro_rich"]/div[@class="video_title"]/span[@class="video_current_state"]/span[@class="current_state"]/text()').extract()
            if not year_info:
                year_info = response.xpath('//div[@class="video_info cf"]/div[@class="info_line cf"]/p/span[text()="%s"]/../span[@class="content"]/a/text()' % u'年份：' ).extract()
            play_date = None
            if year_info:
                play_date = self.get_year(year_info[0])

            #
            dirs = Util.join_list_safely(director_list)
            types = Util.join_list_safely(type_list)
            pers = Util.join_list_safely(performer_list)
            
            #sourceid
            sourceid = ""
            sourceid_list = response.xpath('//div[@class="mod_bd sourceCont"]/@sourceid').extract()
            if sourceid_list:
                sourceid = sourceid_list[0]

            videoitems = []

            ep_item = MediaItem()

            if len(title) > 0:
                ep_item["title"] = title[0]
            if len(pers) > 0:
                ep_item["actor"] = pers
            if len(dirs) > 0:
                ep_item["director"] = dirs
            if types:
                ep_item["type"] = types
            if play_date:
                ep_item["release_date"] = Util.str2date(play_date)

            ep_item["site_id"] = self.site_id
            ep_item["channel_id"] = cat_id
            ep_item["url"] = Util.normalize_url(response.request.url,"qq")
            ep_item["poster_url"] = poster_url
            
            if len(text) > 0:
                ep_item["intro"] = text[0]

            mvitem = MediaVideoItem();
            mvitem["media"] = ep_item;
            mvitem["video"] = videoitems

            vurl = ""
            url_pre = "http://s.video.qq.com/loadplaylist?vkey="
            url_tail = "&vtype=2&otype=json&video_type=2&callback=jQuery191048201349820010364_1425370006500&low_login=1"

            videoid = self.get_qq_showid(response.request.url)
            #videoid = self.get_vid(response.body,response.request.url)
            mvitem["media"]["cont_id"] = videoid
            mvitem["media"]["info_id"] = Util.md5hash(Util.summarize(mvitem["media"]))
            vurl = url_pre + str(sourceid) + url_tail

            tflag = "jQuery191048201349820010364_1425370006500"
            tpitem = self.parse_play_list(cat_id,vurl,tflag,response)
            #没有sourceid，比如专题页面
            if not tpitem:
                tpitem = self.parse_topic_play_list(response)
                videoids = response.xpath('//div[@class="mod_episodes_info episodes_info"]/input[@name="cid"]/@value').extract()
                if videoids:
                    mvitem["media"]["cont_id"] = videoids[0]
            if tpitem:
                mvitem["video"] = tpitem
                Util.set_ext_id(mvitem["media"],mvitem["video"])
                if untrack_id:
                    mvitem["untrack_id"] = untrack_id
                if sid:
                    mvitem["sid"] = sid
                if self.check_url(mvitem):
                    items.append(mvitem)
        except Exception as e: 
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def parse_play_list(self,cat_id,url,flag,response):
        item = None
        videoitems = []
        try:
            ep_item = MediaItem()
            item = MediaVideoItem()
            item["media"] = ep_item
            item['video'] = videoitems

            info = None
            try:
                info = self.httpdownload.get_data(url)
            except Exception as e:
                logging.log(logging.ERROR, traceback.format_exc())
                return videoitems
            if not info or len(info) < 2:
                return videoitems

            msg = info
            bodylen = len(msg)-1
            index = msg.find(flag) + len(flag) + 1
            info = msg[index:bodylen]
            jinfo = json.loads(info)
            if "video_play_list" not in jinfo:
                return videoitems
            itemlist = jinfo["video_play_list"]["playlist"]
            for titem in itemlist:
                if "episode_number" not in titem:
                    continue
                info = titem["episode_number"]
                if info and titem["title"].find(u"预告") < 0 and url.find("qq.com") >= 0:
                    vitem = VideoItem()
                    vitem["title"] = titem["title"]
                    tvnum = string.replace(info,"-","")
                    #集数不是数字，是字符串，http://v.qq.com/detail/x/xk98t8hntls72f4.html
                    tvnum_list = re.findall(r'[\D]+', tvnum)
                    if not tvnum_list:
                        vitem["vnum"] = string.replace(info,"-","")
                    else:
                        continue
                    vitem["os_id"] = self.os_id
                    vitem["site_id"] = self.site_id
                    turl = ""
                    if int(cat_id) == int(self.tv_id) or int(cat_id) == int(self.cartoon_id):
                        turl = Util.normalize_url(titem["url"],"qq","tv")
                    else:
                        turl = Util.normalize_url(titem["url"],"qq")
                    if turl:
                        vitem["ext_id"] = Util.md5hash(turl) 
                        #vitem["cont_id"] = self.get_vid(response.body,turl)
                        vitem["url"] = turl
                        vitem["cont_id"] = self.get_qq_showid(vitem["url"])
                    else:
                        continue
                    videoitems.append(vitem)
                    
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return videoitems

    def parse_topic_play_list(self,response):
        item = None
        videoitems = []
        try:
            subs = response.xpath('//div[@class="mod_video_fragments"]/div[@class="mod_figures_1"]/ul/li')
            for sub in subs:
                vitem = VideoItem()
                title = sub.xpath('./strong/a/text()').extract()
                vitem["os_id"] = self.os_id
                vitem["site_id"] = self.site_id
                turl = sub.xpath('./strong/a/@href').extract()
                if title and title[0].find(u"预告") < 0 :
                    if turl and turl[0].find(".com") < 0 or (turl and turl[0].find("qq.com") >=0 ):                           
                        vitem["title"] = title[0].strip()
                        vitem["vnum"] = self.get_num(vitem["title"])
                        sturl = turl[0]
                        if turl[0].find("qq.com") < 0:
                            sturl = self.url_prefix+turl[0]
                        vitem["url"] = Util.normalize_url(sturl,"qq","tv")
                        vitem["ext_id"] = Util.md5hash(vitem["url"]) 
                        vitem["cont_id"] = self.get_qq_showid(vitem["url"])
                        videoitems.append(vitem)
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return videoitems

    def get_qq_showid(self,url):
        id = ""
        try:
            #http://v.qq.com/detail/j/jlw8mddv9wkv1a3.html
            #http://film.qq.com/cover/y/yuq5nnt2wwlwfle.html
            #r = re.compile(r'http://.+/id_([^_]+).*\.html')
            #r = re.compile(r'http://.+/.+/[0-9a-zA-Z]/([^_]+).*\.html')
            r = re.compile(r'http://[^/]*.qq.com/cover/.+?/([^/]*).html')
            m = r.match(url)
            if m:
                return m.group(1)
            else:
                r = re.compile(r'http://[^/]*.qq.com/[^/]*/.+?/([^/]*).html')
                m = r.match(url)
                if m:
                    return m.group(1) 
        except Exception as e:
            pass
        return id

    def get_vid(self,content,url):
        id = ""
        try:
            #url=http://v.qq.com/cover/k/krl2051za26trxu.html?vid=r0016fx050p"
            if url and url.find("vid") != -1:
                r = re.compile(r'.*[?&]vid=([^&]+)')
                m = r.search(url)
                if m:
                    id = m.group(1)
            if not id and len(content) > 0 :
                #vid:"f0016l11uqt"
                #r = re.compile(r'vid:.([^"])"')
                r = re.compile(r'vid:.(.*)".*')
                m = r.search(content)
                if m:
                    id = m.group(1)
                if not id:
                    #r = re.compile(r".*vid.:.(.*)'.*")
                    r = re.compile(r".*vid.:.'(.*)'.*")
                    m = r.search(content)
                    if m:
                        id = m.group(1)
         
            if not id:
                id = self.get_qq_showid(url)
        except Exception as e:
            pass
        return id

    def convert_url(self,url):
        res = url
        try:
            pass
        except Exception as e:
            pass
        return res

    def check_all(self,mvitem):
        res = True
        try:
            if 'video' not in mvitem:
                res = False
            if 'video' in mvitem:
                if len(mvitem['video']) == 0:
                    res = False

            if res:
                res = self.check_url(mvitem)
        except Exception as e:
            pass
        return res

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

    def get_year(self,data):
        year = None
        try:
            #r = re.compile(r'.*([\d]+).*')
            #m = r.match(data)
            #m = r.search(data)
            #if m:
            #    print "get year",data,m.group(1)
            #    return m.group(1)
            tyear = re.findall(r'[\d]+', data)
            if tyear:
                return tyear[0]
        except Exception as e:
            pass
        return year

    def get_num(self,data):
        num = None
        try:
            #r = re.compile(r'.*(\d+).*')
            #m = r.search(data)
            #if m:
            #    return m.group(1)
            num = re.findall(r'[\d]+', data)
            if num:
                return num[0]
        except Exception as e:
            pass
        return num

