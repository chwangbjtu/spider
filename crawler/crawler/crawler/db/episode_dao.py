# -*- coding:utf-8 -*-
import traceback
from scrapy import log
from db_connect import MysqlConnect
import math

class EpisodeDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn
        self._tb_name = 'episode'

    def get_episode(self, show_id):
        try:
            sql = "SELECT id from %s WHERE show_id = %%s" % (
                    self._tb_name, )
            para = (show_id,)
            res = self._db_conn.db_fetchall(sql, para)
            if res:
                return res[0][0]
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
    
    def insert_episode(self, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "INSERT INTO %s (%s, create_time, update_time) VALUES (%s, now(), now())" % (
                    self._tb_name, 
                    ",".join(keys),
                    ",".join(['%s'] * len(keys)))
            para = values
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def update_episode(self, show_id, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "UPDATE %s SET %s, update_time=now() WHERE show_id = %%s" % (
                    self._tb_name,
                    (",").join(['%s=%%s' % k for k in keys]))
            para = list(values)
            para.append(show_id)
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

if __name__ == "__main__":
    try:
        log.start(loglevel='INFO')
        db_conn = MysqlConnect()

        ep_dao = EpisodeDao(db_conn)

        episode = {}
        show_id = 'xx8'
        episode['show_id'] = show_id
        episode['site_id'] = '1'
        episode['spider_id'] = '2'

        res = ep_dao.get_episode(show_id)
        if not res:
            log.msg('insert: %s' % show_id, level=log.INFO)
            ep_dao.insert_episode(episode)
        else:
            log.msg('update: %s' % show_id, level=log.INFO)
            episode['video_id'] = '15'
            ep_dao.update_episode(show_id, episode)

        db_conn.commit()

    except Exception,e:
        log.msg(traceback.format_exc(), level=log.ERROR)
