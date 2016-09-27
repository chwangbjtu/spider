# -*- coding:utf-8 -*-

import re
import urllib
import time
from datetime import datetime, timedelta
from dateutil import parser

class Util(object):

    @staticmethod
    def get_showid(url):
        r = re.compile(r'http://.+/id_([^_]+).*\.html')
        m = r.match(url)
        if m:
            return m.group(1)

    @staticmethod
    def get_v1_showid(url):
        r = re.compile(r'http://.+/(\d+).shtml')
        m = r.match(url)
        if m:
            return m.group(1)
    @staticmethod
    def get_ifeng_showid(url):
        tmp = url.split("/")[-1]
        tmp = tmp.split('.')[0]
        return tmp.replace("-", "")
    @staticmethod
    def get_tucao_showid(url):
        r = re.compile(r'http://.+/h(\d+)/')
        m = r.match(url)
        if m:
            return m.group(1)
    @staticmethod
    def get_acfun_showid(url):
        r = re.compile(r'http://.+/list(\d+)/index.htm')
        m = r.match(url)
        if m:
            return m.group(1)
    @staticmethod
    def get_sohu_showid(url):
        r = re.compile(r'http://.+/(\d|\w+)\.shtml')
        m = r.match(url)
        if m:
            return m.group(1)

    @staticmethod
    def get_letv_showid(url):
        r = re.compile(r'http://.+/(\d+)\.html')
        m = r.match(url)
        if m:
            return m.group(1)
    @staticmethod
    def get_iqiyi_showid(url):
        r = re.compile(r'http://.+/(.*?)\.html')
        m = r.match(url)
        if m:
            return m.group(1)

    @staticmethod
    def get_youtube_showid(url):
        r = re.compile(r'http[s]{0,1}://.+/watch\?v=([^&]*)')
        m = r.match(url)
        if m:
            return m.group(1)

    @staticmethod
    def get_ku6_showid(url):
        r = re.compile(r'http://v.ku6.com/show/(.*)\.html')
        m = r.search(url)
        if m:
            return m.group(1)

    @staticmethod
    def normalize_youtube_url(url):
        r = re.compile(r'(http[s]{0,1}://.+/watch\?v=[^&]*)')
        m = r.match(url)
        if m:
            return m.group(1)

    @staticmethod
    def unquote(text):
        return urllib.unquote(text.encode('utf8')).decode('utf8')

    @staticmethod
    def encode(dic):
        return urllib.urlencode(dic)

    @staticmethod
    def get_owner(url):
        r = re.compile(r'http://i.youku.com/u/(.+)')
        m = r.match(url)
        if m:
            return m.group(1)

    @staticmethod
    def get_youtube_owner(url):
        r = re.compile(r'http[s]{0,1}://.+/.+/([^/]+)/.+')
        m = r.match(url)
        if m:
            return m.group(1)

    @staticmethod
    def normalize_vp(vp):
        return vp.replace(',', '')

    vp_units = {u'万': 10000, u'亿': 100000000, '万': 10000, '亿': 100000000}
    @staticmethod
    def normalize_played(vp):
        if vp:
            r = re.compile(ur'([\d|,|.]*)(.*)')
            m = r.match(vp)
            if m:
                (num, u) = m.groups()
                num = num.replace(',', '')
                if u and u in Util.vp_units:
                    return str(int(float(num) * Util.vp_units[u]))
                return str(num)
        else:
            return str(0)

    @staticmethod
    def get_pl_id(url):
        r = re.compile(r'http://v.youku.com/.+\?f=(\d+)')
        m = r.match(url)
        if m:
            return m.group(1)

    @staticmethod
    def get_youtube_publish(s):
        r = re.compile(r'Published on (.*)')
        m = r.match(s)
        if m:
            t = m.group(1)
            return Util.get_datetime_abbreviated(t)

    units = {u'刚刚':0, u'分钟':1, u'小时':60, u'天前':1440, u'个月':43200, u'年前':525600, u'':10512000}
    @staticmethod
    def get_upload_time(s):
        if s:
            r = re.compile(r'(\d*)(..)')
            m = r.match(s)
            if m and len(m.groups()) == 2:
                t, u = m.groups()
                if not t:
                    t = '0'
                if u not in Util.units:
                    return Util.units[u'']
                return int(t) * Util.units[u]

    yt_units = {'min':1, 'hou':60, 'day':1440, 'wee':10080, 'mon':43200, 'yea':525600, u'':10512000}
    @staticmethod
    def get_youtube_upload_time(s):
        if s:
            r = re.compile(r'(\d*) (...)')
            m = r.match(s)
            if m and len(m.groups()) == 2:
                t, u = m.groups()
                if not t:
                    t = '0'
                if u not in Util.yt_units:
                    return Util.yt_units[u'']
                return int(t) * Util.yt_units[u]

    @staticmethod
    def get_datetime_delta(dt, minutes):
        return dt - timedelta(minutes=minutes)

    @staticmethod
    def timestamp2datetime(timestamp):
        ltime=time.localtime(timestamp)
        timestr=time.strftime("%Y-%m-%d %H:%M:%S", ltime)
        return timestr

    @staticmethod
    def get_delta_minutes(dt1, dt2):
        delta = dt1 - dt2
        return (delta.seconds + delta.days * 86400) / 60
            
    @staticmethod
    def get_datetime(s):
        format = '%Y-%m-%d %H:%M'
        return datetime.strptime(s, format)

    @staticmethod
    def get_datetime_abbreviated(s):
        format = '%b %d, %Y'
        return datetime.strptime(s, format)

    @staticmethod
    def strip_title(s):
       if s: 
            p = re.compile(ur'视频: (.*)')
            m = re.match(p, s)
            if m:
                return m.group(1)
            else:
                return s

    @staticmethod
    def get_qq_duration(s):
        # '00:06:09' --> 63
        # '1:9' --> 69
        try:
            dur = 0
            l = s.split(':')
            l.reverse()
            for k, v in enumerate(l):
                dur += 60**k*int(v)
            return dur
        except Exception, e:
            print e
            return None

    @staticmethod
    def get_qq_showid(url):
        # http://v.qq.com/cover/r/rch8wwhox28zfhu.html?vid=n0192m8bzd3
        r = re.compile(r'http://.+/.+/.+/(.+)\.html.*')
        m = r.match(url)
        if m:
            return m.group(1)

    @staticmethod
    def get_qq_owner_showid(html):
        # visited_uin : '113141829',
        r = re.compile(r'visited_uin : \'(\w+)\',')
        m = r.search(html)
        if m:
            return m.group(1)

    @staticmethod
    def normalize_qq_played(vp):
        if vp:
            r = re.compile(ur'([\d|,|.]*)(.*)')
            m = r.match(vp)
            if m:
                (num, u) = m.groups()
                num = num.replace(',', '')
                if u and u in Util.vp_units:
                    return str(int(float(num) * Util.vp_units[u]))
                return str(num)
        else:
            return str(0)

    @staticmethod
    def get_qq_upload_time(s):
        try:
            if s.endswith(u'小时前'):
                return Util.get_datetime_delta(datetime.now(), float(s.replace(u'小时前', '')) * 60)
            else:
                return parser.parse(s)
        except Exception, e:
            return None


