# -*- coding:utf-8 -*-
import re
import logging
import traceback
from douban.items import MediaItem
from douban.items import RecommendItem
from douban.items import RevItem, ReviewItem
from douban.common.util import Util


def get_imdb_chief(response):
    try:
        imdb_chiefs = response.xpath('//a[@class="bp_item np_all"]/@href').extract()
        if imdb_chiefs:
            imdb_chief = imdb_chiefs[0].split('/')[2]
            return imdb_chief
    except Exception, e:
        logging.log(logging.ERROR, traceback.format_exc())

def common_parse_media_plus(response):
    try:
        mediaItem = response.request.meta['mediaItem'] if 'mediaItem' in response.request.meta else MediaItem()
        url = response.request.url
        url = Util.douban_url_normalized(url)
        cont_id = dou_id = int(url.split('/')[4])

        #reviews = response.xpath('//a[@href="https://movie.douban.com/subject/%s/reviews"]/text()' % dou_id).re('\d+')
        #comments = response.xpath('//a[@href="https://movie.douban.com/subject/%s/comments"]/text()' % dou_id).re('\d+')
        reviews = response.xpath('//a[re:test(@href, ".*movie.douban.com/subject/%s/reviews")]/text()' % dou_id).re('\d+')
        comments = response.xpath('//a[re:test(@href, ".*movie.douban.com/subject/%s/comments")]/text()' % dou_id).re('\d+')
        if reviews:
            review = int(reviews[0])
        else:
            review = None
        if comments:
            comment = int(comments[0])
        else:
            comment = None

        names = response.xpath('//head/title/text()').extract()
        titles = response.xpath('//div[@id="wrapper"]/div[@id="content"]/h1/span[@property="v:itemreviewed"]/text()').extract()
        posters = response.xpath('//div[@id="mainpic"]/a/img/@src').extract()
        directors = response.xpath('//div[@id="info"]/span/span[text()="%s"]/../span[@class="attrs"]/a' % u"导演")
        writers = response.xpath('//div[@id="info"]/span/span[text()="%s"]/../span[@class="attrs"]/a/text()' % u"编剧").extract()
        actors = response.xpath('//div[@id="info"]/span/span[text()="%s"]/../span[@class="attrs"]/a' % u"主演")
        genres = response.xpath('//div[@id="info"]/span[@property="v:genre"]/text()').extract()
        
        aliasr = re.compile(r'<span class="pl">又名:</span>(.*)<br/>')
        aliasm = aliasr.search(response.body)
        if aliasm:
            aliasl = aliasm.groups()[0].split('/')
        else:
            aliasl = None
        
        districtr = re.compile(r'<span class="pl">制片国家/地区:</span>(.*)<br/>')
        districtm = districtr.search(response.body)
        if districtm:
            districtl = districtm.groups()[0].split('/')
        else:
            districtl = None

        langr = re.compile(r'<span class="pl">语言:</span>(.*)<br/>')
        langm = langr.search(response.body)
        if langm:
            langl = langm.groups()[0].split('/')
        else:
            langl = None

        # vcount
        vcountr = re.compile(r'<span class="pl">集数:</span>\D+(\d+).*<br/>')
        vcountm = vcountr.search(response.body)
        episode_list = response.xpath('//div[@class="episode_list"]/a/text()').extract()
        if vcountm:
            vcount = int(vcountm.groups()[0])
        elif episode_list:
            vcount = len(episode_list)
        else:
            vcount = 1
        
        channel_name = 'movie' if vcount == 1 else 'tv'
        relesas_dates = response.xpath('//div[@id="info"]/span[@property="v:initialReleaseDate"]/text()').re('([0-9-]+)\({0,1}')
        
        # runtime
        runtimes = response.xpath('//div[@id="info"]/span[@property="v:runtime"]/text()').re('(\d+).*')
        runtimer = re.compile(r'<span class="pl">单集片长:</span>\D+(\d+).*<br/>')
        runtimem = runtimer.search(response.body)
        if runtimes:
            runtime = int(runtimes[0])
        elif runtimem:
            runtime = int(runtimem.groups()[0])
        else:
            runtime = None

        scores = response.xpath('//div[@id="interest_sectl"]//strong[@property="v:average"]/text()').extract()
        
        imdbr = re.compile(r'<span class="pl">IMDb链接:</span>\s+<a.*>(.*)</a><br>')
        imdbm = imdbr.search(response.body)
        if imdbm:
            imdb = imdbm.groups()[0]
        else:
            imdb = None
        
        intros = response.xpath('//div[@class="related-info"]/div/span/text()').extract()
        
        if names and ('name' not in mediaItem or not mediaItem['name']):
            mediaItem['name'] = names[0].replace(u'(豆瓣)', '').strip()
        if titles and ('title' not in mediaItem or not mediaItem['title']):
            mediaItem['title'] = titles[0].strip()
        if posters and ('poster' not in mediaItem or not mediaItem['poster']):
            mediaItem['poster'] = posters[0].strip()
        if scores and ('score' not in mediaItem or not mediaItem['score']):
            mediaItem['score'] = float(scores[0].strip())
        mediaItem['cont_id'] = cont_id
        mediaItem['dou_id'] = dou_id
        director = {}
        for d in directors:
            d_names = d.xpath('./text()').extract()
            d_ids = d.xpath('./@href').re('celebrity/(\d+)')
            if d_names:
                d_id = d_ids[0] if d_ids else None
                director.setdefault(d_names[0], d_id)
        mediaItem['director'] = director
        if writers:
            mediaItem['writer'] = Util.lst2str(writers)
        actor = {}
        for a in actors:
            a_names = a.xpath('./text()').extract()
            a_ids = a.xpath('./@href').re('celebrity/(\d+)')
            if a_names:
                a_id = a_ids[0] if a_ids else None
                actor.setdefault(a_names[0], a_id)
        mediaItem['actor'] = actor
        if genres:
            mediaItem['genre'] = Util.lst2str(genres)
        if relesas_dates:
            mediaItem['release_date'] = Util.str2date(relesas_dates[0])
        if runtime:
            mediaItem['runtime'] = runtime
        if scores:
            mediaItem['score'] = float(scores[0])
        if imdb:
            mediaItem['imdb'] = imdb
        if intros:
            # mediaItem['intro'] = intros[0].strip('\n').strip()
            mediaItem['intro'] = ''.join([r.strip('\n').strip() for r in intros])
        if aliasl:
            mediaItem['alias'] = Util.lst2str(aliasl)
        if districtl:
            mediaItem['district'] = Util.lst2str(districtl)
        if langl:
            mediaItem['lang'] = Util.lst2str(langl)
        if review is not None:
            mediaItem['review'] = review
        if comment is not None:
            mediaItem['comment'] = comment
        mediaItem['vcount'] = vcount
        mediaItem['url'] = url
        return mediaItem
    except Exception, e:
        logging.log(logging.ERROR, traceback.format_exc())
        return mediaItem

