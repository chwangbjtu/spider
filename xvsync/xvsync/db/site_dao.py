# -*- coding:utf-8 -*-
import traceback
import logging
from db_connect import MysqlConnect

class SiteDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn

    def get_site(self, site_code):
        try:
            sql = "SELECT site_id, type from site WHERE site_code = %s"
            para = (site_code,)
            res = self._db_conn.db_fetchall(sql, para, True)
            if res:
                return res[0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

if __name__ == "__main__":
    #logging.basicConfig(level=logging.INFO)
    db_conn = MysqlConnect()
    site_dao = SiteDao(db_conn)
    res = site_dao.get_site(site_code='iqiyi')
    print res
