#-*- coding: utf-8 -*-
import traceback
import json
import httplib
import urllib2
import cookielib
import random
import logging
 
class HTTPDownload(object):

    def __init__(self, with_cookie=False):
        self._opener = None
        self._cookies = None
        if with_cookie:
            self._cookies = cookielib.LWPCookieJar()
            handlers = [
                    #urllib2.HTTPHandler(debuglevel=1),
                    #urllib2.HTTPSHandler(debuglevel=1),
                    urllib2.HTTPCookieProcessor(self._cookies)
            ]
            self._opener = urllib2.build_opener(*handlers)
        else:
            self._opener = urllib2.build_opener()

    def make_cookie(self, name, value):
            return cookielib.Cookie(
                version=0,
                name=name,
                value=value,
                port=None,
                port_specified=False,
                domain="",
                domain_specified=True,
                domain_initial_dot=False,
                path="/",
                path_specified=True,
                secure=False,
                expires=None,
                discard=False,
                comment=None,
                comment_url=None,
                rest=None
            )

    def get_data(self, url, ua=None, cookies=None, timeout=1):
        data = ''
        try:
            if cookies:
                for c in cookies:
                    self._cookies.set_cookie(self.make_cookie(c['name'], c['value']))
            req = urllib2.Request(url)
            if ua:
                req.add_header('User-Agent', ua)
            resp =  self._opener.open(req, timeout=timeout)
            chunk_size = 100 * 1024
            while True:
                chunk = None
                try:
                    chunk = resp.read(chunk_size)
                except httplib.IncompleteRead as e:
                    chunk = e.partial

                if not chunk:
                    break
                data += chunk
            resp.close()
        except HTTPError as e:
            logging.log(logging.ERROR, 'Error request [%s], code [%s]' % (url, e.code))
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return data

    def get_cookie(self):
        return ";".join(['%s=%s'%(c.name, c.value) for c in self._cookies])

    def post_data(self, url, body, ua=None, cookies=None, timeout=3):
        data = ''
        try:
            if cookies:
                for c in cookies:
                    self._cookies.set_cookie(self.make_cookie(c['name'], c['value']))
            req = urllib2.Request(url)
            if ua:
                req.add_header('User-Agent', ua)
            resp =  self._opener.open(req, body, timeout=timeout)
            chunk_size = 100 * 1024
            while True:
                chunk = None
                try:
                    chunk = resp.read(chunk_size)
                except httplib.IncompleteRead as e:
                    chunk = e.partial

                if not chunk:
                    break
                data += chunk
            resp.close()
        except HTTPError as e:
            logging.log(logging.ERROR, 'Error request [%s], code [%s]' % (url, e.code))
        except Exception, e:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            return data

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    hc = HTTPDownload(with_cookie=True)
    hc.get_data('http://www.baidu.com')
    c = hc.get_cookie() 
    logging.log(logging.INFO, c)
