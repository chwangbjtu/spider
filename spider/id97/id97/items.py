# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class Id97Item(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


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
    director = scrapy.Field()
    actor = scrapy.Field()
    alias = scrapy.Field()


class VideoItem(scrapy.Item):
    cont_id = scrapy.Field()
    title = scrapy.Field()
    url = scrapy.Field()
    protocol_id = scrapy.Field()
    mid = scrapy.Field()
    tor_ih = scrapy.Field()

