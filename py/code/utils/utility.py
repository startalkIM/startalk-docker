#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'
import re
import json
import time
from conf.sharemsg_params_define import *

class Utility:
    def __init__(self):
        self.MESSAGE_TYPE = {
            'ERROR': self.no_type_error,
            'ELSE': self.handle_else_msg,
            1: self.parse_im_obj,
            2: self.parse_im_voice,
            3: self.parse_im_obj,
            5: self.parse_im_file,
            12: self.parse_im_obj,
            32: self.parse_im_video,
            16: self.parse_im_location,
            30: self.parse_im_obj,
            666: self.parse_im_666card
        }
        self.time_div = '<div style="text-align:center"><span class="time_container">{timestamp}</span></div>'
        self.rightd_div = '<div class="rightd"><div class="main"><div class="speech right">{content}</div></div><div class="rightimg">{name}</div></div>'
        self.lefttd_div = '<div class="leftd"><div class="leftimg">{name}</div><div class="main"><div class="speech left">{content}</div></div></div>'

    def handle_else_msg(self):
        return CANT_SHARE_MSG

    def no_type_error(self):
        raise ValueError

    def handle_sharemsg_timeinterval(self, msg):
        """
        如果时间戳是13位将转换为10位 所以最好
        :param msg:
        :return:
        """
        if not isinstance(msg, dict):
            return msg
        timestamp = 0
        for item in msg:
            item_time = item.get('s', 0)
            if str(item_time) == 13:
                item_time = int(str(item_time)[:-3])
            if item_time - timestamp > MAX_TIME_INVAL:
                _formed_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item_time))
                if 'html' in item.keys():
                    item['time_html'] += self.time_div.format(timestamp=_formed_time)
                else:
                    item['time_html'] = self.time_div.format(timestamp=_formed_time)
                timestamp = item.get('s') if item.get('s') else timestamp
        return msg

    def handle_sharemsg(self, msg):
        """
        msg 是每一条消息
        :param msg:
        :return:
        """
        if not isinstance(msg, dict):
            return msg
        _keys = msg.keys()
        if 'n' not in _keys or 'b' not in _keys or 's' not in _keys or 'd' not in _keys:
            return msg

        result = self.MESSAGE_TYPE[msg.get('t', 'ELSE')](msg.get('b', 'ELSE'))

        return result

    def handle_sharemsg_speaker(self, msg):
        """
        msg 是每一条消息
        :param msg:
        :return:
        """
        if not isinstance(msg, dict):
            return msg
        if msg.get('d') == 1:
            return self.rightd_div
        else:
            return self.lefttd_div

    def gen_url(self, url):
        global FILE_URL
        if 'https://' not in url and 'http://' not in url:
            if not FILE_URL.endswith('/'):
                FILE_URL += '/'
            return FILE_URL + url
        return url

    def parse_im_obj(self, body):
        _pattern = re.compile(r'(\[obj type="([\w]+)" value="([\S]+)"([\w|=|\s|.]+)?\])')
        arr = _pattern.findall(body)
        # for x in range(len(arr)):
        x = ''
        if not len(arr):
            return body
        for item in arr:
            if len(item) != 4:
                break  # TODO 返回个啥
            x = list(map(lambda _: ' ' if not _ else _, item))  # 防止空引起IndexError
            all_obj = x[0]
            type = x[1]
            value = x[2]
            if type == 'image':
                body = body.replace(all_obj, '<img src="' + self.gen_url(value) + '" />')
            elif type == 'url':
                body = body.replace(all_obj, '<a href="' + value + '">' + value + '</a>')
            elif type == 'emoticon':
                emo_type = x[3]
                emo_1 = emo_type.split(' ')
                emo = emo_1[1].split('=')
                value_a = value.split('[')
                value_b = value_a[1].split(']')
                body = body.replace(all_obj, '<img src="{file_url}/file/v2/emo/d/e/'.format(file_url=FILE_URL) + emo[1] + '/' + value_b[
                    0] + '/org" />')
        return body

    def parse_im_file(self, body):
        try:
            _body = json.loads(body)
        except Exception as e:
            print(e)
            return body
        body = '<a href="' + self.gen_url(_body.get('HttpUrl')) + '">下载文件:' + _body.get(
            'FileName') + ',文件大小:' + _body.get('FileSize') + '</a>'
        return body

    def parse_im_voice(self, body):
        try:
            _body = json.loads(body)
        except Exception as e:
            print(e)
            return body
        body = '<a href="https://qt+qunar+com/' + _body['HttpUrl'] + '">语音:' + _body['Secondes'] + '秒,点击下载</a>'
        return body


    def parse_im_video(self, body):
        try:
            _body = json.loads(body)
        except Exception as e:
            print(e)
            return body
        body = '点击图片下载视频:' + _body['FileSize'] + '时长:' + _body['Duration'] + '<br><a href="' + self.gen_url(
            _body['FileUrl']) + '"><img src="' + self.gen_url(_body['ThumbUrl']) + '" /></a>'
        return body

    def parse_im_location(self, body):
        try:
            _body = json.loads(body)
        except Exception as e:
            print(e)
            return body
        body = '点击图片查看位置:' + _body['adress'] + '<br><a href="http://api.map.baidu.com/marker?location=' + _body[
            'latitude'] + ',' + _body['longitude'] + '&title=我的位置&content=' + _body[
                   'adress'] + '&output=html"><img src="' + self.gen_url(_body['fileUrl']) + '" /></a>'
        return body

    def parse_im_666card(self, body):
        try:
            _body = json.loads(body)
        except Exception as e:
            print(e)
            return body
        desc = '点击查看全文' if not _body['desc'] else _body['desc']
        img = self.gen_url(_body['img']) if 'img' in body else 'default.png'
        body = '<a href="' + _body[
            'linkurl'] + '"><div class="g-flexbox"><div class="extleft">' + '<img src="' + img + '" alt="../{{default.png}}"/></div><div class="flex"><p class="line">' + \
               _body['title'] + '</p><p class="line2">' + desc + '</p></div></div></a>'

        return body
