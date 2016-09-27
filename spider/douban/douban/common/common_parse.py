# -*- coding:utf-8 -*-
import re
import logging
import traceback
from douban.items import MediaItem
from util import Util

def common_parse_media(response):
    try:
        logging.log(logging.INFO, 'parse_media: %s' % response.request.url)
        mediaItem = response.request.meta['mediaItem'] if 'mediaItem' in response.request.meta else MediaItem()
        url = response.request.url
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
        #relesas_dates = response.xpath('//div[@id="info"]/span[@property="v:initialReleaseDate"]/text()').re('([0-9-]+)\(')
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
        
        #imdbs = response.xpath('//div[@id="info"]/a[last()]/text()').extract()
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
            mediaItem['intro'] = intros[0].strip('\n').strip()
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


