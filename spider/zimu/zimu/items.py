# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy

class SubtitleItem(scrapy.Item):
    cont_id = scrapy.Field()
    title = scrapy.Field()
    dou_id = scrapy.Field()
    imdb = scrapy.Field()
    site_id = scrapy.Field()
    url = scrapy.Field()
    
    
