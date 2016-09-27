# -*- coding:utf-8 -*-
import traceback
import logging
from db_connect import MysqlConnect
from media_dao import MediaDao
from video_dao import VideoDao
from play_url_dao import PlayUrlDao
from site_dao import SiteDao
from channel_dao import ChannelDao
from os_dao import OsDao
from sync_dao import SyncDao
from untrack_dao import UntrackDao
from review_dao import ReviewDao
from poster_filter_dao import PosterFilterDao
import json
import sys
import hashlib
sys.path.append('.')
#from common.util import Util
from xvsync.common.util import Util

class DbManager(object):

    _db_conn = None
    _daos = {}

    @staticmethod
    def instance():
        if not hasattr(DbManager, "_instance"):
            DbManager._instance = DbManager()
            DbManager._db_conn = MysqlConnect()
            DbManager._daos.update({'media': MediaDao(DbManager._db_conn), 
                                    'video': VideoDao(DbManager._db_conn),
                                    'play_url': PlayUrlDao(DbManager._db_conn),
                                    'site': SiteDao(DbManager._db_conn),
                                    'channel': ChannelDao(DbManager._db_conn),
                                    'os': OsDao(DbManager._db_conn),
                                    'sync': SyncDao(DbManager._db_conn),
                                    'untrack': UntrackDao(DbManager._db_conn),
                                    'review': ReviewDao(DbManager._db_conn),
                                    'poster_filter': PosterFilterDao(DbManager._db_conn),
                                    })
        return DbManager._instance

    def commit_transaction(self):
        self._db_conn.commit()

    def insert_media_video(self, item):
        try:
            mid = item['mid'] if 'mid' in item else None
            self.insert_media(item['media'], commit=False, mid=mid)
            for v in item['video']:
                self.insert_video(v, commit=False)
                self.insert_play_url(v, commit=False)
            self.commit_transaction()

            if 'ext_video' in item and item['ext_video']:
                self.insert_ext_video(item['ext_video'])

            if 'review' in item and item['review']:
                self.insert_media_review(item['review'])

            if 'sid' in item and item['sid'] and 'ext_id' in item['media']:
                self.fix_sync_rel(item['sid'], item['media']['ext_id'])

            if 'untrack_id' in item and item['untrack_id']:
                self.delete_untrack(item['untrack_id'])

        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def insert_media(self, item, commit=True, mid=None):
        try:
            dao = self._daos['media']
            value_dict = {}

            if not Util.check_item(item):
                logging.log(logging.INFO, 'Missing essential key: %s' % item['url'])
                return False

            ext_id = item['ext_id']
            info_id = item['info_id']
            value_dict['ext_id'] = ext_id
            value_dict['info_id'] = info_id
            if 'cont_id' in item:
                value_dict['cont_id'] = item['cont_id']
            if 'title' in item:
                value_dict['title'] = item['title']
            if 'director' in item:
                value_dict['director'] = item['director']
            if 'writer' in item:
                value_dict['writer'] = item['writer']
            if 'actor' in item:
                value_dict['actor'] = item['actor']
            if 'type' in item:
                value_dict['type'] = item['type']
            if 'district' in item:
                value_dict['district'] = item['district']
            if 'release_date' in item:
                value_dict['release_date'] = item['release_date']
            if 'duration' in item:
                value_dict['duration'] = item['duration']
            if 'channel_id' in item:
                value_dict['channel_id'] = item['channel_id']
            if 'score' in item:
                value_dict['score'] = item['score']
            if 'site_id' in item:
                value_dict['site_id'] = item['site_id']
            if 'vcount' in item:
                value_dict['vcount'] = item['vcount']
            if 'latest' in item:
                value_dict['latest'] = item['latest']
            if 'paid' in item:
                value_dict['paid'] = item['paid']
            if 'url' in item:
                value_dict['url'] = item['url']
            if 'intro' in item:
                value_dict['intro'] = item['intro']
            
            #filter specail value from dict
            value_dict = Util.filt_item(value_dict)

            if mid:
                dao.update_media_by_mid(mid, value_dict)
            else:
                res = dao.get_media(ext_id, info_id)
                if not res:
                    dao.insert_media(value_dict)
                else:
                    dao.update_media(ext_id, info_id, value_dict)

            #poster
            if 'poster_url' in item and item['poster_url']:
                if not mid:
                    mid = dao.get_media(ext_id, info_id)
                if mid:
                    poster_val = {'mid': mid, 'url': item['poster_url']}
                    res = dao.get_poster(mid)
                    if not res:
                        dao.insert_poster(poster_val)
                    else:
                        dao.update_poster(mid, poster_val)

            if commit:
                self.commit_transaction()

        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_media(self, ext_id, info_id):
        try:
            dao = self._daos['media']
            res = dao.get_media(ext_id, info_id)
            self.commit_transaction()

            return res
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def insert_video(self, item, commit=True):
        try:
            dao = self._daos['video']
            media_dao = self._daos['media']
            value_dict = {}

            ext_id = item['ext_id']
            media_ext_id = item['media_ext_id']
            mid = media_dao.get_media(media_ext_id, None)

            if mid:
                value_dict['ext_id'] = ext_id
                value_dict['mid'] = mid
                if 'cont_id' in item:
                    value_dict['cont_id'] = item['cont_id']
                if 'title' in item:
                    value_dict['title'] = item['title']
                if 'vnum' in item:
                    value_dict['vnum'] = item['vnum']
                if 'site_id' in item:
                    value_dict['site_id'] = item['site_id']
                if 'intro' in item:
                    value_dict['intro'] = item['intro']

                res = dao.get_video(ext_id)
                if not res:
                    dao.insert_video(value_dict)
                else:
                    dao.update_video(ext_id, value_dict)

                #thumbnail
                if 'thumb_url' in item:
                    vid = dao.get_video(ext_id)
                    if vid:
                        thumb_val = {'vid': vid, 'url': item['thumb_url']}
                        res = dao.get_thumb(vid)
                        if not res:
                            dao.insert_thumb(thumb_val)
                        else:
                            dao.update_thumb(vid, thumb_val)

            if commit:
                self.commit_transaction()

        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_video(self, ext_id):
        try:
            dao = self._daos['video']
            res = dao.get_video(ext_id)
            self.commit_transaction()

            return res
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_site(self, site_code):
        try:
            dao = self._daos['site']
            res = dao.get_site(site_code)
            self.commit_transaction()

            return res
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_channel(self, channel_name):
        try:
            dao = self._daos['channel']
            res = dao.get_channel(channel_name)
            self.commit_transaction()
            return res
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_channel_name(self, channel_id):
        try:
            dao = self._daos['channel']
            res = dao.get_channel_name(channel_id)
            self.commit_transaction()
            return res
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_channel_map(self):
        try:
            dao = self._daos['channel']
            res = dao.get_channel_map()
            self.commit_transaction()
            return res
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_os(self, os_name):
        try:
            dao = self._daos['os']
            res = dao.get_os(os_name)
            self.commit_transaction()

            return res
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def insert_play_url(self, item, commit=True):
        try:
            dao = self._daos['play_url']
            video_dao = self._daos['video']
            value_dict = {}

            video_ext_id = item['ext_id']
            os_id = item['os_id']
            vid = video_dao.get_video(video_ext_id)

            if vid:
                value_dict['vid'] = vid
                if 'url' in item:
                    value_dict['url'] = item['url']
                if 'os_id' in item:
                    value_dict['os_id'] = os_id
                if 'format_id' in item:
                    value_dict['format_id'] = item['format_id']

                res = dao.get_play_url(vid, os_id)
                if not res:
                    dao.insert_play_url(value_dict)
                else:
                    dao.update_play_url(vid, os_id, value_dict)

            if commit:
                self.commit_transaction()

        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def insert_ext_video(self, item, commit=True):
        try:
            media_dao = self._daos['media']
            video_dao = self._daos['video']
            site_id = item['site_id']
            channel_id = item['channel_id']
            media_ext_id = item['media_ext_id']
            sid = media_dao.get_media(media_ext_id, None)

            for v in item['urls']:
                if not v:
                    continue
                video_ext_id = Util.md5hash(v)
                self.insert_untrack_ss({'url': v, 'md5': video_ext_id, 'channel_id': channel_id, 'sid': sid})
                '''
                video_ext_id = Util.md5hash(v)
                video_mid = video_dao.get_video_mid(video_ext_id)
                if video_mid:
                    self.insert_sync_rel({'sid': sid, 'mid': video_mid, 'site_id': site_id})
                    self.insert_untrack({'url': v, 'md5': video_ext_id, 'channel_id': channel_id, 'sid': sid, 'stat': 1})
                else:
                    self.insert_untrack({'url': v, 'md5': video_ext_id, 'channel_id': channel_id, 'sid': sid})
                '''
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def insert_sync_rel(self, item, commit=True):
        try:
            dao = self._daos['sync']
            value_dict = {}

            sid = item['sid']
            mid = item['mid']

            value_dict['sid'] = sid
            value_dict['mid'] = mid
            value_dict['site_id'] = item['site_id']

            res = dao.get_rel(sid, mid)
            if not res:
                dao.insert_rel(value_dict)
            else:
                dao.update_rel(sid, mid, value_dict)

            if commit:
                self.commit_transaction()

        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def insert_untrack_ss(self, item, commit=True):
        try:
            dao = self._daos['untrack']
            url = item['url']
            md5 = item['md5']
            sid = item['sid']
            site_code = Util.guess_site(url)
            # le --> letv; mgtv --> hunantv
            replace_site_dict = {'le': 'letv', 'mgtv': 'hunantv'}
            site_code = replace_site_dict.get(site_code, site_code)
            channel_id = item['channel_id']
            value_dict = {'sid': sid, 'md5':md5, 'url':url, 'channel_id': channel_id, 'site_code':site_code}
            res = dao.get_untrack_ss(sid, site_code)
            if len(res) > 1:
                max_ctime = max([r['ctime'] for r in res])
                for r in res:
                    uid = r['id']
                    if r['ctime'] < max_ctime:
                        pass
                        #print 'delete:', uid
                        #dao.delete_untrack_real(uid)
                    elif md5 != r['md5']:
                        #print 'update:', uid, md5, r['md5'], url, r['url'], r['stat']
                        # 更新untrack表，重置stat、invalid状态
                        value_dict['stat'] = 0
                        value_dict['invalid'] = 0
                        dao.update_untrack(uid, value_dict)
                    else:
                        pass
            elif len(res) == 1:
                if md5 != res[0]['md5']:
                    uid = res[0]['id']
                    # 更新untrack表，重置stat、invalid状态
                    value_dict['stat'] = 0
                    value_dict['invalid'] = 0
                    #print 'update:', uid, md5, res[0]['md5'], url, res[0]['url'], res[0]['stat']
                    dao.update_untrack(uid, value_dict)
            else:
                #print 'insert:', value_dict
                dao.insert_untrack(value_dict)
            if commit:
                self.commit_transaction()
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def insert_untrack(self, item, commit=True):
        try:
            dao = self._daos['untrack']
            value_dict = {}

            sid = item['sid']
            md5 = item['md5']
            url = item['url']
            site_code = Util.guess_site(url)

            value_dict['sid'] = sid
            value_dict['md5'] = md5
            value_dict['url'] = url
            value_dict['site_code'] = site_code
            if 'channel_id' in item:
                value_dict['channel_id'] = item['channel_id']
            if 'stat' in item:
                value_dict['stat'] = item['stat']

            res = dao.get_untrack(md5)
            if not res:
                dao.insert_untrack(value_dict)
            else:
                dao.update_untrack(res, value_dict)

            if commit:
                self.commit_transaction()

        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def fix_sync_rel(self, sid, media_ext_id, commit=True):
        try:
            media_dao = self._daos['media']

            mid = media_dao.get_media(media_ext_id, None)
            site_id = self.get_sync_site_id(sid)
            if mid:
                self.insert_sync_rel({'sid': sid, 'mid': mid, 'site_id': site_id})

            if commit:
                self.commit_transaction()
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def delete_untrack(self, untrack_id, commit=True):
        try:
            dao = self._daos['untrack']
            value_dict = {}

            dao.delete_untrack(untrack_id)

            if commit:
                self.commit_transaction()
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def insert_media_review(self, item, commit=True):
        try:
            review_dao = self._daos['review']
            media_dao = self._daos['media']
            media_ext_id = item['media_ext_id']
            mid = media_dao.get_media(media_ext_id, None)

            for r in item['urls']:
                if not r:
                    continue
                rv_id = Util.get_douban_rvid(r)
                res = review_dao.get_review(rv_id)
                if not res:
                    review_dao.insert_review({'mid': mid, 'url': r, 'rv_id': rv_id})

            if commit:
                self.commit_transaction()

        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_untrack_url(self, site_code, stat=None):
        try:
            dao = self._daos['untrack']
            res = dao.get_untrack_url(site_code, stat)
            self.commit_transaction()

            return res
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_sync_site_id(self, sid):
        try:
            dao = self._daos['sync']
            res = dao.get_sync_site_id(sid)
            self.commit_transaction()

            return res
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def get_video_url(self, site_code):
        try:
            dao = self._daos['video']
            res = dao.get_video_url(site_code)
            self.commit_transaction()

            return res
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def has_poster_filter_md5(self, md5):
        try:
            dao = self._daos['poster_filter']
            res = dao.has_poster_filter_md5(md5)
            self.commit_transaction()
            return res
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    def has_poster_filter_url(self, url):
        md5 = hashlib.md5(url).hexdigest()
        return self.has_poster_filter_md5(md5)

    def get_poster_filter_md5(self):
        try:
            dao = self._daos['poster_filter']
            res = dao.get_poster_filter_md5()
            self.commit_transaction()
            return res
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

