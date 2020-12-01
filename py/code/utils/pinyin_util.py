#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'
"""
第三方库
https://github.com/mozillazg/python-pinyin
"""
from pypinyin import pinyin, Style


class PinyinUtil:
    """
    只保留中文， 返回拼音或者首字母， 不考虑多音字
    可通过修改回调函数errors来选择保留非中文字符
    """

    def __init__(self):
        pass

    def get_all(self, text):
        a = self.get_pinyin(text)
        b = self.get_first_letter(text)
        return [a, b]

    @staticmethod
    def get_pinyin(text):
        if not isinstance(text, str):
            text = str(text)
        res = pinyin(text, style=Style.NORMAL, errors=lambda x: x)  # 拼音
        res = ''.join([x[0] for x in res])
        return res

    @staticmethod
    def get_first_letter(text):
        if not isinstance(text, str):
            text = str(text)
        res = pinyin(text, style=Style.FIRST_LETTER, errors=lambda x: x)  # 首字母
        res = ''.join([x[0] for x in res])
        return res

# a = PinyinUtil()
# print(a.get_all("a []][2阿斯顿发而非【】【】【！！！"))