def common_parse_media(response):
    try:
        #logging.log(logging.INFO, 'parse_media: %s' % response.request.url)
        mediaItem = response.request.meta['mediaItem'] if 'mediaItem' in response.request.meta else MediaItem()
        url = response.request.url
        url = Util.douban_url_normalized(url)
        cont_id = dou_id = int(url.split('/')[4])
        titles = response.xpath('//div[@id="wrapper"]/div[@id="content"]/h1/span[@property="v:itemreviewed"]/text()').extract()
        posters = response.xpath('//div[@id="mainpic"]/a/img/@src').extract()
        directors = response.xpath('//div[@id="info"]/span/span[text()="%s"]/../span[@class="attrs"]/a/text()' % u"导演").extract()
        writers = response.xpath('//div[@id="info"]/span/span[text()="%s"]/../span[@class="attrs"]/a/text()' % u"编剧").extract()
        actors = response.xpath('//div[@id="info"]/span/span[text()="%s"]/../span[@class="attrs"]/a/text()' % u"主演").extract()
        genres = response.xpath('//div[@id="info"]/span[@property="v:genre"]/text()').extract()
        
        aliasr = re.compile(r'<span class="pl">又名:</span>(.*)<br/>')
        aliasm = aliasr.search(response.body)
        if aliasm:
            aliasl = aliasm.groups()[0].split('/')
        else:
            aliasl = None
        
        districtr = re.compile(r'<span class="pl">制片国家/地区:</span>(.*)<br/>')
        districtm = districtr.search(response.body)
        if districtm:
            districtl = districtm.groups()[0].split('/')
        else:
            districtl = None

        langr = re.compile(r'<span class="pl">语言:</span>(.*)<br/>')
        langm = langr.search(response.body)
        if langm:
            langl = langm.groups()[0].split('/')
        else:
            langl = None

        # vcount
        vcountr = re.compile(r'<span class="pl">集数:</span>\D+(\d+).*<br/>')
        vcountm = vcountr.search(response.body)
        episode_list = response.xpath('//div[@class="episode_list"]/a/text()').extract()
        if vcountm:
            vcount = int(vcountm.groups()[0])
        elif episode_list:
            vcount = len(episode_list)
        else:
            vcount = 1
        
        channel_name = 'movie' if vcount == 1 else 'tv'
        relesas_dates = response.xpath('//div[@id="info"]/span[@property="v:initialReleaseDate"]/text()').re('([0-9-]+)\({0,1}')
        
        # runtime
        runtimes = response.xpath('//div[@id="info"]/span[@property="v:runtime"]/text()').re('(\d+).*')
        runtimer = re.compile(r'<span class="pl">单集片长:</span>\D+(\d+).*<br/>')
        runtimem = runtimer.search(response.body)
        if runtimes:
            runtime = int(runtimes[0])
        elif runtimem:
            runtime = int(runtimem.groups()[0])
        else:
            runtime = None

        scores = response.xpath('//div[@id="interest_sectl"]//strong[@property="v:average"]/text()').extract()
        
        imdbr = re.compile(r'<span class="pl">IMDb链接:</span>\s+<a.*>(.*)</a><br>')
        imdbm = imdbr.search(response.body)
        if imdbm:
            imdb = imdbm.groups()[0]
        else:
            imdb = None
        
        intros = response.xpath('//div[@class="related-info"]/div/span/text()').extract()
        
        if titles and ('title' not in mediaItem or not mediaItem['title']):
            mediaItem['title'] = titles[0].strip()
        if posters and ('poster' not in mediaItem or not mediaItem['poster']):
            mediaItem['poster'] = posters[0].strip()
        if scores and ('score' not in mediaItem or not mediaItem['score']):
            mediaItem['score'] = float(scores[0].strip())
        mediaItem['cont_id'] = cont_id
        mediaItem['dou_id'] = dou_id
        if directors:
            mediaItem['director'] = Util.lst2str(directors)
        if writers:
            mediaItem['writer'] = Util.lst2str(writers)
        if actors:
            mediaItem['actor'] = Util.lst2str(actors)
        if genres:
            mediaItem['genre'] = Util.lst2str(genres)
        if relesas_dates:
            mediaItem['release_date'] = Util.str2date(relesas_dates[0])
        if runtime:
            mediaItem['runtime'] = runtime
        if scores:
            mediaItem['score'] = float(scores[0])
        if imdb:
            mediaItem['imdb'] = imdb
        if intros:
            # mediaItem['intro'] = intros[0].strip('\n').strip()
            mediaItem['intro'] = ''.join([r.strip('\n').strip() for r in intros])
        if aliasl:
            mediaItem['alias'] = Util.lst2str(aliasl)
        if districtl:
            mediaItem['district'] = Util.lst2str(districtl)
        if langl:
            mediaItem['lang'] = Util.lst2str(langl)
        mediaItem['vcount'] = vcount
        #mediaItem['channel_id'] = self.channel_map[channel_name]
        #mediaItem['site_id'] = self.site_id
        mediaItem['url'] = url
        return mediaItem
    except Exception, e:
        logging.log(logging.ERROR, traceback.format_exc())
        return mediaItem

