#!/usr/bin/env python
# -*- coding:utf-8 -*-
# from string import punctuation
import json
import collections
import itertools
from xml.etree import ElementTree as eTree
# from utils.regex_utils import non_text_pattern, non_text_pattern_with_dot
from utils.regex_utils import *


class MessageHandler:
    def __init__(self):
        pass

    @staticmethod
    def handle_normal(body):
        """
        :param body: 原文内容
        :return:
            tag - int
            gros - collection.defaultdict(list) (key - [value1, value2])
            body - string
        """
        cata_dicts = collections.defaultdict(list)
        res = spe_pattern.findall(body)
        tag = 0
        if res:
            try:
                for gro_num, i in enumerate(res):
                    ii = i.strip('[]')
                    grotype = type_pattern.findall(ii)
                    if len(grotype) == 1:
                        grotype = grotype[0]
                        if grotype == 'emoticon':
                            value = value_pattern.findall(ii)[0]
                            width = width_pattern.findall(ii)[0]
                            body = body.replace(i, '[emo_{value}_{width}]'.format(value=value, width=width))
                        else:
                            tag = 1
                            r_dicts = filter(lambda x: '=' in x, ii.split())
                            attrib_dict = {}
                            for e in r_dicts:
                                e = e.strip('["]')
                                attrib_dict[e.split('=', 1)[0].strip('["]')] = \
                                    e.split('=', 1)[1].strip('["]')
                            attrib_dict['order'] = gro_num + 1
                            cata_dicts[grotype].append(attrib_dict)
                            body = body.replace(i, '[{}_{}]'.format(grotype, str(gro_num + 1)))
                    else:
                        print("get normal error %s", body)
            except Exception as e:
                print('handle_normal error, origin \n {}'.format(body))
                print(e)

        else:
            cata_dicts = None
        return tag, body, cata_dicts

    @staticmethod
    def handle_voice(body):
        """
        :param body: 原文内容
        :return:
            tag - int
            gros - dict
            body - string
        """
        tag = 0
        try:
            if isinstance(body, str):
                v_content = json.loads(body)
                body = '[voice]'
                gro = v_content
                tag = 2
        except:
            print("get voice error %s", body)
            gro = None
        return tag, body, gro

    @staticmethod
    def handle_file(body):
        """
        :param body: 原文内容
        :return:
            tag - int
            gros - dict
            body - string
        """
        tag = 0
        try:
            if isinstance(body, str):
                v_content = json.loads(body)
                body = '[file]'
                gro = v_content
                tag = 3
        except:
            print("get voice error %s", body)
            gro = None
        return tag, body, gro

    @staticmethod
    def handle_video(body):  # TODO:缩略图什么的。。？
        """
        :param body: 原文内容
        :return:
            tag - int
            gros - dict
            body - string
        """
        tag = 0
        try:
            res = spe_pattern.findall(body)
            video_normal = video_pattern.findall(body)
            video_send = send_video_pattern.findall(body)
            video_url = ''
            if res:
                video_url = value_pattern.findall(body)[0]
            elif video_normal:
                video_url = video_normal[0]
            elif video_send:
                video_url = video_send[0]
            gro = {'url': video_url}
            body = '[video]'
            tag = 4
        except Exception as e:
            print("get video error %s", body)  # TODO:

            gro = None
        return tag, body, gro

    @staticmethod
    def handle_code(body):
        """
        :param body: 原文内容
        :return:
            tag - int
            gros - dict
            body - string [code]
        """
        tag = 0
        try:
            code = {'code': body}
            body = '[code]'
            tag = 5
        except:
            print("get code error %s", body)
            code = None
        return tag, body, code

    @staticmethod
    def handle_ball(body):
        """
        :param body: 原文内容
        :return:
            tag - int
            gros - dict
            body - string [share]
        """
        tag = 0
        try:
            gro = json.loads(body)
            body = '[share]'
            tag = 6
        except:
            gro = None
        return tag, body, gro


