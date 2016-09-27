# -*- coding:utf-8 -*-
import re
import time
import json
import urlparse
import traceback
import logging
from dateutil import parser
from datetime import datetime
from hashlib import md5
import urllib2
from httplib import IncompleteRead 
#import tldextract

URL_TYPE_MAIN  = 0
URL_TYPE_PLAY = 1
URL_TYPE_MEDIA = 2

class Util(object):

    LIST_MAX_LENGTH  = 10

    @staticmethod
    def join_list_safely(lst, split='|'):
        result = ''
        try:
            if lst == None:
                return result
            results = lst[0:Util.LIST_MAX_LENGTH]
            result = split.join([s.strip() for s in results])
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return result

    @staticmethod
    def get_url_content(url):
        result = ''
        try:
            if url:
                request = urllib2.Request(url=url)
                response = urllib2.urlopen(request)
                response_url = response.geturl()
                #http://www.hunantv.com/v/2/2905
                #http://www.hunantv.com/v/2/2905/
                if url.endswith('/') == False:
                    url = url + '/'
                if response_url.endswith('/') == False:
                    response_url = response_url + '/'
                if response_url == url:
                    #没有跳转
                    result = response.read()
        except IncompleteRead, e:
            result = ''.join(e.partial)
        finally:
            return result

    @staticmethod
    def set_ext_id(mediaItem, videoItems):
        try:
            if mediaItem and videoItems:
                title = mediaItem['title'] if 'title' in mediaItem else '' 
                earliest = 0
                try:
                    res_vnum = int(videoItems[earliest]['vnum']) if 'vnum' in videoItems[earliest] else 1
                except Exception, e:
                    res_vnum = 1
                index = 0
                for item in videoItems:
                    try:
                        dest_vnum = int(item['vnum']) if 'vnum' in item else 1
                        if dest_vnum < res_vnum:
                            earliest = index
                            res_vnum = dest_vnum
                        index = index+1
                        if not ('title' in item and item['title'] and item['title'].strip()):
                            item['title'] = title + str(dest_vnum)
                    except Exception, e:
                        continue
                #找到该album最早的一集或一期节目
                earliest_video = videoItems[earliest]
                mediaItem['ext_id'] = Util.md5hash(earliest_video['url'])
                for item in videoItems:
                    item['media_ext_id'] = mediaItem['ext_id']
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())

    @staticmethod
    def prefix_url_parse(url):
        prefix_url = ''
        try:
            result = urlparse.urlparse(url)
            prefix_url = '%s://%s' % (result.scheme, result.netloc)
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return prefix_url

    @staticmethod
    def url_type_parse(url):
        url_type = ''
        try:
            if url:
                if url.startswith('/'):
                    url_type = UrlType.SLASH
                elif url.startswith('http'):
                    url_type = UrlType.HTTP
                elif url.startswith('www'):
                    url_type = UrlType.WWW
                else:
                    url_type = UrlType.NOSLASH
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return url_type
        
    @staticmethod
    def get_absolute_url(url, prefix_url=''):
        absolute_url = ''
        try:
            url_type = Util.url_type_parse(url)
            if url_type == UrlType.HTTP:
                absolute_url = url
            elif url_type == UrlType.WWW:
                absolute_url = 'http://' + url
            elif url_type == UrlType.SLASH:
                absolute_url = prefix_url + url
            else:
                absolute_url = prefix_url + '/' + url
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return absolute_url

    @staticmethod
    def copy_media_to_video(mediaItem, videoItem):
        if mediaItem == None or videoItem == None:
            return
        videoItem['title'] = mediaItem['title'] if 'title' in mediaItem else None
        videoItem['intro'] = mediaItem['intro'] if 'intro' in mediaItem else None 
        videoItem['thumb_url'] = mediaItem['poster_url'] if 'poster_url' in mediaItem else None 
            
    @staticmethod
    def guess_site(url):
        try:
            special_site = ['61', 'kumi']
            for s in special_site:
                if url.startswith('http://%s.' % s):
                    return s

            r = re.compile('http[s]{0,1}://.+\.(.*?)\.(com.cn)')
            m = r.match(url.split('?')[0])
            if m:
                return m.group(1)

            r = re.compile('http[s]{0,1}://.+\.(.*?)\.[com|cn|tv]')
            m = r.match(url.split('?')[0])
            if m:
                return m.group(1)
            '''
            ext = tldextract.extract(url)
            return ext.domain
            '''
        except Exception as e:
            logging.log(logging.INFO, 'fail to guess site: %s' % url)

    @staticmethod
    def md5hash(key):
        try:
            if isinstance(key, unicode):
                return md5(key.encode('utf8')).hexdigest()
            return md5(key).hexdigest()
        except Exception as e:
            logging.log(logging.INFO, 'fail to calculate md5: %s' % key)

    @staticmethod
    def normalize_url(url, site=None, channel=None):
        try:
            if not site:
                site = Util.guess_site(url)
            normalize_fun = None
            res = None
            if channel:
                method = 'normalize_%s_%s' % (site, channel)
                if hasattr(url_normalize, method):
                    normalize_fun = getattr(url_normalize, method)
            if not channel or not normalize_fun:
                method = 'normalize_%s' % site
                normalize_fun = getattr(url_normalize, method)
                if hasattr(url_normalize, method):
                    normalize_fun = getattr(url_normalize, method)
            if normalize_fun:
                res = normalize_fun(url)
            if res:
                return res
            return url
        except Exception as e:
            logging.log(logging.INFO, 'url not normalize: %s' % url)
            return url

    @staticmethod
    def convert_url(url, site=None):
        try:
            if not site:
                site = Util.guess_site(url)
            convert_fun = None
            res = None
            method = 'convert_%s' % (site, )
            if hasattr(url_convert, method):
                convert_fun = getattr(url_convert, method)
            if convert_fun:
                res = convert_fun(url)
            if res:
                return res
            return url
        except Exception as e:
            logging.log(logging.INFO, 'url not convert: %s' % url)
            return url

    @staticmethod
    def str2date(para):
        try:
            return parser.parse(str(para))
        except Exception as e:
            logging.log(logging.INFO, 'connot convert type(para) %s to date' % para)

    @staticmethod
    def date2str(dt):
        try:
            format = '%Y%m%d'
            return dt.strftime(format)
        except Exception as e:
            logging.log(logging.INFO, 'connot convert date %s to string' % dt)

    @staticmethod    
    def get_qq_showid(url):
        id = ""
        try:
            #http://v.qq.com/detail/j/jlw8mddv9wkv1a3.html
            #r = re.compile(r'http://.+/id_([^_]+).*\.html')
            r = re.compile(r'http://.+/.+/[0-9a-zA-Z]/([^_]+).*\.html')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            pass
        return id

    @staticmethod    
    def summarize(media):
        try:
            keys = ['cont_id', 'site_id', 'title', 'director', 'actor']
            seg = [str(media[k]) for k in keys if k in media and media[k]]
            return ''.join(seg)
        except Exception as e:
            logging.log(logging.INFO, 'connot summarize: %s' % json.dumps(media))

    @staticmethod    
    def filt_item(item):
        try:
            filter = [u'未知']
            return dict((k, v) for k, v in item.iteritems() if v not in filter)
        except Exception as e:
            logging.log(logging.INFO, 'fail to filt: %s' % json.dumps(item))
            return item

    @staticmethod    
    def check_item(item):
        essential_keys = ['title', 'ext_id', 'info_id', 'cont_id']
        for k in essential_keys:
            if k not in item or not item[k]:
                return False
        return True

    @staticmethod
    def get_douban_rvid(url):
        try:
            r = re.compile('http://.*?\.com/review/(\d+)')
            m = r.match(url)
            if m:
                return m.group(1)
        except Exception as e:
            logging.log(logging.INFO, 'fail to filt: %s' % json.dumps(item))

    @staticmethod
    def extract_number(s):
        try:
            if s:
                r = re.compile(r'\d+')
                m = r.findall(s)
                return "".join(m)

        except Exception as e:
            logging.log(logging.INFO, 'fail to extract number: %s' % s)

    @staticmethod
    def extract_whole_number(s):
        try:
            if s:
                return int(s)
        except Exception as e:
            logging.log(logging.INFO, 'fail to extract whole number: %s' % s)
            
    @staticmethod
    def get_current_year():
        try:
            return str(datetime.now().year)
        except Exception as e:
            logging.log(logging.INFO, 'fail to filt: %s' % json.dumps(item))
            return ''

