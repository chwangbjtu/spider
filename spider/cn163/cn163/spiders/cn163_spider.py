# -*- coding: utf-8 -*-
import scrapy
import logging
import traceback
from hashlib import md5
from scrapy.http import Request
from scrapy.spiders import Spider
from cn163.items import MediaVideoItem, MediaItem, VideoItem
try:
    from cn163.hades_db.db_mgr import DbManager
    from cn163.hades_common.util import extract_dou_id, extract_imdb, extract_protocol, extract_info_ih
except ImportError:
    from hades_db.db_mgr import DbManager
    from hades_common.util import extract_dou_id, extract_imdb, extract_protocol, extract_info_ih


class Cn163Spider(scrapy.Spider):
    name = "cn163"
    site_code = 'cn163'
    allowed_domains = ["cn163.net"]
    mgr = DbManager.instance()
    site_id = str(mgr.get_site_by_code(site_code)["site_id"])
    protocol_map = mgr.get_protocol_map()

    def __init__(self, *args, **kwargs):
        super(Cn163Spider, self).__init__(*args, **kwargs)
        self.url_prefix = ""

    def start_requests(self):
        start_url = "http://cn163.net/ddc1/"
        yield Request(url=start_url, callback=self.parse_page)


    def parse_page(self, response):
        logging.log(logging.INFO, "parse_page:%s" % response.request.url)

        movie_items = response.xpath('//div[@id="content"]/div[@class="entry_box"]//div[@class="archive_title"]/h2/a')
        for mitem in movie_items:
            try:
                title = mitem.xpath('./text()').extract()[0].split('/')[0]
                url = mitem.xpath('./@href').extract()[0]
                req = Request(url=url, callback=self.parse_media)
                req.meta.update({'title': title})
                yield req
            except IndexError, e:
                logging.log(logging.ERROR, traceback.format_exc())
                continue
        next_pages = response.xpath('//div[@id="pagenavi"]//a[@title="%s"]/@href' % u'下一页').extract()
        if next_pages:
            req = Request(url=self.url_prefix+next_pages[0], callback=self.parse_page)
            #yield req


    def parse_media(self, response):
        logging.log(logging.INFO, "parse_media:%s" % response.request.url)

        try:
            dou_id_urls = response.xpath('//table[@class="movie-info-table"]/tbody/tr/td/a[@class="score"]/@href').extract()
            imdb_urls = response.xpath('//table[@class="movie-info-table"]/tbody/tr/td/a[@class="imdb"]/@href').extract()

            m_item = MediaItem()
            m_item['title'] = response.request.meta['title']
            #m_item['dou_id'] = extract_dou_id(dou_id_urls[0]) if dou_id_urls else None
            #m_item['imdb'] = extract_imdb(imdb_urls[0]) if imdb_urls else None
            m_item['cont_id'] = response.request.url.split('/')[4]
            m_item['url'] = response.request.url
            m_item['site_id'] = self.site_id

            vitems = []
            resource_list = response.xpath('//div[@id="entry"]/ol/li/a')
            if not resource_list:
                resource_list = response.xpath('//div[@id="entry"]/p/a')
            for resource in resource_list:
                try:
                    url = resource.xpath('./@href').extract()[0]
                    if 'cn163.net' in url:
                        continue
                    title = resource.xpath('./text()').extract()[0]
                    if title.endswith(u'网盘'):
                        continue
                    vcont_id = md5(url).hexdigest()
                    protocol = extract_protocol(url)
                    if protocol == 'http':
                        if 'http://t.cn' in url:
                            protocol = 'bt'
                    if protocol in self.protocol_map and protocol != 'http':
                        v_item = VideoItem()
                        v_item['url'] = url
                        v_item['title'] = title
                        v_item['cont_id'] = vcont_id
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

        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())


