# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re
import urllib2
import traceback
from scrapy import log

class youtube_util(object):

    #channels_domain = ['paid_channels', 'music', 'comedy',\
    #                    'file_entertainment', 'gaming', 'beauty_fashion',\
    #                    'from_tv', 'automotive', 'animation',\
    #                    'top_youtube_collections', 'sports', 'how-to_diy',\
    #                    'tech', 'science_education', 'cooking_health',\
    #                    'causes_non-profits', 'news_politics', 'lifestyle']

    subject_paths = ['channel', 'user']

    @staticmethod
    def url_type_parse(url):
        spider_type = 'page'
        try:                           
            regex_express = 'https://www\.youtube\.com/(\w+)[/\?#&]?.*'
            regex_pattern = re.compile(regex_express)
            result = regex_pattern.search(url)
            if result:
                results = result.groups()
                path_split = results[0]
                if path_split == 'channels':
                    spider_type = 'channel'
                elif path_split in youtube_util.subject_paths: 
                    spider_type = 'subject'
                elif path_split == 'results':
                    spider_type = 'search'
                elif path_split == 'playlist':
                    spider_type == 'video_set'
                elif path_split == 'watch':
                    spider_type == 'video'
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return spider_type

    @staticmethod
    def url_split(url):
        protocol = None
        domain = None
        rest = None
        try:                           
            protocol, rest = urllib2.splittype(url)
            if not protocol:
                protocol = 'https'
                rest = '//' + rest
            domain, rest = urllib2.splithost(rest)
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return (protocol, domain, rest) 
