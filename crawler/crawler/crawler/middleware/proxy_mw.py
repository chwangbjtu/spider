import re
import random
import base64
from scrapy import log

class RandomProxy(object):
    def __init__(self, settings):
        self.proxy_list = settings.get('PROXY_LIST')
        self.__load_proxy()

    def __load_proxy(self):
        proxies = []
        for f in self.proxy_list:
            fd = open(f)
            for line in fd.readlines():
                seg = line.split()
                #select fast anonymous proxy
                if seg[3] == "anonymity" and float(seg[4]) < 1:
                    proxies.append("http://%s:%s" % (seg[1], seg[2]))
            fd.close()
        
        self.proxies = set(proxies)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        # Don't overwrite with a random one (server-side state for IP)
        #if 'proxy' in request.meta:
        #    return

        if len(self.proxies) < 10:
            self.__load_proxy()

        proxy_address = random.choice(list(self.proxies))
        print "---proxy [total %s]: %s" % (len(self.proxies), proxy_address)
        request.meta['proxy'] = proxy_address

    def process_exception(self, request, exception, spider):
        if 'proxy' in request.meta:
            proxy = request.meta['proxy']
            print '---proxy fail'
            log.msg('Removing failed proxy <%s>, %d proxies left' % (proxy, len(self.proxies)))
            try:
                if proxy in self.proxies:
                    self.proxies.remove(proxy)
            except ValueError:
                pass
class SpecificProxy(object):
    def __init__(self, settings):
        self._proxy = settings.get('PROXY_HOST')
        self._spider_list = ['youtube_hottest', 'youtube_channel', 'youtube_search_video']

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        if spider.name in self._spider_list:
            request.meta['proxy'] = self._proxy

    def process_exception(self, request, exception, spider):
        if 'proxy' in request.meta:
            log.msg('proxy fail: %s' % self._proxy)
 
