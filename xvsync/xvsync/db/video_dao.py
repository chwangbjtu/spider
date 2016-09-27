# -*- coding:utf-8 -*-
import traceback
import logging
from db_connect import MysqlConnect
import math

class VideoDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn

    def get_video(self, ext_id):
        try:
            sql = "SELECT vid from video WHERE ext_id = %s"
            para = (ext_id,)
            res = self._db_conn.db_fetchall(sql, para)
            if res:
                return res[0][0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
    
    def insert_video(self, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "INSERT INTO video (%s) VALUES (%s)" % (
                    ",".join(keys),
                    ",".join(['%s'] * len(keys)))
            para = values
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def update_video(self, ext_id, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "UPDATE video SET %s WHERE ext_id = %%s" % (
                    (",").join(['%s=%%s' % k for k in keys]))
            para = list(values)
            para.append(ext_id)
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_thumb(self, vid):
        try:
            sql = "SELECT thumb_id from thumb WHERE vid = %s"
            para = (vid,)
            res = self._db_conn.db_fetchall(sql, para)
            if res:
                return res[0][0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
    
    def insert_thumb(self, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "INSERT INTO thumb (%s) VALUES (%s)" % (
                    ",".join(keys),
                    ",".join(['%s'] * len(keys)))
            para = values
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def update_thumb(self, vid, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "UPDATE thumb  SET %s WHERE vid = %%s" % (
                    (",").join(['%s=%%s' % k for k in keys]))
            para = list(values)
            para.append(vid)
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_video_mid(self, video_ext_id):
        try:
            sql = "SELECT v.mid FROM play_url AS u JOIN video AS v ON v.mid = u.vid WHERE v.ext_id = %s"
            para = (video_ext_id,)
            res = self._db_conn.db_fetchall(sql, para)
            if res:
                return res[0][0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_video_url(self, site_code):
        try:
            sql = "SELECT v.mid AS mid, p.url AS url, c.name AS name, c.code as code FROM video AS v \
                   JOIN play_url AS p ON v.vid = p.vid AND p.os_id=1 \
                   JOIN site AS s ON v.site_id = s.site_id AND s.site_code = %s \
                   JOIN media AS m ON m.mid = v.mid \
                   JOIN channel AS c ON m.channel_id = c.channel_id"
            para = (site_code,)
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

        ep_dao = VideoDao(db_conn)
        mid = ep_dao.get_video_mid('5bdbd821eb1bf5479a5e1592c38d35a9')
        logging.log(logging.INFO, '%s' % mid)

        '''
        thumb = {}
        vid = 8
        thumb['vid'] = vid
        thumb['url'] = 'http://ppp'

        res = ep_dao.get_thumb(vid)
        if not res:
            logging.log(logging.INFO, 'insert: %s' % vid, level=log.INFO)
            ep_dao.insert_thumb(thumb)
        else:
            logging.log(logging.INFO, 'update: %s' % vid, level=log.INFO)
            thumb['url'] = 'http://nnn'
            ep_dao.update_thumb(vid, thumb)
        '''

        '''
        video = {}
        ext_id = 'xxx'
        video['ext_id'] = ext_id
        video['title'] = 'y'

        res = ep_dao.get_video(ext_id)
        if not res:
            logging.log(logging.INFO, 'insert: %s' % ext_id, level=log.INFO)
            ep_dao.insert_video(video)
        else:
            logging.log(logging.INFO, 'update: %s' % ext_id, level=log.INFO)
            video['title'] = 'z'
            ep_dao.update_video(ext_id, video)
        '''

        db_conn.commit()

    except Exception,e:
        logging.log(logging.ERROR, traceback.format_exc())
