# -*- coding:utf-8 -*- 
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors import LinkExtractor
from scrapy import log
from crawler.common.util import Util
from crawler.items import EpisodeItem

class SohuFunSpreadSpider(CrawlSpider):
    name = "sohu_fun_spread"
    pipelines = ['MysqlStorePipeline']
    spider_id = "17"
    site_id = "3"
    allowed_domains = ["tv.sohu.com"]
    start_urls = (
        'http://tv.sohu.com/ugc/fun/',
        'http://tv.sohu.com/ugc/fun/dv/',
        'http://tv.sohu.com/ugc/fun/smile/',
        'http://tv.sohu.com/ugc/fun/lovely/',
        'http://my.tv.sohu.com/wm/ch/p133103.html',
        )
    rules = (Rule(LinkExtractor(allow=r'.*my.tv.sohu.com/.*html$'), callback='parse_media', follow=False),)
    
    def parse_media(self, response, **kwargs):
        items = []
        try:
            title = response.xpath('//div[@id="crumbsBar"]/div/div[@class="left"]/h2/text()').extract()
            tag = response.xpath('//meta[@name="keywords"]/@content').extract()
            #show_id = Util.get_sohu_showid(response.request.url)
            thumb = response.xpath('//script').re(',sCover: \'(.*)\'')
            upload = response.xpath('//script').re(',uploadTime: \'(.*)\'')
            description = response.xpath('//p[@class="rel cfix"]/@title').extract()
            played = response.xpath('//span[@class="vbtn vbtn-play"]/em/i/text()').extract()
            print played, upload
            video_id = response.xpath('//script').re('vid = \'(\d+)\'')
            
            ep_item = EpisodeItem()
            if video_id:
                ep_item['video_id'] = video_id[0]
                ep_item['show_id'] = video_id[0]
                if title:
                    ep_item['title'] = title[0]
                if tag:
                    ep_item['tag'] = tag[0].strip().replace(',', '|')
                if upload:
                    ep_item['upload_time'] = upload[0] + ":00"
                if description:
                    ep_item['description'] = description[0].strip()
                if thumb:
                    ep_item['thumb_url'] = thumb[0]
                if played:
                    ep_item['played'] = Util.normalize_played(played[0])
               
                ep_item['category'] = u"搞笑"               
                ep_item['spider_id'] = self.spider_id
                ep_item['site_id'] = self.site_id
                ep_item['url'] = response.request.url

                items.append(ep_item)
                log.msg("spider success, title:%s" % (ep_item['title']), level=log.INFO)
        except Exception as e:
            log.msg(traceback.format_exc(), level=log.ERROR)
        finally:
            return items
    
    
    
    
    