# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re
import urlparse
import urllib2
import traceback
from scrapy import log

class iqiyi_util(object):

    channel_domains = ['yule', 'sports', 'news',\
            'dianying', 'trailer', 'weidianying',\
            'dianshiju', 'zongyi', 'talkshow',\
            'dongman', 'games',\
            'life', 'baby', 'edu',\
            'lvyou',\
            'fun', 'dv', 'paike',\
            'business', 'tech', 'auto',\
            'mil', 'ad', 'jilupian',\
            'live', 'tese', 'qiyichupin',\
            'fashion', 'shishang', 'f',\
            'music', 'yinyue',\
            'child', 'shaoer']
    video_library_domains = ['lib', 'v']
    category_domains = ['list']
    so_domains = ['so']
    tags_domains = ['tags']
    user_domains = ['i', 'u']

    @staticmethod
    def url_splits(url):
        domain_splits = []
        path_splits = []
        try:
            if url:
                protocol, rest = urllib2.splittype(url)
                if not protocol:
                    rest = '//' + rest
                host, rest = urllib2.splithost(rest)
                #域部分解析
                if host:
                    splits = host.split('.')
                    if splits:
                        index_list = range(len(splits))
                        index_list.reverse()
                        for index in index_list:
                            if not splits[index]:
                                splits.remove('')
                        domain_splits += splits
                #路径部分解析
                if rest:
                    rest = urlparse.urlparse(rest)
                    splits = rest.path.split('/')
                    if splits:
                        index_list = range(len(splits))
                        index_list.reverse()
                        for index in index_list:
                            if not splits[index]:
                                splits.remove('')
                        path_splits += splits
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return (domain_splits, path_splits)

    @staticmethod
    def channel_parse(domain_splits, path_splits):
        channel = None
        location = None
        try:
            if domain_splits:
                domain = domain_splits[0]
                if domain not in ['www', 'iqiyi']:
                    channel = domain
                    path = 'domain'
                    return (channel, location)
            channel = None
            if path_splits:
                domain = path_splits[0]
                channel = domain
                path = 'path'
                return (channel, location)
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return (channel, location)
    
    @staticmethod
    def url_channel_parse(url):
        channel = None
        location = None
        try:    
            domain_splits, path_splits = iqiyi_util.url_splits(url)
            channel, location = iqiyi_util.channel_parse(domain_splits, path_splits)
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return (channel, location) 
    
    @staticmethod
    def url_type_parse(url):
        spider_type = 'page'
        try:                           
            channel, location = iqiyi_util.url_channel_parse(url)
            if channel in iqiyi_util.so_domains:
                spider_type = 'search'
            elif channel in iqiyi_util.category_domains:
                spider_type = 'category'
            elif channel in iqiyi_util.tags_domains:
                spider_type = 'tags'
            elif channel in iqiyi_util.user_domains:
                spider_type = 'user'
            elif channel in iqiyi_util.video_library_domains:
                spider_type = 'lib'
                spider_type = iqiyi_util.url_type_parse_second(url, spider_type, channel)
            else:
                if location == 'domain':
                    if channel in iqiyi_util.channel_domains:
                        spider_type = 'channel'
                else:
                    if channel in iqiyi_util.channel_domains:
                        spider_type = 'channel'
                        spider_type = iqiyi_util.url_type_parse_second(url, spider_type, channel)
                    else:
                        spider_type = 'page'
                        spider_type = iqiyi_util.url_type_parse_second(url, spider_type, channel)                                           
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return spider_type
            
    @staticmethod
    def url_type_parse_second(url, spider_type, channel):
        try:
            if spider_type == 'lib':
                if channel == 'v':
                    spider_type = 'channel'
                    return spider_type
                #http://www.iqiyi.com/lib/yinyue/-94--223----------11-1-2--1-.html
                regex_express = 'http://www\.iqiyi\.com/lib/[a-zA-Z]+/[-\d]+\.html.*' % channel
                regex_pattern = re.compile(regex_express)
                match = regex_pattern.search(url)
                if match:
                    spider_type = 'category'
                    return spider_type                
                #http://www.iqiyi.com/lib/dianshiju/中国大陆,2014_11_1.html
                regex_express = 'http://www\.iqiyi\.com/lib/[a-zA-Z]+/.*[_\d]+\.html.*' % channel
                regex_pattern = re.compile(regex_express)
                match = regex_pattern.search(url)
                if match:
                    spider_type = 'category'
                    return spider_type
                #http://www.iqiyi.com/lib
                #http://www.iqiyi.com/lib/                
                regex_express = 'http://www\.iqiyi\.com/lib[/]{0,1}'
                regex_pattern = re.compile(regex_express)
                match = regex_pattern.search(url)
                if match:
                    spider_type = 'channel'
                    return spider_type
                #http://www.iqiyi.com/lib/dianying
                #http://www.iqiyi.com/lib/dianying/ 
                regex_express = 'http://www\.iqiyi\.com/lib/([a-zA-Z]+)[/]{0,1}'
                regex_pattern = re.compile(regex_express)
                match = regex_pattern.search(url)
                if match:
                    channel = match.group(1)
                    if channel and channel in channel_domains:
                        spider_type = 'channel'
                        return spider_type                
            elif spider_type == 'channel':
                #http://www.iqiyi.com/dianshiju/playlist295748402.html#vfrm=2-3-0-1          
                regex_express = 'http://www\.iqiyi\.com/%s/playlist[\d]+\.html.*' % channel
                regex_pattern = re.compile(regex_express)
                match = regex_pattern.search(url)
                if match:
                    spider_type = 'video_set'
                    return spider_type
                #http://www.iqiyi.com/dianshiju/20110610/26e4e286f48551b5.html#vfrm=2-3-0-1            
                regex_express = 'http://www\.iqiyi\.com/%s/[\d]+/[\w]+\.html.*' % channel
                regex_pattern = re.compile(regex_express)
                match = regex_pattern.search(url)
                if match:
                    spider_type = 'video'
            else:
                #http://www.iqiyi.com/a_19rrguehx9.html#vfrm=2-3-0-1
                regex_express = 'http://www\.iqiyi\.com/a_[\w]+\.html.*'
                regex_pattern = re.compile(regex_express)
                match = regex_pattern.search(url)
                if match:
                    spider_type = 'video_set'
                    return spider_type
                
                #http://www.iqiyi.com/lib/s_214734305.html#vfrm=2-3-0-1
                #http://www.iqiyi.com/lib/m_200047914.html#vfrm=2-3-0-1
                regex_express = 'http://www\.iqiyi\.com/lib/(s|m)_[\w]+\.html.*'
                regex_pattern = re.compile(regex_express)
                match = regex_pattern.search(url)
                if match:
                    spider_type = 'video_set'
                    return spider_type                
                
                #http://www.iqiyi.com/w_19rs83hax9.html#vfrm=2-3-0-1
                #http://www.iqiyi.com/v_19rro3mxtc.html#vfrm=2-3-0-1 
                regex_express = 'http://www\.iqiyi\.com/(w|v)_[\w]+\.html.*'
                regex_pattern = re.compile(regex_express)
                match = regex_pattern.search(url)
                if match:
                    spider_type = 'video'
                    return spider_type
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return spider_type        
