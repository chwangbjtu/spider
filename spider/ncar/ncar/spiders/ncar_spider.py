# -*- coding: utf-8 -*-
import scrapy
import logging
import traceback
import urlparse
from hashlib import md5
from scrapy.http import Request
from scrapy.spiders import Spider
from ncar.items import MediaVideoItem, MediaItem, VideoItem
from scrapy.utils.project import get_project_settings
try:
    from ncar.hades_db.db_mgr import DbManager
    from ncar.hades_common.util import extract_dou_id, extract_imdb, extract_protocol, extract_info_ih, Util
except ImportError:
    from hades_db.db_mgr import DbManager
    from hades_common.util import extract_dou_id, extract_imdb, extract_protocol, extract_info_ih, Util


class NcarSpider(scrapy.Spider):
    name = "ncar"
    site_code = 'ncar'
    allowed_domains = ["bbs.ncar.cc"]
    mgr = DbManager.instance()
    site_id = str(mgr.get_site_by_code(site_code)["site_id"])
    protocol_map = mgr.get_protocol_map()
    max_number = 10000

    def __init__(self, *args, **kwargs):
        super(NcarSpider, self).__init__(*args, **kwargs)
        self.url_prefix = "http://bbs.ncar.cc/"
        self.api_murl = "http://bbs.ncar.cc/forum.php?mod=viewthread&tid=%s"

    def start_requests(self):
        self.load_member_variable()
        if 0 == self.max_number:
            start_url = "http://bbs.ncar.cc/forum.php?mod=forumdisplay&fid=%s"
        else:
            start_url = "http://bbs.ncar.cc/forum.php?mod=forumdisplay&fid=%s&filter=lastpost&orderby=lastpost"
        for fid in self.channel_switch:
            yield Request(url=start_url % fid, callback=self.parse_forumdisplay)


    def load_member_variable(self):
        try:
            max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
            if int == type(max_update_page):
                self.max_number = max_update_page
            self.channel_switch = get_project_settings().get('CHANNEL_SWITCH')
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())


    def parse_forumdisplay(self, response):
        logging.log(logging.INFO, "parse_forumdisplay:%s" % response.request.url)

        page = response.request.meta['page'] if 'page' in response.request.meta else 1

        ths = response.xpath('//tbody[re:test(@id, "normalthread_\d+")]//a[@onclick="atarget(this)"]')
        for th in ths:
            try:
                url = self.url_prefix + th.xpath('./@href').extract()[0]
                req = Request(url=url, callback=self.parse_viewthread)
                yield req
            except IndexError, e:
                logging.log(logging.ERROR, traceback.format_exc())
                continue

        if 0 == self.max_number or page < self.max_number:
            next_pages = response.xpath('//a[@class="nxt"]/@href').extract()
            if next_pages:
                req = Request(url=self.url_prefix+next_pages[0], callback=self.parse_forumdisplay, meta={'page': page+1})
                yield req


    def parse_viewthread(self, response):
        logging.log(logging.INFO, "parse_viewthread:%s" % response.request.url)

        try:
            para_dict = urlparse.parse_qs(urlparse.urlparse(response.request.url).query)
            mcont_id = tid = para_dict.get('tid')[0]

            tables = response.xpath('//div[@id="postlist"]/div[re:test(@id, "post_\d+")]/table')

            m_item = response.request.meta['m_item'] if 'm_item' in response.request.meta else None
            if not m_item:
                m_item = MediaItem()
                title = response.xpath('//span[@id="thread_subject"]/text()').re(u'[\u4e00-\u9fa5-Za-z0-9—·:：]+')[0]
                directors = tables[0].xpath('//td[@class="t_f"]').re(u'导演[：|:]\s*([^<]*)')
                actors = tables[0].xpath('//td[@class="t_f"]').re(u'主演[：|:]\s*([^<]*)')
                aliass = tables[0].xpath('//td[@class="t_f"]').re(u'又名[：|:]\s*([^<]*)')
                imdbs = tables[0].xpath('//td[@class="t_f"]').re(u'IMDb链接[：|:]\s*(tt\d+)')

                m_item['title'] = title
                if directors:
                    m_item['director'] = Util.join_list_safely(directors[0].split('/'))
                if actors:
                    m_item['actor'] = Util.join_list_safely(actors[0].replace(u'/ 更多...', '').split('/'))
                if aliass:
                    m_item['alias'] = Util.join_list_safely(aliass[0].split('/'))
                if imdbs:
                    m_item['imdb'] = imdbs[0]
                m_item['url'] = self.api_murl % mcont_id
                m_item['site_id'] = self.site_id
                m_item['cont_id'] = mcont_id

            vitems = []
            for table in tables:
                # // -> .//
                vs = table.xpath('.//td[@class="t_f"]//a[re:test(text(), ".*\.torrent")]')
                for v in vs:
                    vtitles = v.xpath('./text()').extract()
                    vurls = v.xpath('./@href').extract()
                    if vtitles and vurls:
                        v_item = VideoItem()
                        v_item['url'] = self.url_prefix + vurls[0]
                        v_item['title'] = vtitles[0]
                        #v_item['cont_id'] = md5(v_item['url']).hexdigest()
                        v_item['protocol_id'] = self.protocol_map['bt']
                        vitems.append(v_item)

            for v in vitems:
                req = Request(url=v_item['url'], callback=self.parse_torrent, meta={'m_item':m_item, 'v_item':v})
                yield req

            '''
            if vitems:
                mvitem = MediaVideoItem()
                mvitem["media"] = m_item
                mvitem['video'] = vitems
                yield mvitem
            '''

            next_viewthreads = response.xpath('//a[@class="nxt"]/@href').extract()
            if next_viewthreads:
                req = Request(url=self.url_prefix+next_viewthreads[0], callback=self.parse_viewthread, meta={'m_item':m_item})
                yield req
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())


    def parse_torrent(self, response):
        logging.log(logging.INFO, "parse_torrent:%s" % response.request.url)

        try:
            v_item = response.request.meta['v_item']
            m_item = response.request.meta['m_item']

            torrent_info = Util.get_torrent_info(response.body)
            v_item['cont_id'] = torrent_info['th']

            mvitem = MediaVideoItem()
            mvitem["media"] = m_item
            mvitem['video'] = [v_item]
            yield mvitem
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