if __name__ == "__main__":
    try:
        import json
        import copy
        logging.basicConfig(level=logging.INFO)
        mgr = DbManager.instance()

        #print mgr.has_poster_filter_md5('969fb1ad59ae31bd36c55b25a5d9100a')
        #print mgr.has_poster_filter_url(u'http://image11.m1905.cn/images/nopic_small.gif')
        print mgr.get_poster_filter_md5()
        '''
        res = mgr.get_untrack_url('youku')
        logging.log(logging.INFO, json.dumps(res))
        '''
        '''
        review = {}
        review['media_ext_id'] = 'af6a006fbc1f68e51f9ab45e4ed9c597'
        review['urls'] = ['http://movie.douban.com/review/7113080/', 'http://movie.douban.com/review/6867040/']
        mgr.insert_media_review(review)
        '''
        '''
        untrack = {}
        md5 = 'bfa89e563d9509fbc5c6503dd50faf2e'
        url = 'http://www.baidu.com'
        untrack['md5'] = md5
        untrack['url'] = url
        untrack['channel_id'] = 10
        untrack['site_code'] = 'youku'
        #mgr.insert_untrack(untrack)
        '''
        '''
        ext_video = {'site_id': 60, 'media_ext_id': 'af6a006fbc1f68e51f9ab45e4ed9c597', 'urls': ['http://v.qq.com/cover/r/rf34ba48pr2rqhk.html', 'http://v.qq.com/cover/j/jk7gtt5a4knk6k4.html']}
        mgr.insert_ext_video(ext_video)
        '''
        '''
        sync_rel = {'sid': 6661, 'mid': 101, 'site_id': 60}
        mgr.insert_sync_rel(sync_rel)
        '''
        '''
        mgr.get_os('web')
        '''
        media = {}
        media_ext_id = '111111'
        media['ext_id'] = media_ext_id
        media['info_id'] = 'iii'
        media['title'] = 'y'
        media['title'] = 'title'
        media['director'] = 'director'
        media['writer'] = 'writer'
        media['actor'] = 'actor'
        media['type'] = 'type'
        media['district'] = 'district'
        media['release_date'] = '20141111'
        media['duration'] = 2334
        media['channel_id'] = 10
        media['score'] = 4.4
        media['site_id'] = 12
        media['vcount'] = 10
        media['latest'] = 20121002
        media['url'] = 'http://uuu'
        media['intro'] = 'intro'
        media['poster_url'] = 'http://ppp'
        video = {}
        video_ext_id = 'vvv'
        video['ext_id'] = video_ext_id
        video['media_ext_id'] = media_ext_id
        video['title'] = 'tt'
        video['vnum'] = 21
        video['site_id'] = 10
        video['intro'] = 'uu'
        video['url'] = 'http://zzz'
        video['os_id'] = 10
        video['format_id'] = 10
        video['thumb_url'] = 'http://ttt'
        video2 = copy.deepcopy(video)
        video2['ext_id'] = '222'
        video2['url'] = 'http://aaa'
        video2['thumb_url'] = 'http://t22'
        video3 = copy.deepcopy(video)
        video3['ext_id'] = '222'
        video3['url'] = 'http://bbb'
        video3['thumb_url'] = 'http://t33'
        video3['os_id'] = 20
        mv = {}
        mv['media'] = media
        mv['video'] = [video, video2, video3]
        mv['sid'] = '11451'
        mv['untrack_id'] = '113610'
        #mgr.insert_media_video(mv)

        '''
        video = {}
        ext_id = 'vvv'
        video['ext_id'] = ext_id
        video['media_ext_id'] = 'xxx'
        video['title'] = 'tt'
        video['vnum'] = 21
        video['site_id'] = 10
        video['intro'] = 'uu'
        video['url'] = 'http://zzz'
        video['os_id'] = 10
        video['format_id'] = 10

        mgr.insert_video(video)
        mgr.insert_play_url(video)
        logging.log(logging.INFO, '%s' % mgr.get_video(ext_id))

        media = {}
        ext_id = 'xxx'
        info_id = 'iii'
        media['ext_id'] = ext_id
        media['title'] = 'y'
        media['title'] = 'title'
        media['director'] = 'director'
        media['writer'] = 'writer'
        media['actor'] = 'actor'
        media['type'] = 'type'
        media['district'] = 'district'
        media['release_date'] = '20141111'
        media['duration'] = 2334
        media['channel_id'] = 10
        media['score'] = 4.4
        media['site_id'] = 12
        media['vcount'] = 10
        media['latest'] = 20121002
        media['intro'] = 'intro'

        mgr.insert_media(media)
        logging.log(logging.INFO, '%s' % mgr.get_media(ext_id, info_id))
        '''

    except Exception, e:
        logging.log(logging.ERROR, traceback.format_exc())