def common_parse_recommend(response):
    try:
        #logging.log(logging.INFO, 'parse_recommend: %s' % response.request.url)
        recommendItem = response.request.meta['recommendItem'] if 'recommendItem' in response.request.meta else RecommendItem()
        url = response.request.url
        url = Util.douban_url_normalized(url)
        dou_id = int(url.split('/')[4])

        recommendItem['dou_id'] = dou_id

        rec_lst = []
        rec_urls = response.xpath('//div[@class="recommendations-bd"]/dl/dt/a/@href').extract()
        for rurl in rec_urls:
            rurl =  Util.douban_url_normalized(rurl)
            rec_lst.append(int(rurl.split('/')[4]))
        if rec_lst:
            recommendItem['rec_lst'] = rec_lst
        return recommendItem
    except Exception, e:
        logging.log(logging.ERROR, traceback.format_exc())

def common_parse_review(response):
    try:
        #logging.log(logging.INFO, 'parse_review: %s' % response.request.url)
        #reviewItem = response.request.meta['reviewItem'] if 'reviewItem' in response.request.meta else ReviewItem()
        #rev_lst = reviewItem['rev_lst'] if 'rev_lst' in reviewItem else []
        rev_lst = []
        #url = response.request.url
        #url = Util.douban_url_normalized(url)
        #dou_id = int(url.split('/')[4])

        #reviewItem['dou_id'] = dou_id

        h3s = response.xpath('//div[@class="review"]/div[@class="review-hd"]/h3')
        for h3 in h3s:
            revItem = RevItem()
            user_urls = h3.xpath('./a[@class="review-hd-avatar"]/@href').extract()
            rev_ids = h3.xpath('./div[@class="review-hd-expand"]/@id').extract()

            if user_urls:
                user_url =user_urls[0]
                neck_name = user_url.split('/')[4]
                revItem['neck_name'] = neck_name
            if rev_ids:
                rev_id = rev_ids[0].replace('tb-', '')
                revItem['rev_id'] = rev_id

            if 'neck_name' in revItem and 'rev_id' in revItem:
                rev_lst.append(revItem)

        #if rev_lst:
        #    reviewItem['rev_lst'] = rev_lst

        #return reviewItem
        return rev_lst
    except Exception, e:
        logging.log(logging.ERROR, traceback.format_exc())

def get_cookie(response):
    try:
        cookie = {}
        set_cookie = response.headers.getlist('Set-Cookie')
        if set_cookie:
            cookie_list = set_cookie[0].split(';')
            for cl in cookie_list:
                k, v = cl.split('=')
                cookie[k] = v.strip('\"')
    except Exception, e:
        logging.log(logging.ERROR, traceback.format_exc())
    finally:
        return cookie

