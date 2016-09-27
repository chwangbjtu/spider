# -*- coding:utf-8 -*-
import re
from dateutil import parser

class Util(object):

    @staticmethod
    def lst2str(lst, split='|'):
        if not lst:
            return ''
        else:
            return split.join([s.strip() for s in lst])

    @staticmethod
    def str2date(para):
        try:
            return parser.parse(str(para))
        except Exception,e:
            return None

    @staticmethod
    def douban_url_normalized(url):
        # https://movie.douban.com/subject/3011091/?from=subject-page
        # ↓↓↓↓↓
        # https://movie.douban.com/subject/3011091/
        r = re.compile('(\w+://\w+.\w+.\w+/\w+/\d+/{0,1})?.*')
        m = r.search(url)
        if m:
            res = m.groups()[0]
        else:
            res = url
        return res


if __name__ == '__main__':
    print Util.douban_url_normalized('https://movie.douban.com/subject/3011091/?from=subject-page')
