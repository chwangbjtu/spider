# -*- coding:utf-8 -*-
import traceback
import logging
from db_connect import MysqlConnect
import math

class SyncDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn

    def get_rel(self, sid, mid):
        try:
            sql = "SELECT rel_id from sync WHERE sid = %s and mid = %s "
            para = [sid, mid]
            res = self._db_conn.db_fetchall(sql, para)
            if res:
                return res[0][0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
    
    def insert_rel(self, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "INSERT INTO sync (%s) VALUES (%s)" % (
                    ",".join(keys),
                    ",".join(['%s'] * len(keys)))
            para = values
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def update_rel(self, sid, mid, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "UPDATE sync SET %s WHERE sid = %%s and mid = %%s" % (
                    (",").join(['%s=%%s' % k for k in keys]))
            para = list(values)
            para += [sid, mid]
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_sync_site_id(self, sid):
        try:
            sql = "SELECT site_id FROM media WHERE mid = %s "
            para = [sid,]
            res = self._db_conn.db_fetchall(sql, para)
            if res:
                return res[0][0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
    
if __name__ == "__main__":
    try:
        import json
        logging.basicConfig(level=logging.INFO)
        db_conn = MysqlConnect()

        sync_dao = SyncDao(db_conn)

        sync = {}
        sid = '6660'
        mid = '100'
        sync['sid'] = sid
        sync['mid'] = mid
        sync['site_id'] = 60

        res = sync_dao.get_rel(sid, mid)
        if not res:
            logging.log(logging.INFO, 'insert: %s, %s' % (sid, mid), level=log.INFO)
            sync_dao.insert_rel(sync)
        else:
            logging.log(logging.INFO, 'update: %s, %s' % (sid, mid), level=log.INFO)
            sync_dao.update_rel(sid, mid, sync)

        db_conn.commit()

    except Exception,e:
        logging.log(logging.ERROR, traceback.format_exc())
