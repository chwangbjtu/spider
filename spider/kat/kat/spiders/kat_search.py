# -*- coding: utf-8 -*-
import re
import json
import scrapy
import logging
import traceback
from hashlib import md5
from scrapy import Selector
from scrapy.http import Request
from scrapy.spiders import Spider
from kat.items import MediaVideoItem, MediaItem, VideoItem
from scrapy.utils.project import get_project_settings
try:
    from kat.hades_db.db_mgr import DbManager
    from kat.hades_common.util import extract_dou_id, extract_imdb, extract_protocol, extract_info_ih
except ImportError:
    from hades_db.db_mgr import DbManager
    from hades_common.util import extract_dou_id, extract_imdb, extract_protocol, extract_info_ih


class KatSpider(scrapy.Spider):
    name = "kat_search"
    site_code = 'kat'
    allowed_domains = ["kat.cr"]
    mgr = DbManager.instance()
    site_id = str(mgr.get_site_by_code(site_code)["site_id"])
    protocol_map = mgr.get_protocol_map()
    max_number = 10000

    def __init__(self, *args, **kwargs):
        super(KatSpider, self).__init__(*args, **kwargs)
        self.url_prefix = "https://kat.cr"
        self.search_api = "https://kat.cr/usearch/%s category:%s/"
        self.url_getepisode = "https://kat.cr/media/getepisode/%s/"


    def start_requests(self):
        fields = self.mgr.get_kat_search_fields()
        if fields:
            for title, name in fields:
                f = title.replace(name, '')
                f.strip()
                if f:
                    for t in ['tv', 'movies']:
                        yield Request(url=self.search_api % (f, t), callback=self.parse_search)


    def parse_search(self, response):
        logging.log(logging.INFO, "parse_search:%s" % response.request.url)

        # https://kat.cr/usearch/Jupiter%20Ascending%20category:movie/
        urls = response.xpath('//h1/a[@itemprop="url"]/@href').extract()
        if urls:
            req = Request(url=self.url_prefix+urls[0], callback=self.parse_all_episode)
            return [req]

        # https://kat.cr/usearch/Synchronicity%20category:tv/
        urls = response.xpath('//div[@class="dataList"]/ul[1]/li[1]/a/@href').extract()
        if urls:
            req = Request(url=self.url_prefix+urls[0], callback=self.parse_all_episode)
            return [req]

        # https://kat.cr/usearch/Synchronicity%20category:movies/
        urls = response.xpath('//tr[@id]//a[@class="cellMainLink"]/@href').extract()
        if urls:
            req = Request(url=self.url_prefix+urls[0], callback=self.parse_one_episode)
            return [req]


    def parse_one_episode(self, response):
        logging.log(logging.INFO, "parse_one_episode:%s" % response.request.url)

        # 未处理的不规则情况 https://kat.cr/scenes-from-a-marriage-scener-ur-ett-%C3%83-ktenskap-bergman-7-t1145619.html 
        urls = response.xpath('//div[@class="dataList"]/ul[1]/li[1]/a/@href').extract()
        if urls:
            req = Request(url=self.url_prefix+urls[0], callback=self.parse_all_episode)
            yield req


    def parse_all_episode(self, response):
        logging.log(logging.INFO, "parse_all_episode:%s" % response.request.url)

        try:
            mtitle = response.xpath('//table[@class="doublecelltable"]//tr/td[1]/h1/text()').extract()[0]
            imdb_url = response.xpath('//div[@class="torrentMediaInfo"]/div[@class="dataList"]/ul/li/strong[text()="IMDb link:"]/../a/@href').extract()[0]
            imdb = extract_imdb(imdb_url)

            # tv
            seasons = response.xpath('//table[@class="doublecelltable"]//tr/td[1]/h3')
            for season in seasons:
                snums = season.xpath('./text()').re('\d+')
                if snums:
                    snum = int(snums[0])
                    resources = season.xpath('./following-sibling::div[1]/div/div[@class="infoList versionsFolded"]/a[@class="infoListCut"]')
                    for r in resources:
                        
                        vnums = r.xpath('./span[@class="versionsEpNo"]/text()').re('\d+')
                        vtitles = r.xpath('./span[@class="versionsEpName"]/text()').extract()
                        if not vnums or not vtitles:
                            continue
                        vnum = int(vnums[0])
                        if vnum <= 0:
                            continue
                        vtitle = vtitles[0]
                        episode_nums = r.xpath('./@onclick').re('\d+')
                        if not episode_nums:
                            continue
                        episode_num = episode_nums[0]

                        m_item = MediaItem()
                        m_item['title'] = mtitle + '_Season' + str(snum)
                        m_item['url'] = response.request.url
                        m_item['site_id'] = self.site_id
                        #m_item['imdb'] = imdb + '|' + str(snum)
                        m_item['cont_id'] = imdb + '|' + str(snum)

                        req = Request(url=self.url_getepisode % episode_num, callback=self.parse_resource, meta={'m_item':m_item, 'vtitle':vtitle, 'vnum':vnum})
                        yield req
            # movie
            vitems = []
            dids = response.xpath('//div[@class="tabs tabSwitcher"]/div[@id]/@id').extract()
            for did in dids:
                for x in ['Torrent magnet link', 'Download torrent file']:
                    vurls = response.xpath('//div[@id="%s"]/table//tr[@id]/td[1]/div[1]/a[@title="%s"]/@href' % (did, x)).extract()
                    vtitles = response.xpath('//div[@id="%s"]/table//tr[@id]/td[1]/div[1]/a[@title="%s"]/../../div[@class="torrentname"]/div/a/text()' % (did, x)).extract()
                    if not vurls or not vtitles:
                        continue
                    vurl = vurls[0]
                    vtitle = vtitles[0]
                    if vurl.startswith('//'):
                        vurl = 'https:' + vurl
                    protocol = extract_protocol(vurl)
                    if protocol in self.protocol_map and protocol != 'http':
                        v_item = VideoItem()
                        v_item['url'] = vurl
                        v_item['title'] = vtitle
                        v_item['cont_id'] = md5(vurl).hexdigest()
                        v_item['protocol_id'] = self.protocol_map[protocol]
                        if protocol == 'magnet':
                            v_item['tor_ih'] = extract_info_ih(vurl)
                        vitems.append(v_item)

            if vitems:
                m_item = MediaItem()
                m_item['title'] = mtitle
                m_item['url'] = response.request.url
                m_item['site_id'] = self.site_id
                #m_item['imdb'] = imdb
                m_item['cont_id'] = imdb

                mvitem = MediaVideoItem()
                mvitem["media"] = m_item
                mvitem['video'] = vitems

                yield mvitem

        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())


    def parse_resource(self, response):
        logging.log(logging.INFO, "parse_resource:%s" % response.request.url)

        m_item = response.request.meta['m_item']
        vtitle = response.request.meta['vtitle']
        vnum = response.request.meta['vnum']

        vitems = []
        for x in ['Torrent magnet link', 'Download torrent file']:
            vurls = response.xpath('//table[@class="data"]//tr/td[1]//a[@title="%s"]/@href' % x).extract()
            rtitles = response.xpath('//table[@class="data"]//tr/td[1]//a[@title="%s"]/../../div[@class="torrentname"]/div/a/text()' % x).extract()
            if not vurls:
                continue
            vurl = vurls[0]
            rtitle = rtitles[0]
            if vurl.startswith('//'):
                vurl = 'https:' + vurl
            protocol = extract_protocol(vurl)
            if protocol in self.protocol_map and protocol != 'http':
                v_item = VideoItem()
                v_item['url'] = vurl
                v_item['title'] = rtitle
                v_item['vnum'] = vnum
                #v_item['vtitle'] = vtitle
                v_item['cont_id'] = md5(vurl).hexdigest()
                v_item['protocol_id'] = self.protocol_map[protocol]
                if protocol == 'magnet':
                    v_item['tor_ih'] = extract_info_ih(vurl)
                vitems.append(v_item)

            mvitem = MediaVideoItem()
            mvitem["media"] = m_item
            mvitem['video'] = vitems

            yield mvitem

