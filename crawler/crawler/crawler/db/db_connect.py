# -*- coding:utf-8 -*-
import MySQLdb
import traceback
from scrapy import log
import time

class MysqlConnect(object):
    DB_HOST = '192.168.16.165'
    DB_USER = 'root'
    DB_PWD = 'funshion'
    DB_NAME = 'crawler'
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
                    self.connect()
                else:
                    break
                time.sleep(1)
                
        except Exception,e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def commit(self):
        try:
            self._db_conn.commit()
            return True
        except Exception, e:
            self.rollback()
            log.msg(traceback.format_exc(), level=log.ERROR)
            return False

    def rollback(self):
        try:
            self._db_conn.rollback()
            return True
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)
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
            log.msg(traceback.format_exc(), level=log.ERROR)
            log.msg('%s: %s' % (sql, para))
            #log.msg("db exception: %s" % (str(e),))
            #self.execute_sql(sql, para)
        except Exception, e:
            cursor.close()
            log.msg(traceback.format_exc(), level=log.ERROR)
            log.msg('%s: %s' % (sql, para))

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
            log.msg("db exception: %s" % (str(e),))
            log.msg('%s: %s' % (sql, para))
        except Exception, e:
            cursor.close()
            log.msg(traceback.format_exc(), level=log.ERROR)
            log.msg('%s: %s' % (sql, para))

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
            log.msg("db exception: %s" % (str(e),))
        except Exception, e:
            cursor.close()
            log.msg(traceback.format_exc(), level=log.ERROR)

import os
import datetime

if __name__ == "__main__":

    try:
        #log.start(loglevel='INFO')
        db_conn = MysqlConnect()
        if db_conn:
            show_id = u'XNzEzODc3ODI0\\/\''
            title = u'评论比视频更精彩！'
            sql = "insert into episode (show_id, title, update_time) values (%s, %s, now())"
            para = (show_id, title,)
            db_conn.execute_sql(sql, para, )

            sql = "select id, show_id from episode where show_id = %s"
            para = (show_id, )
            res = db_conn.db_fetchall(sql, para)
            for r in res:
                print r[0], r[1]
                #log.msg('get episode %s: %s' % (r[0], r[1]))

            #raise MySQLdb.Error
            db_conn.commit()
            db_conn.close()
    except Exception,e:
        log.msg(traceback.format_exc(), level=log.ERROR)
