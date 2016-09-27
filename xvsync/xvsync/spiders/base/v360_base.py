# -*- coding:utf-8 -*- 
import logging
from scrapy.http import HtmlResponse
from scrapy.selector import Selector
import traceback
import re
import json
from xvsync.common.formatter import V360Formatter
from xvsync.common.util import Util
from xvsync.common.http_download import HTTPDownload

import re
def get_cluster_id(url):
    r = re.compile('http://.+/(.*?)\.html')
    m = r.match(url)
    if m:
        return m.group(1)

class V360ParserBase(object):
    
    def __init__(self):
        pass

    def parse_options(self, response):
        return []

    def parse_page_list(self, response):
        try:
            #video results
            urls = response.xpath('//div[@class="result-view"]/ul/li/div[@class="cont"]/p[@class="video-title"]/a/@href').extract()
            #pages
            next_page = response.xpath('//div[@class="gpage"]/a[@class="page-next"]/@href').extract()

            return {'urls': urls, 'next_page': next_page}
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_media_info(self, response):
        pass

    def parse_video(self, response):
        pass

    def parse_review(self, response):
        pass

class V360ParserMovie(V360ParserBase):

    httpdownload = HTTPDownload()
    
    def __init__(self):
        super(V360ParserBase, self).__init__()

    def parse_options(self, response):
        try:
            filter = response.xpath('//div[@id="filter"]')
            #category
            cat_codes = filter.xpath('./div[2]/dl[1]/dd/a/@href').re(r'cat=([^&]*)')
            cat_names = filter.xpath('./div[2]/dl[1]/dd/a[@href]/text()').extract()
            cats = zip(cat_codes, cat_names)
            cats.append((u'all', u'全部'))

            #area
            area_codes = filter.xpath('./div[2]/dl[2]/dd/a/@href').re(r'area=([^&]*)')
            area_names = filter.xpath('./div[2]/dl[2]/dd/a[@href]/text()').extract()
            areas = zip(area_codes, area_names)
            areas.append((u'all', u'全部'))

            #year
            years = filter.xpath('./div[2]/dl[3]/dd/a/@href').re(r'year=([^&]*)')
            years.append(u'all')

            #rank
            ranks = response.xpath('//li[@class="tabitem"]/a/@href').re(r'rank=([^&]*)')
            ranks.append(u'rankhot')

            urls = []
            for cat in cats:
                for area in areas:
                    for year in years:
                        for rank in ranks:
                            urls.append('http://v.360.cn/dianying/list.php?rank=%s&cat=%s&year=%s&area=%s' % (rank, cat[0], year, area[0]))

            return urls

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_media_info(self, response):
        try:
            result = {}
            #main
            main = response.xpath('//div[@id="main"]')

            #base info
            base_info = main.xpath('./div[1]/div[2]')
            title = base_info.xpath('./div[1]/h1[@id="film_name"]/text()').extract()
            director = base_info.xpath('./div[1]/dl[@id="director"]/dd/a[not(@id)]/text()').extract()
            actor = base_info.xpath('./div[1]/dl[@id="actor"]/dd/a/text()').extract()
            #tag = base_info.xpath('./div[1]/dl[@id="genre"]/dd/a/text()').extract()
            type = None
            area = base_info.xpath('./div[1]/div[@class="text"]/dl[@class="area"]/dd/text()').extract()
            year = base_info.xpath('./div[1]/div[@class="text"]/dl[@class="year"]/dd/text()').extract()
            duration = base_info.xpath('./div[1]/div[@class="text"]/dl[@class="duration"]/dd/text()').extract()
            score_int = base_info.xpath('./div[1]/div[@class="aggregate-rating"]/div[1]/p/span/em/text()').extract()
            score_dec = base_info.xpath('./div[1]/div[@class="aggregate-rating"]/div[1]/p/span/text()').extract()

            #side info
            side = main.xpath('./div[1]/div[1]')
            poster = side.xpath('./div/descendant-or-self::*/img/@src').extract()
            #movieid = side.xpath('./div/a/@movieid').extract()
            pay = side.xpath('./div/a/em').extract()

            #intro
            desc = main.xpath('./div[2]/div[2]')
            intro = desc.xpath('//p[@class="more"]/text()').extract()
            if not intro:
                intro = desc.xpath('//p[@class="less"]/text()').extract()

            
            #
            try:
                contid = get_cluster_id(response.request.url)
                tag_url = "http://android.api.360kan.com/coverpage/?id="+contid+"&cat=1&method=coverpage.data&refm=selffull&ss=4&token=2bf65a903d03167e48d38694f8aa4f1a&ver=71&ch=360sjzs"
                taginfo = self.httpdownload.get_data(tag_url)
                if taginfo and len(taginfo) > 32:
                    subtaginfo = taginfo[32:]
                    jtaginfo = json.loads(subtaginfo)
                    if "data" in jtaginfo and "data" in jtaginfo["data"] and "type" in jtaginfo["data"]["data"]:
                        type = jtaginfo["data"]["data"]["type"]
            except Exception as e:
                pass

            if title:
                result['title'] = title[0]
            if director:
                result['director'] = V360Formatter.join(director)
            if actor:
                result['actor'] = V360Formatter.join(actor)
            if type:
                result['type'] = V360Formatter.join(type)
            if area:
                result['district'] = V360Formatter.rejoin(area[0])
            if year:
                result['release_date'] = Util.str2date(year[0])
            if duration:
                result['duration'] = V360Formatter.duration(duration[0])
            if score_int and score_dec:
                result['score'] = V360Formatter.score(score_int[0], score_dec[0])
            elif score_int:
                result['score'] = V360Formatter.score(score_int[0], None)
            if poster:
                result['poster_url'] = poster[0]
            #if movieid:
            #    result['cont_id'] = movieid[0]
            result['cont_id'] = get_cluster_id(response.request.url)
            if pay:
                result['paid'] = 1
            if intro:
                result['intro'] = ''.join(intro)

            return result

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_video(self, response):
        try:
            sup = response.xpath('//ul[@id="supplies"]/li/a/@href').extract()
            sup_more = response.xpath('//div[@class="menu"]//ul/li/a/@href').extract()

            supplies = sup + sup_more

            return [Util.normalize_url(Util.convert_url(u), channel='movie') for u in supplies]

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_review(self, response):
        try:
            reviews = response.xpath('//div[@id="reviews"]/div[2]/ul/li/div/a/@href').extract()
            return reviews
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

