# -*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import re
import urllib2
import traceback
from scrapy import log

class youku_util(object):

    channel_domains = ['tv', 'movie', 'zy', 'music', 'comic',\
                'news', 'jilupian', 'sports', 'finance', 'edu', 'gongyi'\
                'ent', 'dv', 'game', 'fun', 'paike', 'original', \
                'life', 'fashion', 'travel', 'auto', 'tech', 'baby']
    category_domains = ['v', 'v_olist', 'v_showlist']
    video_set_domains = ['show_page']
    user_domains = ['i']
    video_domains = ['v']

    @staticmethod
    def url_type_parse(url):
        spider_type = "page"
        try:
            regex_express = 'http://(\w+)\.youku\.com.*'
            regex_pattern = re.compile(regex_express)
            result = regex_pattern.search(url)
            if result:
                results = result.groups()
                domain_split = results[0]
                if domain_split in youku_util.channel_domains:
                    spider_type = 'channel'
                elif domain_split in youku_util.user_domains:
                    spider_type = 'user'
                elif domain_split in youku_util.video_domains:
                    spider_type = 'video'
                else:
                    spider_type = youku_util.url_type_parse_second(url, spider_type) 
            else:
                regex_express = 'http://(\w+)\.soku\.com.*'
                regex_pattern = re.compile(regex_express)
                result = regex_pattern.search(url)
                if result:
                    spider_type = 'search'
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return spider_type
    @staticmethod
    def url_type_parse_second(url, spider_type):
        second_spider_type = spider_type
        try:
            if second_spider_type == 'page':
                (protocol, domain, rest) = youku_util.url_split(url)
                if rest:
                    rests = rest.split('/')
                    if len(rests) >= 2:
                        first_path = rests[1].strip()
                        if first_path in youku_util.category_domains: 
                            second_spider_type = 'category'
                        elif first_path in youku_util.video_set_domains:
                            second_spider_type = 'video_set'
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return second_spider_type

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
