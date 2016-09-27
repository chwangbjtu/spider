# -*- coding:utf-8 -*-
import traceback
import logging

class OsDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn

    def get_os(self, os_name):
        try:
            sql = "SELECT os_id from os WHERE os_name = %s"
            para = (os_name,)
            res = self._db_conn.db_fetchall(sql, para, True)
            if res:
                return res[0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
