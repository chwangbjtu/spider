# -*- coding:utf-8 -*-
import traceback
import logging
from db_connect import MysqlConnect

class ReviewDao(object):
    def __init__(self, db_conn):
        self._db_conn = db_conn

    def get_review(self, rv_id):
        try:
            sql = "SELECT id FROM review WHERE rv_id = %s"
            para = (rv_id,)
            res = self._db_conn.db_fetchall(sql, para)
            if res:
                return res[0][0]
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
    
    def insert_review(self, value_dict):
        try:
            keys = value_dict.keys()
            values = value_dict.values()
            sql = "INSERT INTO review (%s) VALUES (%s)" % (
                    ",".join(keys),
                    ",".join(['%s'] * len(keys)))
            para = values
            self._db_conn.execute_sql(sql, para)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

if __name__ == "__main__":
    try:
        import json
        logging.basicConfig(level=logging.INFO)
        db_conn = MysqlConnect()

        rv_dao = ReviewDao(db_conn)
        review = {}
        rv_id = '7214367'
        review['rv_id'] = rv_id
        review['mid'] = '100'
        review['url'] = 'http://movie.douban.com/review/7214367/'

        res = rv_dao.get_review(rv_id)
        if not res:
            logging.log(logging.INFO, 'insert: %s' % rv_id, level=log.INFO)
            rv_dao.insert_review(review)

        db_conn.commit()

    except Exception,e:
        logging.log(logging.ERROR, traceback.format_exc())
