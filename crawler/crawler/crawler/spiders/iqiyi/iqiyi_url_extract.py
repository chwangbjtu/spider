# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re
import traceback
from scrapy import log
from scrapy.selector import Selector
from iqiyi_util import iqiyi_util

class iqiyi_url_extract(object):
    
    fashion_channels = ['fashion', 'shishang', 'f']
    music_channels = ['music', 'yinyue']
    child_channels = ['child', 'shaoer']

    list_url_prefix = 'http://list.iqiyi.com'
    iqiyi_url_prefix = 'http://www.iqiyi.com'
    so_url_prefix = 'http://so.iqiyi.com'
    
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
            #若当前页面类型是频道页面，则分为如下两种情况
            #   （1）http://www.iqiyi.com/*** 或者 http://***.iqiyi.com
            #   （2）http://www.iqiyi.com/lib/***            
            #若当前页面类型不是频道页面，直接忽略
            spider_type = iqiyi_util.url_type_parse(url)
            if spider_type == 'channel':
                current_channel_urls = []
                channel = None
                regex_pattern = re.compile('http://www\.iqiyi\.com/lib/([a-zA-Z]+).*')
                result = regex_pattern.search(url)
                if result:
                    results = result.groups()
                    channel = results[0]
                    #fashion同义词
                    if channel in iqiyi_url_extract.fashion_channels:
                        for fashion_channel in iqiyi_url_extract.fashion_channels:
                            same_url = url.replace(channel, fashion_channel)
                            current_channel_urls.append(same_url)
                    #music同义词
                    elif channel in iqiyi_url_extract.music_channels:
                        for music_channel in iqiyi_url_extract.music_channels:
                            same_url = url.replace(channel, music_channel)
                            current_channel_urls.append(same_url)
                    #child同义词
                    elif channel in iqiyi_url_extract.child_channels:
                        for child_channel in iqiyi_url_extract.child_channels:
                            same_url = url.replace(channel, child_channel)
                            current_channel_urls.append(same_url)
                    #其他
                    current_channel_urls.append(url)                  
                else:
                    regex_pattern = re.compile('http://([a-zA-Z]+)\.iqiyi\.com.*')
                    result = regex_pattern.search(url)                    
                    if result:
                        results = result.groups()
                        channel = results[0]
                        #fashion同义词
                        if channel in iqiyi_url_extract.fashion_channels:
                            for fashion_channel in iqiyi_url_extract.fashion_channels:
                                same_url = url.replace(channel, fashion_channel)
                                current_channel_urls.append(same_url)
                                same_url = url.replace(channel, 'www')
                                same_url = same_url.replace('.com', '.com/%s'%fashion_channel)
                                current_channel_urls.append(same_url)
                        #music同义词
                        elif channel in iqiyi_url_extract.music_channels:
                            for music_channel in iqiyi_url_extract.music_channels:
                                same_url = url.replace(channel, music_channel)
                                current_channel_urls.append(same_url)
                                same_url = url.replace(channel, 'www')
                                same_url = same_url.replace('.com', '.com/%s'%music_channel)
                                current_channel_urls.append(same_url)
                        #child同义词
                        elif channel in iqiyi_url_extract.child_channels:
                            for child_channel in iqiyi_url_extract.child_channels:
                                same_url = url.replace(channel, child_channel)
                                current_channel_urls.append(same_url)
                                same_url = url.replace(channel, 'www')
                                same_url = same_url.replace('.com', '.com/%s'%child_channel)
                                current_channel_urls.append(same_url)                                
                        #其他
                        current_channel_urls.append(url)
                        same_url = url.replace(channel, 'www')
                        same_url = same_url.replace('.com', '.com/%s'%channel)
                        current_channel_urls.append(same_url)                        
                    else:
                        regex_pattern = re.compile('http://www\.iqiyi\.com/([a-zA-Z]+).*')
                        result = regex_pattern.search(url)                    
                        if result:
                            results = result.groups()
                            channel = results[0]     
                            #fashion同义词
                            if channel in iqiyi_url_extract.fashion_channels:
                                for fashion_channel in iqiyi_url_extract.fashion_channels:
                                    same_url = url.replace(channel, fashion_channel)
                                    current_channel_urls.append(same_url)
                                    same_url = same_url.replace('/%s'%channel, '')
                                    same_url = url.replace('www', fashion_channel)
                                    current_channel_urls.append(same_url)
                            #music同义词
                            elif channel in iqiyi_url_extract.music_channels:
                                for music_channel in iqiyi_url_extract.music_channels:
                                    same_url = url.replace(channel, music_channel)
                                    current_channel_urls.append(same_url)
                                    same_url = same_url.replace('/%s'%channel, '')
                                    same_url = url.replace('www', music_channel)
                                    current_channel_urls.append(same_url)                                    
                            #child同义词
                            elif channel in iqiyi_url_extract.child_channels:
                                for child_channel in iqiyi_url_extract.child_channels:
                                    same_url = url.replace(channel, child_channel)
                                    current_channel_urls.append(same_url)
                                    same_url = same_url.replace('/%s'%channel, '')
                                    same_url = url.replace('www', child_channel)
                                    current_channel_urls.append(same_url)                                
                            #其他
                            current_channel_urls.append(url)
                            same_url = same_url.replace('/%s'%channel, '')
                            same_url = url.replace('www', channel)
                            current_channel_urls.append(same_url)                

            #提取所有iqiyi的url           
            iqiyi_hrefs = sel.xpath('//a/@href[re:test(., "[./:\w]*iqiyi\.com")]')
            if iqiyi_hrefs:
                if current_channel_urls:
                    for channel_url in current_channel_urls:
                        regex_express = '(%s.+)' % channel_url
                        channel_hrefs = iqiyi_hrefs.re(regex_express)
                        if channel_hrefs:
                            items = items + channel_hrefs
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
            #（1）如果当前页是分类页，则分为两种情况
            #   （1）以list.iqiyi.com为开头的分类页
            #       过滤出子分类的URL
            #   （2）以www.iqiyi.com/lib/yinyue/为开头的分类页，该分类又分为两种
            #       （1）http://www.iqiyi.com/lib/yinyue/-94--223----------11-1-2--1-.html
            #       （2）http://www.iqiyi.com/lib/dianshiju/,中国大陆,2015_11_1.html
            #       过滤出子分类的URL
            #（2）如果当前页不是分类页
            spider_type = iqiyi_util.url_type_parse(url)
            if spider_type == 'category':
                regex_pattern = re.compile('/www/([\d]+)/([\d-]+)-iqiyi-[\d-]+\.html')
                result = regex_pattern.search(url)
                if result:
                    results = result.groups()
                    if len(results) >= 2:
                        channel_type = results[0]
                        category_filters = results[1].split('-')
                        category_hrefs = sel.xpath('//a/@href[re:test(., "^/www/%s/[\d-]+-iqiyi-[\d-]+\.html")]'%channel_type).extract()
                        if category_hrefs:
                            for category_href in category_hrefs:
                                result = regex_pattern.search(category_href)
                                results = result.groups()
                                temp_filters = results[1].split('-')
                                filter_flag = True
                                for category_filter in category_filters:
                                    if category_filter and category_filter not in temp_filters:
                                        filter_flag = False
                                if filter_flag == True:
                                    category_href = iqiyi_url_extract.list_url_prefix + category_href
                                    items.append(category_href)
                
                regex_pattern = re.compile('/lib/([a-zA-Z]+)/([\d-]+)\.html')
                result = regex_pattern.search(url)
                if result:
                    results = result.groups()
                    if len(results) >= 2:
                        channel_type = results[0]
                        category_filters = results[1].split('-')
                        category_hrefs = sel.xpath('//a/@href[re:test(., "^/lib/%s/[\d-]+\.html")]'%channel_type).extract()
                        if category_hrefs:
                            for category_href in category_hrefs:
                                result = regex_pattern.search(category_href)
                                results = result.groups()
                                temp_filters = results[1].split('-')
                                filter_flag = True
                                for category_filter in category_filters:
                                    if category_filter and category_filter not in temp_filters:
                                        filter_flag = False
                                if filter_flag == True:
                                    category_href = iqiyi_url_extract.iqiyi_url_prefix + category_href
                                    items.append(category_href)

                    regex_pattern = re.compile('/lib/([a-zA-Z]+)/(.*)_[\d_]+\.html')
                    result = regex_pattern.search(url)
                    if result:
                        results = result.groups()
                        if len(results) >= 2:
                            channel_type = results[0]
                            category_filters = results[1].split(',')
                            category_hrefs = sel.xpath('//a/@href[re:test(., "^/lib/%s/.*_[\d_]+\.html")]'%channel_type).extract()
                            if category_hrefs:
                                for category_href in category_hrefs:
                                    result = regex_pattern.search(category_href)
                                    results = result.groups()
                                    temp_filters = results[1].split(',')
                                    filter_flag = True
                                    for category_filter in category_filters:
                                        if category_filter and category_filter not in temp_filters:
                                            filter_flag = False
                                    if filter_flag == True:
                                        category_href = iqiyi_url_extract.iqiyi_url_prefix + category_href
                                        items.append(category_href)                    
            else: 
                try:
                    channel, location = iqiyi_util.url_channel_parse(url)
                except Exception, e:
                    log.msg('url is invalid')
                    log.msg(traceback.format_exc(), level=log.ERROR)
                    return items
                #提取所有iqiyi的url
                iqiyi_hrefs = sel.xpath('//a/@href[re:test(., "[./:\w]*iqiyi\.com")]')
                if iqiyi_hrefs:
                    #分类页URL
                    #   (1)提取http://list.iqiyi.com/www/6/152-155------------11-1-1-iqiyi--.html
                    category_hrefs = None
                    category_hrefs = iqiyi_hrefs.re('(http://list\.iqiyi\.com/www/[\d]+/[\d-]*-iqiyi-[-]*\.html.*)')
                    if category_hrefs:
                        items = items + category_hrefs
                    #   (2)提取http://www.iqiyi.com/lib/yinyue/-94--223----------11-1-2--1-.html
                    #fashion同义词
                    if channel in iqiyi_url_extract.fashion_channels:
                        for fashion_channel in iqiyi_url_extract.fashion_channels:
                            category_hrefs = None
                            regex_express = '(http://www\.iqiyi\.com/lib/%s/[\d-]+\.html.*)' % fashion_channel
                            category_hrefs = iqiyi_hrefs.re(regex_express)
                            if category_hrefs:
                                items = items + category_hrefs
                    #music同义词
                    if channel in iqiyi_url_extract.music_channels:
                        for music_channel in iqiyi_url_extract.music_channels:
                            category_hrefs = None
                            regex_express = '(http://www\.iqiyi\.com/lib/%s/[\d-]+\.html.*)' % music_channel
                            category_hrefs = iqiyi_hrefs.re(regex_express)
                            if category_hrefs:
                                items = items + category_hrefs
                    #child同义词
                    if channel in iqiyi_url_extract.child_channels:
                        for child_channel in iqiyi_url_extract.child_channels:
                            category_hrefs = None
                            regex_express = '(http://www\.iqiyi\.com/lib/%s/[\d-]+\.html.*)' % child_channel
                            category_hrefs = iqiyi_hrefs.re(regex_express)
                            if category_hrefs:
                                items = items + category_hrefs
                    #其他
                    else:
                        category_hrefs = None
                        regex_express = '(http://www\.iqiyi\.com/lib/%s/[\d-]+\.html.*)' % channel
                        category_hrefs = iqiyi_hrefs.re(regex_express)
                        if category_hrefs:
                            items = items + category_hrefs
                    #   (3)提取http://www.iqiyi.com/lib/dianshiju/古装,美国,2010-2000_11_1.html
                    #fashion同义词
                    if channel in iqiyi_url_extract.fashion_channels:
                        for fashion_channel in iqiyi_url_extract.fashion_channels:
                            category_hrefs = None
                            regex_express = '(http://www\.iqiyi\.com/lib/%s/.*[d_]+\.html.*)' % fashion_channel
                            category_hrefs = iqiyi_hrefs.re(regex_express)
                            if category_hrefs:
                                items = items + category_hrefs
                    #music同义词
                    if channel in iqiyi_url_extract.music_channels:
                        for music_channel in iqiyi_url_extract.music_channels:
                            category_hrefs = None
                            regex_express = '(http://www\.iqiyi\.com/lib/%s/.*[d_]+\.html.*)' % music_channel
                            category_hrefs = iqiyi_hrefs.re(regex_express)
                            if category_hrefs:
                                items = items + category_hrefs
                    #child同义词
                    if channel in iqiyi_url_extract.child_channels:
                        for child_channel in iqiyi_url_extract.child_channels:
                            category_hrefs = None
                            regex_express = '(http://www\.iqiyi\.com/lib/%s/[\d-]+\.html.*)' % child_channel
                            category_hrefs = iqiyi_hrefs.re(regex_express)
                            if category_hrefs:
                                items = items + category_hrefs

                    #其他
                    else:
                        category_hrefs = None
                        regex_express = '(http://www\.iqiyi\.com/lib/%s/[\d-]+\.html.*)' % channel
                        category_hrefs = iqiyi_hrefs.re(regex_express)
                        if category_hrefs:
                            items = items + category_hrefs         
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items

    @staticmethod            
    def search_url_extract(url, content):
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
            #爬取策略
            #（1）如果当前页是搜索页面，采用的相对地址，且对带有_site_iqiyi
            #（2）如果当前页不是搜索页面，则采用绝对地址
            #提取所有iqiyi的搜索url（绝对地址|相对地址）
            spider_type = iqiyi_util.url_type_parse(url)
            if spider_type == 'search':
                iqiyi_so_hrefs = sel.xpath('//a/@href[re:test(., "^q_.+_site_iqiyi_.+")]').extract()
                if iqiyi_so_hrefs:
                    iqiyi_so_hrefs = iqiyi_url_extract.so_url_prefix + '/so/' + iqiyi_so_hrefs
                    items = items + iqiyi_so_hrefs
            else:
                #提取所有iqiyi的url
                iqiyi_hrefs = sel.xpath('//a/@href[re:test(., "[./:\w]*iqiyi\.com")]')
                if iqiyi_hrefs:
                    iqiyi_so_hrefs = iqiyi_hrefs.re('(http://so\.iqiyi\.com/so/q_.+)')
                    if iqiyi_so_hrefs:
                        items = items + iqiyi_so_hrefs
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
            #提取所有iqiyi的url
            iqiyi_hrefs = sel.xpath('//a/@href[re:test(., "[./:\w]*iqiyi\.com")]')
            if iqiyi_hrefs:
                #剧集页URL
                #   （1）提取http://www.iqiyi.com/a_19rrguehx9.html#vfrm=2-3-0-1
                video_set_hrefs = iqiyi_hrefs.re('(http://www\.iqiyi\.com/a_[\w]+\.html.*)')
                if video_set_hrefs:
                    items = items + video_set_hrefs
                #   （2）提取http://www.iqiyi.com/lib/s_214734305.html
                #   （3）提取http://www.iqiyi.com/lib/m_214734305.html
                video_set_hrefs = None
                video_set_hrefs = iqiyi_hrefs.re('(http://www\.iqiyi\.com/lib/[sm]_[\w]+\.html.*)')
                if video_set_hrefs:
                    items = items + video_set_hrefs                
                #   （4）提取http://www.iqiyi.com/dianshiju/playlist295748402.html#vfrm=2-3-0-1
                try:
                    channel, location = iqiyi_util.url_channel_parse(url)
                except Exception, e:
                    log.msg('url is invalid')
                    log.msg(traceback.format_exc(), level=log.ERROR)
                    return items
                #fashion同义词
                if channel in iqiyi_url_extract.fashion_channels:
                    for fashion_channel in iqiyi_url_extract.fashion_channels:
                        video_set_hrefs = None
                        regex_express = '(http://www\.iqiyi\.com/%s/playlist[\d]+\.html.*)' % fashion_channel
                        video_set_hrefs = iqiyi_hrefs.re(regex_express)
                        if video_set_hrefs:
                            items = items + video_set_hrefs
                #music同义词
                elif channel in iqiyi_url_extract.music_channels:
                    for music_channel in iqiyi_url_extract.music_channels:
                        video_set_hrefs = None
                        regex_express = '(http://www\.iqiyi\.com/%s/playlist[\d]+\.html.*)' % music_channel
                        video_set_hrefs = iqiyi_hrefs.re(regex_express)
                        if video_set_hrefs:
                            items = items + video_set_hrefs
                #child同义词
                elif channel in iqiyi_url_extract.child_channels:
                    for child_channel in iqiyi_url_extract.child_channels:
                        video_set_hrefs = None
                        regex_express = '(http://www\.iqiyi\.com/%s/playlist[\d]+\.html.*)' % child_channel
                        video_set_hrefs = iqiyi_hrefs.re(regex_express)
                        if video_set_hrefs:
                            items = items + video_set_hrefs
                #其他
                else:
                    video_set_hrefs = None
                    regex_express = '(http://www\.iqiyi\.com/%s/playlist[\d]+\.html.*)' % channel
                    video_set_hrefs = iqiyi_hrefs.re(regex_express)
                    if video_set_hrefs:
                        items = items + video_set_hrefs          
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items    
    
    @staticmethod            
    def tags_url_extract(url, content):
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
            #提取所有iqiyi的url
            iqiyi_hrefs = sel.xpath('//a/@href[re:test(., "[./:\w]*iqiyi\.com")]')
            if iqiyi_hrefs:            
                #标签页URL
                tags_hrefs = iqiyi_hrefs.re('(http://www\.iqiyi\.com/tags/[\w]+\.html.*)')
                if tags_hrefs:
                    items = items + tags_hrefs
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
            #爬取策略
            #   （1）http://www.iqiyi.com/u/1064362165
            #   （2）http://i.iqiyi.com/1063208820
            #提取所有iqiyi的url
            iqiyi_hrefs = sel.xpath('//a/@href[re:test(., "[./:\w]*iqiyi\.com")]')
            if iqiyi_hrefs:            
                user_hrefs = iqiyi_hrefs.re('(http://www\.iqiyi\.com/u/[\w]+)')
                if user_hrefs:
                    items = items + user_hrefs
                user_hrefs = None
                user_hrefs = iqiyi_hrefs.re('(http://i\.iqiyi\.com/[\w]+)')
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
            #爬取策略
            #   （1）http://www.iqiyi.com/w_19rs83hax9.html#vfrm=2-3-0-1
            #   （2）http://www.iqiyi.com/v_19rro3mxtc.html#vfrm=2-3-0-1
            #   （3）http://www.iqiyi.com/yinyue/20120907/93081bd904240290.html#vfrm=2-3-0-1
            #提取所有iqiyi的url
            iqiyi_hrefs = sel.xpath('//a/@href[re:test(., "[./:\w]*iqiyi\.com")]')
            if iqiyi_hrefs:
                video_hrefs = iqiyi_hrefs.re('(http://www\.iqiyi\.com/[vw]_[\w]+\.html.*)')
                if video_hrefs:
                    items = items + video_hrefs 
                video_hrefs = None
                video_hrefs = iqiyi_hrefs.re('(http://www\.iqiyi\.com/[a-zA-Z]+/[\d]+/[\w]+\.html.*)')
                if video_hrefs:
                    items = items + video_hrefs                    
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items            
