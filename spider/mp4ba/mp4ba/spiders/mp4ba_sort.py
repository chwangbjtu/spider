# -*- coding:utf-8 -*- 
from scrapy.spiders import Spider
from scrapy.http import Request
import logging
import traceback
import re
from scrapy.utils.project import get_project_settings
from hashlib import md5
from mp4ba.items import MediaVideoItem, MediaItem, VideoItem
from hades_common.util import Util
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
try:
    from mp4ba.hades_db.db_mgr import DbManager
except ImportError:
    from hades_db.db_mgr import DbManager

class Mp4baSort(Spider):
    name = "mp4ba_sort"
    pipelines = ['CategoryPipeline', 'MysqlStorePipeline']
    site_code = 'mp4ba'
    allowed_domains = ["www.mp4ba.com"]
    mgr = DbManager.instance()
    site_id = str(mgr.get_site_by_code(site_code)["site_id"])
    protocol_code = 'bt'
    protocol_id = mgr.get_protocol_map().get(protocol_code)
    max_number=10000
    def __init__(self, *args, **kwargs):
        super(Mp4baSort, self).__init__(*args, **kwargs)
        self._sort_api = "http://www.mp4ba.com/index.php?sort_id=%s"
        self._url_prefix = "http://www.mp4ba.com/"

        self._start = []
        for i in range(1,12):
            # 1-11:国产电影、港台电影、欧美电影、日韩电影、海外电影、动画电影、国产电视剧、港台电视剧、欧美电视剧、日韩电视剧、综艺娱乐
            self._start.append({'url': self._sort_api % i})
            #break
    def start_requests(self):
        try:
            self.load_member_variable()
            items = []
            for s in self._start:
                items.append(Request(url=s['url'], callback=self.parse_list))
                #break
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
    def load_member_variable(self):
        try:
            max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
            if max_update_page and max_update_page > 0:
                self.max_number = max_update_page
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
    def parse_list(self, response):
        try:
            page = response.request.meta['page'] if 'page' in response.request.meta else 1
            logging.log(logging.INFO, "parse_list:%s" % response.request.url)
            items = []

            data_list = response.xpath('//tbody[@id="data_list"]/tr')
            for data in data_list:
                urls = data.xpath('./td[3]/a/@href').extract()
                titles = data.xpath('./td[3]/a/text()').extract()

                url = self._url_prefix + urls[0].strip('\n') if urls else None
                title_short = titles[0].split('.')[0].strip() if titles else None
                title_long = titles[0].strip() if titles else None
                #url="http://www.mp4ba.com/show.php?hash=02ad1035b4a43df77352864ae274b51cadd9d111"
                if url:
                    items.append(Request(url=url, callback=self.parse_show, meta={'title_short': title_short, 'title_long': title_long}))
                    #return items
            # next page
            if page < self.max_number:
                next_page_sel = response.xpath('//div[@class="pages clear"]/a[@class="nextprev"]/@href').extract()
                if next_page_sel:
                    next_page_url = self._url_prefix + next_page_sel[-1]
                    items.append(Request(url=next_page_url, callback=self.parse_list,meta={'page':page+1}))
            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
    def parse_person_info(self,pattern,content):
        res={}
        try:
            for (k, v) in pattern.items():
                for r in v:
                    m = r.findall(content)
                    if m:
                        tmp = m[0]
                        if tmp.find('<br>')!=-1:
                            tmp = tmp.replace('<br>','')
                            tmp = tmp.replace('\r\n','/')
                        res[k] = tmp
                        if not res[k]:
                            res[k] = u""
                        break
                    res[k] = u""
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return res
    def parse_show(self, response):
        try:
            logging.log(logging.INFO, "parse_show:%s" % response.request.url)
            items = []
            seed_urls = response.xpath('//a[@id="download"]/@href').extract()
            seed_url = self._url_prefix + seed_urls[0] if seed_urls else None

            info = response.xpath('//div[@class="intro"]').extract()
            #print info
            #return items
            #print len(info)
            pattern = {'director':[re.compile(u'导演:(.*?)<br>', re.S),re.compile(u'导\u3000\u3000演\u3000(.*?)<br>', re.S)], \
                        'actor':[re.compile(u'主演:(.*?)<br>', re.S),re.compile(u'主\u3000\u3000演\u3000(.*?)</p>', re.S),re.compile(u'主\u3000\u3000演 : (.*?)<br>', re.S),re.compile(u'演\u3000\u3000员(.*?)</p>', re.S)], \
                        'alias':[re.compile(u'又名:(.*?)<', re.S),re.compile(u'译\u3000\u3000名\u3000(.*?)<', re.S),re.compile(u'外文名(.*?)<br>', re.S),re.compile(u'中文片名(.*?)<br>', re.S)], \
                        'imdb':[re.compile(u'IMDb链接:(.*?)<', re.S),re.compile(u'IMDB链接(.*?)<br>', re.S),re.compile(u'iMDB链接(.*?)<br', re.S)]}
            res = self.parse_person_info(pattern,info[0])
            #print res
            #print info[0]
            #print res['imdb']
            #print res['director']
            #print res['actor']
            #return items
            m_item = MediaItem()
            m_item['title'] = response.request.meta['title_short']
            m_item['cont_id'] = md5(response.request.url).hexdigest()
            m_item['site_id'] = self.site_id
            m_item['url'] = response.request.url
            if res['director']:
                director=res['director']
                if director.find('<')!=-1:
                    director=director[:director.find('<')]
                director=director.replace('/','|')
                m_item['director']=director
            if res['actor']:
                actor = res['actor']
                if actor.find('<')!=-1:
                    actor = actor[:actor.find('<')] 
                actor = actor.replace('\u3000','') 
                actor = actor.replace(':','') 
                actor = actor.replace(u'】','') 
                actor = actor.replace(u'：','') 
                act = actor.split('/')
                actor=""
                for it in act:
                    if it.find('(')!=-1:
                        it = it[:it.find('(')]
                    if it.find('（')!=-1:
                        it = it[:it.find('（')]
                    if it.find('...')!=-1:
                        it = it[:it.find('...')]
                    if it.find('…')!=-1:
                        it = it[:it.find('…')]
                    it = it.replace(u'更多','').strip()
                    if it:
                        if actor:
                            actor =actor +"|"
                            actor = actor +it
                        else:
                            actor=it
                actor =actor.replace('/','|')    
                m_item['actor'] = actor
            if res['alias']:
                alias=res['alias']
                alias = alias.replace(':','') 
                if alias.find('<')!=-1:
                    alias=alias[:alias.find('<')]
                alias =alias.replace('/','|')
                m_item['alias'] = alias
            if res['imdb']:
                imdb=res['imdb']
                if imdb.find('imdb.com')!=-1:
                    r = re.compile(r'http://www.imdb.com/title/(\w+)')
                    m = r.findall(imdb)
                    if m:
                        imdb = m[0]
                m_item['imdb'] = imdb
                #print m_item['imdb']
            #print m_item['actor']
            #return items
            v_item = VideoItem()
            v_item['url'] = seed_url
            v_item['title'] = response.request.meta['title_long']
            v_item['cont_id'] = md5(seed_url).hexdigest()
            v_item['protocol_id'] = self.protocol_id

            mvitem = MediaVideoItem()
            mvitem["media"] = m_item
            mvitem['video'] = [v_item]
            items.append(mvitem)

            return items
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())

