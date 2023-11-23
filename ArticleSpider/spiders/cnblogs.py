import re
import json

import scrapy
import requests
import undetected_chromedriver as uc
from scrapy.http import Request
from urllib import parse

from ArticleSpider.items import CnblogsspiderItem


class CnblogsSpider(scrapy.Spider):
    name = "cnblogs"
    allowed_domains = ["news.cnblogs.com"]
    start_urls = ["https://news.cnblogs.com"]
    custom_settings = {
        "COOKIES_ENABLE": True
    }

    def start_requests(self):
        browser = uc.Chrome()
        browser.get("https://account.cnblogs.com/signin")  # 自己电脑的chrome版本不能太旧
        input("请回车继续：")
        cookies = browser.get_cookies()
        cookies_dict = {}
        for cookie in cookies:
            cookies_dict[cookie["name"]] = cookie["value"]
        for url in self.start_urls:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            }
            yield Request(url, headers=headers, cookies=cookies, callback=self.parse)

    def parse(self, response):
        """
        解析新闻的列表页面，得到每条新闻的详情url，得到下一页新闻列表的url
        :param response: 新闻列表页请求成功返回页面参数
        :return: yield出去获得的url，交给相应的函数解析
        """
        # 解析得到每条新闻的详情页
        post_nodes = response.xpath("//div[@id='news_list']//div[@class='news_block']")[:1]
        for post_node in post_nodes:
            post_url = post_node.xpath(".//h2/a/@href").extract_first()
            yield Request(url=parse.urljoin(response.url, post_url), callback=self.parse_detail)

        # 解析得到下一页新闻列表页的url
        # next_url_node = response.xpath("//div[@class='pager']//a[contains(text(), 'Next >')]")
        # if next_url_node:
        #     next_url = next_url_node.xpath("./@href").extract_first("")
        #     yield Request(url=parse.urljoin(response.url, next_url), callback=self.parse)

    def parse_detail(self, response):
        """
        获取新闻详情页的信息，包括标题，创建日期，主体，标签，点赞数，浏览数，讨厌数，评论数
        :param response: 新闻详情页请求成功返回参数
        :return:
        """
        match_re = re.match(".*?(\d+)", response.url)
        if match_re:
            article_item = CnblogsspiderItem()
            news_main = response.xpath("//div[@id='news_main']")
            news_title = news_main.xpath("./div[@id='news_title']/a/text()").extract_first("")
            create_date = news_main.xpath("./div[@id='news_info']//span[@class='time']/text()").extract_first("")
            news_body = news_main.xpath("./div[@id='news_content']").extract_first("")
            news_tags = ",".join(news_main.xpath(".//div[@class='news_tags']//a[@class='catalink']/text()").extract())

            # 分析得到点赞数这些数据存在于ajax请求中，解析得到该ajax请求的url是什么
            post_id = match_re.group(1)
            num_url = parse.urljoin(response.url, "/NewsAjax/GetAjaxNewsInfo?contentId={}".format(post_id))
            # 这一部分使用了requests库，是同步库，在scrapy异步性很强的框架中尽量少用，否则之后的请求容易被block住
            # html = requests.get(url=num_url)
            # j_data = json.loads(html.text)
            # praise_num = j_data["DiggCount"]
            # view_num = j_data["TotalView"]
            # dislike_num = j_data["BuryCount"]
            # comment_num = j_data["CommentCount"]

            # 针对requests的改进，直接得到这个url然后yield出去，交给scrapy引擎下载，再设置回调函数，并同时将item数据传递到回调函数
            article_item["news_title"] = news_title
            article_item["create_date"] = create_date
            article_item["news_body"] = news_body
            article_item["news_tags"] = news_tags

            meta = {"article_item": article_item}
            yield Request(url=num_url, meta=meta, callback=self.parse_num)

    def parse_num(self, response):
        """
        parse_detail中的一个回调函数，由于点赞数，浏览数，讨厌数，评论数由ajax动态加载，获取其html抓取数据
        :param response: 点赞数，浏览数，讨厌数，评论数由ajax请求html返回结果
        :return:
        """
        article_item = response.meta["article_item"]
        j_data = json.loads(response.text)
        praise_num = j_data["DiggCount"]
        view_num = j_data["TotalView"]
        dislike_num = j_data["BuryCount"]
        comment_num = j_data["CommentCount"]

        article_item["praise_num"] = praise_num
        article_item["view_num"] = view_num
        article_item["dislike_num"] = dislike_num
        article_item["comment_num"] = comment_num
        yield article_item
