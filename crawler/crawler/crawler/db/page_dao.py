# -*- coding:utf-8 -*-
import traceback
from scrapy import log
from db_connect import MysqlConnect
import math

class PageDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn
        self._tb_name = 'page'
        self._site_tb_name = 'site'

    def get_ordered_page(self, site_name=[]):
        try:
            sql = "SELECT p.id, p.url, p.user, p.site_id, p.audit, p.priority FROM %s AS p \
                    LEFT JOIN %s AS s \
                    ON s.site_id = p.site_id " % (
                    self._tb_name, self._site_tb_name)
            para = None
            if site_name:
                sql += "WHERE s.site_name in (%s)" % ",".join(['"%s"' % s for s in site_name])
            res = self._db_conn.db_fetchall(sql, para, as_dic=True)

            return res

        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
    
if __name__ == "__main__":
    try:
        import json
        log.start(loglevel='INFO')
        db_conn = MysqlConnect()

        page_dao = PageDao(db_conn)

        res = page_dao.get_ordered_page(site_name=['youku', 'iqiyi'])
        #res = page_dao.get_ordered_page()
        db_conn.commit()
        if res:
            log.msg(json.dumps(res))


    except Exception,e:
        log.msg(traceback.format_exc(), level=log.ERROR)
