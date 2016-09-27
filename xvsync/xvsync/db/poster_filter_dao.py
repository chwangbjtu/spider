# -*- coding:utf-8 -*-
import traceback
import logging
from db_connect import MysqlConnect
import math

class PosterFilterDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn

    def has_poster_filter_md5(self, md5):
        try:
            sql = "select count(*) from poster_filter where md5=%s"
            para = (md5, )
            res = self._db_conn.db_fetchall(sql, para)
            if res and res[0][0] > 0:
                return True
            else:
                return False
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_poster_filter_md5(self):
        try:
            sql = "select md5 from poster_filter"
            res = self._db_conn.db_fetchall(sql)
            if res:
                return [r[0] for r in res]
            else:
                return []
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())


if __name__ == "__main__":
        db_conn = MysqlConnect()
        dao = PosterFilterDao(db_conn)
        #res = dao.has_poster_filter_md5('969fb1ad59ae31bd36c55b25a5d9100a')
        res = dao.get_poster_filter_md5()
        print res

