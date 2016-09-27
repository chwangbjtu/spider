# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field

class EpisodeItem(Item):
    show_id = Field()
    video_id = Field()
    owner_show_id = Field()
    title = Field()
    tag = Field()
    category = Field()
    played = Field()
    upload_time = Field()
    spider_id = Field()
    site_id = Field()
    url = Field()
    thumb_url = Field()
    description = Field()
    stash = Field()
    duration = Field()
    priority = Field()
    format_id = Field()
    audit = Field()

    kw_id = Field()
    pg_id = Field()
    cat_id = Field()
    subject_id = Field()

class UserItem(Item):
    owner_id = Field()
    show_id = Field()
    user_name = Field()
    intro = Field()
    played = Field()
    fans = Field()
    vcount = Field() #video count
    spider_id = Field()
    site_id = Field()
    url = Field()
    aka = Field()