class UrlType(object):
    HTTP = 0
    WWW = 1
    SLASH = 2
    NOSLASH = 3

class UrlConvert(object):

    def convert_qq(self, url):
        try:
            r = re.compile(r'(http://[^/]*/[^/]*/[^/]*/[^/]*)/[^.]*?(\..*)')
            m = r.match(url)
            if m:
                return ''.join(m.groups())
            
        except Exception as e:
            logging.log(logging.INFO, 'fail to convert: %s' % url)

    def convert_kankan(self, url):
        try:
            r = re.compile(r'(http://[^/]*/[^/]*/[^/]*/[^/]*)/[^.]*?(\..*)')
            m = r.match(url)
            if m:
                return ''.join(m.groups())
            
        except Exception as e:
            logging.log(logging.INFO, 'fail to convert: %s' % url) 

    def convert_m1905(self, url):
        try:
            return url.replace('m1905', '1905')
        except Exception as e:
            logging.log(logging.INFO, 'fail to convert: %s' % url)

url_convert = UrlConvert()

class UrlType(object):
    HTTP = 0
    WWW = 1
    SLASH = 2
    NOSLASH = 3

class UrlNormalize(object):

    def normalize_youtube(self, url):
        r = re.compile(r'(http[s]{0,1}://.+?/watch\?v=[^&]*)')
        m = r.match(url)
        if m:
            return m.group(1)

