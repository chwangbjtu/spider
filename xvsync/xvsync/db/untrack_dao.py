# -*- coding:utf-8 -*-
import traceback
import logging
from db_connect import MysqlConnect
import math

class UntrackDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn

    def get_untrack(self, md5):
        try:
            sql = "SELECT id FROM untrack WHERE md5 = %s "
            para = [md5, ]
            res = self._db_conn.db_fetchall(sql, para)
            if res:
                return res[0][0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_untrack_ss(self, sid, site_code):
        try:
            sql = "SELECT * FROM untrack WHERE sid = %s AND site_code = %s"
            para = [sid, site_code]
            res = self._db_conn.db_fetchall(sql, para, as_dic=True)
            if res:
                return res
            return []
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def insert_untrack(self, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "INSERT INTO untrack (%s) VALUES (%s)" % (
                    ",".join(keys),
                    ",".join(['%s'] * len(keys)))
            para = values
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def update_untrack(self, id, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "UPDATE untrack SET %s WHERE id = %%s" % (
                    (",").join(['%s=%%s' % k for k in keys]))
            para = list(values)
            para += [id, ]
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def delete_untrack_real(self, untrack_id):
        try:
            sql = "DELETE FROM untrack WHERE id = %s "
            para = [untrack_id, ]
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def delete_untrack(self, untrack_id):
        try:
            #sql = "DELETE FROM untrack WHERE id = %s"
            sql = "UPDATE untrack SET stat = 1 WHERE id = %s"
            para = [untrack_id, ]
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_untrack_url(self, site_code, stat=None):
        try:
            if stat is None:
                sql = "SELECT t.url, c.name, c.code, t.sid, t.id as untrack_id FROM untrack AS t JOIN channel AS c ON t.channel_id = c.channel_id WHERE t.site_code = %s "
                para = [site_code, ]
            else:
                sql = "SELECT t.url, c.name, c.code, t.sid, t.id as untrack_id FROM untrack AS t JOIN channel AS c ON t.channel_id = c.channel_id WHERE t.site_code = %s AND t.stat = %s "
                para = [site_code, stat]
            res = self._db_conn.db_fetchall(sql, para, as_dic=True)
            if res:
                return res
            return []
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
    
if __name__ == "__main__":
    try:
        import json
        logging.basicConfig(level=logging.INFO) 
        db_conn = MysqlConnect()

        dao = UntrackDao(db_conn)
        res = dao.get_untrack_url('youku')
        logging.log(logging.INFO, json.dumps(res))

        '''
        untrack = {}
        md5 = 'bfa89e563d9509fbc5c6503dd50faf2e'
        url = 'http://www.baidu.com'
        untrack['md5'] = md5
        untrack['url'] = url
        untrack['channel_id'] = 10
        untrack['site_code'] = 'youku'

        res = dao.get_untrack(md5)
        if not res:
            logging.log(logging.INFO, 'insert: %s, %s' % (md5, url), level=log.INFO)
            dao.insert_untrack(untrack)
        else:
            logging.log(logging.INFO, 'delete: %s' % (md5, ), level=log.INFO)
            dao.delete_untrack(md5)
        '''

        db_conn.commit()

    except Exception,e:
        logging.log(logging.ERROR, traceback.format_exc())
