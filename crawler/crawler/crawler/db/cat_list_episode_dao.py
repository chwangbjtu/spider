# -*- coding:utf-8 -*-
import traceback
from scrapy import log
from db_connect import MysqlConnect
import math

class CatListEpisodeDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn
        self._tb_name = 'cat_list_episode'

    def add_cat_list_episode(self, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "REPLACE INTO %s (%s) VALUES (%s)" % (
                    self._tb_name, 
                    ",".join(keys),
                    ",".join(['%s'] * len(keys)))
            para = values
            self._db_conn.execute_sql(sql, para)

        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
    
if __name__ == "__main__":
    try:
        import json
        log.start(loglevel='INFO')
        db_conn = MysqlConnect()

        cat_list_ep_dao = CatListEpisodeDao(db_conn)

        cat_list_ep_dao.add_cat_list_episode({'cat_id': '10', 'show_id': 'xx33ff'})

        db_conn.commit()

    except Exception,e:
        log.msg(traceback.format_exc(), level=log.ERROR)