if __name__ == "__main__":
    urls = [u'http://v.youku.com/v_show/id_XNzEzOTQwNjg0.html', 
            u'http://v.youku.com/v_show/id_XNzE0MTQxNzg0.html', 
            u'http://v.youku.com/v_show/id_XNzE0MTQxNzg0_ev_1.html', 
            u'http://v.youku.com/v_show/id_XNzEzODc0NjI0.html?from=y1.2-1-91.3.1-1.1-1-1-0',
            u'http://v.youku.com/v_show/id_XNTEzMDAwODU2.html?f=18922524']
    print map(Util.get_showid, urls)

    print Util.get_youtube_showid('https://www.youtube.com/watch?v=9rrzeYPWA2M')
    print Util.get_ku6_showid('http://v.ku6.com/show/Hsi9eEAKxYTj74V-q0znpQ...html&?from=my')

    print Util.normalize_youtube_url('https://www.youtube.com/watch?v=9rrzeYPWA2M')
    print Util.normalize_youtube_url('https://www.youtube.com/watch?v=jsrgJHmRoTY&list=UUEf_Bc-KVd7onSeifS3py9g')

    text = u'%E6%B5%B7%E5%8D%97|%E8%88%B9%E8%88%B6|%E8%B6%8A%E5%8D%97|%E4%B8%AD%E6%96%B9%E4%BA%BA|%E8%B6%8A%E5%8D%97%E8%AF%AD%E7%BF%BB%E8%AF%91|%E8%88%AA%E8%A1%8C%E6%97%B6%E9%97%B4|'
    print Util.unquote(text)


    urls = [u'http://i.youku.com/u/UMTc5MjY1NTY=',
            u'http://hz.youku.com/red/click.php?tp=1&cp=4003694&cpp=1000492&url=http://weibo.com/1848007337']
    print map(Util.get_owner, urls)

    print Util.get_youtube_owner('https://www.youtube.com/channel/UC0v-tlzsn0QZwJnkiaUSJVQ/about')

    vps = [u'1,233', u'407,184,631', u'4,385,086,614']
    print map(Util.normalize_vp, vps)

    urls = [u'http://v.youku.com/v_show/id_XNzA1ODM4MTA0.html?f=22197445', u'http://v.youku.com/v_show/id_XNzA1ODM4MTA0.html']
    print filter(None, map(Util.get_pl_id, urls))

    s = [u'刚刚 上传', u'3分钟前 上传', u'13分钟前 上传', u'4小时前 上传', u'14小时前 上传', u'5天前 上传', u'15天前 上传', u'2个月前 上传', u'12个月前 上传', u'6年前 上传', u'16年前 上传', u'', None, u'33未知']
    print map(Util.get_upload_time, s)

    yt_s = ['8 hours ago', '5 days ago', '1 week ago', '10 months ago', '1 year ago']
    print map(Util.get_youtube_upload_time, yt_s)

    print Util.get_datetime_delta(datetime.now(), 10)

    print Util.get_delta_minutes(datetime.now(), Util.get_datetime_delta(datetime.now(), 12))

    print Util.get_datetime('2014-07-16 09:12')
    print Util.get_datetime_abbreviated('Jan 12, 2011')
    print Util.get_youtube_publish('Published on Jun 22, 2011')

    played = [u'20.9万', '8,354', '8,357万', '1.43亿', u'8,408万', u'0', '0', '122', '4,234', '14哇', u'No views']
    print map(Util.normalize_played, played)

    title = [u'视频: 小苹果', u'小视频: 苹果', u'小苹果视频: 果果', u'视频: ']
    print '|'.join(map(Util.strip_title, title))

    iqiyi_url = ['http://www.iqiyi.com/v_19rrn8q2kw.html#vfrm=2-4-0-1', 'http://www.iqiyi.com/v_19rrn8q2kw.html#vfrm=2-4-0-1&curid=321645700_ebc7e1ea38fd761c162a382ad8d7a557', 'http://www.iqiyi.com/v_19rrnkewbw.html']
    print map(Util.get_iqiyi_showid, iqiyi_url)
    print "----------"
    info = '"document.domain=\'ku6.com\';(function(){var d=[{id:"sHfDUuBWM5bJG2cVMlZuug..",refers:"0",upcount:"0",downcount:"0",count:"33935"}];gotPlayCounts(d,null);})()"'
    #r = re.compile(r'(?<=count:\")[\d]*\"}];(?=gotPlayCounts)"')
    info1 = "I'm singing while you're dancing"
    r = re.compile(',count:"(\d+)?')
    m = r.search(info)
    print m
    if m:
        print m.groups(0)[0]

    r = re.compile(r',count:"(\d+)?"')
    print r.search(info).groups() 
