# -*- coding:utf-8 -*- 
from scrapy.spiders import CrawlSpider, Rule
from scrapy.http import Request
from scrapy.linkextractors import LinkExtractor
import logging
import traceback
import json
import re

from scrapy.utils.project import get_project_settings
from hades_common.util import Util
#from imdb.spiders.base.v360_base import *
#from imdb.common.util import *
from imdb.items import MediaItem
from imdb.items import MediaVideoItem
from imdb.items import VideoItem
try:
    from imdb.hades_db.db_mgr import DbManager
except ImportError:
    from hades_db.db_mgr import DbManager

class imdb_spider(CrawlSpider):
    name = "imdb"
    site_code = "imdb"
    allowed_domains = ["www.imdb.com"]
    url_prefix = 'http://www.imdb.com/'

    #rules = (Rule(LinkExtractor(allow=r'.*.imdb.com/title/tt.*', tags=('a',)), callback='parse_media', follow=False, cb_kwargs={'channel': 'movie'}),
    #rules = (Rule(LinkExtractor(allow=r'.*itle/tt.*/\?.*', tags=('a',)), callback='parse_media'),
    rules = (Rule(LinkExtractor(allow=r'.*itle/tt(\d+)/\?.*', tags=('a',)), callback='parse_media',follow=True),
            #Rule(LinkExtractor(allow=r'.*imdb.com/chart/top.*', tags=('a',))),
            #Rule(LinkExtractor(allow=r'.*imdb.com/calendar.*', tags=('a',))),
            )

    start_urls = [#'www.mp4ba.com',
                  'http://www.imdb.com/chart/toptv',
                  'http://www.imdb.com/?ref_=nv_home',
                  #'http://www.imdb.com/title/tt0374463/?ref_=tt_rec_tti',
                  #'http://www.imdb.com/title/tt0111161/?',
                  'http://www.imdb.com/chart/top?ref_=nv_wl_img_3'
                 ]

    def __init__(self, *args, **kwargs):
        super(imdb_spider, self).__init__(*args, **kwargs)
        self.mgr = DbManager.instance()

        self.site_id = self.mgr.get_site_by_code(self.site_code)["site_id"]

    def parse_media(self, response, **kwargs):
        logging.log(logging.INFO, 'parse_media: %s' % response.request.url)
        try:
            
            #channel = kwargs['channel']
            items = []

            ep_item = MediaItem()
            
            title_list = response.xpath('//div[@class="title_wrapper"]/h1/text()').extract()
            if title_list:
                ep_item["title"] = title_list[0].replace(u"\xa0",u"")

            actor_list = self.parse_actors(response)
            ep_item["actor"] =  Util.join_list_safely(actor_list)

            director_list = self.parse_director(response)
            ep_item["director"] = Util.join_list_safely(director_list)

            ep_item["site_id"] = str(self.site_id)
            #ep_item["channel_id"] = self.channel_map['movie']
            ep_item["url"] = response.request.url
            ep_item["cont_id"] = str(self.get_imdb_pageid(response.request.url))
            #ep_item["info_id"] = Util.md5hash(Util.summarize(ep_item))
            
            #mvitem = MediaVideoItem();
            #mvitem["media"] = ep_item;
            

            #mvitem['video'] = []
            #Util.set_ext_id(mvitem["media"], mvitem["video"])
            #items.append(mvitem)
            #print mvitem
            #return items
            items.append(ep_item)
            
            return items

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

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

    def get_imdb_pageid(self,url):
        id = ""
        try:
            #http://www.mp4ba.com/show.php?hash=253c0710f1349efe0c05bdb4b1657637789c8a68
            #http://www.imdb.com/title/tt3072482/
            r = re.compile(r'.*/title/(.*)/.*')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            print "err",e
            pass
        return id
