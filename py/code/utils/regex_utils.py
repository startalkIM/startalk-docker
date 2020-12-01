#!/usr/bin/env python
# -*- coding:utf-8 -*-

import re

text_pattern = re.compile("\w")
non_text_pattern = re.compile("\W")
non_text_pattern_with_dot = re.compile("[^\w.。—_-]")
chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')

emo_pattern = re.compile('\[obj\stype=.*?emoticon.*?\svalue=.*?]')
url_pattern = re.compile('\[obj\stype=.*?url.*?\svalue=.*?]')
pic_pattern = re.compile('\[obj\stype=.*?image.*?\svalue=.*?]')
dict_value_pattern = re.compile('^(?:\"|&quot;|\[)?.*?(?:\"|&quot;|\])?$')
spe_pattern = re.compile('\[obj\stype=.*?\svalue=".*?".*?(?:\"\]|\])')
type_pattern = re.compile('type=(?:\"|&quot;)(\w+?)(?:\"|&quot;)\s')
value_pattern = re.compile('value=(?:\"|&quot;)(.+?)(?:\"|&quot;)')
width_pattern = re.compile('width=(.*?)\s')
video_pattern = re.compile('(?:Video|video):\s?(.*?)$')
send_video_pattern = re.compile(r'\[obj type="url" value="(.*?)"\]')
