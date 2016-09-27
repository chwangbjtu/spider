# -*- coding:utf-8 -*-
from scrapy.spider import Spider
from scrapy.selector import Selector
from scrapy.http import Request
from scrapy import log
from crawler.common.util import Util
from crawler.items import EpisodeItem, UserItem
import traceback
import re
from datetime import datetime, timedelta

class IfengEntNewestSpider(Spider):
    name        = "ifeng_ent_newest"
    pipelines = ['NewestItemPipeline', 'MysqlStorePipeline']
    spider_id   = "16"
    site_id     = "4"
    allowed_domains = ["www.ifeng.com", "v.ifeng.com", "survey.news.ifeng.com"]
    start_urls = (
        'http://v.ifeng.com/vlist/nav_category/ent_all/update/1/list.shtml',
        )
    url_prefix = 'http://v.ifeng.com'
    url_next   = 'http://v.ifeng.com/vlist/nav_category/ent_all/update/%d/list.shtml'
    url_num    = 'http://survey.news.ifeng.com/getaccumulator_weight.php?format=js&serverid=2&key=%s'
    def _extract_time(self, time):
        if time.startswith(u'\u53d1\u5e03:\u4eca\u5929'): #today u'\u53d1\u5e03:\u4eca\u5929'
            time = time.replace(u'\u53d1\u5e03:\u4eca\u5929', '')
            time = datetime.now().strftime("%Y-%m-%d")+ " " +time.strip() + ":00"
        elif time.startswith(u'\u53d1\u5e03:\u6628\u5929'):
            time = time.replace(u'\u53d1\u5e03:\u6628\u5929', '')
            time = (datetime.now() - timedelta(days = 1)).strftime("%Y-%m-%d")+ " " +time.strip() + ":00"
        elif time.startswith(u'\u53d1\u5e03:\u524d\u5929'):
            time = time.replace(u'\u53d1\u5e03:\u524d\u5929', '')
            time = (datetime.now() - timedelta(days = 2)).strftime("%Y-%m-%d")+ " " +time.strip() + ":00"
        elif time.startswith(u'\u53d1\u5e03:'):
            time = time.replace(u'\u53d1\u5e03:', '')
            time = time.strip()
            if time.endswith(u'\u5206\u949F\u524D'):
                time = time.replace(u'\u5206\u949F\u524D', '')
                time = (datetime.now() - timedelta(minutes = int(time.strip()))).strftime("%Y-%m-%d %H:%M:%S") 
            else:
                time = datetime.now().strftime("%Y-") + time.strip() + ":00"
        return time
        
    def _parse_ent_list(self, response):
        vlist = []
        for sel in response.xpath('//*[@id="list_ent"]/li'):
            link    = sel.xpath('h6/a/@href')
            link    = link.extract()[0] if link else ""
            time    = sel.xpath('p/text()')
            time    = time.extract()[0] if time else ""
            if time:
                time = self._extract_time(time)

            vlist.append({'link': link, 'time':time})
        return vlist
        
    def _next_page(self, response):    
        next_link = None
        try:
            fields = response.request.url.split('/')
            if len(fields) > 2:
                next_number = int(fields[-2]) + 1
                next_link = self.url_next % next_number if next_number <= 30 else None
        except Exception, err:
            next_link = None
        finally:
            return next_link

    def parse_played(self, response):
        items = []
        try:
            log.msg(response.request.url, level=log.INFO)
            body            = response.xpath('//body/p/text()')
            play_num        = body.re('"browse":(\d*)}')[0]
            _item         = response.meta
            
            ep_item = EpisodeItem()
            ep_item['show_id']      = _item['show_id']
            ep_item['title']        = _item['title']
            ep_item['tag']          = _item['tag']
            ep_item['category']     = _item['category']
            ep_item['upload_time']  = _item['upload_time']
            ep_item['spider_id']    = _item['spider_id']
            ep_item['site_id']      = _item['site_id']
            ep_item['url']          = _item['url']
            ep_item['description']  = _item['description']
            ep_item['played']       = int(play_num)
            items.append(ep_item)
        except Exception, err:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
            
    def parse_episode(self, response):
        items = []
        try:
            log.msg(response.request.url, level=log.INFO)
            title       = response.xpath('//head/meta[@property="og:title"]/@content')
            title = title.extract()[0].strip() if title else ""
            category    = response.xpath('//head/meta[@property="og:category"]/@content')
            category    = category.extract()[0].strip() if category else u"\u5a31\u4e50"
            description = response.xpath('//head/meta[@property="og:description"]/@content')
            description = description.extract()[0].strip() if description else ""
            
            upload_time = response.xpath('//div[@class="playerinfo"]/p/text()')
            upload_time = upload_time.re(u'\u53d1\u5e03:(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})') if upload_time else ""
            upload_time = upload_time[0] if upload_time else ""
            upload_time = upload_time if upload_time else response.meta['time']  

            play_num    = response.xpath('//div[@class="playerinfo"]/p/span[@id="numPlay"]/text()')
            play_num    = play_num.re(u'\u64ad\u653e\u6570:(\d+)') if play_num else ""
            request_played = False if play_num else True
            play_num    = play_num[0] if play_num else "0"
            
            tags        = response.xpath('//li[@class="vtags"]/a/text()')
            tags        = tags.extract() if tags else []
            tag = ''
            for a in tags:
                tag = tag + '|' + a if tag else a
            tag = tag if tag else u"\u5a31\u4e50"
            
            video_id    = response.request.url.split("/")[-1]
            video_id    = video_id.split('.')[0]
            
            ep_item = EpisodeItem()
            ep_item['show_id']  = video_id.replace("-", "")
            #ep_item['video_id'] = video_id
            ep_item['title']    = title
            ep_item['tag']      = tag
            ep_item['category'] = category
            ep_item['played']   = int(play_num)
            ep_item['upload_time']  = datetime.strptime(upload_time,'%Y-%m-%d %H:%M:%S')
            ep_item['spider_id']    = self.spider_id
            ep_item['site_id']      = self.site_id
            ep_item['url']          = response.request.url
            ep_item['description']  = description
            
            if request_played:
                items.append(Request(url= self.url_num % video_id, callback=self.parse_played, meta = ep_item) )
            else:
                items.append(ep_item)
        except Exception, err:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
            
    # entry point
    def parse(self, response):
        items = []
        try:
            #log.msg(response.request.url, level=log.INFO)
            vlist = self._parse_ent_list(response)
            items.extend([Request(url=url['link'], callback=self.parse_episode, meta = {'time': url['time']}) for url in vlist])
            next_page = self._next_page(response)
            if next_page:
                items.extend([Request(url= next_page, callback=self.parse)])
        except Exception, err:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
