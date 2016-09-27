# -*- coding:utf-8 -*-
import MySQLdb
import traceback
import logging
import time

class MysqlConnect(object):
    #DB_HOST = '127.0.0.1'
    #DB_HOST = '192.168.177.3'
    DB_HOST = '192.168.28.203'
    DB_USER = 'root'
    DB_PWD = 'funshion'
    DB_NAME = 'xvsync_20151130'
    DB_PORT = 3306

    def __init__(self):
        self._db_conn = None
        self.connect()

    def __del__(self):
        self.close()

    def ping(self):
        try:
            self._db_conn.ping()
            return True
        except Exception, e:
            return False

    def close(self):
        try:
            if self._db_conn:
                self._db_conn.close()
                self._db_conn = None
            return True
        except Exception, e:
            return False

    def connect(self):
        try:
            self._db_conn = MySQLdb.connect(host=self.DB_HOST, user=self.DB_USER, passwd=self.DB_PWD,db=self.DB_NAME, port=self.DB_PORT, charset = 'utf8')
            self._db_conn.autocommit(False)
            return True
        except:
            return False

    def reconnect(self):
        try:
            while True:
                if not self.ping():
                    logging.log(logging.INFO, '++reconnected db')
                    self.connect()
                else:
                    break
                time.sleep(1)
                
        except Exception,e:
            logging.log(logging.ERROR, traceback.format_exc())

    def commit(self):
        try:
            self._db_conn.commit()
            return True
        except Exception, e:
            self.rollback()
            logging.log(logging.ERROR, traceback.format_exc())
            return False

    def rollback(self):
        try:
            self._db_conn.rollback()
            return True
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
            return False

    def execute_sql(self, sql, para=None):
        try:
            self.reconnect()
            cursor = self._db_conn.cursor()
            if para:
                cursor.execute(sql, para)
            else:
                cursor.execute(sql)
            cursor.close()
        except (AttributeError, MySQLdb.OperationalError), e:
            cursor.close()
            logging.log(logging.INFO, "db exception: %s" % (str(e),))
            logging.log(logging.INFO, '%s: %s' % (sql, para))
        except Exception, e:
            cursor.close()
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, '%s: %s' % (sql, para))

    def db_fetchall(self, sql, para=None, as_dic=False):
        try:
            self.reconnect()
            if as_dic:
                cursor = self._db_conn.cursor(MySQLdb.cursors.DictCursor)
            else:
                cursor = self._db_conn.cursor()
            if para:
                cursor.execute(sql, para)
            else:
                cursor.execute(sql)
            result = cursor.fetchall()
            cursor.close()
            return result
        except (AttributeError, MySQLdb.OperationalError), e:
            cursor.close()
            logging.log(logging.INFO, "db exception: %s" % (str(e),))
            logging.log(logging.INFO, '%s: %s' % (sql, para))
        except Exception, e:
            cursor.close()
            logging.log(logging.ERROR, traceback.format_exc())
            logging.log(logging.INFO, '%s: %s' % (sql, para))

    def call_proc_db(self, proc_name, tuple_list):
        try:
            self.reconnect()
            cursor = self._db_conn.cursor()
            cursor.callproc(proc_name, tuple_list)
            row = cursor.fetchone()
            if row:
                cursor.close()
                self._db_conn.commit()
        except (AttributeError, MySQLdb.OperationalError), e:
            cursor.close()
            logging.log(logging.INFO, "db exception: %s" % (str(e),))
        except Exception, e:
            cursor.close()
            logging.log(logging.ERROR, traceback.format_exc())

import os
import datetime

if __name__ == "__main__":

    try:
        logging.basicConfig(level=logging.INFO)
        db_conn = MysqlConnect()
        if db_conn:
            res = db_conn.db_fetchall(sql='SELECT * FROM channel AS c', para=None)
            for r in res:
                print r
            '''
            ext_id = u'12'
            title = u'title'
            sql = "insert into media (ext_id, title) values (%s, %s)"
            para = (ext_id, title,)
            db_conn.execute_sql(sql, para, )

            sql = "select mid, ext_id from media where ext_id = %s"
            para = (ext_id, )
            res = db_conn.db_fetchall(sql, para)
            for r in res:
                logging.log(logging.INFO, 'get media %s: %s' % (r[0], r[1]))
            '''
            db_conn.commit()
            db_conn.close()
    except Exception,e:
        logging.log(logging.ERROR, traceback.format_exc())
