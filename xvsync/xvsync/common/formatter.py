# -*- coding:utf-8 -*- 
import re

class V360Formatter(object):

    @staticmethod
    def score(integer, decimal):
        if not integer:
            return '0'
        if not decimal: 
            return integer
        return integer + decimal

    @staticmethod
    def duration(str):
        if not str:
            return '0'
        r = re.compile(r'\D*(\d+)\D*')
        m = r.match(str)
        if m:
            return m.group(1)
        return '0'

    @staticmethod
    def year(str):
        if not str:
            return '0'
        r = re.compile(r'\D*(\d+)\D*')
        m = r.match(str)
        if m:
            return m.group(1)
        return '0'

    @staticmethod
    def episode_num(str):
        res = {}
        if str:
            patterns = {'vcount': [re.compile(ur'共(\d+)集'), re.compile(ur'全(\d+)集')], 
                        'latest': [re.compile(ur'更新至(\d+)集'), re.compile(ur'更新至([\d-]+)期')]}
            for k, v in patterns.items():
                for p in v:
                    m = p.search(str)
                    if m:
                        res[k] = m.group(1)
                        break
            if 'vcount' in res and 'latest' not in res:
                res['latest'] = res['vcount']
        return res
    
    @staticmethod
    def stage(str):
        if str:
            r = r'[\d-]+'
            m = re.findall(r, str)
            if m:
                return m[0]
        return ''

    @staticmethod
    def split(p, seperator=[' ', '/']):
        return re.split(r'[%s]+' % ''.join(seperator), p)

    @staticmethod
    def join(p, joiner='|', strip=True, limit=10):
        if not limit:
            limit = len(p)
        if joiner:
            return joiner.join([s.strip() for s in p[0:limit]])
        return joiner.join(p[0:limit])

    @staticmethod
    def rejoin(p, seperator=[' ', '/'], joiner='|', limit=10):
        segment = V360Formatter.split(p, seperator)
        return V360Formatter.join(segment, joiner, limit=limit)

if __name__ == "__main__":
    print V360Formatter.score('6', '.3')
    print V360Formatter.score(None, '.3')
    print V360Formatter.score('6', None)

    print V360Formatter.duration(u'98分钟')

    print V360Formatter.year(u'2014年')
    print V360Formatter.year(u'2014-3-1')

    print V360Formatter.episode_num(None)
    print V360Formatter.episode_num(u'更新至26集 / 共28集')
    print V360Formatter.episode_num(u'更新至16集')
    print V360Formatter.episode_num(u'共43集')
    print V360Formatter.episode_num(u'更新至2014-04-26期')
    print V360Formatter.episode_num(u'a26bc28dd')
    print V360Formatter.episode_num(u'a268')
    print V360Formatter.episode_num(u'a268dd')

    print V360Formatter.split(u'李慧珠 / 邓伟恩 / 温伟基', seperator=['/', ' '])
    print V360Formatter.split(u'李慧珠', seperator=['/', ' '])
    print V360Formatter.split(u'李慧珠  邓伟恩  温伟基', seperator=['/', ' '])

    print V360Formatter.rejoin(u'李慧珠 / 邓伟恩 / 温伟基')
    print V360Formatter.rejoin(u'李慧珠')
    print V360Formatter.rejoin(u'李慧珠  邓伟恩  温伟基')
    print V360Formatter.rejoin(u'李慧珠  邓伟恩  温伟基', limit=2)
    print V360Formatter.rejoin(u'李慧珠  邓伟恩  温伟基', limit=None)

    print V360Formatter.stage(u'2014-05-03期')
    print V360Formatter.stage(u'2014-05-03')
    print V360Formatter.stage(u'20140503')
    print V360Formatter.stage(u'第20140503期')
    print V360Formatter.stage(u'第2014and0503期')

