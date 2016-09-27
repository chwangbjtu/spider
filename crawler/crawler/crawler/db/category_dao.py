# -*- coding:utf-8 -*-
import traceback
from scrapy import log
from db_connect import MysqlConnect
import math

class CategoryDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn
        self._tb_name = 'category'
        self._site_tb_name = 'site'

    def get_cat_ids(self, site_name=None):
        try:
            sql = "SELECT cat_name, cat_id FROM %s AS e, %s AS s \
                    WHERE e.site_id = s.site_id " % (self._tb_name, self._site_tb_name)
            para = None
            if site_name:
                sql += " AND s.site_name = %s "
                para = (site_name, )
            res = self._db_conn.db_fetchall(sql, para, as_dic=True)

            ret = {}
            for item in res:
                ret[item['cat_name']] = item['cat_id']
            return ret
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
    
if __name__ == "__main__":
    try:
        import json
        log.start(loglevel='INFO')
        db_conn = MysqlConnect()

        category_dao = CategoryDao(db_conn)

        res = category_dao.get_cat_ids('funshion')
        log.msg(json.dumps(res))

    except Exception,e:
        log.msg(traceback.format_exc(), level=log.ERROR)
