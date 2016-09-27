# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy

class SoftwareItem(scrapy.Item):
    # define the fields for your item here like:
    cont_id = scrapy.Field()
    site_id = scrapy.Field()
    title = scrapy.Field()
    size = scrapy.Field()
    url = scrapy.Field()
    cat_id = scrapy.Field()
    platform_id = scrapy.Field()
    score = scrapy.Field()
    update_time = scrapy.Field()
    download = scrapy.Field()
    src_url = scrapy.Field()
    version = scrapy.Field()
    os_version = scrapy.Field()
    os_bit = scrapy.Field()
    protocol_id = scrapy.Field()

