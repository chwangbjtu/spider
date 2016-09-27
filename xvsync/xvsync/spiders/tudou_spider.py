# -*- coding:utf-8 -*-
from scrapy.spiders import Spider
from scrapy.selector import Selector
from scrapy.http import Request
import logging
from xvsync.common.util import Util
from xvsync.items import MediaItem
from xvsync.items import MediaVideoItem
from xvsync.items import VideoItem
from xvsync.common.http_download import HTTPDownload
from xvsync.db.db_mgr import DbManager
from scrapy.utils.project import get_project_settings
import traceback
import re
import json
import string
from datetime import datetime

class tudou_spider(Spider):
    name = "tudou"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    site_code = "tudou"
    site_id = ""   #tudou
    allowed_domains = ["www.tudou.com"]
    pre_url = "http://www.tudou.com/s3portal/service/pianku/data.action?pageSize=90&app=mainsitepc&deviceType=1&tags=&tagType=3&firstTagId="
    tail_url = "&areaCode=110000&initials=&hotSingerId=&sortDesc=pubTime&pageNo="
    #used for guess_site 
    site_name = Util.guess_site("http://www.tudou.com")

    mgr = DbManager.instance()
    os_id = mgr.get_os('web')["os_id"]
    site_id = str(mgr.get_site(site_code)["site_id"])
    channel_map = {}
    channel_map = mgr.get_channel_map()
    max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
    id_map = {}
    httpdownload = HTTPDownload()
    cmd = None

    def __init__(self, json_data=None, *args, **kwargs):
        super(tudou_spider, self).__init__(*args, **kwargs)
        cat_urls = []
        tasks = []
        if json_data:
            data = json.loads(json_data)
            self.cmd = data["cmd"]
            if self.cmd == "assign":
                tasks = data["task"]
            elif self.cmd == "trig":
                stat = data['stat'] if 'stat' in data else None
                tasks = self.mgr.get_untrack_url(self.site_code, stat)
            ttask={}
            if "id" in data and "url" in data:
                ttask["id"] = data["id"]
                ttask["url"] = data["url"]
                ttask["sid"] = ""
                ttask["untrack_id"] = ""
                cat_urls.append(ttask)
            if tasks:
                for task in tasks:
                    ttask={}
                    ttask["url"] = task["url"]
                    code = task["code"]
                    ttask["id"] = self.channel_map[code]
                    ttask["untrack_id"] = task["untrack_id"]
                    ttask["sid"] = task["sid"]
                    cat_urls.append(ttask)
            #cat_urls = data["cat_urls"]

        self._cat_urls = []
        if cat_urls:
            self._cat_urls = cat_urls

    def start_requests(self):
        try:
            items = []

            cat_urls = []

            movie_id = self.mgr.get_channel('电影')["channel_id"]
            tv_id = self.mgr.get_channel('电视剧')["channel_id"]
            variety_id = self.mgr.get_channel('综艺')["channel_id"]
            cartoon_id = self.mgr.get_channel('动漫')["channel_id"]

            self.id_map = {str(movie_id):"5",str(tv_id):"3",str(variety_id):"6",str(cartoon_id):"4"}
            #不需要url字段，通过土豆网不同频道的id来拼出url
            if not self._cat_urls and not self.cmd:
                #cat_urls = [{'url':'','id':tv_id}]
                cat_urls = [{'url':'','id':movie_id},
                        {'url':'','id':tv_id},
                        {'url':'','id':variety_id},
                        {'url':'','id':cartoon_id}]

                for cat in cat_urls:
                    url = ""
                    type_id = ""
                    if cat['id'] == movie_id:
                        type_id = self.id_map[str(movie_id)]
                    elif cat['id'] == tv_id:
                        type_id = self.id_map[str(tv_id)]
                    elif cat['id'] == variety_id:
                        type_id = self.id_map[str(variety_id)]
                    elif cat['id'] == cartoon_id:
                        type_id = self.id_map[str(cartoon_id)]
                    url = self.pre_url + type_id + self.tail_url
                    page_num = int(self.get_page_num(url+ "10000"))/90 + 1
                    #page_num = 4
                    for i in range(page_num):
                        surl = self.pre_url + type_id + self.tail_url + str(i+1)
                        items.append(Request(url=surl, callback=self.parse, meta={'cat_id': cat['id'],'page':1}))
            else:
                for cat in self._cat_urls:
                    channel_id = str(cat["id"])
                    items.append(Request(url=cat['url'], callback=self.parse_single_episode, meta={'cat_id': channel_id,'page':1,"untrack_id":cat["untrack_id"],"sid":cat["sid"]}))

            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_page_num(self,url):
        num = None
        try:
            info = self.httpdownload.get_data(url)
            jinfo = json.loads(info)
            num = jinfo["total"]
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

        return num

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
                urls = response.xpath('//div[@class="mod_player_head cf"]/div[1]/div[1]/a[3]/@href').extract()

            if urls:
                turl = self.url_prefix + urls[0]
                items.append(Request(url=turl, callback=self.parse_episode_info, meta={'cat_id': cat_id,'poster_url':'','page':1,"untrack_id":untrack_id,"sid":sid}))
            else:
                poster_url = ""
                title = ""
                actor = ""
                info_url = response.xpath('//div[@class="summary_main"]/div[@class="fix"]/h1[@class="kw"]/a/@href').extract()
                if info_url:
                    items.append(Request(url=info_url[0], callback=self.parse_episode_info, meta={'cat_id': cat_id,'poster_url':poster_url,'title':title,"actor":actor,"untrack_id":untrack_id,"sid":sid}))
                #items.append(Request(url=response.request.url, callback=self.parse_episode_play, meta={'cat_id': cat_id,'poster_url':'','page':1}))
                #response.request.meta['poster_url'] = ''
                #self.parse_episode_play(response)

            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse(self,response):
        try:
            logging.log(logging.INFO, 'parse: %s' % response.request.url)
            
            cat_id = response.request.meta['cat_id']
            #poster_url = response.request.meta['poster_url']
            items = []

            play_url = ""
            jinfo = json.loads(response.body)
            for tmedia in jinfo["items"]:
                title = tmedia["title"]
                actor_list = []
                for tactor in tmedia["actors"]:
                    actor_list.append(tactor["name"])
                actor = Util.join_list_safely(actor_list)
                #actor = "|".join([t.strip() for t in actor_list])
                poster_url = tmedia["picUrl_200x300"]
                play_url = tmedia["playUrl"]
                if "updateInfo" in tmedia and tmedia["updateInfo"].find("预告") >= 0:
                    continue
                else:
                    items.append(Request(url=play_url, callback=self.parse_episode_play, meta={'cat_id': cat_id,'poster_url':poster_url,'title':title,'actor':actor}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

        return items

    def parse_episode_play(self,response):
        try:
            logging.log(logging.INFO, 'parse_episode_play: %s' % response.request.url)

            cat_id = response.request.meta['cat_id']
            poster_url = response.request.meta['poster_url']
            title = response.request.meta['title']
            actor = response.request.meta['actor']
            
            items = []

            info_url = response.xpath('//div[@class="summary_main"]/div[@class="fix"]/h1[@class="kw"]/a/@href').extract()
            if info_url:
                items.append(Request(url=info_url[0], callback=self.parse_episode_info, meta={'cat_id': cat_id,'poster_url':poster_url,'title':title,"actor":actor}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc()) 

        return items

    def parse_episode_info(self,response):
        try:
            logging.log(logging.INFO, 'parse_episode_info: %s' % response.request.url)
            cat_id = response.request.meta['cat_id']
            poster_url = response.request.meta['poster_url']
            title = response.request.meta['title']
            actor = response.request.meta['actor']
            untrack_id = ""
            sid = ""
            if "untrack_id" in response.request.meta:
                untrack_id = response.request.meta['untrack_id']
            if "sid" in response.request.meta:
                sid = response.request.meta['sid']
            items = []

            if not poster_url:
                poster_url_list = response.xpath('//div[@class="cover_img"]/div[@class="pack pack_album"]/div[@class="pic"]/img/@src').extract()
                if poster_url_list:
                    poster_url = poster_url_list[0]
            if not title:
                title_list = response.xpath('//div[@class="cover_info"]/h2/strong/@title').extract()
                if title_list:
                    title = title_list[0]
            if not actor:
                #actor_list = response.xpath('//div[@class="cover_keys"]/span/a/text()').extract()
                actor_list = response.xpath('//div[@class="cover_keys"]/span/span[text()="%s"]/../a/text()'  % u' 主演：').extract()
                if actor_list:
                    actor = Util.join_list_safely(actor_list)
                    #actor = "|".join([t.strip() for t in actor_list])

            #performer
            pers = actor
            type_list = response.xpath('//div[@class="cover_keys"]/span/span[text()="%s"]/../a/text()'  % u'类型：\n').extract()
            district_list = response.xpath('//div[@class="cover_keys"]/span/span[text()="%s"]/../a/text()'  % u'地区：').extract()
            release_date_list = response.xpath('//div[@class="cover_keys"]/span/span[text()="%s"]/../a/text()'  % u'年代：').extract()
            types = None
            if type_list:
                types = Util.join_list_safely(type_list)
            
            #director
            director_list = response.xpath('//div[@class="cover_keys"]/span/span[text()="%s"]/../a/text()'  % u'编导：').extract()
            if not director_list:
                director_list = response.xpath('//div[@class="cover_keys"]/span/span[text()="%s"]/../a/text()'  % u'导演：').extract()
            dirs = Util.join_list_safely(director_list)
            #dirs = "|".join([t.strip() for t in director_list])
            #text
            text = response.xpath('//div[@class="cover_info"]/div[@class="desc"]/p/text()').extract()

            #sourceid
            sourceid = self.get_tudou_showid(response.request.url)
            videoitems = []
            ep_item = MediaItem()

            if len(title) > 0:
                ep_item["title"] = title
            if len(pers) > 0:
                ep_item["actor"] = pers
            if len(dirs) > 0:
                ep_item["director"] = dirs
            if types:
                ep_item["type"] = types
            if district_list:
                ep_item["district"] = district_list[0].strip()
            if release_date_list:
                ep_item["release_date"] = Util.str2date(release_date_list[0])

            #ep_item["info_id"] = Util.md5hash(tinfo)
            ep_item["cont_id"] = sourceid
            ep_item["site_id"] = self.site_id
            ep_item["url"] = response.request.url
            ep_item["channel_id"] = cat_id
            ep_item["poster_url"] = poster_url
            
            if len(text) > 0:
                ep_item["intro"] = text[0]

            mvitem = MediaVideoItem();
            mvitem["media"] = ep_item;
            mvitem["video"] = videoitems

            lurl = "http://www.tudou.com/crp/getAlbumvoInfo.action?charset=utf-8&areaCode=110000&acode=" + str(sourceid)
            info = self.httpdownload.get_data(lurl)
            jinfo = json.loads(info)
            if "items" in jinfo:
                for sitem in jinfo["items"]:
                    vitem = VideoItem()
                    vitem["title"] = sitem["itemTitle"]
                    vitem["vnum"] = sitem["episode"]
                    vitem["os_id"] = self.os_id
                    trailer = sitem['trailer']
                    if not sitem["itemPlayUrl"]:
                        continue
                    #预告片
                    if trailer:
                        continue
                    turl = Util.normalize_url(sitem["itemPlayUrl"],"tudou")
                    vitem["url"] = turl
                    vitem["os_id"] = self.os_id
                    vitem["site_id"] = self.site_id
                    vitem["ext_id"] = Util.md5hash(turl)
                    vitem["cont_id"] = self.get_tudou_showid(turl)
                    #if "ext_id" not in mvitem["media"]:
                    #    mvitem["media"]["ext_id"] = vitem["ext_id"]
                    #vitem["media_ext_id"] = vitem["ext_id"]
                    mvitem["video"].append(vitem)

            if len(mvitem["video"]) > 0:
                Util.set_ext_id(mvitem["media"],mvitem["video"])
                mvitem["media"]["info_id"] = Util.md5hash(Util.summarize(mvitem["media"]))
                if untrack_id:
                    mvitem["untrack_id"] = untrack_id
                if sid:
                    mvitem["sid"] = sid
                if self.check_url(mvitem):
                    items.append(mvitem)
        except Exception as e: 
            logging.log(logging.ERROR, traceback.format_exc())
        return items

    def get_tudou_showid(self,url):
        id = ""
        try:
            #http://www.tudou.com/albumcover/ZPUPBy0CC6c.html
            r = re.compile(r'http://.+/.*/([^/].*).html')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return id

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
