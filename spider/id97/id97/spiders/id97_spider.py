# -*- coding: utf-8 -*-
import scrapy
import logging
import traceback
from hashlib import md5
from scrapy.http import Request
from scrapy.spiders import Spider
from id97.items import MediaVideoItem, MediaItem, VideoItem
from scrapy.utils.project import get_project_settings
try:
    from id97.hades_db.db_mgr import DbManager
    from id97.hades_common.util import extract_dou_id, extract_imdb, extract_protocol, extract_info_ih, Util
except ImportError:
    from hades_db.db_mgr import DbManager
    from hades_common.util import extract_dou_id, extract_imdb, extract_protocol, extract_info_ih, Util


class Id97Spider(scrapy.Spider):
    name = "id97"
    site_code = 'id97'
    allowed_domains = ["www.id97.com"]
    mgr = DbManager.instance()
    site_id = str(mgr.get_site_by_code(site_code)["site_id"])
    protocol_map = mgr.get_protocol_map()
    max_number = 10000

    def __init__(self, *args, **kwargs):
        super(Id97Spider, self).__init__(*args, **kwargs)
        self.url_prefix = "http://www.id97.com"

    def start_requests(self):
        self.load_member_variable()
        start_url = "http://www.id97.com/videos/movie/"
        yield Request(url=start_url, callback=self.parse_page)


    def load_member_variable(self):
        try:
            max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
            if int == type(max_update_page) and max_update_page != 0:
                self.max_number = max_update_page
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())


    def parse_page(self, response):
        logging.log(logging.INFO, "parse_page:%s" % response.request.url)

        page = response.request.meta['page'] if 'page' in response.request.meta else 1

        movie_items = response.xpath('//div[@class="col-md-12"]/div[@class="col-md-1-5 col-sm-4 col-xs-6 movie-item"]')
        for mitem in movie_items:
            try:
                title = mitem.xpath('./div[@class="movie-item-in"]/a/@title').extract()[0]
                url = mitem.xpath('./div[@class="movie-item-in"]/a/@href').extract()[0]
                req = Request(url=url, callback=self.parse_media)
                req.meta.update({'title': title})
                yield req
            except IndexError, e:
                logging.log(logging.ERROR, traceback.format_exc())
                continue
        if page < self.max_number:
            next_pages = response.xpath('//div[@class="pager-bg"]/ul/li/a[@rel="next"]/@href').extract()
            if next_pages:
                req = Request(url=self.url_prefix+next_pages[0], callback=self.parse_page, meta={'page': page+1})
                yield req


    def parse_media(self, response):
        logging.log(logging.INFO, "parse_media:%s" % response.request.url)

        try:
            dou_id_urls = response.xpath('//table[@class="movie-info-table"]/tbody/tr/td/a[@class="score"]/@href').extract()
            imdb_urls = response.xpath('//table[@class="movie-info-table"]/tbody/tr/td/a[@class="imdb"]/@href').extract()
            directors = response.xpath('//table[@class="movie-info-table"]/tbody/tr/td[1]/span[text()="%s"]/../../td[2]/a/text()' % u'导演：').extract()
            actors = response.xpath('//table[@class="movie-info-table"]/tbody/tr/td[1]/span[text()="%s"]/../../td[2]/a/text()' % u'主演：').extract()
            aliass = response.xpath('//table[@class="movie-info-table"]/tbody/tr/td[1]/span[text()="%s"]/../../td[2]/text()' % u'又名：').extract()

            m_item = MediaItem()
            m_item['title'] = response.request.meta['title']
            m_item['dou_id'] = extract_dou_id(dou_id_urls[0]) if dou_id_urls else None
            m_item['imdb'] = extract_imdb(imdb_urls[0]) if imdb_urls else None
            m_item['cont_id'] = response.request.url.split('/')[6].split('.')[0]
            m_item['url'] = response.request.url
            m_item['site_id'] = self.site_id

            if directors:
                m_item['director'] = Util.join_list_safely(directors)
            if actors:
                m_item['actor'] = Util.join_list_safely(actors)
            if aliass:
                aliass = aliass[0].split('/')
                m_item['alias'] = Util.join_list_safely(aliass)

            vitems = []
            resource_list = response.xpath('//table[@class="table table-hover"]/tbody/tr')
            for resource in resource_list:
                try:
                    url = resource.xpath('./td[@class="text-break"]/div/a/@href').extract()[0]
                    title = resource.xpath('./td[@class="text-break"]/div/a/@title').extract()[0]
                    vcont_id = resource.xpath('./td[@class="text-break"]/div/a/@id').extract()[0]
                    protocol = extract_protocol(url)
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


