# -*- coding:utf-8 -*-
from scrapy.spiders import Spider
from scrapy.utils.project import get_project_settings
from scrapy.http import Request
import logging
import traceback
import json
import re
from baidusoftware.items import SoftwareItem
try:
    from baidusoftware.hades_db.db_mgr import DbManager
except ImportError:
    from hades_db.db_mgr import DbManager
    
class BaiduSoftwareSpider(Spider):
    name = "baidusoftware"
    pipelines = ['MysqlStorePipeline']
    site_code = "baidusoftware"
    mgr = DbManager.instance()
    site_id = str(mgr.get_site_by_code(site_code)["site_id"])
    protocol_id = mgr.get_protocol_map()['http']
    platform_map = mgr.get_platform_map()
    
    def __init__(self, *args, **kwargs):
        super(BaiduSoftwareSpider, self).__init__(*args, **kwargs)
        self._start = [
                        {'url':'http://rj.baidu.com/index.html', 'platform':'pc'},
                        {'url':'http://shouji.baidu.com/software/', 'platform':'mobile'},
                        {'url':'http://shouji.baidu.com/game/', 'platform':'mobile'},
                      ]
                      
        self._pc_host = "http://rj.baidu.com"
        self._mobile_host = "http://shouji.baidu.com"
        max_update_page = get_project_settings().get('MAX_UPDATE_PAGE')
        self._limit = max_update_page if max_update_page > 0 else None
        self._pc_os_type_map = {'1':'Win2000',
                                '10':'WinXP',
                                '100':'Win2003',
                                '1000':'Vista',
                                '10000':'Win7',
                                '100000':'Win8',
                                '10000000':'Win10',
                                '1000000':'Mac'}
                                
        self._pc_os_bit_map = {'1':'32', '10':'64'}
                      
    def start_requests(self):
        items = []
        try:
            for s in self._start:
                items.append(Request(url=s['url'], callback=getattr(self, "parse_list_" + s['platform'])))
        
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
            
        finally:
            return items
            
    def parse_list_pc(self, response):
        items = []
        try:
            meta = response.request.meta
            config_sel = response.xpath('//script[@type="text/javascript"]').re('.*var configs = (.*);')
            if config_sel:
                configs = json.loads(config_sel[0].strip())
                lists = configs['data']['category']['list']
                for list in lists:
                    catalog = list['class_name']
                    url = self._pc_host + '/soft/lists/%s' % (list['class_id'])
                    cat_id = self.mgr.get_cat_id(1, catalog)['cat_id']
                    meta['cat_id'] = cat_id
                    items.append(Request(url, callback=self.parse_pc_catalog, meta=meta))
                        
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
    
        finally:
            return items
            
    def parse_list_mobile(self, response):
        items = []
        try:
            meta = response.request.meta
            catalog_sels = response.xpath('//ul[@class="cate"]/li/div/a')
            if catalog_sels:
                for catalog_sel in catalog_sels:
                    catalog = catalog_sel.xpath('./text()').extract()
                    if catalog:
                        catalog = catalog[0].encode("UTF-8")
                        cat_id = self.mgr.get_cat_id(2, catalog)['cat_id']
                        meta['cat_id'] = cat_id
                        
                    url = catalog_sel.xpath('./@href').extract()
                    if url:
                        url = self._mobile_host + url[0]
                        items.append(Request(url, callback=self.parse_mobile_catalog, meta=meta))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
    
        finally:
            return items
            
    def parse_mobile_catalog(self, response):
        items = []
        try:
            meta = response.request.meta
            catalog_url = self.get_catalog_url(response.request.url)
            sub_catalog_sel = response.xpath(u'//div[@class="sec-app clearfix"]/ul/li/a[text()!="全部"]/@href').extract()
            for sub_catalog in sub_catalog_sel:
                sub_catalog_url = catalog_url + sub_catalog
                items.append(Request(sub_catalog_url, callback=self.parse_mobile_detail, meta=meta))
                
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
    
        finally:
            return items
            
    def parse_mobile_detail(self, response):
        items = []
        try:
            meta = response.request.meta
            catalog_url = self.get_catalog_url(response.request.url)
            app_sels = response.xpath('//div[@class="list-bd app-bd"]/ul/li')
            for app_sel in app_sels:
                software_item = SoftwareItem()
                software_item['site_id'] = self.site_id
                software_item['cat_id'] = meta['cat_id']
                software_item['platform_id'] = self.platform_map['android']
                
                title_sel = app_sel.xpath('.//div[@class="app-meta"]/p[@class="name"]/text()').extract()
                if title_sel:
                    software_item['title'] = title_sel[0].encode("UTF-8")
                    
                size_sel = app_sel.xpath('.//div[@class="app-meta"]/p[@class="down-size"]/span[@class="size"]/text()').extract()
                if size_sel:
                    software_item['size'] = size_sel[0]
                    
                download_times_sel = app_sel.xpath('.//div[@class="app-meta"]/p[@class="down-size"]/span[@class="down"]/text()').extract()
                if download_times_sel:
                    software_item['download'] = self.normalize_played(download_times_sel[0])
                    
                url_sel = app_sel.xpath('.//div[@class="app-meta"]/p[@class="down-btn"]/span/@data_url').extract()
                if url_sel:
                    software_item['url'] = url_sel[0]
                    
                src_url_sel = app_sel.xpath('./div/a/@href').extract()
                if src_url_sel:
                    software_item['src_url'] = self._mobile_host + src_url_sel[0]
                    
                score_sel = app_sel.xpath('.//div[@class="app-meta"]//span[@class="star"]/span/@style').extract()
                if score_sel:
                    software_item['score'] = self.get_score(score_sel[0])
                    
                version_sel = app_sel.xpath('.//div[@class="app-meta"]/p[@class="down-btn"]/span/@data_versionname').extract()
                if version_sel:
                    software_item['version'] = version_sel[0]
                    
                cont_id_sel = app_sel.xpath('.//div[@class="app-meta"]/p[@class="down-btn"]/span/@data-tj').extract()
                if cont_id_sel:
                    cont_id = cont_id_sel[0].encode("UTF-8").split('_')
                    software_item['cont_id'] = cont_id[1] + '_' + cont_id[2]
                    
                software_item['protocol_id'] = self.protocol_id   
                items.append(software_item)
                logging.log(logging.INFO, "insert android item into db, cont_id:%s, title:%s" % (software_item['cont_id'], software_item['title']))
                
            next_page_sel = response.xpath('//div[@class="pager"]/ul/li[@class="next"]/a/@href').extract()
            if next_page_sel:
                if self._limit and self.get_next_page_num(next_page_sel[0]) > self._limit:
                    return items
                next_page = catalog_url + next_page_sel[0]
                items.append(Request(next_page, callback=self.parse_mobile_detail, meta=meta))
        
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
    
        finally:
            return items
            
    def parse_pc_catalog(self, response):
        items = []
        try:
            meta = response.request.meta
            config_sel = response.xpath('//script[@type="text/javascript"]').re('.*var configs = (.*);')
            if config_sel:
                configs = json.loads(config_sel[0].strip())
                lists = configs['data']['softList']['list']
                for list in lists:
                    detail_info = {}
                    detail_info['cont_id'] = list['soft_id']
                    detail_info['title'] = list['soft_name']
                    detail_info['url'] = list['url']
                    detail_info['size'] = str(list['file_size']) + 'M'
                    detail_info['score'] = list['point']
                    detail_info['update_time'] = list['update_time']
                    
                    meta['detail_info'] = detail_info
                    detail_url = self.get_detail_url(list['soft_id'])
                    items.append(Request(detail_url, callback=self.parse_pc_detail, meta=meta))
                    
                pages = configs['data']['page']
                current = pages['currP']
                total = pages['totalP']
                if current != total:
                    if self._limit and current > self._limit:
                        return items
                    next_page = self._pc_host + pages['baseURL'] + str(current+1)
                    items.append(Request(next_page, callback=self.parse_pc_catalog, meta=meta))
                
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
    
        finally:
            return items
            
    def parse_pc_detail(self, response):
        items = []
        try:
            meta = response.request.meta
            detail_info = meta['detail_info']
            config_sel = response.xpath('//script[@type="text/javascript"]/text()').extract()
            for sel in config_sel:
                if sel:
                    r = re.compile(r'.*var configs = (.*);')
                    m = r.search(sel)
                    if m:
                        configs = json.loads(m.group(1))
                        download_times = configs['data']['softInfo']['download_num']
                        version = configs['data']['softInfo']['version']
                        baidu_type = configs['data']['softInfo']['os_type'].keys()
                        os_version = '|'.join([self._pc_os_type_map[i] for i in baidu_type])
                        baidu_bit = configs['data']['softInfo']['os_bit'].keys()
                        os_bit = '|'.join([self._pc_os_bit_map[i] for i in baidu_bit])
                        
                        break
            # config_sel = response.xpath('//script[@type="text/javascript"]').re('.*var configs = (.*);')
            # if config_sel:
                # configs = json.loads(config_sel[0].strip())
                # download_times = configs['data']['softInfo']['download_num']
            software_item = SoftwareItem()
            software_item['site_id'] = self.site_id
            software_item['cat_id'] = meta['cat_id']
            software_item['cont_id'] = detail_info['cont_id']
            software_item['title'] = detail_info['title']
            software_item['url'] = detail_info['url']
            software_item['size'] = detail_info['size']
            software_item['score'] = detail_info['score']
            software_item['update_time'] = detail_info['update_time']
            software_item['download'] = download_times if download_times else 0
            software_item['version'] = version if version else ''
            software_item['os_version'] = os_version if os_version else ''
            platform_key = 'macos' if software_item['os_version'] == 'Mac' else 'windows'
            software_item['platform_id'] = self.platform_map[platform_key]
            software_item['os_bit'] = os_bit if os_bit else ''
            software_item['protocol_id'] = self.protocol_id
            software_item['src_url'] = response.request.url
            items.append(software_item)
            logging.log(logging.INFO, "insert %s item into db, cont_id:%s, title:%s" % (platform_key, software_item['cont_id'], software_item['title']))
        except Exception as e:
            logging.log(logging.ERROR, traceback.format_exc())
    
        finally:
            return items
            
    def get_detail_url(self, cat_id):
        url = "http://rj.baidu.com/soft/detail/%s.html" % (cat_id)
        return url
        
    def get_score(self, star):
        score = 0
        r = re.compile(r'width:(\d+)%')
        m = r.match(star)
        if m:
            score = float(m.group(1)) / 10
        return score 
        
    def get_next_page_num(self, page):
        num = 0
        r = re.compile(r'list_(\d+).html')
        m = r.match(page)
        if m:
            num = int(m.group(1))
        return num 
        
    def normalize_played(self, vp):
        vp_units = {u'万': 10000, u'亿': 100000000, '万': 10000, '亿': 100000000}
        if vp:
            r = re.compile(ur'([\d|,|.]*)(.*)下载')
            m = r.match(vp)
            if m:
                (num, u) = m.groups()
                num = num.replace(',', '')
                if u and u in vp_units:
                    return str(int(float(num) * vp_units[u]))
                return str(num)
        else:
            return str(0)
            
    def get_catalog_url(self, url):
        catalog_url = url
        r = re.compile(r'(.*)list_\d.html')
        m = r.match(url)
        if m:
            catalog_url = m.group(1)
        return catalog_url
            