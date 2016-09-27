# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re
import json
import urllib2
import traceback
import time
from datetime import datetime
from scrapy import log
from scrapy.spider import Spider
from scrapy.selector import Selector
from scrapy.http import Request, FormRequest
from crawler.common.util import Util
from crawler.db.db_mgr import DbManager
from crawler.items import EpisodeItem, UserItem
from scrapy.utils.project import get_project_settings

from youku_util import youku_util
from youku_url_extract import youku_url_extract

class youku_spider(Spider):
    
    name = 'youku_spider'
    site_id = '1'

    subscribe_ids = {'all': '1', 'channel':'2', 'keyword':'4', 'page':'8', 'cagtegory':'16', 'subject':'32', 'manual':'64'}

    #prefix urls
    youku_url_prefix = "http://www.youku.com"
    soku_url_prefix = "http://www.soku.com"
    vpaction_url = "http://v.youku.com/v_vpactionInfo/id"
    playlength_url = "http://v.youku.com/player/getPlayList/VideoIDS"

    #global variable
    mgr = DbManager.instance()
    channel_exclude = mgr.get_channel_exclude()
    category_exclude = mgr.get_cat_exclude()
    ordered_played_threshold = get_project_settings().get('ORDERED_PLAYED_THRESHOLD')
    hottest_played_threshold = get_project_settings().get('HOTTEST_PLAYED_THRESHOLD')
    newest_time_threshold = get_project_settings().get('NEWEST_TIME_THRESHOLD')

    #default value
    max_search_page = "0"
    
    def __init__(self, *args, **kwargs):
        super(youku_spider, self).__init__(*args, **kwargs)
        self.spider_parses = {'channel':self.channel_parse,\
                        'video_set':self.video_set_parse,\
                        'search':self.search_parse,\
                        'video':self.video_parse,\
                        'page':self.page_parse,\
                        'user':self.user_parse,\
                        'category':self.category_parse} 
        
        # #新的接口方式
        # #自动订阅接口
        # self.subscribe_type = kwargs['type'] if 'type' in kwargs.keys() else None
        # #手动订阅接口
        # self.subscribe_url = kwargs['url'] if 'url' in kwargs.keys() else None
        # self.subscribe_id = kwargs['id'] if 'id' in kwargs.keys() else None
        #
        #以下老的接口方式
        #自动订阅接口
        self.subscribe_type = kwargs['type'] if 'type' in kwargs.keys() else None       
        #手动订阅接口
        #   频道订阅urls
        subscribe_channel_urls = kwargs['channel_urls'] if 'channel_urls' in kwargs.keys() else None 
        #   分类订阅urls
        subscribe_cat_urls = kwargs['cat_urls'] if 'cat_urls' in kwargs.keys() else None
        #   页面订阅urls
        subscribe_page_urls = kwargs['page_urls'] if 'page_urls' in kwargs.keys() else None
        #   专题订阅urls
        subscribe_subject_urls = kwargs['subject_urls'] if 'subject_urls' in kwargs.keys() else None
        #   关键词订阅urls
        self.subscribe_keywords = kwargs['keywords'] if 'keywords' in kwargs.keys() else None
        self.subscribe_cat_ids = kwargs['cat_ids'] if 'cat_ids' in kwargs.keys() else []

        self.subscribe_url = None 
        self.subscribe_id_key = None
        self.subscribe_id_value = None      
        url = None
        key = None
        try:
            if subscribe_channel_urls:
                log.msg("subscribe_channel_url:", level=log.DEBUG)
                subscribe_channel_urls = json.loads(subscribe_channel_urls)
                key = None
                url = subscribe_channel_urls[0]
            
            if subscribe_cat_urls:
                log.msg("subscribe_cat_url:", level=log.DEBUG)
                subscribe_cat_urls = json.loads(subscribe_cat_urls)
                key = 'cat_id'
                url = subscribe_cat_urls[0]

            if subscribe_page_urls:
                log.msg("subscribe_page_url:", level=log.DEBUG)
                subscribe_page_urls = json.loads(subscribe_page_urls)
                key = 'pg_id' 
                url = subscribe_page_urls[0]
            
            if subscribe_subject_urls:
                log.msg("subscribe_subject_url:", level=log.DEBUG)
                subscribe_subject_urls = json.loads(subscribe_subject_urls)
                key = None 
                url = subscribe_subject_urls[0]
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
            return
        
        if url:
            log.msg(url, level=log.DEBUG)
            self.subscribe_url = url['url'] if 'url' in url.keys() else None
            self.subscribe_id_value = url['id'] if 'id' in url.keys() else None
        if key:
            self.subscribe_id_key = key
        
        if self.subscribe_keywords:
            log.msg("subscribe_keywords:", level=log.DEBUG)
            self.subscribe_keywords = json.loads(self.subscribe_keywords)
            self.subscribe_id_key = 'kw_id' 
            for url in self.subscribe_keywords:
                log.msg(url, level=log.DEBUG)
        
        if self.subscribe_cat_ids:
            log.msg("subscribe_cat_ids:", level=log.DEBUG)
            self.subscribe_cat_ids = json.loads(self.subscribe_cat_ids)
            for url in self.subscribe_cat_ids:
                log.msg(url, level=log.DEBUG)
       #解析spider_type 
        self.spider_type_resolve()

    def spider_type_resolve(self):
        self.spider_type = None
        try:
            if self.subscribe_keywords:
                self.spider_type = 'search' 
            elif self.subscribe_url:
                #通过分析URL得到spider_type
                self.spider_type = youku_util.url_type_parse(self.subscribe_url)
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def start_requests(self):
        items = []
        try:
            items += self.load_start_urls()        
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def load_start_urls(self):
        items = []
        try:
            if self.subscribe_url:
                log.msg('url:%s     spider_type:%s      subscribe_type:%s '% (self.subscribe_url, self.spider_type, self.subscribe_type))
            else:
                log.msg('url is not provided,   spider_type:%s      subsribe_type:%s' % (self.spider_type, self.subscribe_type))                    
            #先以spider_type为依据，因为这是根据url分析而来，可靠性更强
            #当spider_type为空时，就以subscribe_type为依据（subscribe_type为用户提供的）
            if not self.spider_type:
                self.max_search_page = get_project_settings().get('MAX_SEARCH_PAGE')
                if self.subscribe_type:
                    if self.subscribe_type == 'channel':
                        self.spider_id = self.subscribe_ids['channel']
                        items += self.load_channel_urls()    
                    elif self.subscribe_type == 'keyword':
                        self.spider_id = self.subscribe_ids['keyword']
                        items += self.load_keyword_urls()
                    elif self.subscribe_type == 'page':
                        self.spider_id = self.subscribe_ids['page']
                        items += self.load_page_urls()    
                    elif self.subscribe_type == 'category':
                        self.spider_id = self.subscribe_ids['category']
                        items += self.load_category_urls()    
                    elif self.subscribe_type == 'subject':
                        self.spider_id = self.subscribe_ids['subject']
                        items += self.load_subject_urls()    
                    else:
                        log.msg('subscribe_type:%s is not supported' % self.subscribe_type)
                else:
                    log.msg('subscribe_type and url are not provided, youku_spider will crawl all the urls')
                    yes_or_no = raw_input('are you to continue to crawl all the urls, it will use a long time(yes/no):')
                    if yes_or_no and yes_or_no.lower() == "yes":
                        log.msg('youku_spider will crawl all the urls, it will use a long time...')
                        self.spider_id = self.subscribe_ids['all']
                        items += self.load_channel_urls()    
                        items += self.load_keyword_urls()
                        items += self.load_page_urls()    
                        items += self.load_category_urls()    
                        items += self.load_subject_urls()    
                    else:
                        log.msg('youku_spider will exit')
            else:
                self.max_search_page = get_project_settings().get('MAX_MANUAL_SEARCH_PAGE')
                self.spider_id = self.subscribe_ids['manual']
                if self.spider_type == 'search':
                    #由于关键词没有提供url,所以需要与订阅方式的共享load_keyword_url的代码
                    items += self.load_keyword_urls()
                elif self.spider_type in self.spider_parses.keys():
                    items.append(Request(url=self.subscribe_url, callback=self.spider_parses[self.spider_type], meta={'page':1, self.subscribe_id_key:self.subscribe_id_value}))
                else:
                    log.msg('url:%s     spider_type:%s is not supported' % (self.subscribe_url, self.subscribe_type))            
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items    
        
    def load_keyword_urls(self):
        items = []
        try:
            if self.spider_type:
                keywords = self.subscribe_keywords
                cat_ids = self.subscribe_cat_ids
            else:
                keywords = self.mgr.get_keywords(st='video', site_name='youku')
                cat_ids = self.mgr.get_cat_ids('youku')

            sort = {'composite': 1, 'new': 2, 'played': 3, 'comment': 4, 'favor': 5}
            quality = {'high': 1, 'super': 6, 'default': 0}
            pub_time = {'day': 1, 'week': 7, 'month': 31, 'year': 365, 'default': 0}
            run_time = {'10min': 1, '30min': 2, '60min': 3, 'plus': 4, 'default': 0}

            for kw in keywords:
                cat_id = cat_ids[kw['user']] if kw['user'] in cat_ids else 0
                url = '%s/search_video/q_%s_orderby_%s_cateid_%s_limitdate_%s?sfilter=1' % \
                        (self.soku_url_prefix, urllib2.quote(kw['keyword'].encode('utf8')), sort['played'], cat_id, pub_time['month'])
                items.append(Request(url=url, callback=self.search_parse, meta={'page':1, 'kw_id': kw['id']}))            
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def load_channel_urls(self):
        items = []
        try:
            channels = self.mgr.get_ordered_url(site_name='youku')
            for channel in channels:
                url = channel['url']
                spider_type = youku_util.url_type_parse(url)
                log.msg('subscribe_type:%s     url:%s      spider_type:%s' % (self.subscribe_type, url, spider_type))
                if spider_type in self.spider_parses.keys():
                    items.append(Request(url=url, callback=self.spider_parses[spider_type], meta={'page':1}))
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def load_page_urls(self):
        items = []
        try:
            pages = self.mgr.get_ordered_page(site_name=['youku'])
            for page in pages:
                url = page['url']
                spider_type = youku_util.url_type_parse(url)
                log.msg('subscribe_type:%s     url:%s      spider_type:%s' % (self.subscribe_type, url, spider_type))
                if spider_type in self.spider_parses.keys():
                    items.append(Request(url=url, callback=self.spider_parses[spider_type], meta={'page':1, 'pg_id':page['id']}))
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def load_category_urls(self):
        items = []
        try:
            categories = self.mgr.get_cat_url('youku')
            for category in categories:
                url = category['url']
                spider_type = youku_util.url_type_parse(url)
                log.msg('subscribe_type:%s     url:%s      spider_type:%s' % (self.subscribe_type, url, spider_type))
                if spider_type in self.spider_parses.keys():
                    items.append(Request(url=url, callback=self.spider_parses[spider_type], meta={'page':1, 'cat_id':category['id']}))
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def load_subject_urls(self):
        items = []
        try:
            subjects = self.mgr.get_subjects('youku')
            for subject in subjects:
                url = subject['url']
                spider_type = youku_util.url_type_parse(url)
                log.msg('subscribe_type:%s     url:%s      spider_type:%s' % (self.subscribe_type, url, spider_type))
                if spider_type in self.spider_parses.keys():
                    items.append(Request(url=url, callback=self.spider_parses[spider_type], meta={'page':1, 'subject_id':subject['id']}))        
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def channel_parse(self, response):
        items = []
        try:
            page = response.request.meta['page'] if 'page' in response.request.meta else 1
            page = int(page)
            if page > int(self.max_search_page):
                return items
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else None
            pg_id = response.request.meta['pg_id'] if 'pg_id' in response.request.meta else None
            cat_id = response.request.meta['cat_id'] if 'cat_id' in response.request.meta else None
            subject_id = response.request.meta['subject_id'] if 'subject_id' in response.request.meta else None
            
            url = response.request.url
            body = response.body
            #频道
            results = youku_url_extract.channel_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.channel_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))

            #分类
            results = youku_url_extract.category_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.category_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))

            #剧集
            results = youku_url_extract.video_set_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_set_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))             
            #用户
            results = youku_url_extract.user_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.user_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))             

            #播放
            results = youku_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))           
            #下一页
            next_pages = response.xpath('//div[@class="yk_pager"]/ul/li[@class="next"]/a/@href').extract()
            for url in next_pages:
                if url.startswith('/'):
					url = self.youku_url_prefix + url
                items.append(Request(url=url, callback=self.channel_parse, meta={'page': page+1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
                break
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
            
    def video_set_parse(self, response):
        items = []
        try:
            page = response.request.meta['page'] if 'page' in response.request.meta else 1
            page = int(page)
            if page > int(self.max_search_page):
                return items
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else None
            pg_id = response.request.meta['pg_id'] if 'pg_id' in response.request.meta else None
            cat_id = response.request.meta['cat_id'] if 'cat_id' in response.request.meta else None
            subject_id = response.request.meta['subject_id'] if 'subject_id' in response.request.meta else None

            url = response.request.url
            body = response.body
            
            #用户
            results = youku_url_extract.user_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.user_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))             

            #播放
            results = youku_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id})) 
            #http://www.youku.com/show_page/id_zdfee6f12875611e4b2ad.html
            show_id = None 
            regex_express = 'http://www\.youku\.com/show_page/(id_[\w]+)\.html.*'
            regex_pattern = re.compile(regex_express)
            result = regex_pattern.search(url)
            if result:
                results = result.groups()
                show_id = results[0]
            if not show_id:
                return items
            #tab click(标签页点击)
            show_url_format = 'http://www.youku.com/show_%s_'+ show_id +'.html?dt=json&__rt=1&__ro=reload_%s'
            subnav_ids = response.xpath('//div[@id="subnav_wrap"]//ul[@class="tb"]/li/@id').extract()
            for subnav_id in subnav_ids:
                regex_express = 'subnav_(.+)'
                regex_pattern = re.compile(regex_express)
                result = regex_pattern.search(subnav_id)
                if result:
                    results = result.groups()
                    subnav_id_str = results[0]
                    show_url = show_url_format % (subnav_id_str, subnav_id_str)
                    items.append(Request(url=show_url, callback=self.video_set_parse_show_subnav, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id})) 

            #button click(视频集展开)
            show_episode_url_format = 'http://www.youku.com/show_episode/'+ show_id +'.html?dt=json&divid=%s&__rt=1&__ro=%s'
            episode_ids = response.xpath('//div[@class="pgm-tab"]//div[normalize-space(@class)="pgm-list"]/ul/li/@data').extract()
            for episode_id in episode_ids:
               show_url =  show_episode_url_format % (episode_id, episode_id)
               items.append(Request(url=show_url, callback=self.page_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id})) 
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def video_set_parse_show_subnav(self, response):
        items = []
        try:
            page = response.request.meta['page'] if 'page' in response.request.meta else 1
            page = int(page)
            if page > int(self.max_search_page):
                return items 
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else None
            pg_id = response.request.meta['pg_id'] if 'pg_id' in response.request.meta else None
            cat_id = response.request.meta['cat_id'] if 'cat_id' in response.request.meta else None
            subject_id = response.request.meta['subject_id'] if 'subject_id' in response.request.meta else None

            url = response.request.url
            body = response.body
            #用户
            results = youku_url_extract.user_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.user_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))             
            #播放
            results = youku_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id})) 
            #button click(视频集展开)
            show_episode_url_format = 'http://www.youku.com/show_episode/'+ show_id +'.html?dt=json&divid=%s&__rt=1&__ro=%s'
            episode_ids = response.xpath('//div[@class="pgm-tab"]//div[normalize-space(@class)="pgm-list"]/ul/li/@data').extract()
            for episode_id in episode_ids:
               show_url =  show_episode_url_format % (episode_id, episode_id)
               items.append(Request(url=show_url, callback=self.page_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id})) 
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def category_parse(self, response):
        items = []
        try:
            page = response.request.meta['page'] if 'page' in response.request.meta else 1
            page = int(page)
            if page > int(self.max_search_page):
                return items 
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else None
            pg_id = response.request.meta['pg_id'] if 'pg_id' in response.request.meta else None
            cat_id = response.request.meta['cat_id'] if 'cat_id' in response.request.meta else None
            subject_id = response.request.meta['subject_id'] if 'subject_id' in response.request.meta else None

            url = response.request.url
            body = response.body               
            
            #分类
            results = youku_url_extract.category_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.category_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #剧集
            results = youku_url_extract.video_set_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_set_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))             
            #用户
            results = youku_url_extract.user_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.user_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))             

            #播放
            results = youku_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))           
            
            #next pages
            next_pages = response.xpath('//div[@class="yk_pager"]/ul/li[@class="next"]/a/@href').extract()
            for url in next_pages:
                if url.startswith('/'):
                    url = self.youku_url_prefix + url
                items.append(Request(url=url, callback=self.category_parse, meta={'page':page+1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
    
    def user_parse(self, response):
        items = []
        try:
            page = response.request.meta['page'] if 'page' in response.request.meta else 1
            page = int(page)
            if page > int(self.max_search_page):
                return items 
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else None
            pg_id = response.request.meta['pg_id'] if 'pg_id' in response.request.meta else None
            cat_id = response.request.meta['cat_id'] if 'cat_id' in response.request.meta else None
            subject_id = response.request.meta['subject_id'] if 'subject_id' in response.request.meta else None
            #用户页面爬取策略
            #    （1）获取用户的相关信息
            #    （2）爬取该用户的所有video urls
            script = response.xpath('/html/head/script')
            show_id = script.re('ownerEncodeid = \'(.+)\'')
            if show_id and show_id not in self.channel_exclude:
                #user info
                items += self.user_info_parse(response)
                #user video
                items.append(Request(url=response.request.url+"/videos", callback=self.user_video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            else:
                log.msg("user id excluded: %s" % show_id)
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def user_info_parse(self, response):
        items = []
        try:
            #用户信息爬取    
            user_item = UserItem()
            #owner id 
            script = response.xpath('/html/head/script')
            show_id = script.re('ownerEncodeid = \'(.+)\'')
            owner_id = script.re('ownerId = \"(\d+)\"')
            if show_id:
                user_item['show_id'] = show_id
            else:
                return items
            if owner_id:
                user_item['owner_id'] = owner_id
            else:
                return items

            #user profile
            up = response.xpath('//div[@class="profile"]')
            if up:
                user_name = up.xpath('./div[@class="info"]/div[@class="username"]/a[1]/@title').extract()
                played = up.xpath('./div[@class="state"]/ul/li[@class="vnum"]/em/text()').extract()
                fans = up.xpath('./div[@class="state"]/ul/li[@class="snum"]/em/text()').extract()

                if user_name:
                    user_item['user_name'] = user_name[0]
                if played:
                    user_item['played'] = Util.normalize_vp(played[0])
                if fans:
                    user_item['fans'] = Util.normalize_vp(fans[0])

            #youku profile
            yp = response.xpath('//div[@class="YK-profile"]')
            if yp:
                intro = yp.xpath('./div[@class="userintro"]/div[@class="desc"]/p[2]/text()').extract()
                
                if intro:
                    user_item['intro'] = ''.join(intro)
            
            #count
            yh = response.xpath('//div[@class="YK-home"]')
            vcount = '0'
            if yh:
                video_count = yh.xpath('div[1]/div/div/div/div[@class="title"]/span/a/text()').re(u'\((\d+)\)')

                if video_count:
                    vcount = video_count[0]

            user_item['vcount'] = vcount
            
            user_item['site_id'] = self.site_id
            user_item['spider_id'] = self.spider_id
            user_item['url'] = response.request.url
            
            items.append(user_item)
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def user_video_parse(self, response):
        items = []
        try:
            page = response.request.meta['page'] if 'page' in response.request.meta else 1
            page = int(page)
            if page > int(self.max_search_page):
                return items 
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else None
            pg_id = response.request.meta['pg_id'] if 'pg_id' in response.request.meta else None
            cat_id = response.request.meta['cat_id'] if 'cat_id' in response.request.meta else None
            subject_id = response.request.meta['subject_id'] if 'subject_id' in response.request.meta else None

            url = response.request.url
            body = response.body
            #播放
            results = youku_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))           
            #get last_str and ajax_url
            last_str= response.selector.re(u'\'last_str\':\'([^\']*)\'')
            ajax_url = response.selector.re(u'\'ajax_url\':\'([^\']*)\'')

            #reqest sibling page
            if ajax_url:
                sibling_page = (3 * page - 1, 3 * page)
                for p in sibling_page:
                    s = last_str[0] if last_str else u''
                    para = {"v_page":str(page), "page_num":str(p), "page_order":"1", "last_str":s}
                    items.append(FormRequest(url=self.youku_url_prefix + ajax_url[0] + "fun_ajaxload/",
                                formdata=para,
                                method='GET',
                                callback=self.user_video_parse,
                                meta={'page': page, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))            
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def search_parse(self, response):
        items = []
        try:
            page = response.request.meta['page'] if 'page' in response.request.meta else 1
            page = int(page)
            if page > int(self.max_search_page):
                return items         
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else None
            pg_id = response.request.meta['pg_id'] if 'pg_id' in response.request.meta else None
            cat_id = response.request.meta['cat_id'] if 'cat_id' in response.request.meta else None
            subject_id = response.request.meta['subject_id'] if 'subject_id' in response.request.meta else None

            url = response.request.url
            body = response.body
            #剧集
            results = youku_url_extract.video_set_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_set_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))            
            #用户
            results = youku_url_extract.user_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.user_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))             
            #播放
            results = None
            results = youku_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #下一页
            next_pages = response.xpath('//div[@class="sk_pager"]/ul/li[@class="next"]/a/@href').extract()
            for url in next_pages:
                if url.startswith('/'):
                    url = self.soku_url_prefix + url
                items.append(Request(url=url, callback=self.search_parse, meta={'page': page+1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
                break
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
            
    def page_parse(self, response):
        items = []
        try:
            page = response.request.meta['page'] if 'page' in response.request.meta else 1
            page = int(page)
            if page > int(self.max_search_page):
                return items 
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else None
            pg_id = response.request.meta['pg_id'] if 'pg_id' in response.request.meta else None
            cat_id = response.request.meta['cat_id'] if 'cat_id' in response.request.meta else None
            subject_id = response.request.meta['subject_id'] if 'subject_id' in response.request.meta else None

            url = response.request.url
            body = response.body               
            #用户
            results = youku_url_extract.user_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.user_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))             
            #播放
            results = youku_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #next pages
            next_pages = response.xpath('//div[@class="yk_pager"]/ul/li[@class="next"]/a/@href').extract()
            for url in next_pages:
                if url.startswith('/'):
                    url = self.youku_url_prefix + url
                items.append(Request(url=url, callback=self.page_parse, meta={'page': page+1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def video_parse(self, response):
        items = []
        try:
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else None
            pg_id = response.request.meta['pg_id'] if 'pg_id' in response.request.meta else None
            cat_id = response.request.meta['cat_id'] if 'cat_id' in response.request.meta else None
            subject_id = response.request.meta['subject_id'] if 'subject_id' in response.request.meta else None

            #check video's category
            category_str = response.xpath('//div[@class="base_info"]/div[@class="guide"]/div/a/text()').extract()
            category = None
            if category_str:
                category = category_str[0].replace(u'频道', '')
            if category:
                if category in self.category_exclude:
                    log.msg("video category excluded: %s" % category)
                    return
            
            owner = response.xpath('//div[@class="yk-userinfo"]/div[@class="user-name"]/a/@href').extract()
            owner_show_id = None
            if owner:
                owner_show_id = Util.get_owner(owner[0])
                if owner_show_id in self.channel_exclude:
                    log.msg("video owner excluded: %s" % owner_show_id)
                    return

            #episode info
            show_id = Util.get_showid(response.request.url)

            title = response.xpath('//div[@class="base_info"]/h1/descendant-or-self::*/text()').extract()       
            upload = response.xpath('//div[@class="yk-videoinfo"]/div[@class="time"]/text()').extract()
            description = response.xpath('//div[@class="yk-videoinfo"]/div[@id="text_long"]/text()').extract()

            scripts = response.xpath('//script[@type="text/javascript"]')
            video_id = scripts.re('videoId = \'(\d+)\'')
            tag = scripts.re('tags="(.+)"')

            episode_item = EpisodeItem() 
           
            if show_id:
                episode_item['show_id'] = show_id
            else:
                return
            if video_id:
                episode_item['video_id'] = video_id[0]
            if owner_show_id:
                episode_item['owner_show_id'] = owner_show_id
            if title:
                episode_item['title'] = Util.strip_title("".join(title))
            if tag:
                episode_item['tag'] = Util.unquote(tag[0]).rstrip('|')
            if category:
                episode_item['category'] = category
            if upload:
                t = Util.get_upload_time(upload[0])
                if t:
                    episode_item['upload_time'] = Util.get_datetime_delta(datetime.now(), t)
            if description:
                episode_item['description'] = description[0]

            episode_item['spider_id'] = self.spider_id
            episode_item['site_id'] = self.site_id
            episode_item['url'] = response.request.url

            episode_item['kw_id'] = kw_id
            episode_item['pg_id'] = pg_id
            episode_item['cat_id'] = cat_id
            episode_item['subject_id'] = subject_id

            if video_id:
                items.append(Request(url=self.vpaction_url+video_id[0], callback=self.vpaction_parse, meta={'episode_item':episode_item}))
            else:
                items.append(episode_item)
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
    
    def vpaction_parse(self, response):
        items = []
        try:
            episode_item = response.request.meta['episode_item']
            vp = response.xpath('//div[@id="videodetailInfo"]/ul/li').re(u'<label>总播放数:</label><span.*>(.+)</span>')
            if vp:
                episode_item['played'] = Util.normalize_vp(vp[0])
            show_id = episode_item['show_id']
            if show_id: 
                items.append(Request(url=self.playlength_url+show_id, callback=self.playlength_parse, meta={'episode_item': episode_item}))
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def playlength_parse(self, response):
        try:
            episode_item = response.request.meta['episode_item']
            msg = response.body
            if msg:
                json_info = json.loads(msg)
                playlength = str(int(float(json_info['data'][0]["seconds"])))
                thumb_url = json.info['data'][0]['logo']
                if playlength:
                    episode_item['duration'] = playlength
                if thumb_url:
                    episode_item['thumb_url'] = thumb_url
            return episode_item
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)            
