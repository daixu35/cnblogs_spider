# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface

import codecs
import json

import MySQLdb
from itemadapter import ItemAdapter
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exporters import JsonItemExporter
from twisted.enterprise import adbapi


# 1.process_item()方法必须是这个名字，在此函数中完成对数据的导出入库，必须return item
# 2.spider_closed()在爬虫关闭时调用，记得在此关闭打开的文件，数据库连接等资源
# 3.__init__()方法在爬虫启动时调用，用于初始化各种连接
class ArticlespiderPipeline:
    def process_item(self, item, spider):
        return item


# 使用twisted异步网络框架的方法进行数据的异步入库，保证scrapy的并发特性，内部实际维护了一个数据库的连接池
class ArticleTwistedMysqlSave(object):
    @classmethod  # 类方法from_settings也是scrapy规定的写法，必须这样命名，scrapy框架会自动找到这个方法注入设置
    def from_settings(cls, settings):
        db_params = {
            "host": settings["MYSQL_HOST"],
            "db": settings["MYSQL_DBNAME"],
            "user": settings["MYSQL_USER"],
            "passwd": settings["MYSQL_PASSWORD"],
            "charset": "utf-8",
            "cursorclass": MySQLdb.cursors.DictCursor,
            "use_unicode": True
        }
        dbpool = adbapi.ConnectionPool("MySQLdb", **db_params)
        return cls(dbpool)

    def __init__(self, dbpool):
        self.dbpool = dbpool

    # 使用runInteraction()函数，它的第一个参数是一个函数对象，就是我们执行插入数据的mysql函数，内部会调用连接池中的一个
    # 数据库连接开辟一个新的子线程处理，这里得小心，如果这个函数中可能使用到全局变量等的时候，要注意线程通信和同步，与它十
    # 分相似的是runWithConnection()函数，它也是一样的声明，但是它当它运行时，是在主线程中运行，而不会开新的子线程，它是
    # 线程安全的。
    def process_item(self, item, spider):
        query = self.dbpool.runInteraction(self.__do_insert, item)
        query.addErrback(self.__handle_error)

    def __do_insert(self, cursor, item):
        insert_sql = ("INSERT INTO jobbole_article(title, url, create_date, fav_nums) VALUES (%s, %s, %s, %s) "
                      "ON DUPLICATE KEY UPDATE (create_date, fav_num)")
        cursor.excute(insert_sql, (item.get("title", ""), item["url"], item["create_date"], item["fav_nums"]))

    def __handle_error(self, failure, item, spider):
        print(failure)

# 同步方式数据入库Mysql
class ArticleMysqlSave(object):
    def __init__(self):
        self.conn = MySQLdb.connect("127.0.0.1", "root", "123456", "article_spider",
                                    charset="utf-8", use_unicode=True)
        self.cur = self.conn.cursor()

    def process_item(self, item, spider):
        insert_sql = ("INSERT INTO jobbole_article(title, url, create_date, fav_nums) VALUES (%s, %s, %s, %s) "
                      "ON DUPLICATE KEY UPDATE (create_date, fav_num)")
        self.cur.execute(insert_sql, (item.get("title", ""), item["url"], item["create_date"], item["fav_nums"]))
        self.conn.commit()
        return item

    def spider_closed(self, spider):
        self.cur.close()
        self.conn.close()


# 将抓取到的字段保存进本地文件
class ArticleWithJsonSave(object):
    def __init__(self):
        self.file = codecs.open("data.json", "a", encoding="utf-8")

    def process_item(self, item, spider):
        lines = json.dumps(dict(item), ensure_ascii=False) + "\n"
        self.file.write(lines)
        return item

    def spider_closed(self, spider):
        self.file.close()


# 使用scrapy内置的exporter组件导出数据，这个例子只是json的，其他csv之类的都大同小异，具体看文档
class ArticleExporterWithJson(object):
    def __init__(self):
        self.file = open("data.json", "w")
        self.exporter = JsonItemExporter(self.file, encodings="utf-8", ensurascii=False)
        self.exporter.start_exporting()

    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item

    def spider_closed(self, spider):
        self.exporter.finish_exporting()
        self.file.close()


# 1.关于图片处理的pipline，需要对图片的保存路径做保存，如果需要对图片做处理也在此
# 2.The FilesPipeline.item_completed() method called when all file requests for a single item have completed
#   (either finished downloading, or failed for some reason).图片下载完成后最后调用这个FilesPipeline.item_completed()
#   方法，所以需要对图片需要有什么后续处理在这做
class ArticleImagesPipline(ImagesPipeline):
    def item_completed(self, results, item, info):
        if "image_url" in item:
            image_path = []
            for st, value in results:
                image_path.append(value["path"])
            item["image_path"] = image_path

        return item

