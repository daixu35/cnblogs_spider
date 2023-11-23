# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ArticlespiderItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class CnblogsspiderItem(scrapy.Item):
    news_title = scrapy.Field()
    create_date = scrapy.Field()
    news_body = scrapy.Field()
    news_tags = scrapy.Field()
    praise_num = scrapy.Field()
    view_num = scrapy.Field()
    dislike_num = scrapy.Field()
    comment_num = scrapy.Field()

