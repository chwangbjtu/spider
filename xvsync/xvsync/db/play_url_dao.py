# -*- coding:utf-8 -*-
import traceback
import logging
from db_connect import MysqlConnect
import math

class PlayUrlDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn

    def get_play_url(self, vid, os_id):
        try:
            sql = "SELECT pid from play_url WHERE vid = %s and os_id = %s"
            para = (vid, os_id)
            res = self._db_conn.db_fetchall(sql, para)
            if res:
                return res[0][0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
    
    def insert_play_url(self, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "INSERT INTO play_url (%s) VALUES (%s)" % (
                    ",".join(keys),
                    ",".join(['%s'] * len(keys)))
            para = values
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def update_play_url(self, vid, os_id, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "UPDATE play_url SET %s WHERE vid = %%s and os_id = %%s" % (
                    (",").join(['%s=%%s' % k for k in keys]))
            para = list(values)
            para += (vid, os_id)
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

if __name__ == "__main__":
    try:
        logging.basicConfig(level=logging.INFO)
        db_conn = MysqlConnect()

        ep_dao = PlayUrlDao(db_conn)

        play_url = {}
        vid = 1
        os_id = 10
        play_url['vid'] = vid
        play_url['os_id'] = 10
        play_url['url'] = 'http://xxx'

        res = ep_dao.get_play_url(vid, os_id)
        if not res:
            logging.log(logging.INFO, 'insert: %s' % vid, level=log.INFO)
            ep_dao.insert_play_url(play_url)
        else:
            logging.log(logging.INFO, 'update: %s' % vid, level=log.INFO)
            play_url['url'] = 'http://yyy'
            ep_dao.update_play_url(vid, os_id, play_url)

        db_conn.commit()

    except Exception,e:
        logging.log(logging.ERROR, traceback.format_exc())