class V360ParserTv(V360ParserBase):
    
    def __init__(self):
        super(V360ParserBase, self).__init__()

    def parse_options(self, response):
        try:
            filter = response.xpath('//div[@id="filter"]')
            #category
            cat_codes = filter.xpath('./div[2]/dl[1]/dd/a/@href').re(r'cat=([^&]*)')
            cat_names = filter.xpath('./div[2]/dl[1]/dd/a[@href]/text()').extract()
            cats = zip(cat_codes, cat_names)
            cats.append((u'all', u'全部'))

            #area
            area_codes = filter.xpath('./div[2]/dl[2]/dd/a/@href').re(r'area=([^&]*)')
            area_names = filter.xpath('./div[2]/dl[2]/dd/a[@href]/text()').extract()
            areas = zip(area_codes, area_names)
            areas.append((u'all', u'全部'))

            #year
            years = filter.xpath('./div[2]/dl[3]/dd/a/@href').re(r'year=([^&]*)')
            years.append(u'all')

            urls = []
            for cat in cats:
                for area in areas:
                    for year in years:
                        urls.append('http://v.360.cn/dianshi/list.php?cat=%s&year=%s&area=%s' % (cat[0], year, area[0]))

            return urls
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_media_info(self, response):
        try:
            result = {}

            #details
            details = response.xpath('//div[@class="v-details"]')
            title = details.xpath('./div[@class="v-title clearfix"]/span[@id="film_name"]/text()').extract()
            poster = details.xpath('./div[@class="v-poster"]/descendant-or-self::*/img/@src').extract()
            #movieid = details.xpath('./div[@class="v-poster"]/a/@movieid').extract()

            #base info
            base_info = details.xpath('./div[@class="v-main-info clearfix"]')
            actor = base_info.xpath('./div[1]/p[@id="actors"]/a/text()').extract()
            director = base_info.re(re.compile(r'<i>%s</i>(.*?)</p>' % u'导演：', re.S))
            area = base_info.re(re.compile(r'<i>%s</i>(.*?)</p>' % u'地区：', re.S))
            category  = base_info.re(re.compile(r'<i>%s</i>(.*?)</p>' % u'类型：', re.S))
            year = base_info.re(re.compile(r'<i>%s</i>(.*?)</p>' % u'年代：', re.S))

            intro = base_info.xpath('./p[@class="intro"]/span[@id="full-intro"]/text()').extract()
            if not intro:
                intro = base_info.xpath('./p[@class="intro"]/span[@id="part-intro"]/text()').extract()
            if not intro:
                intro = base_info.xpath('./p[@class="intro"]/span[@class="text"]/text()').extract()
            episode_num = base_info.xpath('./p[@class="episode clearfix"]/text()').extract()
            score_int = base_info.xpath('./div[@class="aggregate-rating"]/div[1]/p/span/em/text()').extract()
            score_dec = base_info.xpath('./div[@class="aggregate-rating"]/div[1]/p/span/text()').extract()

            #side info
            side_info = details.xpath('./div[@id="left_info"]')

            if title:
                result['title'] = title[0]
            if poster:
                result['poster_url'] = poster[0]
            #if movieid:
            #    result['cont_id'] = movieid[0]
            result['cont_id'] = get_cluster_id(response.request.url)
            if actor:
                result['actor'] = V360Formatter.join(actor)
            if director:
                result['director'] = V360Formatter.rejoin(director[0])
            if area:
                result['district'] = V360Formatter.rejoin(area[0])
            if category:
                result['type'] = V360Formatter.rejoin(category[0])
            if year:
                result['release_date'] = Util.str2date(year[0])
            if intro:
                result['intro'] = ''.join(intro)
            if episode_num:
                vc = V360Formatter.episode_num(episode_num[0].strip())
                if 'vcount' in vc:
                    result['vcount'] = vc['vcount']
                if 'latest' in vc:
                    result['latest'] = re.sub(r"[^\d]", "", vc['latest'])
            if score_int and score_dec:
                result['score'] = V360Formatter.score(score_int[0], score_dec[0])
            elif score_int:
                result['score'] = V360Formatter.score(score_int[0], None)

            return result

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_video(self, response):
        try:
            supplies = response.xpath('//div[@id="tv-play"]/div[@class="box"]/div/div/a[1]/@href').extract()

            return [Util.normalize_url(Util.convert_url(u), channel='tv') for u in supplies]

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

