# -*- coding: utf-8 -*-
import scrapy
import logging
import traceback
from hashlib import md5
from scrapy.http import Request
from scrapy.spiders import Spider
from ttmeiju.items import MediaVideoItem, MediaItem, VideoItem
from scrapy.utils.project import get_project_settings
try:
    from ttmeiju.hades_db.db_mgr import DbManager
    from ttmeiju.hades_common.util import extract_dou_id, extract_imdb, extract_protocol, extract_info_ih
except ImportError:
    from hades_db.db_mgr import DbManager
    from hades_common.util import extract_dou_id, extract_imdb, extract_protocol, extract_info_ih


class TtmeijuSpider(scrapy.Spider):
    name = "ttmeiju"
    site_code = 'ttmeiju'
    allowed_domains = ["ttmeiju.com"]
    mgr = DbManager.instance()
    site_id = str(mgr.get_site_by_code(site_code)["site_id"])
    protocol_map = mgr.get_protocol_map()
    max_number = 10000

    def __init__(self, *args, **kwargs):
        super(TtmeijuSpider, self).__init__(*args, **kwargs)
        pass

    def start_requests(self):
        self.load_member_variable()
        if self.max_number == 0:
            start_url = "http://www.ttmeiju.com/summary.html"
        else:
            start_url = "http://www.ttmeiju.com/"
        yield Request(url=start_url, callback=self.parse_page)


    def load_member_variable(self):
        try:
            max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
            if int == type(max_update_page):
                self.max_number = max_update_page
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())


    def parse_page(self, response):
        logging.log(logging.INFO, "parse_page:%s" % response.request.url)

        if self.max_number == 0:
            movie_items = response.xpath('//table[@class="seedtable"]//tr[@align="center"]/td[2]/a')
        else:
            movie_items = response.xpath('//table[@class="seedtable"]//tr[@class="Scontent"]/td[2]/a')

        for mitem in movie_items:
            try:
                title = mitem.xpath('./text()').extract()[0].split()[0]
                url = mitem.xpath('./@href').extract()[0]
                if url.endswith('Movie.html'):
                    req = Request(url=url, callback=self.parse_movie)
                    yield req
                m_item = MediaItem()
                m_item['title'] = title
                try:
                    m_item['cont_id'] = md5(url).hexdigest()
                except UnicodeEncodeError, e:
                    continue
                m_item['url'] = url
                m_item['site_id'] = self.site_id
                if self.max_number == 0:
                    req = Request(url=url, callback=self.parse_resource)
                else:
                    req = Request(url=url, callback=self.parse_seed)
                req.meta.update({'m_item': m_item})
                yield req
            except Exception, e:
                logging.log(logging.ERROR, traceback.format_exc())
                continue


    def parse_seed(self, response):
        logging.log(logging.INFO, "parse_seed:%s" % response.request.url)

        m_item = response.request.meta['m_item']

        try:
            url = response.xpath('//table[@class="seedtable"]//tr/td/a/span[@class="seedfootlink"]/../@href').extract()
            if url:
                req = Request(url=url[0], callback=self.parse_resource)
                req.meta.update({'m_item': m_item})
                yield req
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())


    def parse_movie(self, response):
        logging.log(logging.INFO, "parse_movie:%s" % response.request.url)
        
        resource_list = response.xpath('//table[@class="seedtable"]//tr[@class="Scontent"]')
        for resource in resource_list:
            try:
                title = resource.xpath('./td[2]/a/text()').extract()[0].strip('\n').strip()
                url = resource.xpath('./td[2]/a/@href').extract()[0].strip('\n').strip()
            except Exception, e:
                continue

            m_item = MediaItem()
            m_item['title'] = title
            try:
                m_item['cont_id'] = md5(url).hexdigest()
            except UnicodeEncodeError, e:
                continue
            m_item['url'] = url
            m_item['site_id'] = self.site_id

            vitems = []
            xp = 'td[3]/a[@title="%s"]/@href'
            for x in [xp % u'BT美剧片源下载', xp % u'磁力链高清美剧下载', xp % u'ed2k高清片源']:
                vurl = resource.xpath(x).extract()
                if not vurl:
                    continue
                else:
                    vurl = vurl[0]
                protocol = extract_protocol(vurl)
                if protocol not in self.protocol_map or protocol == 'http':
                    continue

                v_item = VideoItem()
                v_item['url'] = vurl
                v_item['title'] = title
                try:
                    v_item['cont_id'] = md5(vurl).hexdigest()
                except UnicodeEncodeError, e:
                    continue
                v_item['protocol_id'] = self.protocol_map[protocol]
                if protocol == 'magnet':
                    v_item['tor_ih'] = extract_info_ih(url)
                    vitems.append(v_item)

            mvitem = MediaVideoItem()
            mvitem["media"] = m_item
            mvitem['video'] = vitems

            req = Request(url=url, callback=self.parse_movie_episode)
            req.meta.update({'mvitem': mvitem})
            yield req
            #yield mvitem

            try:
                next_page = response.xpath('//a[@class="next"]/@href').extract()
                if next_page:
                    next_url = response.request.url.split('?')[0] + next_page[0]
                    req = Request(url=next_url, callback=self.parse_movie)
                    yield req
            except Exception, e:
                logging.log(logging.ERROR, traceback.format_exc())


    def parse_movie_episode(self, response):
        logging.log(logging.INFO, "parse_movie_episode:%s" % response.request.url)

        mvitem = response.request.meta['mvitem']
        imdbs = response.xpath('//a/@href').re('tt\d+')
        if imdbs:
            mvitem['media']['imdb'] = imdbs[0].strip()

        yield mvitem


    def parse_resource(self, response):
        logging.log(logging.INFO, "parse_resource:%s" % response.request.url)

        try:
            m_item = response.request.meta['m_item']

            vitems = []
            resource_list = response.xpath('//table[@class="seedtable"]//tr[@class="Scontent"]')
            for resource in resource_list:
                try:
                    title = resource.xpath('./td[2]/a/text()').extract()[0].strip('\n').strip()
                    
                    xp = 'td[3]/a[@title="%s"]/@href'
                    for x in [xp % u'BT美剧片源下载', xp % u'磁力链高清美剧下载', xp % u'ed2k高清片源']:
                        url = resource.xpath(x).extract()
                        if not url:
                            continue
                        else:
                            url = url[0]
                        protocol = extract_protocol(url)
                        if protocol not in self.protocol_map or protocol == 'http':
                            continue
                        v_item = VideoItem()
                        v_item['url'] = url
                        v_item['title'] = title
                        try:
                            v_item['cont_id'] = md5(url).hexdigest()
                        except UnicodeEncodeError, e:
                            continue
                        v_item['protocol_id'] = self.protocol_map[protocol]
                        if protocol == 'magnet':
                            v_item['tor_ih'] = extract_info_ih(url)
                        vitems.append(v_item)
                except Exception, e:
                    logging.log(logging.ERROR, traceback.format_exc())

            mvitem = MediaVideoItem()
            mvitem["media"] = m_item
            mvitem['video'] = vitems

            yield mvitem

            next_page = response.xpath('//a[@class="next"]/@href').extract()
            if next_page:
                next_url = response.request.url.split('?')[0] + next_page[0]
                req = Request(url=next_url, callback=self.parse_resource)
                req.meta.update({'m_item': m_item})
                yield req
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())


