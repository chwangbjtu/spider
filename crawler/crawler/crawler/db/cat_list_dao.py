# -*- coding:utf-8 -*-
import traceback
from scrapy import log
from db_connect import MysqlConnect
import math

class CatListDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn
        self._tb_name = 'cat_list'
        self._site_tb_name = 'site'

    def get_cat_url(self,site_name):
        try:
            sql = "SELECT c.id, c.url ,c.cat_name,c.audit, c.priority FROM %s AS c \
                    LEFT JOIN %s AS s \
                    ON s.site_id = c.site_id \
                    WHERE true " % (
                    self._tb_name, self._site_tb_name)
            para = []
            if site_name:
                sql += " and s.site_name = %s"
                para.append(site_name)
            res = self._db_conn.db_fetchall(sql, para, as_dic=True)

            return res
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
    
if __name__ == "__main__":
    try:
        import json
        log.start(loglevel='INFO')
        db_conn = MysqlConnect()

        cat_list_dao = CatListDao(db_conn)

        #res = cat_list_dao.get_cat_url()
        res = cat_list_dao.get_cat_url("youku")
        log.msg(json.dumps(res), level=log.INFO)

    except Exception,e:
        log.msg(traceback.format_exc(), level=log.ERROR)
