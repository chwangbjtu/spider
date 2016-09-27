# -*- coding:utf-8 -*-
import traceback
from scrapy import log
from db_connect import MysqlConnect
import math

class SubjectDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn
        self._tb_name = 'subject'
        self._site_tb_name = 'site'

    def get_subjects(self, site_name=None):
        try:
            sql = "SELECT j.id, j.subject_name,j.url FROM %s AS j \
                    LEFT JOIN %s AS s \
                    ON s.site_id = j.site_id \
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

        subject_dao = SubjectDao(db_conn)

        res = subject_dao.get_subjects(site_name='iqiyi')

        db_conn.commit()
        if res:
            log.msg(json.dumps(res))


    except Exception,e:
        log.msg(traceback.format_exc(), level=log.ERROR)