class V360ParserVariaty(V360ParserBase):
    
    def __init__(self):
        super(V360ParserBase, self).__init__()

    def parse_options(self, response):
        try:
            filter = response.xpath('//div[@id="filter"]')
            #category
            cat_codes = filter.xpath('./div[2]/dl[1]/dd/a/@href').re(r'cat=([^&]*)')
            cat_names = filter.xpath('./div[2]/dl[1]/dd/a[@href]/text()').extract()
            cats = zip(cat_codes, cat_names)
            cats.append((u'all', u'全部'))

            #area
            area_codes = filter.xpath('./div[2]/dl[2]/dd/a/@href').re(r'area=([^&]*)')
            area_names = filter.xpath('./div[2]/dl[2]/dd/a[@href]/text()').extract()
            areas = zip(area_codes, area_names)
            areas.append((u'all', u'全部'))

            urls = []
            for cat in cats:
                for area in areas:
                    urls.append('http://v.360.cn/zongyi/list.php?cat=%s&area=%s' % (cat[0], area[0]))

            return urls
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_media_info(self, response):
        try:
            result = {}
            #info
            info = response.xpath('//div[@id="info"]')
            title = info.xpath('//span[@id="film_name"]/text()').extract()
            intro = info.xpath('//p[@id="full-intro"]/text()').extract()
            if not intro:
                intro = info.xpath('//p[@id="part-intro"]/text()').extract()
            if not intro:
                intro = info.xpath('//p[@class="text"]/text()').extract()
            episode_num = info.xpath('//div[@class="gclearfix"]/p/text()').extract()

            #poster
            poster = response.xpath('//div[@id="left_info"]/div[@id="poster"]/descendant-or-self::*/img/@src').extract()
            #movieid = response.xpath('//div[@id="left_info"]/div[@id="poster"]/a/@movieid').extract()

            #other info
            otherinfo = response.xpath('//div[@id="otherinfo"]')
            actor = otherinfo.re('<em>主持人：</em><span[^>]*>(.*?)</span>'.decode('utf8'))
            category = otherinfo.re('<em>类型：</em><span[^>]*>(.*?)</span>'.decode('utf8'))
            area = otherinfo.re('<em>地区：</em><span[^>]*>(.*?)</span>'.decode('utf8'))
            station = otherinfo.re('<em>播出：</em><span[^>]*>(.*?)</span>'.decode('utf8'))

            if title:
                result['title'] = title[0]
            if intro:
                result['intro'] = ''.join(intro).strip()
            if episode_num:
                vc = V360Formatter.episode_num(episode_num[0].strip())
                if 'vcount' in vc:
                    result['vcount'] = vc['vcount']
                if 'latest' in vc:
                    result['latest'] = re.sub(r"[^\d]", "", vc['latest'])

            if poster:
                result['poster_url'] = poster[0]
            #if movieid:
            #    result['cont_id'] = movieid[0]
            result['cont_id'] = get_cluster_id(response.request.url)
            if actor:
                result['actor'] = V360Formatter.rejoin(actor[0])
            if category:
                result['type'] = V360Formatter.rejoin(category[0])
            if area:
                result['district'] = V360Formatter.rejoin(area[0])
            if station:
                result['station'] = station[0]

            return result

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_video(self, response):
        try:
            ext_video = []
            cluster_id = get_cluster_id(response.request.url)
            cluster_site = response.xpath('//ul[@id="supplies"]/li/@site').extract()
            cluster_site_popup = response.xpath('//div[@id="supplies-popup"]/div/@site').extract()
            cluster_site_single = response.xpath('//div[@id="listing"]/div/div[@class="content"]/@site').extract()
            cluster_src = set(cluster_site + cluster_site_popup + cluster_site_single)
            for site in cluster_src:
                url = 'http://www.360kan.com/cover/zongyilist?id=%s&do=switchsite&site=%s' % (cluster_id, site)
                downloader = HTTPDownload()
                content = downloader.get_data(url)

                json_data = json.loads(content)
                sel = Selector(text=json_data['data'], type="html")
                video = sel.xpath('//dl/dt/a/@href').extract()

                if video:
                    ext_video.append(Util.normalize_url(Util.convert_url(video[0]), channel='variaty'))
            return ext_video
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

