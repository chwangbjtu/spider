# -*- coding:utf-8 -*-
import traceback
from scrapy import log
from db_connect import MysqlConnect
import math

class OrderedDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn
        self._tb_name = 'ordered'
        self._owner_tb_name = 'owner'
        self._site_tb_name = 'site'

    def get_ordered_url(self, site_name=None):
        try:
            sql = "SELECT n.url, d.user,d.audit,n.show_id, d.priority FROM %s AS d \
                    LEFT JOIN %s AS n \
                    ON d.show_id = n.show_id \
                    LEFT JOIN %s AS s \
                    ON s.site_id = n.site_id " % (
                    self._tb_name, self._owner_tb_name, self._site_tb_name)
            para = None
            if site_name:
                sql += "WHERE s.site_name = %s"
                para = (site_name, )
            res = self._db_conn.db_fetchall(sql, para, as_dic=True)

            return res

        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
    
if __name__ == "__main__":
    try:
        import json
        log.start(loglevel='INFO')
        db_conn = MysqlConnect()

        ordered_dao = OrderedDao(db_conn)

        #res = ordered_dao.get_ordered_url(site_name="youtube")
        res = ordered_dao.get_ordered_url()
        db_conn.commit()
        if res:
            log.msg(json.dumps(res))


    except Exception,e:
        log.msg(traceback.format_exc(), level=log.ERROR)
