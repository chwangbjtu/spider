# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy

class MediaVideoItem(scrapy.Item):
    media = scrapy.Field()
    video = scrapy.Field()
    ext_video = scrapy.Field()
    review = scrapy.Field()
    sid = scrapy.Field()
    untrack_id = scrapy.Field()
    mid = scrapy.Field()

class MediaItem(scrapy.Item):
    ext_id = scrapy.Field() #media id in external site; should be unique
    info_id = scrapy.Field()
    cont_id = scrapy.Field()
    title = scrapy.Field()
    director = scrapy.Field()
    writer = scrapy.Field()
    actor = scrapy.Field()
    type = scrapy.Field()
    district = scrapy.Field()
    release_date = scrapy.Field()
    duration = scrapy.Field()
    channel_id = scrapy.Field()
    score = scrapy.Field()
    site_id = scrapy.Field()
    vcount = scrapy.Field()
    latest = scrapy.Field()
    paid = scrapy.Field()
    url = scrapy.Field()
    intro = scrapy.Field()
    poster_url = scrapy.Field()

class VideoItem(scrapy.Item):
    ext_id = scrapy.Field() #video id in external site; should be unique
    media_ext_id = scrapy.Field()   #video's parent id; that is media id in external site
    cont_id = scrapy.Field()
    title = scrapy.Field()
    vnum = scrapy.Field()
    site_id = scrapy.Field()
    intro = scrapy.Field()
    url = scrapy.Field()
    os_id = scrapy.Field()
    format_id = scrapy.Field()
    thumb_url = scrapy.Field()

class ExtVideoItem(scrapy.Item):
    media_ext_id = scrapy.Field()   #parent ext_id
    site_id = scrapy.Field()    #parent site
    urls = scrapy.Field()   #all external videos in one list
    channel_id = scrapy.Field()

class ReviewItem(scrapy.Item):
    media_ext_id = scrapy.Field()   #parent ext_id
    urls = scrapy.Field()   #all review urls in one list
    
class ImdbMediaVideoItem(scrapy.Item):
    media = scrapy.Field()
    video = scrapy.Field()
    
class ImdbMediaItem(scrapy.Item):
    imdb = scrapy.Field() 
    pimdb = scrapy.Field()
    snum = scrapy.Field() 
    title = scrapy.Field() 
    director = scrapy.Field() 
    actor = scrapy.Field() 

class ImdbVideoItem(scrapy.Item):
    imdb = scrapy.Field() 
    pimdb = scrapy.Field() 
    enum = scrapy.Field() 
    title = scrapy.Field() 
    
