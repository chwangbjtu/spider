# -*- coding:utf-8 -*-
import traceback
from scrapy import log
from db_connect import MysqlConnect
import math

class UserDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn
        self._tb_name = 'owner'

    def get_user(self, show_id):
        try:
            sql = "SELECT id FROM %s WHERE show_id = %%s" % (
                    self._tb_name, )
            para = (show_id,)
            res = self._db_conn.db_fetchall(sql, para)
            if res:
                return str(res[0][0])
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
    
    def insert_user(self, value_dict):
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

    def update_user(self, show_id, value_dict):
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

        user_dao = UserDao(db_conn)

        '''
        '''
        user = {}
        show_id = 'Xapd34521x'
        user['show_id'] = show_id

        if not user_dao.get_user(show_id):
            user_dao.insert_user(user)
        else:
            user['owner_id'] = '123455'
            user_dao.update_user(show_id, user)
        db_conn.commit()


    except Exception,e:
        log.msg(traceback.format_exc(), level=log.ERROR)
