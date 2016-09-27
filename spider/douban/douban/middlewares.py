# -*- coding: utf-8 -*-
from scrapy.conf import settings
import random
from scrapy import signals
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
try:
    from douban.hades_db.db_mgr import DbManager
except ImportError:
    from hades_db.db_mgr import DbManager

class RandomProxy(object):
    def __init__(self, settings):
        self.mgr = DbManager.instance()
        self.sd_proxy_list = settings.get('SD_PROXY_LIST')
        self.proxies = set(self.sd_proxy_list)
        self.load_proxy_web()

    def load_proxy_web(self):
        #res = self.mgr.get_proxies_by_siteCode('douban')
        #res = self.mgr.get_proxy_web_all()
        #self.proxies.update(['%s://%s:%s' % (r['protocol'].lower(), r['ip'], r['port']) for r in res])
        #print len(self.proxies)
        pass

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        if len(self.proxies) < 20:
            self.load_proxy_web()
        if 'proxy' in request.meta:
            return
        else:
            p = random.choice(list(self.proxies))
            request.meta['proxy'] = p

    def process_exception(self, request, exception, spider):
        pass
        '''
        if 'proxy' in request.meta:
            p = request.meta['proxy']
            if p in self.proxies:
                self.proxies.remove(p)
        '''

class RandomUserAgentMiddleware(UserAgentMiddleware):
    def __init__(self, user_agent):
        super(RandomUserAgentMiddleware, self).__init__()
        self.user_agent = user_agent
        self.ua_list = settings.get('USER_AGENT_LIST')
        #self.user_agent = random.choice(self.ua_list)

    def process_request(self, request, spider):
        ua = random.choice(self.ua_list)
        if ua:
            request.headers.setdefault('User-Agent', ua)

