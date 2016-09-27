# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class DoubanItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class MediaItem(scrapy.Item):
    cont_id = scrapy.Field()
    name = scrapy.Field()
    title = scrapy.Field()
    alias = scrapy.Field()
    director = scrapy.Field()
    writer = scrapy.Field()
    actor = scrapy.Field()
    genre = scrapy.Field()
    district = scrapy.Field()
    lang = scrapy.Field()
    runtime = scrapy.Field() # int
    release_date = scrapy.Field() # date
    #channel_id = scrapy.Field() # int
    score = scrapy.Field() # float
    review = scrapy.Field() # int
    comment = scrapy.Field() # int
    site_id = scrapy.Field() # int
    vcount = scrapy.Field() # int
    latest = scrapy.Field() 
    dou_id = scrapy.Field() # int
    imdb = scrapy.Field()    
    imdb_chief = scrapy.Field()
    poster = scrapy.Field()
    url = scrapy.Field()
    intro = scrapy.Field()

class RecommendItem(scrapy.Item):
    dou_id = scrapy.Field()
    rec_lst = scrapy.Field()


class ReviewItem(scrapy.Item):
    dou_id = scrapy.Field()
    rev_lst = scrapy.Field()


class RevItem(scrapy.Item):
    rev_id = scrapy.Field()
    neck_name = scrapy.Field()


class UserInfoItem(scrapy.Item):
    neck_name = scrapy.Field()
    do = scrapy.Field()
    wish = scrapy.Field()
    collect = scrapy.Field()


class ImdbChiefItem(scrapy.Item):
    imdb = scrapy.Field()
    imdb_chief = scrapy.Field()
