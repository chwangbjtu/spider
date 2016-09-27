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
    name = "kat_revise"
    site_code = 'kat'
    allowed_domains = ["kat.cr"]
    mgr = DbManager.instance()
    site_id = str(mgr.get_site_by_code(site_code)["site_id"])
    protocol_map = mgr.get_protocol_map()
    max_number = 10000

    def __init__(self, *args, **kwargs):
        super(KatSpider, self).__init__(*args, **kwargs)
        self.url_prefix = "https://kat.cr"
        self.url_api = "https://kat.cr/%s/%s/"
        self.url_getepisode = "https://kat.cr/media/getepisode/%s/"


    def start_requests(self):
        ms = self.mgr.get_kat_revise_media()
        print len(ms)
        if ms:
            for m in ms:
                vurls = self.mgr.get_kat_revise_video(m['mid'])
                if not vurls:
                    continue
                else:
                    yield Request(url=m['url'], callback=self.parse_all_episode, meta={'vurls':vurls})

    def parse_all_episode(self, response):
        logging.log(logging.INFO, "parse_all_episode:%s" % response.request.url)

        vurls = response.request.meta['vurls']

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
                        m_item['cont_id'] = imdb + '|' + str(snum)

                        req = Request(url=self.url_getepisode % episode_num, callback=self.parse_resource, meta={'m_item':m_item, 'vtitle':vtitle, 'vnum':vnum, 'vurls':vurls})
                        yield req
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())


    def parse_resource(self, response):
        logging.log(logging.INFO, "parse_resource:%s" % response.request.url)

        m_item = response.request.meta['m_item']
        vtitle = response.request.meta['vtitle']
        vnum = response.request.meta['vnum']
        revise_vurls = response.request.meta['vurls']

        vitems = []
        for x in ['Torrent magnet link', 'Download torrent file']:
            vurls = response.xpath('//table[@class="data"]//tr/td[1]//a[@title="%s"]/@href' % x).extract()
            rtitles = response.xpath('//table[@class="data"]//tr/td[1]//a[@title="%s"]/../../div[@class="torrentname"]/div/a/text()' % x).extract()
            if not vurls:
                continue
            for i, vurl in enumerate(vurls):
                if vurl.startswith('//'):
                    vurl = 'https:' + vurl
                if vurl not in revise_vurls:
                    continue
                rtitle = rtitles[i]
                protocol = extract_protocol(vurl)
                if protocol in self.protocol_map and protocol != 'http':
                    v_item = VideoItem()
                    v_item['url'] = vurl
                    v_item['title'] = rtitle
                    v_item['vnum'] = vnum
                    v_item['cont_id'] = md5(vurl).hexdigest()
                    v_item['protocol_id'] = self.protocol_map[protocol]
                    if protocol == 'magnet':
                        v_item['tor_ih'] = extract_info_ih(vurl)
                    vitems.append(v_item)

        if vitems:
            mvitem = MediaVideoItem()
            mvitem["media"] = m_item
            mvitem['video'] = vitems

            yield mvitem

