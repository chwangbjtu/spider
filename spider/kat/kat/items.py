# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class MediaVideoItem(scrapy.Item):
    media = scrapy.Field()
    video = scrapy.Field()


class MediaItem(scrapy.Item):
    cont_id = scrapy.Field()
    title = scrapy.Field()
    site_id = scrapy.Field()
    dou_id = scrapy.Field()
    imdb = scrapy.Field()
    url = scrapy.Field()


class VideoItem(scrapy.Item):
    cont_id = scrapy.Field()
    title = scrapy.Field()
    vnum = scrapy.Field()
    #vtitle = scrapy.Field()
    url = scrapy.Field()
    protocol_id = scrapy.Field()
    mid = scrapy.Field()
    tor_ih = scrapy.Field()

