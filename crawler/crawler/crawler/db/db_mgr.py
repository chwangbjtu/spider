# -*- coding:utf-8 -*-
import sys
import traceback
from scrapy import log
from db_connect import MysqlConnect
from episode_dao import EpisodeDao
from user_dao import UserDao
from ordered_dao import OrderedDao
from page_dao import PageDao
from keyword_dao import KeywordDao
from keyword_episode_dao import KeywordEpisodeDao
from subject_dao import SubjectDao
from subject_episode_dao import SubjectEpisodeDao
from page_episode_dao import PageEpisodeDao
from cat_list_dao import CatListDao
from cat_list_episode_dao import CatListEpisodeDao
from cat_exclude_dao import CatExcludeDao
from channel_exclude_dao import ChannelExcludeDao
from category_dao import CategoryDao
from tag_dao import TagDao

class DbManager(object):

    _db_conn = None
    _daos = {}

    @staticmethod
    def instance():
        if not hasattr(DbManager, "_instance"):
            DbManager._instance = DbManager()
            DbManager._db_conn = MysqlConnect()
            DbManager._daos.update({'episode': EpisodeDao(DbManager._db_conn), 
                                    'user': UserDao(DbManager._db_conn),
                                    'keyword': KeywordDao(DbManager._db_conn),
                                    'keyword_episode': KeywordEpisodeDao(DbManager._db_conn),
                                    'subject': SubjectDao(DbManager._db_conn),
                                    'subject_episode': SubjectEpisodeDao(DbManager._db_conn),
                                    'page_episode': PageEpisodeDao(DbManager._db_conn),
                                    'ordered': OrderedDao(DbManager._db_conn), 
                                    'page': PageDao(DbManager._db_conn), 
                                    'cat_list': CatListDao(DbManager._db_conn), 
                                    'cat_episode': CatListEpisodeDao(DbManager._db_conn), 
                                    'cat_exclude': CatExcludeDao(DbManager._db_conn), 
                                    'channel_exclude': ChannelExcludeDao(DbManager._db_conn), 
                                    'category': CategoryDao(DbManager._db_conn), 
                                    'tag': TagDao(DbManager._db_conn), 
                                    })
        return DbManager._instance

    def commit_transaction(self):
        self._db_conn.commit()

    def insert_episode(self, item):
        try:
            dao = self._daos['episode']
            value_dict = {}

            show_id = item['show_id']
            value_dict['show_id'] = show_id
            if 'video_id' in item:
                value_dict['video_id'] = item['video_id']
            if 'owner_show_id' in item:
                value_dict['owner_show_id'] = item['owner_show_id']
            if 'title' in item:
                value_dict['title'] = item['title']
            if 'tag' in item:
                value_dict['tag'] = item['tag']
            if 'category' in item:
                value_dict['category'] = item['category']
            if 'played' in item:
                value_dict['played'] = item['played']
            if 'upload_time' in item:
                value_dict['upload_time'] = item['upload_time']
            if 'spider_id' in item:
                value_dict['spider_id'] = item['spider_id']
            if 'site_id' in item:
                value_dict['site_id'] = item['site_id']
            if 'url' in item:
                value_dict['url'] = item['url']
            if 'thumb_url' in item:
                value_dict['thumb_url'] = item['thumb_url']
            if 'description' in item:
                value_dict['description'] = item['description']
            if 'stash' in item:
                value_dict['stash'] = item['stash']
            if 'duration' in item:
                value_dict['duration'] = item['duration']
            if 'priority' in item:
                value_dict['priority'] = item['priority']
            if 'format_id' in item:
                value_dict['format_id'] = item['format_id']
            if 'audit' in item:
                value_dict['audit'] = item['audit']

            res = dao.get_episode(show_id)
            if not res:
                #new episode, just insert
                dao.insert_episode(value_dict)
            else:
                #episode exist, update
                dao.update_episode(show_id, value_dict)

            if 'pg_id' in item and item['pg_id']:
                pg_ep_dict = {}
                pg_ep_dict['pg_id'] = item['pg_id']
                pg_ep_dict['show_id'] = item['show_id']
                pg_ep_dao = self._daos['page_episode']
                pg_ep_dao.add_page_episode(pg_ep_dict)

            if 'kw_id' in item and item['kw_id']:
                kw_ep_dict = {}
                kw_ep_dict['kw_id'] = item['kw_id']
                kw_ep_dict['show_id'] = item['show_id']
                kw_ep_dao = self._daos['keyword_episode']
                kw_ep_dao.add_keyword_episode(kw_ep_dict)

            if 'cat_id' in item and item['cat_id']:
                cat_ep_dict = {}
                cat_ep_dict['cat_id'] = item['cat_id']
                cat_ep_dict['show_id'] = item['show_id']
                cat_ep_dao = self._daos['cat_episode']
                cat_ep_dao.add_cat_list_episode(cat_ep_dict)

            if 'subject_id' in item and item['subject_id']:
                sub_ep_dict = {}
                sub_ep_dict['subject_id'] = item['subject_id']
                sub_ep_dict['show_id'] = item['show_id']
                sub_ep_dao = self._daos['subject_episode']
                sub_ep_dao.add_subject_episode(sub_ep_dict)

            #log.msg('----%s--%s' % (item['show_id'], item['subject_id']), level=log.ERROR)
            self.commit_transaction()

        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def insert_user(self, item):
        try:
            dao = self._daos['user']
            value_dict = {}

            show_id = item['show_id']
            value_dict['show_id'] = show_id
            if 'owner_id' in item:
                value_dict['owner_id'] = item['owner_id']
            if 'user_name' in item:
                value_dict['user_name'] = item['user_name']
            if 'intro' in item:
                value_dict['intro'] = item['intro']
            if 'played' in item:
                value_dict['played'] = item['played']
            if 'fans' in item:
                value_dict['fans'] = item['fans']
            if 'vcount' in item:
                value_dict['vcount'] = item['vcount']
            if 'spider_id' in item:
                value_dict['spider_id'] = item['spider_id']
            if 'site_id' in item:
                value_dict['site_id'] = item['site_id']
            if 'url' in item:
                value_dict['url'] = item['url']
            if 'aka' in item:
                value_dict['aka'] = item['aka']

            if not dao.get_user(show_id):
                #new user, just insert
                dao.insert_user(value_dict)
            else:
                #user exist, update
                dao.update_user(show_id, value_dict)
            
            #commit
            self.commit_transaction()
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def get_ordered_url(self, site_name=None):
        try:
            dao = self._daos['ordered']
            res = dao.get_ordered_url(site_name=site_name)
            self.commit_transaction()

            return res
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def get_ordered_page(self, site_name=None):
        try:
            dao = self._daos['page']
            res = dao.get_ordered_page(site_name=site_name)
            self.commit_transaction()

            return res
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def get_keyword_url(self, site_name=None):
        try:
            dao = self._daos['keyword']
            res = dao.get_keyword_url(site_name=site_name)
            self.commit_transaction()
            return res
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)


    def get_subjects(self, site_name=None):
        try:
            dao = self._daos['subject']
            res = dao.get_subjects(site_name=site_name)
            self.commit_transaction()

            return res
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def get_cat_url(self,site):
        try:
            dao = self._daos['cat_list']
            res = dao.get_cat_url(site)
            self.commit_transaction()

            return res
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def get_cat_exclude(self):
        try:
            dao = self._daos['cat_exclude']
            res = dao.get_cat_exclude()
            self.commit_transaction()

            return res
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def get_channel_exclude(self):
        try:
            dao = self._daos['channel_exclude']
            res = dao.get_channel_exclude()
            self.commit_transaction()

            return res
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def get_cat_ids(self, site_name=None):
        try:
            dao = self._daos['category']
            res = dao.get_cat_ids(site_name)
            self.commit_transaction()

            return res
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

    def get_tags(self):
        try:
            dao = self._daos['tag']
            res = dao.get_tags()
            self.commit_transaction()

            return res
        except Exception, e:
            log.msg(traceback.format_exc(), level=log.ERROR)

