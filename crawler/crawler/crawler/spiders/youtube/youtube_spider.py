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

from youtube_util import youtube_util
from youtube_url_extract import youtube_url_extract

class youtube_spider(Spider):
    
    name = 'youtube_spider'
    site_id = '2'

    subscribe_ids = {'all': '5', 'channel':'10', 'keyword':'20', 'page':'40', 'category':'80', 'subject':'160', 'manual':'320'}

    #prefix urls
    youtube_url_prefix = 'https://www.youtube.com'
    thumb_url_prefix = 'https://i.ytimg.com/vi'

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
        super(youtube_spider, self).__init__(*args, **kwargs)
        self.spider_parses = {'channel':self.channel_parse,\
                        'video_set':self.video_set_parse,\
                        'search':self.search_parse,\
                        'video':self.video_parse,\
                        'page':self.page_parse,\
                        'subject':self.subject_parse} 
        
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
                self.spider_type = youtube_util.url_type_parse(self.subscribe_url)
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
                    log.msg('subscribe_type and url are not provided, youtube_spider will crawl all the urls')
                    yes_or_no = raw_input('are you to continue to crawl all the urls, it will use a long time(yes/no):')
                    if yes_or_no and yes_or_no.lower() == "yes":
                        log.msg('youtube_spider will crawl all the urls, it will use a long time...')
                        self.spider_id = self.subscribe_ids['all']
                        items += self.load_channel_urls()    
                        items += self.load_keyword_urls()
                        items += self.load_page_urls()    
                        items += self.load_category_urls()    
                        items += self.load_subject_urls()    
                    else:
                        log.msg('youtube_spider will exit')
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
            else:
                keywords = self.mgr.get_keywords(st='video', site_name='youtube')
            for kw in keywords:
                url = '%s/results?filters=video%%2Cweek&search_sort=video_view_count&search_query=%s' % \
                    (self.youtube_url_prefix, urllib2.quote(kw['keyword'].encode('utf8')))
                items.append(Request(url=url, callback=self.search_parse, meta={'page':1, 'kw_id': kw['id']}))            
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def load_channel_urls(self):
        items = []
        try:
            channels = self.mgr.get_ordered_url(site_name='youtube')
            for channel in channels:
                url = channel['url']
                spider_type = youtube_util.url_type_parse(url)
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
            pages = self.mgr.get_ordered_page(site_name=['youtube'])
            for page in pages:
                url = page['url']
                spider_type = youtube_util.url_type_parse(url)
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
            categories = self.mgr.get_cat_url('youtube')
            for category in categories:
                url = category['url']
                spider_type = youtube_util.url_type_parse(url)
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
            subjects = self.mgr.get_subjects('youtube')
            for subject in subjects:
                url = subject['url']
                spider_type = youtube_util.url_type_parse(url)
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
            results = youtube_url_extract.channel_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.channel_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #主题
            results = youtube_url_extract.subject_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.subject_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))

            #剧集
            results = youtube_url_extract.video_set_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_set_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))             
            #播放
            results = youtube_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))           
            #下一页(暂未发现，分页现象)

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
            
            #播放
            results = youtube_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id})) 
            #加载更多
            loading_more_hrefs = response.xpath('//button/@data-uix-load-more-href').extract()
            if loading_more_hrefs:
                for loading_more_href in loading_more_hrefs:
                    if loading_more_href.startswith('/'):
                        loading_more_href = self.youtube_url_prefix + loading_more_href
                    items.append(Request(url=loading_more_href, callback=self.loading_more_parse_json, meta={'page':2, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id})) 
                    break
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def loading_more_parse_json(self, response):
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
            body = json.loads(body)
            if body:
                content = body['content_html']
                if content:
                    video_hrefs = youtube_url_extract.video_url_extract(url, content)
                    if video_hrefs:
                        items = items + video_hrefs
                loading_more = body['load_more_widget_html']
                if loading_more:
                    sel = Selector(text=loading_more)
                    loading_more_hrefs = sel.xpath('//button/@data-uix-load-more-href').extract()
                    if loading_more_hrefs:
                        for loading_more_href in loading_more_hrefs:
                            if loading_more_href.startswith('/'):
                                loading_more_href = self.youtube_url_prefix + loading_more_href
                            items.append(Request(url=loading_more_href, callback=self.loading_more_parse_json, meta={'page':page+1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id})) 
                            break
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
            #主题（这里不抓取，youtube搜索后，主题的相关度不大，不予抓取）
            #剧集
            results = youtube_url_extract.video_set_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_set_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))            
            #播放
            results = None
            results = youtube_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #下一页
            next_pages = response.xpath('//div[@role="navigation"]//a[@data-link-type="next"]/@href').extract()
            if next_pages:
                for href in next_pages:
                    if href.startswith('/'):
                        href = self.youtube_url_prefix + href
                    items.append(Request(url=href, callback=self.search_parse, meta={'page': page+1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))    
                    break
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
            
    def subject_parse(self, response):
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

            #主题
            results = youtube_url_extract.subject_url_extract(url, body)
            if results:
                for result in results:
                    #只获取深度为max_search_page的关联主题
                    items.append(Request(url=result, callback=self.subject_parse, meta={'page':page+1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))            

            #剧集
            results = youtube_url_extract.video_set_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_set_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))            

            #播放
            results = youtube_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #next page
            loading_more_hrefs = response.xpath('//button/@data-uix-load-more-href').extract()
            if loading_more_hrefs:
                for loading_more_href in loading_more_hrefs:
                    if loading_more_href.startswith('/'):
                        loading_more_href = self.youtube_url_prefix + loading_more_href
                    items.append(Request(url=loading_more_href, callback=self.loading_more_parse_json, meta={'page':2, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id})) 
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
            
            #主题
            results = youtube_url_extract.subject_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.subject_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))            

            #播放
            results = youtube_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))            
            #下一页
            next_pages = response.xpath('//div[@class="mod-page"]//a[@data-key="down"]/@href').extract()
            if next_pages:
                #传统的下一页表示方法
                next_pages = response.xpath('//div[@role="navigation"]//a[@data-link-type="next"]/@href').extract()
                if next_pages:
                    for href in next_pages:
                        if href.startswith('/'):
                            href = self.youtube_url_prefix + href
                        items.append(Request(url=href, callback=self.page_parse, meta={'page': page+1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))    
                        break
            else:
                #加载更多的下一页
                loading_more_hrefs = response.xpath('//button/@data-uix-load-more-href').extract()
                if loading_more_hrefs:
                    for loading_more_href in loading_more_hrefs:
                        if loading_more_href.startswith('/'):
                            loading_more_href = self.youtube_url_prefix + loading_more_href
                        items.append(Request(url=loading_more_href, callback=self.loading_more_parse_json, meta={'page':2, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id})) 
                        break
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

            show_id = Util.get_youtube_showid(response.request.url)
            if not show_id:
                return items

            #owner
            owner = response.xpath('//div[@class="yt-user-info"]/a/@data-ytid').extract()
            owner_url = response.xpath('//div[@class="yt-user-info"]/a/@href').extract()
            owner_show_id = None
            if owner:
                owner_show_id = owner[0]
                items.append(Request(url=self.youtube_url_prefix + owner_url[0] + "/about", callback=self.video_about_parse))

            #video info
            title = response.xpath('//span[@id="eow-title"]/text()').extract()
            tag = response.xpath('./head/meta[@name="keywords"]/@content').extract()
            description = response.xpath('//p[@id="eow-description"]/descendant-or-self::*/text()').extract()
            played = response.xpath('//div[@class="watch-view-count"]/text()').extract()
            category = response.xpath('//div[@id="watch-description"]//ul[@class="content watch-info-tag-list"]/li/a/text()').extract()
            upload = response.xpath('//meta[@itemprop="datePublished"]/@content').extract()
            #该方法获取的缩略图
            thumb_url = response.xpath('//link[@itemprop="thumbnailUrl"]/@href').extract()
            #other info
            sts = re.search(r'\"sts\": ?(\d+)', response.body)
            
            ep_item = EpisodeItem()
            ep_item['show_id'] = show_id
            #这里缩略图采用合成的方式得到['default', 'mqdefault', 'hqdefault', 'sddefault', 'maxresdefault']
            #ep_item['thumb_url'] = self.thumb_url_prefix + '/' + show_id + '/default.jpg'
            if owner_show_id:
                ep_item['owner_show_id'] = owner_show_id
            if title:
                ep_item['title'] = title[0].strip()
            if tag:
                ep_item['tag'] = tag[0].replace(', ', '|')
            if description:
                ep_item['description'] = "\n".join(description)
            if played:
                pld = Util.normalize_played(played[0])
                if pld:
                    ep_item['played'] = Util.normalize_played(played[0])
                else:
                    ep_item['played'] = '0'

            if kw_id:
                ep_item['kw_id'] = kw_id
            if pg_id:
                ep_item['pg_id'] = pg_id                
            if cat_id:
                ep_item['cat_id'] = cat_id
            if subject_id:
                ep_item['subject_id'] = subject_id    

            if thumb_url:
                ep_item['thumb_url'] = thumb_url[0]
            if category:
                category = category[0].strip()
                #https://www.youtube.com/watch?v=lwy4qwaByVQ
                ep_item['category'] = category.replace('&', '|')
            if upload:
                upload = upload[0].strip()
                struct_time = None
                struct_time = time.strptime(upload, '%b %d, %Y')
                if not struct_time:
                    struct_time = time.strptime(upload, '%Y年%m月%d日')
                if struct_time:
                    time_str = time.strftime('%Y-%m-%d %H:%M:%S', struct_time)
                    #time_str = "%s-%s-%s %s" % (struct_time.tm_year, struct_time.tm_mon, struct_time.tm_mday, time_str)
                    ep_item['upload_time'] = time_str

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = Util.normalize_youtube_url(response.request.url)

            query = Util.encode({'video_id': ep_item['show_id'], \
                                 'eurl': 'https://youtube.googleapis.com/v/' + ep_item['show_id'], \
                                 'sts': sts.groups()[0] if sts else ''})
            items.append(Request(url='http://www.youtube.com/get_video_info?'+query, callback=self.video_other_info_parse, meta={'item': ep_item}))
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def video_other_info_parse(self, response):
        items = []
        try:
            item = response.request.meta['item'] if 'item' in response.request.meta else None
            if item:
                #duration
                duration = re.search(r'length_seconds=(\d+)', response.body)
                if duration:
                    item['duration'] = duration.groups()[0]
                    items.append(item)
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def video_about_parse(self, response):
        items = []
        try:
            show_id = response.xpath('//meta[@itemprop="channelId"]/@content').extract()
            user_name = response.xpath('//span[@class="qualified-channel-title-text"]/a/text()').extract()
            fans = response.xpath('//ul[@class="about-stats"]/li').re(re.compile(r'<li.*>.*<b>([\d|,]*)</b>.*subscribers.*</li>', re.S))
            played = response.xpath('//ul[@class="about-stats"]/li').re(re.compile(r'<li.*>.*<b>([\d|,]*)</b>.*views.*</li>', re.S))
            intro = response.xpath('//div[@class="about-description branded-page-box-padding"]/descendant-or-self::*/text()').extract()

            if show_id:
                user_item = UserItem()
                user_item['show_id'] = show_id[0]
                if user_name:
                    user_item['user_name'] = user_name[0]
                if fans:
                    user_item['fans'] = Util.normalize_played(fans[0])
                if played:
                    user_item['played'] = Util.normalize_played(played[0])
                if intro:
                    user_item['intro'] = "".join(intro).strip()
                user_item['spider_id'] = self.spider_id
                user_item['site_id'] = self.site_id
                user_item['url'] = response.request.url[:-len('/about')]

                items.append(user_item)
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
