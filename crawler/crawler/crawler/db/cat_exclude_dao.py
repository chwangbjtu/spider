# -*- coding:utf-8 -*-
import traceback
from scrapy import log
from db_connect import MysqlConnect
import math

class CatExcludeDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn
        self._tb_name = 'cat_exclude'

    def get_cat_exclude(self):
        try:
            sql = "SELECT cat_name from %s" % (self._tb_name, )
            res = self._db_conn.db_fetchall(sql)
            return [r[0] for r in res]
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
    
if __name__ == "__main__":
    try:
        log.start(loglevel='INFO')
        db_conn = MysqlConnect()

        cat_exclude_dao = CatExcludeDao(db_conn)

        res = cat_exclude_dao.get_cat_exclude()
        log.msg('%s' % res, level=log.INFO)

    except Exception,e:
        log.msg(traceback.format_exc(), level=log.ERROR)