if __name__ == "__main__":
    try:
        import json
        #log.start(loglevel='INFO')
        mgr = DbManager.instance()
        '''
        item = dict()
        item['show_id'] = 'xxxxxxx'
        mgr.insert_episode(item)

        item['video_id'] = '11111'
        item['owner_show_id'] = 'x3333'
        item['title'] = 'foo'
        item['tag'] = 'bar'
        item['category'] = '2'
        mgr.insert_episode(item)

        '''
        '''
        item = dict()
        item['show_id'] = 'xxxxxxx'
        mgr.insert_user(item)

        item['owner_id'] = '3333'
        item['user_name'] = 'foo'
        item['intro'] = 'introooo'
        item['played'] = '111111'
        item['fans'] = '222'
        item['video_count'] = '33'
        mgr.insert_user(item)
        '''
        #log.msg('|'.join(mgr.get_cat_url()), level=log.INFO)
        #log.msg(json.dumps(mgr.get_cat_url("iqiyi")), level=log.INFO)
        #log.msg('|'.join(mgr.get_cat_exclude()), level=log.INFO)
        #log.msg('|'.join(mgr.get_channel_exclude()), level=log.INFO)
        #log.msg(json.dumps(mgr.get_tags()))
        #log.msg(json.dumps(mgr.get_cat_ids('funshion')))
        print 'dd'
        print mgr.get_keyword_url('youku')

    except Exception, e:
        log.msg(traceback.format_exc(), level=log.ERROR)
