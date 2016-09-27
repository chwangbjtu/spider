# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re
import urlparse
import traceback
from scrapy import log
from scrapy.selector import Selector

from youku_util import youku_util

class youku_url_extract(object):
    
    youku_url_prefix = 'http://www.youku.com'
    soku_url_prefix = 'http://www.soku.com'

    @staticmethod
    def channel_url_extract(url, content):
        items = []
        try:
            if not url:
                log.msg('channel_url_extract: url is not provided')
                return items
            sel = None 
            try:
                sel = Selector(text=content)
            except Exception, e:
                log.msg('content to be parsed is not xml or html')
                log.msg(traceback.format_exc(), level=log.ERROR)
                return items
            if not sel:
                return items
            #爬取策略
            #若当前页面类型是频道页
            #   获取当前频道的子频道页面
            #若当前页面类型不是频道页面
            #   直接获取所有频道(当前未使用)
            spider_type = youku_util.url_type_parse(url)
            if spider_type == 'channel':
                url = response.request.url
                result = urlparse.urlparse(url)
                if result:
                    result = 'http://%s%s'%(result.netloc, result.path)
                    #提取出全部所有的youku的url
                    youku_hrefs = sel.xpath('//a/@href[re:test(., "[./:\w]*youku\.com")]')
                    if youku_hrefs:
                    #    http://zy.youku.com        ->        http://zy.youku.com/gaoxiao
                        regex_express = '(%s/.+)' % result
                        channel_hrefs = youku_hrefs.re(regex_express)
                        if channel_hrefs:
                            items = items + channel_hrefs
            else:
                items = []
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    @staticmethod            
    def search_url_extract(url, content):
        items = []
        try:
            if not url:
                log.msg('search_url_extract: url is not provided')
                return items
            sel = None 
            try:
                sel = Selector(text=content)
            except Exception, e:
                log.msg('content to be parsed is not xml or html')
                log.msg(traceback.format_exc(), level=log.ERROR)
                return items
            if not sel:
                return items
            #爬取策略
            #若当前页面类型是搜索页
            #   获取子搜索页,相对地址
            #若当前页面类型不是搜索页
            #   直接获取所有搜索链接
            spider_type = youku_util.url_type_parse(url)
            if spider_type == 'search':
                #search filters
                url_filters = []
                regex_express = '/v\?(.+)[./?#].*'
                regex_pattern = re.compile(regex_express)
                result = regex_pattern.search(url)
                if result:
                    results = result.groups()
                    url_filters = results[0].split('&')
                #search items
                search_hrefs = sel.xpath('//a/@href[re:test(., "^/v\?(.+)[./?#].*")]').extract()
                if search_hrefs:
                    for search_href in search_hrefs:
                        result = regex_pattern.search(search_href)
                        if result:
                            results = result.groups()
                            search_filters = results[0].split('&')
                            not_in_flag = False
                            for url_filter in url_filters:
                                if url_filter and url_filter not in search_filters:
                                    not_in_flag = True
                                    break
                            if not not_in_flag:
                                search_href = youku_url_extract.soku_url_prefix + search_href
                                items.append(search_href)

            else:
                soku_hrefs = sel.xpath('//a/@href[re:test(., "[./:\w]*soku\.com")]')
                if soku_hrefs:
                    search_hrefs = soku_hrefs.re('(http://www\.soku\.com/v\?keyword=.+)') 
                    if search_hrefs:
                        items = items + search_hrefs
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
    
    @staticmethod
    def category_url_extract(url, content):
        items = []
        try:
            if not url:
                log.msg('category_url_extract: url is not provided')
                return items
            sel = None 
            try:
                sel = Selector(text=content)
            except Exception, e:
                log.msg('content to be parsed is not xml or html')
                log.msg(traceback.format_exc(), level=log.ERROR)
                return items
            if not sel:
                return items
            #爬取策略
            #若当前的页面类型是分类页面，则按如下方式爬取
            #   获取包含更多过滤条件的url
            #    （1）根据当前的url，截取[v/|v_olist/|v_showlist/]*.html之间的字符
            #    （2）以_为分隔符，获取key:value对
            #    （3）获取当前页面中包含所有key:value对的url，即为当前需要收集的url
            #若当前的页面类型不是分类页面，则直接获取所有的分类URL
            spider_type = youku_util.url_type_parse(url)
            if spider_type == 'category':
                #category filters
                url_filters = []
                regex_express = '/(v|v_olist|v_showlist)/(.+)\.html.*'
                regex_pattern = re.compile(regex_express)
                result = regex_pattern.search(url)
                if result:
                    results = result.groups()
                    if len(results) >= 2:
                        url_filters = results[1].split('_')
                        if 'c' in url_filters:
                            index = url_filters.index('c')
                            url_filters[index] = url_filters[index] + url_filters[index+1]
                            url_filters.remove(url_filters[index+1])
                #category items
                category_hrefs = sel.xpath('//a/@href[re:test(., "^/(v|v_olist|v_showlist)/(c|c_)[\d]+.*\.html.*")]').extract()
                if category_hrefs:
                    for category_href in category_hrefs:
                        result = regex_pattern.search(category_href)
                        if result:
                            results = result.groups()
                        if len(results) >= 2:
                            category_filters = results[1].split('_')
                            if 'c' in category_filters:
                                index = category_filters.index('c')
                                category_filters[index] = category_filters[index] + category_filters[index+1]
                                category_filters.remove(category_filters[index+1])
                            not_in_flag = False
                            index = 0
                            for url_filter in url_filters:
                                if index%2 == 0:
                                    if url_filter and url_filter not in category_filters:
                                        not_in_flag = True
                                        break
                                index = index + 1
                            if not not_in_flag:
                                category_href = youku_url_extract.youku_url_prefix + category_href
                                items.append(category_href)
            else:
                #提取出全部所有的youku的url
                youku_hrefs = sel.xpath('//a/@href[re:test(., "[./:\w]*youku\.com")]')
                category_hrefs = youku_hrefs.re('(http://www\.youku\.com/v/c[\d_]+.*\.html)')
                if category_hrefs:
                    items = items + category_hrefs
                category_hrefs = youku_hrefs.re('(http://www\.youku\.com/v_olist/c[\d_]+.*\.html)')
                if category_hrefs:
                    items = items + category_hrefs
                category_hrefs = youku_hrefs.re('(http://www\.youku\.com/v_showlist/c[\d_]+.*\.html)')
                if category_hrefs:
                    items = items + category_hrefs
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items            

    @staticmethod
    def video_set_url_extract(url, content):
        items = []
        try:
            sel = None 
            try:
                sel = Selector(text=content)
            except Exception, e:
                log.msg('content to be parsed is not xml or html')
                log.msg(traceback.format_exc(), level=log.ERROR)
                return items
            if not sel:
                return items            
            #提取出全部所有的youku的url
            youku_hrefs = sel.xpath('//a/@href[re:test(., "[./\:\w]*youku\.com")]')
            if youku_hrefs:
                video_set_hrefs = youku_hrefs.re('(http://www\.youku\.com/show_page/id_[\w]+\.html.*)')
                if video_set_hrefs:
                    items = items + video_set_hrefs
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items    

    @staticmethod            
    def user_url_extract(url, content):
        items = []
        try:
            sel = None 
            try:
                sel = Selector(text=content)
            except Exception, e:
                log.msg('content to be parsed is not xml or html')
                log.msg(traceback.format_exc(), level=log.ERROR)
                return items
            if not sel:
                return items
            #提取出全部所有的youku的url
            youku_hrefs = sel.xpath('//a/@href[re:test(., "[./\:\w]*youku\.com")]')
            if youku_hrefs:
                user_hrefs = youku_hrefs.re('(http://i\.youku\.com/u/[\w]+.*)') 
                if user_hrefs:
                    items = items + user_hrefs
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items            

    @staticmethod            
    def video_url_extract(url, content):
        items = []
        try:
            sel = None 
            try:
                sel = Selector(text=content)
            except Exception, e:
                log.msg('content to be parsed is not xml or html')
                log.msg(traceback.format_exc(), level=log.ERROR)
                return items
            if not sel:
                return items
            #提取出全部所有的youku的url
            youku_hrefs = sel.xpath('//a/@href[re:test(., "[./\:\w]*youku\.com")]')
            if youku_hrefs:
                video_hrefs = youku_hrefs.re('(http://v\.youku\.com/v_show/id_[\w]+\.html.*)')
                if video_hrefs:
                    items = items + video_hrefs
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items            