class TextHandler:
    def __init__(self):
        pass

    @staticmethod
    def symbol_to_english(text):
        if not isinstance(text, str):
            return text
        text = text.replace('——', '_')

        table = {ord(f): ord(t) for f, t in zip(
            u'，。！？【】（）％＃＠＆１２３４５６７８９０ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ！＠＃＄％＾＆＊（）＿＋～【】、；，。、',
            u',.!?[]()%#@&1234567890abcdefghijklmnopqrstuvwxyz!@#$%^&*()_+~[]\;,./')}
        return text.translate(table)

    @staticmethod
    def merge_list_of_dict(*lists,key_tag='uri'):
        res = []
        key_agg = []
        for _l in lists:
            if isinstance(_l, dict):
                if _l not in res:
                    if key_tag:
                        if _l.get(key_tag) not in key_agg:
                            res.append(_l)
                            key_agg.append(_l.get(key_tag))
                    else:
                        res.append(_l)
            elif isinstance(_l, list):
                for _t in _l:
                    if not isinstance(_t, dict):
                        print('NON DICT FOUND')
                        continue
                    if _t not in res:
                        if key_tag:
                            if _t.get(key_tag) not in key_agg:
                                res.append(_t)
                                key_agg.append(_t[key_tag])
    
                        else:
                            res.append(_t)
        return res

    @staticmethod
    def check_subset(criteria, test):
        if not isinstance(criteria, (list, set, tuple)) or not isinstance(test, (list, set, tuple)):
            return False
        return all([z in criteria for z in test])

    @staticmethod
    def formulate_text(text):
        if not isinstance(text, str):
            return text
        # 去空格
        if ' ' in text:
            text = ''.join(text.split())
        # 去非文字同时去大写
        return non_text_pattern.sub('', text).lower()

    @staticmethod
    def formulate_text_to_uid(text):
        if not isinstance(text, str):
            return text
        if ' ' in text:
            text = ''.join(text.split())
        text = text.replace('。', '.')
        text = text.replace('——', '_')
        return non_text_pattern_with_dot.sub('', text).lower()

    @staticmethod
    def get_qchatid(msg):
        root = eTree.fromstring(msg)
        qchatid = root.attrib.get('qchatid', None)
        return qchatid


class CommonLib:
    def __init__(self):
        self.counter = 0

    def iter_check(self, data):
        while True:
            res = [x[self.counter] for x in data]
            yield res
            self.counter += 1

    def check_user_in_lists(self, user, lists):
        # 为了防止结果不准（例如搜索he jingyu, he抢走了jingyu.he 而jingyu再也无法命中导致漏数据）
        # 这里最好的办法是把每个关键词都拉出来一个数组 然后计算distinct 用户数量是否大于等于搜索关键词数
        # 但是要遍历所有群组成员，可能会很慢
        res = {}
        _len = len(user)
        for u in user:
            res[u] = []
            for to_u in lists:
                if u in to_u:
                    res[u].append(to_u)
        my_iter = self.iter_check(res.values())
        while True:
            try:
                ss = next(my_iter)
                print(ss)
                if len(set(ss)) >= _len:
                    return True
            except StopIteration:
                print('ITER FOUND NONE')
                break
        values = list(res.values())
        while True:
            try:
                x = itertools.product(*values)
                _t = next(x)
                if len(set(_t)) >= _len:
                    return True
            except StopIteration:
                print('ALL FAILED')
                break
        return False



class Multiple_iter:
    def __init__(self):
        """
        逐次返回[[1,2],[1,2],[1,2]]中的
        [1,1,1]
        [2,2,2]
        :param data:
        """
        self.ind = 0

    def __iter__(self, data):
        self.ind = 0

        self.data = data
        return self

    def __next__(self):
        res = [x[self.ind] for x in self.data]
        self.ind += 1
        return res
