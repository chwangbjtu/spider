# -*- coding:utf-8 -*-
import traceback
import logging

class ChannelDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn

    def get_channel_map(self):
        try:
            channel_map = {}
            sql = "SELECT * from channel"
            res = self._db_conn.db_fetchall(sql, as_dic=True)
            for r in res:
                channel_map[r['code']] = r['channel_id']
            return channel_map
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_channel(self, channel_name):
        try:
            sql = "SELECT channel_id, code from channel WHERE name=%s"
            para = (channel_name,)
            res = self._db_conn.db_fetchall(sql, para, True)
            if res:
                return res[0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_channel_name(self, channel_id):
        try:
            sql = "SELECT name, code from channel WHERE channel_id=%s"
            para = (channel_id,)
            res = self._db_conn.db_fetchall(sql, para, True)
            if res:
                return res[0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
