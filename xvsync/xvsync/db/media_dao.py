# -*- coding:utf-8 -*-
import traceback
import logging
from db_connect import MysqlConnect
import math

class MediaDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn

    def get_media(self, ext_id, info_id):
        try:
            sql = "SELECT mid from media WHERE ext_id = %s "
            para = [ext_id, ]
            if info_id:
                sql += " or info_id = %s "
                para.append(info_id)
            res = self._db_conn.db_fetchall(sql, para)
            if res:
                return res[0][0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
    
    def insert_media(self, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "INSERT INTO media (%s) VALUES (%s)" % (
                    ",".join(keys),
                    ",".join(['%s'] * len(keys)))
            para = values
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def update_media(self, ext_id, info_id, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "UPDATE media SET %s WHERE ext_id = %%s" % (
                    (",").join(['%s=%%s' % k for k in keys]))
            para = list(values)
            para.append(ext_id)
            if info_id:
                sql += " or info_id = %s "
                para.append(info_id)
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def update_media_by_mid(self, mid, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "UPDATE media SET %s WHERE mid = %%s" % (
                    (",").join(['%s=%%s' % k for k in keys]))
            para = list(values)
            para.append(mid)
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_poster(self, mid):
        try:
            sql = "SELECT poster_id from poster WHERE mid = %s"
            para = (mid,)
            res = self._db_conn.db_fetchall(sql, para)
            if res:
                return res[0][0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
    
    def insert_poster(self, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "INSERT INTO poster (%s) VALUES (%s)" % (
                    ",".join(keys),
                    ",".join(['%s'] * len(keys)))
            para = values
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def update_poster(self, mid, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "UPDATE poster  SET %s WHERE mid = %%s" % (
                    (",").join(['%s=%%s' % k for k in keys]))
            para = list(values)
            para.append(mid)
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

if __name__ == "__main__":
    try:
        logging.basicConfig(level=logging.INFO)
        db_conn = MysqlConnect()

        ep_dao = MediaDao(db_conn)

        poster = {}
        mid = 28
        poster['mid'] = mid
        poster['url'] = 'http://ppp'

        res = ep_dao.get_poster(mid)
        if not res:
            logging.log(logging.INFO, 'insert: %s' % mid)
            ep_dao.insert_poster(poster)
        else:
            logging.log(logging.INFO, 'update: %s' % mid)
            poster['url'] = 'http://nnn'
            ep_dao.update_poster(mid, poster)
        '''
        media = {}
        ext_id = 'xxx'
        info_id = 'iii'
        media['ext_id'] = ext_id
        media['info_id'] = info_id
        media['title'] = 'y'

        res = ep_dao.get_media(ext_id, info_id)
        if not res:
            logging.log(logging.INFO, 'insert: %s' % ext_id, level=log.INFO)
            ep_dao.insert_media(media)
        else:
            logging.log(logging.INFO, 'update: %s' % ext_id, level=log.INFO)
            media['title'] = 'z'
            ep_dao.update_media(ext_id, info_id, media)
        '''

        db_conn.commit()

    except Exception,e:
        logging.log(logging.ERROR, traceback.format_exc())
