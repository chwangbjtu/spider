# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re
import json
import urllib2
import traceback
from datetime import datetime
from scrapy import log
from scrapy.spider import Spider
from scrapy.selector import Selector
from scrapy.http import Request, FormRequest
from crawler.common.util import Util
from crawler.db.db_mgr import DbManager
from crawler.items import EpisodeItem, UserItem
from scrapy.utils.project import get_project_settings

from iqiyi_util import iqiyi_util
from iqiyi_url_extract import iqiyi_url_extract

class iqiyi_spider(Spider):
    
    name = 'iqiyi_spider'
    site_id = '5'

    subscribe_ids = {'all': '3', 'channel':'6', 'keyword':'12', 'page':'24', 'category':'48', 'subject':'96', 'manual':'192'}

    #prefix urls
    list_url_prefix = 'http://list.iqiyi.com'
    iqiyi_url_prefix = 'http://www.iqiyi.com'
    so_url_prefix = 'http://so.iqiyi.com'
    playnum_url = 'http://cache.video.iqiyi.com/jp/pc/'
    playlength_url = "http://cache.video.iqiyi.com/a/"
    

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
        super(iqiyi_spider, self).__init__(*args, **kwargs)
        self.spider_parses = {'channel':self.channel_parse,\
                        'video_set':self.video_set_parse,\
                        'search':self.search_parse,\
                        'category':self.category_parse,\
                        'user':self.user_parse,\
                        'video':self.video_parse,\
                        'page':self.page_parse,\
                        'tags':self.tags_parse} 
        
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
                self.spider_type = yi_util.url_type_parse(self.subscribe_url)
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
                    log.msg('subscribe_type and url are not provided, iqiyi_spider will crawl all the urls')
                    yes_or_no = raw_input('are you to continue to crawl all the urls, it will use a long time(yes/no):')
                    if yes_or_no and yes_or_no.lower() == "yes":
                        log.msg('iqiyi_spider will crawl all the urls, it will use a long time...')
                        self.spider_id = self.subscribe_ids['all']
                        items += self.load_channel_urls()    
                        items += self.load_keyword_urls()
                        items += self.load_page_urls()    
                        items += self.load_category_urls()    
                        items += self.load_subject_urls()    
                    else:
                        log.msg('iqiyi_spider will exit')
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
                keywords = self.mgr.get_keywords(st='video', site_name='iqiyi')
            run_time = {'10min': 2, '30min': 3, '60min': 4, 'plus': 5, 'default': 0}
            pub_time = {'day': 1, 'week': 2, 'month': 3, 'default': 0}
            quality = {'high': 3, '720P': 4, 'super': 6, '1080P': 7, 'default': ''}
            sort = {'composite': 1, 'new': 4, 'played': 11}
            for kw in keywords:
                url = "%s/so/q_%s_ctg__t_%s_page_%s_p_%s_qc_%s_rd_%s_site_%s_m_%s_bitrate_%s" % \
                    (self.so_url_prefix, urllib2.quote(kw['keyword'].encode('utf8')), run_time['default'], 1, 1, 0, pub_time['default'], "iqiyi", sort['composite'], quality['default'])
                items.append(Request(url=url, callback=self.search_parse, meta={'page':1, 'kw_id': kw['id']}))            
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def load_channel_urls(self):
        items = []
        try:
            channels = self.mgr.get_ordered_url(site_name='iqiyi')
            for channel in channels:
                url = channel['url']
                spider_type = iqiyi_util.url_type_parse(url)
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
            pages = self.mgr.get_ordered_page(site_name=['iqiyi'])
            for page in pages:
                url = page['url']
                spider_type = iqiyi_util.url_type_parse(url)
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
            categories = self.mgr.get_cat_url('iqiyi')
            for category in categories:
                url = category['url']
                spider_type = iqiyi_util.url_type_parse(url)
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
            subjects = self.mgr.get_subjects('iqiyi')
            for subject in subjects:
                url = subject['url']
                spider_type = iqiyi_util.url_type_parse(url)
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
            results = iqiyi_url_extract.channel_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.channel_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #分类
            results = iqiyi_url_extract.category_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.category_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))               
            #剧集
            results = iqiyi_url_extract.video_set_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_set_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))             
            #标签
            results = iqiyi_url_extract.tags_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.tags_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #用户
            results = iqiyi_url_extract.user_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.user_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))            
            #播放
            results = iqiyi_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))           
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
            
    def video_set_parse(self, response):
        items = []
        try:
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else None
            pg_id = response.request.meta['pg_id'] if 'pg_id' in response.request.meta else None
            cat_id = response.request.meta['cat_id'] if 'cat_id' in response.request.meta else None
            subject_id = response.request.meta['subject_id'] if 'subject_id' in response.request.meta else None

            url = response.request.url
            body = response.body
            #模拟ajax获取更多数据
            #http://www.iqiyi.com/a_19rrguehx9.html#vfrm=2-3-0-1
            regex_express = 'http://www\.iqiyi\.com/a_[\w]+\.html.*'
            regex_pattern = re.compile(regex_express)
            match = regex_pattern.search(url)
            if match:
                cache_url_prefix = 'http://cache.video.qiyi.com/jp/sdvlst'
                scripts = response.xpath('//script[@type="text/javascript"]')
                categoryId = scripts.re('cid:[ ]*(\d+)')
                sourceId = scripts.re('sourceId:[ ]*(\d+)')                
                years = response.xpath('//div[@id="block-J"]//div[@class="choose-y-bd"]//a/@data-year').extract()
                months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
                for year in years:
                    log('year:%s'%year)
                    for month in months:
                        log('month:%s'%month)
                        tvYear = '%s%s'%(year, month)
                        url = cache_url_prefix + '/%s/%s/%s?categoryId=%s&sourceId=%s&tvYear=%s'%(categoryId, sourceId, tvYear, categoryId, sourceId, tvYear)
                        items.append(Request(url=url, callback=self.video_set_parse_halfjson, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #http://www.iqiyi.com/lib/s_214734305.html#vfrm=2-3-0-1
            regex_express = 'http://www\.iqiyi\.com/lib/s_([\w]+)\.html.*'
            regex_pattern = re.compile(regex_express)
            match = regex_pattern.search(url)
            if match:
                video_url_prefix = 'http://rq.video.iqiyi.com/star/s/w.jsonp'
                results = match.groups()
                id = results[0]
                page = 1
                cids = response.xpath('//a[@class="more"]/@data-cid').extract()
                if cids:
                    cids = set(cids)
                    for cid in cids:
                        url = video_url_prefix + '?id=%s&t=%s&page=%s'%(id, cid, page)
                        items.append(Request(url=url, callback=self.video_set_parse_json, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #http://www.iqiyi.com/lib/m_200047914.html
            regex_express = 'http://www\.iqiyi\.com/lib/m_[\w]+\.html.*'
            regex_pattern = re.compile(regex_express)
            match = regex_pattern.search(url)
            if match:
                title = response.xpath('//div[@class="result_pic"]//a/@title').extract()
                video_url_prefix = 'http://rq.video.iqiyi.com/aries/t/l.fjsonp'
                url = video_url_prefix + '?page=%s&title=%s'%(page, title)
                items.append(Request(url=url, callback=self.video_set_parse_nojson, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #http://www.iqiyi.com/dianshiju/playlist295748402.html#vfrm=2-3-0-1
            #该类型的视频集获取用户与播放即可
            
            #用户
            results = iqiyi_url_extract.user_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.user_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #播放
            results = iqiyi_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id})) 
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
    
    def video_set_parse_halfjson(self, response):
        items = []
        try:
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else None
            pg_id = response.request.meta['pg_id'] if 'pg_id' in response.request.meta else None
            cat_id = response.request.meta['cat_id'] if 'cat_id' in response.request.meta else None
            subject_id = response.request.meta['subject_id'] if 'subject_id' in response.request.meta else None
            
            url = response.request.url
            body = response.body
            regex_pattern = re.compile('(\{.*\})')
            result = regex_pattern.search(body)
            if result:
                results = result.groups()
                content = results[0] 
                content = json.loads(content)
                datas = content['data']
                if datas:
                    for data in datas:
                        url = data['vUrl']
                        #thumb_url = data['tvPicUrl']
                        items.append(Request(url=url, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))                      
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items    

    def video_set_parse_json(self, response):
        items = []
        try:
            kw_id = response.request.meta['kw_id'] if 'kw_id' in response.request.meta else None
            pg_id = response.request.meta['pg_id'] if 'pg_id' in response.request.meta else None
            cat_id = response.request.meta['cat_id'] if 'cat_id' in response.request.meta else None
            subject_id = response.request.meta['subject_id'] if 'subject_id' in response.request.meta else None
            
            url = response.request.url
            body = response.body
            content = json.loads(body)
            datas = content['data']['objs']['allEpisodes']['data']
            if datas:
                for data in datas:
                    url = data['page_url']
                    #thumb_url = data['thumbnail_url']
                    items.append(Request(url=url, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id})) 
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
    
    def video_set_parse_nojson(self, response):
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
            content = json.loads(body)
            content = content['data']['html']
            if content:
                #播放
                results = iqiyi_url_extract.video_url_extract(url, content)
                if results:
                    for result in results:
                        items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
                #下一页
                sel = Selector(text=content)
                href = sel.xpath('//a[@class="a1"]/@href')
                result = href.re('\?page=[ ]*(\d+)[ ]*')
                if result:
                    for page_num in result:
                        page_num = int(page_num)
                        if page_num > int(self.max_search_page):
                            return items
                        if page_num > page:
                            old_str = 'page=%s'% page_num-1
                            new_str = 'page=%s'% page_num
                            url = url.replace(old_str, new_str)
                            items.append(Request(url=url, callback=self.video_set_parse_nojson, meta={'page':page_num, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
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
            results = iqiyi_url_extract.video_set_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_set_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))            
            #标签
            results = None
            results = iqiyi_url_extract.tags_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.tags_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #用户
            results = None
            results = iqiyi_url_extract.user_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.user_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #播放
            results = None
            results = iqiyi_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #下一页
            next_pages = response.xpath('//div[@class="mod-page"]//a[@data-key="down"]/@href').extract()
            if next_pages:
                for href in next_pages:
                    if href.startswith('/'):
                        href = self.so_url_prefix + href
                    items.append(Request(url=href, callback=self.search_parse, meta={'page': page+1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))    
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
            #子分类
            results = iqiyi_url_extract.category_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.category_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))         
            #剧集
            results = iqiyi_url_extract.video_set_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_set_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id})) 
            #标签
            results = iqiyi_url_extract.tags_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.tags_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id})) 
            #用户
            results = iqiyi_url_extract.user_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.user_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #播放
            results = iqiyi_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))                     
            #下一页
            next_pages = response.xpath('//div[@class="mod-page"]//a[@data-key="down"]/@href').extract()
            if next_pages:
                for href in next_pages:
                    if href.startswith('/'):
                        #list.iqiyi.com
                        if url.startswith(self.list_url_prefix):
                            href = self.list_url_prefix + href
                        #www.iqiyi.com/lib/
                        elif url.startswith(self.iqiyi_url_prefix):
                            href = self.iqiyi_url_prefix + href
                    items.append(Request(url=href, callback=self.category_parse, meta={'page': page+1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
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
            
            url = response.request.url
            user_id = None
            #http://www.iqiyi.com/u/1064362165
            regex_pattern = re.compile('http://www\.iqiyi\.com/u/(\w+)[/#?\w]*')
            result = regex_pattern.search(url)
            if result:
                results = result.groups()
                user_id = results[0]
            #http://i.iqiyi.com/1063208820
            if not user_id:   
                regex_pattern = re.compile('http://i\.iqiyi\.com/(\w+)[/#?\w]*')
                result = regex_pattern.search(url)
                if result:
                    results = result.groups()
                    user_id = results[0]                    
            if user_id:
                if user_id not in self.channel_exclude:
                    #user info
                    #items = items + self.user_info_parse(response)
                    #user video
                    url = self.iqiyi_url_prefix + '/u/' + user_id + '/v'
                    items.append(Request(url=url, callback=self.user_video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def user_info_parse(self, response):
        items = []
        try:
            #暂时没有实现，待完成
            return items
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
            results = iqiyi_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #loading more - new
            loading_more_hrefs = response.xpath('//li[@class="list_loading" and @data-loading-scrollname="new"]/@data-loading-src').extract()
            if loading_more_hrefs:
                for loading_more_href in loading_more_hrefs:
                    items.append(Request(url=loading_more_href, callback=self.user_video_parse_loading_more, meta={'page':page, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))                    
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items             

    def user_video_parse_loading_more(self, response):
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
            content = json.loads(body)
            if content:
                content = content['data']
                if content:
                    #播放
                    results = iqiyi_url_extract.video_url_extract(url, content)
                    if results:
                        for result in results:
                            items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))                    
                    
                    sel = Selector(text=content)
                    #loading more
                    loading_more_hrefs = sel.xpath('//li[@class="list_loading" and @data-loading-scrollname="new"]/@data-loading-src').extract()
                    if loading_more_hrefs:
                        for loading_more_href in loading_more_hrefs:
                            items.append(Request(url=loading_more_href, callback=self.user_video_parse_loading_more, meta={'page':page, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
                    #next page
                    next_page_url_prefix = None
                    regex_pattern = re.compile('(.*)\?.*')
                    result = regex_pattern.search(url)
                    if result:
                        results = result.groups()
                        next_page_url_prefix = results[0]
                    if next_page_url_prefix:
                        next_page_hrefs = sel.xpath('//div[@class="mod-page"]//a[@class="a1"]/@href').extract()
                        if next_page_hrefs:
                            for next_page_href in next_page_hrefs:
                                regex_pattern = re.compile('.*page=(\d+).*') 
                                result = regex_pattern.search(next_page_href)
                                if result:
                                    results = result.groups()
                                    page_num = int(results[0])
                                    if page_num > int(self.max_search_page):
                                        return items
                                    if page_num > page:
                                        if next_page_href.startswith('?'):
                                            next_page_href = next_page_url_prefix + next_page_href
                                            items.append(Request(url=next_page_href, callback=self.user_video_parse_loading_more, meta={'page':page+1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))                    
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

            #show_id
            show_id = Util.get_iqiyi_showid(response.request.url)

            #space maybe exist: "albumId:326754200" or "albumId: 326754200"
            albumid = response.selector.re(re.compile(r'albumId: ?(\d+)'))

            #video info
            title = response.xpath('//div[@class="play-tit-l"]/h2/descendant-or-self::*/text()').extract()
            if not title:
                title = response.xpath('//div[@class="play-tit-l"]/h1/descendant-or-self::*/text()').extract()
            if not title:
                title = response.xpath('//div[@class="mod-play-tits"]/h1/descendant-or-self::*/text()').extract()
            if not title:
                title = response.xpath('//div[@class="play-tit play-tit-oneRow play-tit-long"]/h1/descendant-or-self::*/text()').extract()

            category = response.xpath('//div[@class="crumb_bar"]/span[1]/span/a[2]/text()').extract()
            if not category:
                category = response.xpath('//div[@class="play-album-crumbs textOverflow"]/span[1]/a[2]/text()').extract()
            if not category:
                category = response.xpath('//div[@class="crumb_bar"]/span[1]/a[2]/text()').extract()
            if not category:
                category = response.xpath('//div[@class="mod-crumb_bar"]/span[1]/a[2]/text()').extract()

            upload_time = response.xpath('//div[@class="crumb_bar"]/span[3]/span/text()').extract()
            if not upload_time:
                upload_time = response.xpath('//div[@class="crumb_bar"]/span[2]/span/text()').extract()
            
            tag = response.xpath('//span[@id="widget-videotag"]/descendant::*/text()').extract()
            if not tag:
                tag = response.xpath('//span[@class="mod-tags_item vl-block"]/descendant::*/text()').extract()
            if not tag:
                tag = response.xpath('//div[@class="crumb_bar"]/span[2]/a/text()').extract()

            thumb_url = response.xpath('//meta[@itemprop="image"]/@content').extract()
            if not thumb_url:
                thumb_url = response.xpath('//meta[@itemprop="thumbnailUrl"]/@content').extract()
            
            ep_item = EpisodeItem()
            
            if title:
                ep_item['title'] = "".join([t.strip() for t in title])
            if show_id:
                ep_item['show_id'] = show_id
            if tag:
                ep_item['tag'] =  "|".join([t.strip() for t in tag])
            if upload_time:
                ep_item['upload_time'] = upload_time[0].strip()
            if category:
                ep_item['category'] = category[0].strip()
            if thumb_url:
                ep_item['thumb_url'] = thumb_url[0].strip()
                
            if kw_id:
                ep_item['kw_id'] = kw_id
            if pg_id:
                ep_item['pg_id'] = pg_id                
            if cat_id:
                ep_item['cat_id'] = cat_id
            if subject_id:
                ep_item['subject_id'] = subject_id    

            ep_item['spider_id'] = self.spider_id
            ep_item['site_id'] = self.site_id
            ep_item['url'] = response.request.url
            
            if albumid:
                items.append(Request(url=self.playlength_url+albumid[0], callback=self.playlength_parse, meta={'item':ep_item,'albumid':albumid[0]}))
            else:
                items.append(ep_item)            
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def playlength_parse(self,response):
        items = []
        try:
            item = response.request.meta['item']
            albumid = response.request.meta['albumid']
            msg = response.body
            index = msg.find("AlbumInfo=") + len("AlbumInfo=")
            info = msg[index:]
            jinfo = json.loads(info)
            playLength = jinfo["data"]["playLength"]
            if playLength:
                item['duration'] = str(playLength)
            
            items.append(Request(url=self.playnum_url+albumid+"/?qyid=", callback=self.playnum_parse, meta={'item':item}))
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    def playnum_parse(self,response):
        items = []
        try:
            item = response.request.meta['item']
            tplaynum = response.selector.re(re.compile(r':(\d+)'))
            if tplaynum:
                playnum = tplaynum[0]
                if int(playnum) > int(self.hottest_played_threshold):
                    item['played'] = str(playnum)
                    items.append(item)        
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
            
    def tags_parse(self, response):
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
            results = iqiyi_url_extract.user_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.user_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #播放
            results = iqiyi_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))            
            #下一页
            #获取页数
            total_nums = 0
            perpage_nums = 0
            total_nums_str = response.xpath('//div[@class="mod-page"]/@data-huati-total').extract()
            if total_nums_str:
                total_nums = float(total_nums_str[0])
            perpage_nums_str = response.xpath('//div[@class="mod-page"]/@data-huati-perpage').extract()
            if perpage_nums_str:
                perpage_nums = float(perpage_nums_str[0])
            if perpage_nums != 0:
                page_nums = int(math.ceil(total_nums/perpage_nums))
                if page_nums >= 2:
                    i = 2
                    while i <= page_nums:
                        url = url.repalce('.html', '/%s.html'%i)
                        items.append(Request(url=url, callback=self.tags_parse, meta={'page': i, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
                        i = i+1
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
            protocol, rest = urllib2.splittype(url)
            if not protocol:
                protocol = 'http'
                rest = '//' + rest
            if rest:
                domain, rest = urllib2.splithost(rest)
            if domain:
                url_prefix = protocol + '://' + domain
            else:
                url_prefix = self.iqiyi_url_prefix
            body = response.body               
            #用户
            results = iqiyi_url_extract.user_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.user_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))
            #播放
            results = iqiyi_url_extract.video_url_extract(url, body)
            if results:
                for result in results:
                    items.append(Request(url=result, callback=self.video_parse, meta={'page':1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))            
            #下一页
            next_pages = response.xpath('//div[@class="mod-page"]//a[@data-key="down"]/@href').extract()
            if next_pages:
                for href in next_pages:
                    if href.startswith('/'):
                        href = url_prefix + href
                    items.append(Request(url=href, callback=self.page_parse, meta={'page': page+1, 'kw_id':kw_id, 'pg_id':pg_id, 'cat_id':cat_id, 'subject_id':subject_id}))                       
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
            
