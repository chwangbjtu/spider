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
    alias = scrapy.Field()
    director = scrapy.Field()
    writer = scrapy.Field()
    actor = scrapy.Field()
    genre = scrapy.Field()
    district = scrapy.Field()
    lang = scrapy.Field()
    tag = scrapy.Field()
    runtime = scrapy.Field()
    release_date = scrapy.Field()
    channel_id = scrapy.Field()
    score = scrapy.Field()
    site_id = scrapy.Field()
    vcount = scrapy.Field()
    latest = scrapy.Field()
    dou_id = scrapy.Field()
    imdb = scrapy.Field()
    poster = scrapy.Field()
    url = scrapy.Field()
    intro = scrapy.Field()

class VideoItem(scrapy.Item):
    cont_id = scrapy.Field()
    title = scrapy.Field()
    vnum = scrapy.Field()
    url = scrapy.Field()
    protocol_id = scrapy.Field()
    mid = scrapy.Field()
    
