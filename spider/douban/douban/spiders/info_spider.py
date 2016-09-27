# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.http import Request
from douban.items import UserInfoItem
import traceback
import logging
try:
    #from douban.hades_db.db_mgr import DbManager
    from douban.hades_db.mongo_mgr import MongoMgr
except ImportError:
    #from hades_db.db_mgr import DbManager
    from hades_db.mongo_mgr import MongoMgr

class UserInfoSpider(BaseSpider):

  name = "userinfo"
  allowed_domains = ["douban.com"]
  inst = MongoMgr.instance()

  def __init__(self, category=None, *args, **kwargs):
        super(UserInfoSpider, self).__init__(*args, **kwargs)
       # userIdSet = self.inst.get_alone_user_neck_name()
       # for sel in userIdSet:
       #     self.start_urls.append("https://www.douban.com/people/"+sel+"/")
     
  def start_requests(self):
        try:
           userIdSet = self.inst.get_alone_user_neck_name()
           for sel in userIdSet:
                urlStr = []
                urlStr.append("https://movie.douban.com/people/"+sel+"/do?start=0&sort=time&rating=all&filter=all&mode=list")
                urlStr.append("https://movie.douban.com/people/"+sel+"/wish?start=0&sort=time&rating=all&filter=all&mode=list")
                item = UserInfoItem()
                item['neck_name'] = sel
                item['do'] = []
                item['wish'] = []
                item['collect'] = []
                yield Request("https://movie.douban.com/people/"+sel+"/collect?start=0&sort=time&rating=all&filter=all&mode=list", meta={"item":item,"urlStr":urlStr}, callback=self.parse)
        except Exception, e:
             logging.log(logging.ERROR, traceback.format_exc()) 
  def parse(self, response):
        
        item = response.meta['item']
        urlStr = response.meta['urlStr']
        if('avg' in response.meta.keys()):
            avg = response.meta['avg']
            number = response.meta['number']
            counter = response.meta['counter']
            sub = response.url.split("?")[-2].split("/")[-1]
            for sel in response.xpath('//div[@class="item-show"]/div/a'):
                link = "".join(sel.xpath('@href').extract())
                if(sub=="collect"):
                    item['collect'].append(link.split("/")[-2])
                elif(sub=="do"):
                    item['do'].append(link.split("/")[-2])
                else:
                    item['wish'].append(link.split("/")[-2])
            if(int(number)<int(counter)):
                return Request(response.url.split("?")[-2]+"?start="+str(int(avg)*int(number))+"&sort=time&rating=all&filter=all&mode=list",meta={'item':item,"urlStr":urlStr,'avg':avg,'number':int(number)+1,"counter":counter},callback=self.parse)
            else:
                if(len(urlStr)==0):
                    return item
                else:
                    ul = urlStr[0]
                    urlStr.remove(ul)
                    return Request(ul,meta={'item':item,'urlStr':urlStr},callback=self.parse)
        else:
            sub = response.url.split("?")[0].split("/")[-1]
            num = "".join(response.xpath('//div[@class="mode"]/span/text()').extract())
            total = int(num.split("/")[1].replace(" ",""))
            avg =  int(num.split("/")[0].split("-")[1].replace(" ",""))
            for sel in response.xpath('//div[@class="item-show"]/div/a'):
                link = "".join(sel.xpath('@href').extract())
                if(sub=="collect"):
                    item['collect'].append(link.split("/")[-2])
                elif(sub=="do"):
                    item['do'].append(link.split("/")[-2])
                else:
                    item['wish'].append(link.split("/")[-2])
            if(avg<total):
                counter = (total+avg-1)/avg
                number = 1
                return Request(response.url.split("?")[0]+"?start="+str(avg*number)+"&sort=time&rating=all&filter=all&mode=list",meta={'item':item,'avg':avg,'number':number+1,"counter":counter,"urlStr":urlStr},callback=self.parse)
            else:
                if(len(urlStr)==0):
                    return item
                else:
                    ul = urlStr[0]
                    urlStr.remove(ul)
                    return Request(ul,meta={'item':item,'urlStr':urlStr},callback=self.parse)

