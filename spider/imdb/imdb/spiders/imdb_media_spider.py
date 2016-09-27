# -*- coding:utf-8 -*-
from scrapy.spiders import Spider
from scrapy.http import Request
import logging
import traceback
import json
import re
from imdb.items import ImdbMediaVideoItem
from imdb.items import ImdbMediaItem
from imdb.items import ImdbVideoItem
try:
    from imdb.hades_db.db_mgr import DbManager
    from baidusoftware.hades_common.util import Util
except ImportError:
    from hades_db.db_mgr import DbManager
    from hades_common.util import Util
    
class ImdbMediaSpider(Spider):
    name = "imdb_media"
    pipelines = ['MysqlStorePipeline']
    mgr = DbManager.instance()
    
    def __init__(self, *args, **kwargs):
        super(ImdbMediaSpider, self).__init__(*args, **kwargs)
        self._unspidered_imdbs = self.mgr.get_unspidered_imdbs()
        self._imdb_api = "http://www.imdb.com/title/%s/"
        self._season_api = "http://www.imdb.com/title/%s/episodes?season=%s"
        self._host = "http://www.imdb.com"
    
    def start_requests(self):
        try:
            for imdb in self._unspidered_imdbs:
                yield Request(url=self._imdb_api % imdb, callback=self.parse_imdb)
        
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
    def parse_imdb(self, response):
        items = []
        try:
            type_sel = response.xpath('//head/meta[@property="og:type"]/@content').extract()
            if type_sel:
                og_type = type_sel[0]
                if og_type == "video.movie":
                    items = self.build_movie_item(response)
                    
                elif og_type == "video.tv_show":
                    all_episode_sel = response.xpath('//div[@class="vital"]/div/a[@class="bp_item np_episode_guide np_right_arrow"]/@href').extract()
                    if all_episode_sel:
                        all_episode_page = self._host + all_episode_sel[0]
                        items.append(Request(all_episode_page, callback=self.parse_all_episode))
                        
                elif og_type == "video.episode":
                    all_episode_sel = response.xpath('//div[@class="vital"]/div/a[@class="bp_item np_all"]/@href').extract()
                    if all_episode_sel:
                        all_episode_page = self._host + all_episode_sel[0]
                        items.append(Request(all_episode_page, callback=self.parse_all_episode))
            
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
    def parse_all_episode(self, response):
        items = []
        try:
            root_imdb = self.get_imdb(response.request.url)
            season_sel = response.xpath('//div[@class="seasonAndYearNav"]//select[@id="bySeason"]/option/text()').extract()
            if season_sel:
                for i in season_sel:
                    i = i.strip()
                    if i and i != "Unknown":
                        season_num = int(i)
                        season_page = self._season_api % (root_imdb, season_num)
                        items.append(Request(season_page, callback=self.parse_season, meta={"root_imdb":root_imdb, "season":season_num}))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
    def parse_season(self, response):
        items = []
        try:
            root_imdb = response.request.meta['root_imdb']
            season = response.request.meta['season']
            media_video_item = ImdbMediaVideoItem()
            media_item = ImdbMediaItem()
            title_sel = response.xpath('//div[@class="parent"]/h3/a/text()').extract()
            media_item['title'] = title_sel[0]
            media_item['pimdb'] = root_imdb
            media_item['snum'] = season
            
            video_item_list = []
            video_sel = response.xpath('//div[@class="list detail eplist"]//strong/a')
            i = 1
            if video_sel:
                for sel in video_sel:
                    video_item = ImdbVideoItem()
                    url_sel = sel.xpath('./@href').extract()
                    if url_sel:
                        video_url = self._host + url_sel[0]
                        video_item['imdb'] = self.get_imdb(video_url)
                        
                    video_title_sel = sel.xpath('./text()').extract()
                    if video_title_sel:
                        video_title = video_title_sel[0]
                        video_item['title'] = video_title
                    
                    video_item['enum'] = i
                    if video_item:
                        i += 1
                        video_item_list.append(video_item)
                        
            if season == 1:
                media_item['imdb'] = root_imdb
            else:
                media_item['imdb'] = video_item_list[0]['imdb']
                
            for i in video_item_list:
                i['pimdb'] = media_item['imdb']
                
            media_video_item['media'] = media_item
            media_video_item['video'] = video_item_list
            items.append(media_video_item)
            
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
                
        finally:
            return items
            
    def build_movie_item(self, response):
        items = []
        try:
            media_video_item = ImdbMediaVideoItem()
            media_item = ImdbMediaItem()
            imdb = self.get_imdb(response.request.url)
            media_item['imdb'] = imdb
            media_item['pimdb'] = imdb
            media_item['title'] = self.get_title(response)
            actor_list = self.parse_actors(response)
            media_item["actor"] =  Util.join_list_safely(actor_list)
            director_list = self.parse_director(response)
            media_item["director"] = Util.join_list_safely(director_list)
            
            video_item_list = []
            video_item = ImdbVideoItem()
            video_item['imdb'] = imdb
            video_item['pimdb'] = imdb
            video_item['title'] = media_item['title']
            video_item_list.append(video_item)
            
            media_video_item['media'] = media_item
            media_video_item['video'] = video_item_list
            items.append(media_video_item)
            
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
    def get_title(self, response):
        title = ""
        title_list = response.xpath('//div[@class="title_wrapper"]/h1/text()').extract()
        if title_list:
            title = title_list[0].replace(u"\xa0",u"")
        return title
        
    def parse_actors(self,response):
        actor_list = []
        try:
            actor_list =  response.xpath('//div[@class="plot_summary "]/div/span[@itemprop="actors"]/a/span/text()').extract()
            if not actor_list:
                actor_list=response.xpath('//div[@class="plot_summary minPlotHeightWithPoster"]/div/span[@itemprop="actors"]/a/span/text()').extract()
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return actor_list

    def parse_director(slef,response):
        director_list = []
        try:
            director_list = response.xpath('//div[@class="plot_summary "]/div/span[@itemprop="director"]/a/span/text()').extract()
            if not director_list:
                director_list=response.xpath('//div[@class="plot_summary minPlotHeightWithPoster"]/div/span[@itemprop="director"]/a/span/text()').extract()
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
        return director_list
        
    def get_imdb(self, url):
        id = ""
        r = re.compile(r'.*/title/(.*)/.*')
        m = r.match(url)
        if m:
            id = m.group(1)
        return id

            