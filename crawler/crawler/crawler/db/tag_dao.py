# -*- coding:utf-8 -*-
import traceback
from scrapy import log
from db_connect import MysqlConnect
import math

class TagDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn
        self._tb_name = 'tag'

    def get_tags(self):
        try:
            sql = "SELECT tag_name, cat_name, count, weight FROM %s" % (self._tb_name, )
            para = None
            res = self._db_conn.db_fetchall(sql, para, as_dic=True)

            return res
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
    
if __name__ == "__main__":
    try:
        import json
        log.start(loglevel='INFO')
        db_conn = MysqlConnect()

        tag_dao = TagDao(db_conn)

        res = tag_dao.get_tags()
        log.msg(json.dumps(res))

    except Exception,e:
        log.msg(traceback.format_exc(), level=log.ERROR)
