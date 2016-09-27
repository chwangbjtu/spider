# -*- coding:utf-8 -*-
import traceback
import logging
from db_connect import MysqlConnect
import math

class KeywordDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn
        self._tb_name = 'keyword'
        self._site_tb_name = 'site'

    def get_keyword_url(self, site_name=None):
        try:
            sql = "select k.id, k.url, k.user, k.audit, k.priority from %s as k join %s as s on k.site_id = s.site_id " % (self._tb_name, self._site_tb_name)
            para = None
            if site_name:
                sql += " where s.site_name = %s"
                para = (site_name, )
            res = self._db_conn.db_fetchall(sql, para, as_dic=True)
            if res:
                return res
            else:
                return []
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

if __name__ == "__main__":
    try:
        import json
        db_conn = MysqlConnect()
        keyword_dao = KeywordDao(db_conn)
        res = keyword_dao.get_keyword_url('youku')
        db_conn.commit()
        print res

    except Exception,e:
        logging.log(logging.ERROR, traceback.format_exc())
