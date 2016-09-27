# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re
import urlparse
import traceback
from scrapy import log
from scrapy.selector import Selector

from youtube_util import youtube_util

class youtube_url_extract(object):
    
    youtube_url_prefix = 'https://www.youtube.com'
    subject_titles = ['featured', 'videos', 'playlists', 'channels', 'discussion','about']
    
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
            spider_type = youtube_util.url_type_parse(url)
            if spider_type == 'channel':
                channel_hrefs = None
                #获取相对地址
                #提取所有相对url(需以/开头)
                relative_hrefs = sel.xpath('//a/@href[re:test(., "^[/]")]')
                if relative_hrefs:
                    (protocol, domain, rest) = youtube_util.url_split(url)
                    if rest:
                        regex_express = '(%s.+)' % rest
                        channel_hrefs = relative_hrefs.re(regex_express)
                        if channel_hrefs:
                            for channel_href in channel_hrefs:
                                channel_href = youtube_url_extract.youtube_url_prefix + channel_href
                                items.append(channel_href)
                channel_hrefs = None
                #获取绝对地址
                absolute_hrefs = sel.xpath('//a/@href[re:test(., "https://www\.youtube\.com")]')
                if absolute_hrefs:
                    regex_express = '(%s.+)' % url
                    channel_hrefs = absolute_hrefs.re(regex_express)
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
            #   获取子搜索页
            #       以&分割，获取filter,以%2C分割，得到子项
            #若当前页面类型不是搜索页
            #   直接获取所有搜索链接
            spider_type = youtube_util.url_type_parse(url)
            if spider_type == 'search':
                search_hrefs = None
                #获取当前的过滤条件
                #https://www.youtube.com/results?lclk=3d&filters=hd%2Cvideo%2C3d&search_query=psy+style
                regex_express = 'https://www\.youtube\.com/results\?.*filters=(.*)'
                regex_pattern = re.compile(regex_express)
                result = regex_pattern.search(url)
                filters = None
                if result:
                    results = result.groups()
                    paras = results[0].split('&')
                    filters = paras[0]
                    if filters:
                        filters = filters + '%2C'
                #获取相对地址
                #提取所有相对url(需以/开头)
                relative_hrefs = sel.xpath('//a/@href[re:test(., "^[/]")]')
                if relative_hrefs:
                    if filters:
                        regex_express = '(/results\?.*filters=%s.+)'% filters
                        search_hrefs = relative_hrefs.re(regex_express)
                    else:
                        regex_express = '(/results\?.*)'
                        search_hrefs = relative_hrefs.re(regex_express)
                    if search_hrefs:
                        for search_href in search_hrefs:
                            search_href = youtube_url_extract.youtube_url_prefix + search_href
                            items.append(search_href)
                search_hrefs = None
                #获取绝对地址
                absolute_hrefs = sel.xpath('//a/@href[re:test(., "https://www\.youtube\.com")]')
                if absolute_hrefs:
                    if filters:
                        regex_express = '(https://www\.youtube\.com/results\?.*filters=%s.+)'% filters
                        search_hrefs = absolute_hrefs.re(regex_express)
                    else:
                        regex_express = '(https://www\.youtube\.com/results\?.*)'
                        search_hrefs = absolute_hrefs.re(regex_express)
                    if search_hrefs:
                        items = items + search_hrefs
            else:
                search_hrefs = None
                #提取所有相对url(需以/开头)
                relative_hrefs = sel.xpath('//a/@href[re:test(., "^[/]")]')
                if relative_hrefs:
                    regex_express = '(/results\?.*search_query=.*)'
                    search_hrefs = relative_hrefs.re(regex_express)
                    if search_hrefs:
                        for search_href in search_hrefs:
                            search_href = youtube_url_extract.youtube_url_prefix + search_href
                            items.append(search_href)
                search_hrefs = None
                #获取绝对地址
                absolute_hrefs = sel.xpath('//a/@href[re:test(., "https://www\.youtube\.com")]')
                if absolute_hrefs:
                    regex_express = '(https://www\.youtube\.com/results\?.*search_query=.*)'
                    search_hrefs = absolute_hrefs.re(regex_express)
                    if search_hrefs:
                        items = items + search_hrefs
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
            video_set_hrefs = None
            #提取所有相对url(需以/开头)
            relative_hrefs = sel.xpath('//a/@href[re:test(., "^[/]")]')
            if relative_hrefs:
                regex_express = '(/playlist\?list=.*)'
                video_set_hrefs = relative_hrefs.re(regex_express)
                if video_set_hrefs:
                    for video_set_href in video_set_hrefs:
                        video_set_href = youtube_url_extract.youtube_url_prefix + video_set_href
                        items.append(video_set_href)
            video_set_hrefs = None
            #获取绝对地址
            absolute_hrefs = sel.xpath('//a/@href[re:test(., "https://www\.youtube\.com")]')
            if absolute_hrefs:
                regex_express = '(https://www\.youtube\.com/playlist\?list=.*)'
                video_set_hrefs = absolute_hrefs.re(regex_express)
                if video_set_hrefs:
                    items = items + video_set_hrefs
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
            video_hrefs = None
            #提取所有相对url(需以/开头)
            relative_hrefs = sel.xpath('//a/@href[re:test(., "^[/]")]')
            if relative_hrefs:
                regex_express = '(/watch\?v=.*)'
                video_hrefs = relative_hrefs.re(regex_express)
                if video_hrefs:
                    for video_href in video_hrefs:
                        video_href = youtube_url_extract.youtube_url_prefix + video_href
                        items.append(video_href)
            video_hrefs = None
            #获取绝对地址
            absolute_hrefs = sel.xpath('//a/@href[re:test(., "https://www\.youtube\.com")]')
            if absolute_hrefs:
                regex_express = '(https://www\.youtube\.com/watch\?v=.*)'
                video_hrefs = absolute_hrefs.re(regex_express)
                if video_hrefs:
                    items = items + video_hrefs
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items            

    @staticmethod
    def subject_url_extract(url, content):
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
            #   （1）若当前页面类型是主题类型，则按如下方式爬取
            #       （1）若当前的主题地址刚好是在主题页中title为channels，则允许获取所有的主题
            #       （2）若是其他主题地址，只获取该主题类型的子主题类型
            #   （2）若当前页面类型是页面类型，则按如下方式爬取
            #       （1）只获取后缀在subject_titles范围的URL
            #   （3）否则，则直接获取所有的主题URL
                
            spider_type = youtube_util.url_type_parse(url)
            if spider_type == 'subject':
                url_result = urlparse.urlparse(url)
                if url_result and url_result.path:
                    url_path = url_result.path
                    #若当前的主题URL以channels结尾
                    if url_path.endswith('channels') or url_path.endswith('channels/'):
                        lookup_hrefs = sel.xpath('//div[@class="yt-lockup-content"]//a/@href')
                        if lookup_hrefs:
                            #相对地址
                            #   channel
                            subject_hrefs = lookup_hrefs.re('(/channel/.+)')
                            if subject_hrefs:
                                for subject_href in subject_hrefs:
                                    subject_href = youtube_url_extract.youtube_url_prefix + subject_href
                                    items.append(subject_href)
                            
                            subject_hrefs = None
                            #   user
                            subject_hrefs = lookup_hrefs.re('(/user/.+)')
                            if subject_hrefs:
                                for subject_href in subject_hrefs:
                                    subject_href = youtube_url_extract.youtube_url_prefix + subject_href
                                    items.append(subject_href)
                            #绝对地址
                            #   channel
                            subject_hrefs = lookup_hrefs.re('(https://www\.youtube\.com/channel/.+)')
                            if subject_hrefs:
                                items = items + subject_hrefs
                            
                            subject_hrefs = None
                            #   user
                            subject_hrefs = lookup_hrefs.re('(https://www\.youtube\.com/user/.+)')
                            if subject_hrefs:
                                items = items + subject_hrefs
                    else:
                        #当前主题的URL不包含channels，则只获取子主题类型
                        #获取相对url(需以/开头)
                        relative_hrefs = sel.xpath('//a/@href[re:test(., "^[/]")]')
                        if relative_hrefs:
                            #https://www.youtube.com/user/omame3460/playlists
                            (protocol, domain, rest) = youtube_util.url_split(url)
                            if rest:
                                if not rest.endswith('/'):
                                    rest = rest + '/'
                                for title in youtube_url_extract.subject_titles:
                                    subject_hrefs = None
                                    regex_express = '(%s%s.*)'%(rest, title)
                                    subject_hrefs = relative_hrefs.re(regex_express)
                                    if subject_hrefs:
                                        for subject_href in subject_hrefs:
                                            subject_href = youtube_url_extract.youtube_url_prefix + subject_href
                                            items.append(subject_href)
                        #获取绝对地址
                        absolute_hrefs = sel.xpath('//a/@href[re:test(., "https://www\.youtube\.com")]')
                        if absolute_hrefs:
                            (protocols, domain, rest) = youtube_util.url_split(url)
                            if rest:
                                if not rest.endswith('/'):
                                    rest = rest + '/'
                                for title in youtube_url_extract.subject_titles:
                                    subject_hrefs = None
                                    regex_express = '(%s://%s%s%s.*)'%(protocols, domain, rest, title)
                                    subject_hrefs = absolute_hrefs.re(regex_express)
                                    if subject_hrefs:
                                        items = items + subject_hrefs
            elif spider_type == 'page':
                #https://www.youtube.com/sports
                #提取所有相对url(需以/开头)
                relative_hrefs = sel.xpath('//a/@href[re:test(., "^[/]")]')
                if relative_hrefs:
                    for title in youtube_url_extract.subject_titles:
                        subject_hrefs = None
                        #channel
                        regex_express = '(/channel/.+/%s.*)' % title
                        subject_hrefs = relative_hrefs.re(regex_express)
                        if subject_hrefs:
                            for subject_href in subject_hrefs:
                                subject_href = youtube_url_extract.youtube_url_prefix + subject_href
                                items.append(subject_href)

                        subject_hrefs = None
                        #user
                        regex_express = '(/user/.+/%s.*)' % title
                        subject_hrefs = relative_hrefs.re(regex_express)
                        if subject_hrefs:
                            for subject_href in subject_hrefs:
                                subject_href = youtube_url_extract.youtube_url_prefix + subject_href
                                items.append(subject_href)
                        
                #获取绝对地址
                absolute_hrefs = sel.xpath('//a/@href[re:test(., "https://www\.youtube\.com")]')
                if absolute_hrefs:
                    for title in youtube_url_extract.subject_titles:
                        subject_hrefs = None
                        #channel
                        regex_express = '(https://www\.youtube\.com/channel/.+/%s.*)' % title
                        subject_hrefs = absolute_hrefs.re(regex_express)
                        if subject_hrefs:
                            items = items + subject_hrefs

                        subject_hrefs = None
                        #user
                        regex_express = '(https://www\.youtube\.com/user/.+/%s.*)' % title
                        subject_hrefs = absolute_hrefs.re(regex_express)
                        if subject_hrefs:
                            items = items + subject_hrefs
            else:
                #提取所有相对url(需以/开头)
                relative_hrefs = sel.xpath('//a/@href[re:test(., "^[/]")]')
                if relative_hrefs:
                    subject_hrefs = None
                    #channel
                    regex_express = '(/channel/.+)'
                    subject_hrefs = relative_hrefs.re(regex_express)
                    if subject_hrefs:
                        for subject_href in subject_hrefs:
                            subject_href = youtube_url_extract.youtube_url_prefix + subject_href
                            items.append(subject_href)

                    subject_hrefs = None
                    #user
                    regex_express = '(/user/.+)'
                    subject_hrefs = relative_hrefs.re(regex_express)
                    if subject_hrefs:
                        items = items + subject_hrefs
                #获取绝对地址
                absolute_hrefs = sel.xpath('//a/@href[re:test(., "https://www\.youtube\.com")]')
                if absolute_hrefs:
                    subject_hrefs = None
                    #channel
                    regex_express = '(https://www\.youtube\.com/channel/.+)'
                    subject_hrefs = absolute_hrefs.re(regex_express)
                    if subject_hrefs:
                        items = items + subject_hrefs

                    subject_hrefs = None
                    #user
                    regex_express = '(https://www\.youtube\.com/user/.+)'
                    subject_hrefs = absolute_hrefs.re(regex_express)
                    if subject_hrefs:
                        items = items + subject_hrefs
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items            