class V360ParserCartoon(V360ParserBase):
    
    def __init__(self):
        super(V360ParserBase, self).__init__()

    def parse_options(self, response):
        try:
            filter = response.xpath('//div[@id="filter"]')
            #category
            cat_codes = filter.xpath('./div[2]/dl[1]/dd/a/@href').re(r'cat=([^&]*)')
            cat_names = filter.xpath('./div[2]/dl[1]/dd/a[@href]/text()').extract()
            cats = zip(cat_codes, cat_names)
            cats.append((u'all', u'全部'))

            #area
            area_codes = filter.xpath('./div[2]/dl[2]/dd/a/@href').re(r'area=([^&]*)')
            area_names = filter.xpath('./div[2]/dl[2]/dd/a[@href]/text()').extract()
            areas = zip(area_codes, area_names)
            areas.append((u'all', u'全部'))

            #year
            years = filter.xpath('./div[2]/dl[3]/dd/a/@href').re(r'year=([^&]*)')
            years.append(u'all')
            
            urls = []
            for cat in cats:
                for area in areas:
                    for year in years:
                        urls.append('http://v.360.cn/dongman/list.php?cat=%s&year=%s&area=%s' % (cat[0], year, area[0]))

            return urls
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_media_info(self, response):
        try:
            result = {}
            #base info
            base_info = response.xpath('//div[@id="info"]')
            title = base_info.xpath('./div[1]/h1[@id="film_name"]/text()').extract()
            actor = base_info.re(re.compile(r'<em.*?>%s</em>.*?<span.*?>(.*?)</span>' % u'主角：', re.S))
            director = base_info.re(re.compile(r'<em.*?>%s</em>.*?<span.*?>(.*?)</span>' % u'导演：', re.S))
            area = base_info.re(re.compile(r'<em.*?>%s</em>.*?<span.*?>(.*?)</span>' % u'地区：', re.S))
            category = base_info.re(re.compile(r'<em.*?>%s</em>.*?<span.*?>(.*?)</span>' % u'类型：', re.S))
            year = base_info.re(re.compile(r'<em.*?>%s</em>.*?<span.*?>(.*?)</span>' % u'年代：', re.S))
            intro = base_info.xpath('./div[2]/p/em[text()="%s"]/../span[@id="full-intro"]/span/text()'% u'简介：').extract()
            if not intro:
                intro = base_info.xpath('./div[2]/p/em[text()="%s"]/../span[@id="part-intro"]/span/text()'% u'简介：').extract()
            if not intro:
                intro = base_info.xpath('./div[2]/p/em[text()="%s"]/../span[@class="text"]/text()'% u'简介：').extract()
            episode_num = base_info.re(re.compile(r'<em.*?>%s</em>.*?<span.*?>(.*?)</span>' % u'剧集：', re.S))

            #poster
            poster = response.xpath('//div[@id="left_info"]/div[@id="poster"]/descendant-or-self::*/img/@src').extract()
            #movieid = response.xpath('//div[@id="left_info"]/div[@id="poster"]/a/@movieid').extract()

            if title:
                result['title'] = title[0]
            if actor:
                result['actor'] = V360Formatter.rejoin(actor[0])
            if director:
                result['director'] = V360Formatter.rejoin(director[0])
            if area:
                result['district'] = V360Formatter.rejoin(area[0])
            if category:
                result['type'] = V360Formatter.rejoin(category[0])
            if year:
                result['release_date'] = Util.str2date(year[0])
            if intro:
                result['intro'] = ''.join(intro)
            if episode_num:
                vc = V360Formatter.episode_num(episode_num[0].strip())
                if 'vcount' in vc:
                    result['vcount'] = vc['vcount']
                if 'latest' in vc:
                    result['latest'] = re.sub(r"[^\d]", "", vc['latest'])
            if poster:
                result['poster_url'] = poster[0]
            #if movieid:
            #    result['cont_id'] = movieid[0]
            result['cont_id'] = get_cluster_id(response.request.url)

            return result

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

    def parse_video(self, response):
        try:
            supplies = response.xpath('//div[@id="listing"]/div/div[@class="content"]/div/div[@class="part"][1]/a[1]/@href').extract()

            return [Util.normalize_url(Util.convert_url(u), channel='cartoon') for u in supplies]

        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