class UrlNormalize(object):

    def normalize_youtube(self, url):
        r = re.compile(r'(http[s]{0,1}://.+?/watch\?v=[^&]*)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_youku(self, url):
        r = re.compile(r'(http://[^/]*.youku.com.+?/[^/]*.html)')
        m = r.match(url)
        if m:
            return m.group(1)

        r = re.compile(r'http://cps.youku.com/redirect.html.+url=(.+\.html)')
        m = r.match(url)
        if m:
            return m.group(1)

    #def normalize_sohu(self, url):
    #    r = re.compile(r'(http://tv.sohu.com.+?/[^/]*.html)')
    #    m = r.match(url)
    #    if m:
    #        return m.group(1)

    def normalize_sohu(self, url):
        #http://tv.sohu.com/s2014/xcmzdrddp/
        #http://tv.sohu.com/item/MjA4NzM0.html
        #http://tv.sohu.com/20131020/n388515766.shtml
        r = re.compile(r'(http://tv.sohu.com.+?/[^/]*.html)')
        m = r.match(url)
        if m:
            return m.group(1)
        r = re.compile(r'(http://tv.sohu.com/[^/]*./[^/]*./)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_hunantv(self, url):
        r = re.compile(r'(http://www.hunantv.com/v/.*.html)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_mgtv(self, url):
        r = re.compile(r'(http://www.mgtv.com/v/.*.html)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_qq(self,url):
        #http://v.qq.com/cover/b/bnc0cvuskzxnrcl.html
        #http://film.qq.com/cover/q/qt5n3vwuemtibsb.html
        r = re.compile(r'(http://[^/]*.qq.com/cover/.+?/[^/]*.html)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_qq_tv(self,url):
        #http://v.qq.com/cover/b/bnc0cvuskzxnrcl.html?vid=a0015svcr4g
        #http://v.qq.com/cover/4/4y2izzyrtlvyuq1.html?vid=s00158xyxpe
        r = re.compile(r'(http://.*?)\.html\?vid=([^&]+)')
        m = r.match(url)
        if m:
            g = m.groups()
            if len(g) > 1:
                return g[0] + "/" + g[1] + ".html"

        r = re.compile(r'(http://[^/]*.qq.com/cover/.+?/[^/]*.html)')
        #r = re.compile(r'(http://[^/]*.qq.com/cover/.+?/[^/]*.html[^/]*.vid[^&]*)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_qq_cartoon(self,url):
        #http://v.qq.com/cover/7/74gvr40k9u0b63g.html?vid=w0012nzam63
        r = re.compile(r'(http://.*?)\.html\?vid=([^&]+)')
        m = r.match(url)
        if m:
            g = m.groups()
            if len(g) > 1:
                return g[0] + "/" + g[1] + ".html"

        r = re.compile(r'(http://[^/]*.qq.com/cover/.+?/[^/]*.html)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_letv(self, url):
        r = re.compile(r'(http://www.letv.com/ptv/vplay/[\d]+.html)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_le(self, url):
        r = re.compile(r'(http://www.le.com/ptv/vplay/[\d]+.html)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_360kan(self, url):
        r = re.compile(r'(http://www.360kan.com.+?/[^/]*.html)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_kankan(self, url):
        r = re.compile(r'(http://vod.kankan.com/v/[\d]+/[\d]+.shtml\?subid=[\d]+)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_kankan_movie(self, url):
        '''
            (1) http://vod.kankan.com/v/86/86056.shtml
            (2) http://vip.kankan.com/vod/86884.html?fref=kk_search_sort_01
        '''
        r = re.compile(r'(http://[^/]*.kankan.com.+?/[\d]+.[s]?html)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_1905(self, url):
        if url:
            url = url.replace('m1905', '1905')
            r = re.compile(r'(http://[^/]*.1905.com.+?/[\d]+.shtml)')
            m = r.match(url)
            if m:
                return m.group(1)

    def normalize_tudou(self,url):
        #http://www.tudou.com/albumplay/EE22o5LDLMY.html
        #http://www.tudou.com/albumcover/D_uMp8c11hg.html
        #http://www.tudou.com/oplay/uJblXtccBmY/TjygOhGVqcE.html
        r = re.compile(r'(http://www.tudou.com/[^/]*/[^/]*.[s]?html)')
        m = r.match(url)
        if m:
            return m.group(1)
        r = re.compile(r'(http://www.tudou.com/[^/]*/[^/]*/[^/]*.[s]?html)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_iqiyi(self, url):
        r = re.compile(r'(http://www.iqiyi.com/v_[\w]+.html)')
        m = r.match(url)
        if m:
            return m.group(1)
        r = re.compile(r'(http://www.iqiyi.com/[a-zA-Z]+/[\d]+/[\w]+.html)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_pptv(self, url):
        '''
            (1)http://v.pptv.com/show/TSp39FzCMnDTUbk.html?rcc_src=L1
            (2)http://ddp.vip.pptv.com/vod_detail/tOlS0TmfD02wLpY.html
        '''
        r = re.compile(r'(http://v.pptv.com/show/[\w]+.html)')
        m = r.match(url)
        if m:
            return m.group(1)
        r = re.compile(r'(http://ddp.vip.pptv.com/vod_detail/[\w]+.html)')
        m = r.match(url)
        if m:
            return m.group(1)

    def normalize_baofeng(self, url):
        r = re.compile(r'(.*.html)')
        m = r.match(url)
        if m:
            return m.group(1)
        #return url

    def normalize_wasu(self, url):
        #r = re.compile(r'(.*.html)')
        #m = r.match(url)
        #if m:
        #    return m.group(1)
        r = re.compile(r'(http://www.wasu.\b(cn|com|tv)/.*/id/\d+)')
        m = r.match(url)
        if m:
            return m.group(1)


url_normalize = UrlNormalize()

if __name__ == "__main__":
    '''
    urls = [
            [u'http://v.youku.com/v_show/id_XNzE0MTQxNzg0.html', 'youku', 'tv'], 
            [u'http://v.youku.com/v_show/id_XNzEzODc0NjI0.html?from=y1.2-1-91.3.1-1.1-1-1-0', 'youku', 'movie'],
            [u'http://v.youku.com/v_show/id_XNzEzODc0NjI0.html?from=y1.2-1-91.3.1-1.1-1-1-0', 'youku'],
            [u'http://cps.youku.com/redirect.html?id=0000028f&url=http://v.youku.com/v_show/id_XOTUzMDI1NDUy.html&tpa=dW5pb25faWQ9MTAyMjEzXzEwMDAwN18wMV8wMQ', 'youku'],
            [u'https://www.youtube.com/watch?v=mBIAQ1FDynM', 'youtube'],
            [u'http://tv.sohu.com/20150111/n407690847.shtml?txid=4e4df35dda9d8ed32c874b1ad590ef59', 'sohu'],
            [u'http://www.hunantv.com/v/1/18/f/1108467.html#dfadf?fasdfsadf', 'hunantv'],
            [u'http://www.360kan.com/tv/QrprcX7kRWTrN3.html', '360kan'],
            [u'http://vod.kankan.com/v/84/84774/467150.shtml?id=731021', 'kankan', 'tv'],
            ["http://v.qq.com/cover/4/4y2izzyrtlvyuq1.html?vid=s00158xyxpe","qq","tv"],
            ["http://v.qq.com/cover/4/4y2izzyrtlvyuq1.html?vid=s00158xyxpe&other=xx","qq","tv"],
            ["http://v.qq.com/cover/m/miq3dzivmn4q97e/l0016u9nvn8.html","qq","tv"],
            ["http://v.qq.com/cover/7/74gvr40k9u0b63g/w0012nzam63.html","qq","cartoon"],
            ["http://v.qq.com/cover/7/74gvr40k9u0b63g.html?vid=w0012nzam63","qq","cartoon"],
           ]
    for u in urls:
        if len(u) == 2:
            print Util.normalize_url(u[0], u[1])
        elif len(u) == 3:
            print Util.normalize_url(u[0], u[1], u[2])


    for u in urls:
        print Util.md5hash(u[0])
    print Util.md5hash(u'测试')
    print Util.md5hash('测试')

    join_lst = None
    print Util.join_list_safely(join_lst)
    join_lst = []
    print Util.join_list_safely(join_lst)
    join_lst = ['ha' , 'dfsa', 'adaf']
    print Util.join_list_safely(join_lst)
    join_lst = ['ha' , 'dfsa', 'adaf', 'df', '122121', 'ffaf', '876878', '76', '3e2332', 'fasfd', '100000', '2000']
    print Util.join_list_safely(join_lst)

    dates = ['2015-1-2', '20150102', '2015,01,2', '01/02', '01-02', '0102', '2014']
    print map(Util.str2date, dates)

    print Util.date2str(datetime.now())
    print Util.str2date('2001')

    print Util.summarize({'cont_id': 111, 'site_id': 1, 'title': 't', 'director': 'd', 'actor': 'a'})
    '''
    urls = [
            'http://v.ku6.com/show/obNGxLFxAJuBZEMGzyVRtw...html',
            'http://v.qq.com/cover/8/8062ejt3xfs7tjh.html',
            'http://www.1905.com/vod/play/861861.shtml',
            'http://www.tudou.com/albumplay/9AwjpxUFd1c/63LWKY1chhw.html?tpa=dW5pb25faWQ9MTAyMjEzXzEwMDAwMV8wMV8wMQ',
            'http://v.youku.com/v_show/id_XODQ5NzQyNDIw.html?tpa=dW5pb25faWQ9MTAyMjEzXzEwMDAwN18wMV8wMQ',
            'http://www.hunantv.com/v/1/18/f/1108467.html#dfadf?fasdfsadf',
            'http://tv.sohu.com/20150111/n407690847.shtml?txid=4e4df35dda9d8ed32c874b1ad590ef59',
            'https://www.youtube.com/watch?v=mBIAQ1FDynM',
            'http://g.hd.baofeng.com/play/77/play-783577.html',
            'http://www.fun.tv/vplay/m-110049.e-1?alliance=152055',
            'http://v.pptv.com/show/8icpT0DiaeDkyvLbE.html',
            'http://www.wasu.cn/Play/show/id/5346824?refer=sll',
            'http://vod.kankan.com/v/87/87202.shtml?id=731021',
            'http://tv.sohu.com/20150306/n409439192.shtml?txid=19b06d0609b2eda1bcef9b6ce824056a',
            'http://www.56.com/u42/v_MTM1NzY0NDA3.html',
            'http://www.boosj.com/drama_40661_20150305.html',
            'http://tv.cntv.cn/video/C22417/f188463482d23ddfc99c61b90a4e5c44',
            'http://v.ifeng.com/ent/zongyi/201412/01ea90a9-ab44-4e19-b2ee-c817123f0d06.shtml#v_360zl',
            'http://v.pps.tv/play_3GDAOY.html#from_360',
            'http://me.cztv.com/video-2311283.html',
            'http://www.iqiyi.com/v_19rrnpcag4.html',
            'http://www.kumi.cn/donghua/60248_4.html',
            'http://www.baidu.com/',
            'http://www.baidu.com',
            'http://www.wasu.cn/Play/show/id/4425079?refer=v.360.cn',
            'http://video.sina.com.cn/v/b/21122995-1338693724.html',
            'http://61.pps.tv/comic-play/5251/1.shtml',
            'http://61.iqiyi.com/comic-play/1199/1.shtml',
            'http://61.hz.letv.com/comic-play/5301/1.shtml',
            'http://61.tv.sohu.com/comic-play/7429/1.shtml',
            'http://61.youku.com/comic-play/2135/1.shtml',
            'http://kumi.hz.letv.com/donghua/57441_1.html',
           ]
    for url in urls:
        print Util.guess_site(url)
    '''
    print map(Util.guess_site, urls)

    item = {'director': u'嗯嗯', 'actor': u'未知', 'title': u'哦哦', 'duration': 111, 'name': u'未知', 'day': u'未知'}
    print Util.filt_item(item)

    print Util.get_douban_rvid('http://movie.douban.com/review/7214367/')
    print Util.normalize_url("http://www.tudou.com/albumplay/OFCvKK973Kw/ixRVTLx9ZrM.html?aasd=asdf","tudou")
    print Util.normalize_url("http://tv.sohu.com/s2014/xcmzdrddp/#aasd=asdf","sohu")
    print Util.normalize_url("http://tv.sohu.com/item/MjA4NzM0.html?aasd=asdf","sohu")
    print Util.normalize_url("http://tv.sohu.com/20131020/n388515766.shtml?aasd=asdf","sohu")

    urls = [
            'http://www.letv.com/ptv/vplay/21786808.html',
            'http://v.qq.com/cover/8/8062ejt3xfs7tjh.html',
            'http://v.qq.com/cover/p/pernw6by8wusf6a.html?vid=j0010dAnOvj',
            'http://v.qq.com/cover/p/pernw6by8wusf6a/j0010dAnOvj.html',
            'http://vod.kankan.com/v/87/87656.shtml?id=731021',
            'http://vod.kankan.com/v/87/87656/454764.shtml?id=731021',
            'http://www.m1905.com/vod/play/711972.shtml',
            'http://www.1905.com/vod/play/711972.shtml#guessYouLike',
           ]
    print map(Util.convert_url, urls)

    result = Util.get_url_content('http://list.hunantv.com/album/102831.html')
    if result:
        print result
    else:
        print 'None'


    print '---------------'
    print Util.guess_site("http://v.qq.com/prev/b/beybxvsnw4tfdy6.html")
    print Util.guess_site("http://v.qq.com/p/tv/zt/xmblzjh/index.html")
    print Util.guess_site("http://film.qq.com/cover/3/3au50sy4i90heio.html")
    print Util.guess_site("http://v.qq.com")
    print Util.guess_site("http://v.youku.com/v_show/id_XMjA1OTQ3ODAw.html")
    print Util.guess_site("http://so.tv.sohu.com")

    s = [u'7', u'08-06期', u'', None, u'2015年', u'2015-08-06']
    print map(Util.extract_number, s)
    print Util.get_current_year()
    '''
