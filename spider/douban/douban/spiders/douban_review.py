# -*- coding:utf-8 -*-
import re
import json
import traceback
import logging
from scrapy.spiders import Spider
from scrapy.http import Request
from douban.items import RevItem, ReviewItem
from douban.spiders.base.douban_common import common_parse_review
try:
    from douban.hades_db.db_mgr import DbManager
    from douban.hades_db.mongo_mgr import MongoMgr
except ImportError:
    from hades_db.db_mgr import DbManager
    from hades_db.mongo_mgr import MongoMgr

class DoubanReview(Spider):
    '''
    '''
    name = 'douban_review'
    dbmgr = DbManager.instance()
    mongomgr = MongoMgr.instance()

    def __init__(self, *args, **kwargs):
        super(DoubanReview, self).__init__(*args, **kwargs)
        self.seen = list(set(self.dbmgr.get_douban_media_dou_id()) - set(self.mongomgr.get_review_dou_id()))
        self._url_api = "https://movie.douban.com/subject/%s/reviews"

    def start_requests(self):
        try:
            for dou_id in self.seen:
                url = self._url_api % dou_id
                yield Request(url=url, callback=self.parse_review, meta={'dou_id':dou_id})
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_review(self, response):
        try:
            logging.log(logging.INFO, 'parse_review: %s' % response.request.url)
            reviewItem = response.request.meta['reviewItem'] if 'reviewItem' in response.request.meta else ReviewItem()
            if 'dou_id' not in reviewItem:
                reviewItem['dou_id'] = int(response.request.meta['dou_id'])
            rev_lst = reviewItem['rev_lst'] if 'rev_lst' in reviewItem else []
            rev_lst.extend(common_parse_review(response))
            reviewItem['rev_lst'] = rev_lst

            next_pages = response.xpath('//div[@id="paginator"]/a[@class="next"]/@href').extract()
            if next_pages:
                next_page = next_pages[0]
                next_page_url = response.request.url.split('?')[0] + next_page
                return Request(url=next_page_url, callback=self.parse_review, meta={'reviewItem': reviewItem})
            elif self.check_item(reviewItem):
                return reviewItem
            else:
                return []
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def check_item(self, item):
        try:
            assert 'dou_id' in item, 'recommendItem miss dou_id'
            assert 'rev_lst' in item, 'recommendItem miss rec_lst'
            return True
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            return False
