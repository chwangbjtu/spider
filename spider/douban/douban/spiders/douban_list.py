# -*- coding:utf-8 -*-
import re
import json
import traceback
import logging
from itertools import product
from dateutil import parser
from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.selector import Selector
from douban.items import MediaItem
from douban.spiders.base.douban_common import common_parse_media_plus, get_cookie
from scrapy.utils.project import get_project_settings
try:
    from douban.hades_db.db_mgr import DbManager
    #from douban.hades_db.mongo_mgr import MongoMgr
except ImportError:
    from hades_db.db_mgr import DbManager
    #from hades_db.mongo_mgr import MongoMgr

class DoubanList(Spider):
    '''
    '''
    name = 'douban_list'
    site_code = 'douban'
    mgr = DbManager.instance()
    max_number = 10000

    def __init__(self, *args, **kwargs):
        super(DoubanList, self).__init__(*args, **kwargs)
        self.site_id = self.mgr.get_site_id_by_code(self.site_code)

        self.api_movie_tag = 'https://movie.douban.com/j/search_tags?type=%s' # type in ['movie', 'tv']
        self.api_movie_list = 'https://movie.douban.com/j/search_subjects?type=%s&tag=%s&sort=%s&page_limit=%s&page_start=%s'
        self.api_tag_page = 'https://www.douban.com/tag/%s/?focus=movie'
        self.api_tag_list = 'https://www.douban.com/j/tag/items?start=%s&limit=%s&topic_id=%s&topic_name=%s&mod=movie'
        self.api_latest = 'https://movie.douban.com/j/search_subjects?type=%s&tag=热门&sort=time&page_limit=%s&page_start=0'

    def start_requests(self):
        try:
            items = []
            self.load_member_variable()
            if self.max_number == 0:
                items.extend(self.enter_movie())
            else:
                items.extend(self.enter_latest())
            #items.extend(self.enter_tag())
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    def load_member_variable(self):
        try:
            max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
            if int == type(max_update_page):
                self.max_number = max_update_page
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def enter_latest(self):
        func = lambda t: Request(url=self.api_latest % (t, self.max_number), callback=self.movie_list)
        return map(func, ['tv', 'movie'])

    def enter_movie(self):
        '''
            enter_movie → movie_channel_sort → movie_tag → movie_list → →parse_media
                                                         ↑_____________↓
        '''
        enter_url = 'https://movie.douban.com/'
        return [Request(url=enter_url, callback=self.movie_channel_sort)]

    def movie_channel_sort(self, response):
        try:
            logging.log(logging.INFO, 'movie_channel_sort: %s' % response.request.url)
            #cookie = self.get_cookie(response)
            #if not cookie:
            #    cookie = response.request.cookies
            api_movie_tag = self.api_movie_tag
            # movie、tv
            channels = response.xpath('//div[@class="fliter-wp"]/h2/a/@data-type').extract()
            # recommend、time、rank
            sorts = response.xpath('//div[@class="sort"]/label/input/@value').extract()
            if not channels or not sorts:
                raise Exception, u'xpath become invalid at func:movie_channel_sort'
            #func = lambda c: Request(url=api_movie_tag % c, callback=self.movie_tag, cookies=cookie, meta={'channels':[c], 'sorts':sorts})
            func = lambda c: Request(url=api_movie_tag % c, callback=self.movie_tag, meta={'channels':[c], 'sorts':sorts})
            return map(func, channels)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def movie_tag(self, response):
        try:
            logging.log(logging.INFO, 'movie_tag: %s' % response.request.url)
            #cookie = self.get_cookie(response)
            #if not cookie:
            #    cookie = response.request.cookies
            offset = 20
            start = 0
            aml = self.api_movie_list % ('%s', '%s', '%s', 20, 0)
            tags = json.loads(response.body)['tags']
            sorts = response.request.meta['sorts']
            channels = response.request.meta['channels']
            #func = lambda p:Request(url=aml % p, cookies=cookie, callback=self.movie_list)
            func = lambda p:Request(url=aml % p, callback=self.movie_list)
            return map(func, product(channels, tags, sorts))
            #yield Request(url='https://movie.douban.com/j/search_subjects?type=movie&tag=科幻&sort=recommend&page_limit=20&page_start=0', cookies=cookie, callback=self.movie_list)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def movie_list(self, response):
        try:
            logging.log(logging.INFO, 'movie_list: %s' % response.request.url)
            #cookie = self.get_cookie(response)
            #if not cookie:
            #    cookie = response.request.cookies
            items = []
            subjects = json.loads(response.body).get("subjects", [])
            if subjects:
                # media
                for subject in subjects:
                    mediaItem = MediaItem()
                    url = subject.get('url', '')
                    if not url:
                        continue
                    else:
                        url = url.replace('http:', 'https:')
                    mediaItem['title']  = subject.get('title', '')
                    mediaItem['poster'] = subject.get('cover', '')
                    mediaItem['dou_id'] = int(float(subject['id'])) if 'id' in subject else None
                    mediaItem['score'] = float(subject['rate']) if 'rate' in subject else None
                    #items.append(Request(url=url, callback=self.parse_media, cookies=cookie, meta={'mediaItem':mediaItem}))
                    items.append(Request(url=url, callback=self.parse_media, meta={'mediaItem':mediaItem}))
                if self.max_number == 0:
                    # next_list
                    req_url = response.request.url
                    func = lambda x:x.split('=')[1]
                    channel, tag, sort, offset, pos = map(func, req_url.split('?')[1].split('&'))
                    pos = int(pos) + int(offset)
                    next_list_url = self.api_movie_list % (channel, tag, sort, offset, pos)
                    #items.append(Request(url=next_list_url, cookies=cookie, callback=self.movie_list))
                    items.append(Request(url=next_list_url, callback=self.movie_list))
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    def parse_media(self, response):
        try:
            logging.log(logging.INFO, 'parse_media: %s' % response.request.url)
            mediaItem = common_parse_media_plus(response)
            vcount = mediaItem['vcount'] if 'vcount' in mediaItem else 1
            mediaItem['site_id'] = self.site_id
            print mediaItem
            return mediaItem
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            return mediaItem

    def enter_tag(self):
        '''
        enter_tag → tag_type → tag_cloud → tag_page → tag_js →
        
        '''
        enter_url = 'https://movie.douban.com/tag/'
        return [Request(url=enter_url, callback=self.tag_type)]

    def tag_type(self, response):
        try:
            logging.log(logging.INFO, 'tag_type: %s' % response.request.url)
            tags = response.xpath('//div[@class="article"]/table//a/text()').extract()
            nex = response.xpath('//div[@class="article"]/div[1]/span/a/@href').extract()
            tset = set(tags)
            if nex:
                url = nex[0]
                yield Request(url=url, callback=self.tag_cloud, meta={'tset':tset})
            else:
                raise Exception, u'xpath become invalid at func:tag_type'
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def tag_cloud(self, response):
        try:
            logging.log(logging.INFO, 'tag_cloud: %s' % response.request.url)
            api_tag_page = self.api_tag_page
            tset = response.request.meta['tset'] if 'tset' in response.request.meta else set()
            tags = response.xpath('//div[@class="article"]/div[@class="indent tag_cloud"]/span/a/text()').extract()
            if tags:
                tset.update(tags)
            func = lambda t: Request(url=api_tag_page%t, callback=self.tag_page)
            return map(func, list(tset))
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def tag_page(self, response):
        try:
            logging.log(logging.INFO, 'tag_page: %s' % response.request.url)
            items = []
            dls = response.xpath('//div[@id="movie"]/dl')
            for dl in dls:
                mediaItem = MediaItem()
                urls = dl.xpath('./dd/a[@class="title"]/@href').extract()
                titles = dl.xpath('./dd/a[@class="title"]/text()').extract()
                posters = dl.xpath('./dt/a/img/@src').extract()
                if titles:
                    mediaItem['title'] = titles[0].strip()
                if posters:
                    mediaItem['poster'] = posters[0].strip()
                if urls:
                    items.append(Request(url=urls[0], callback=self.parse_media, meta={'mediaItem':mediaItem}))
            js = response.xpath('//body/script/@src').extract()
            if js:
                items.append(Request(url=js[0], callback=self.tag_js))
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    def tag_parse(self, response):
        try:
            items = []
            sel = Selector(response)
            dls = response.xpath('//div[@id="movie"]/dl')
            
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return items

    def tag_js(self, response):
        try:
            logging.log(logging.INFO, 'tag_js: %s' % response.request.url)
            api_tag_list = self.api_tag_list % (9, 6, '%s', '%s')
            topic_idr = re.compile('topic_id:\s+(\d+)')
            topic_idm = topic_idr.search(response.body)
            if topic_idm:
                topic_id = topic_idm.groups()[0]
            else:
                topic_id = ''

            topic_namer = re.compile('topic_name:\s+\'(.*)\'')
            topic_namem = topic_idr.search(response.body)
            if topic_namem:
                topic_name = topic_namem.groups()[0]
            else:
                topic_name = ''

            if topic_id and topic_name:
                return [Request(url=api_tag_list % (topic_id, topic_name), callback=self.tag_json_list)]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def tag_json_list(self, response):
        try:
            logging.log(logging.INFO, 'tag_json_list: %s' % response.request.url)
            items = []
            
            
            # next_json_list
            req_url = response.request.url
            func = lambda x:x.split('=')[1]
            pos, offset, topic_id, topic_name = map(func, req_url.split('?')[1].split('&'))
            pos = int(pos) + int(offset)
            next_url = self.api_tag_list % (pos, offset, topic_id, topic_name)
            items.append(Request(url=next_url, callback=self.tag_json_list))

        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def enter_search(self):
        pass

