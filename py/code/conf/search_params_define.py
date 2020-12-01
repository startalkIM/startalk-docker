#!/usr/bin/env python
# -*- coding:utf-8 -*-
from enum import Enum
# from conf.constants import r_domain

from utils.logger_conf import configure_logger
from utils.get_conf import get_logger_file, get_config_file

config = get_config_file()

"""
搜索用
"""
userGroup = 'Q01'
groupGroup = 'Q02'
singlekeywordGroup = 'Q05'
muckeywordGroup = 'Q06'
commonGroup = 'Q07'
GroupDetail = 'Q10'

QTALK_OPEN_USER_VCARD = 0  # 打开单人名片
QTALK_OPEN_GROUP_VCARD = 1  # 打开群组聊天
QTALK_OPEN_FRIENDS_VC = 2  # 打开好友
QTALK_OPEN_GROUPS_VC = 3  # 打开群组
QTALK_OPEN_UNREAD_MESSAGE = 4  # 打开未读消息
QTALK_OPEN_PUBLIC_ACCOUNT = 5  # 打开公众号
QTALK_WEBVIEW = 6  # 打开webview，渲染url
QTALK_OPEN_USER_CHAT = 7  # 打开单人聊天
QTALK_OPEN_PUBLIC_VCARD = 8  # 打开公众号名片

"""
ckey验证用
"""
if_redis_sentinel = config['redis'].getboolean('if_sentinel')
is_check_ckey = config['qtalk'].getboolean('ckey_check')
single_portrait = config['qtalk']['single_portrait']
muc_portrait = config['qtalk']['muc_portrait']

if if_redis_sentinel:
    pre_rs_hosts = config['redis_sentinel']['hosts'].split(',')
    r_timeout = float(config['redis_sentinel']['timeout'])
    r_master = config['redis_sentinel']['service_name']
    r_password = config['redis_sentinel']['password']
    r_database = int(config['redis_sentinel']['database'])
else:
    r_host = config['redis']['host']
    r_database = config['redis']['database']
    r_timeout = config['redis']['timeout']
    r_port = config['redis']['port']
    r_password = config['redis']['password']

"""
监听kafka制作聊天cache使用
"""
# redis_key_single = r_domain + '_cache_single'
# redis_key_muc = r_domain + '_cache_single'
qtalk_chat_topic = config['kafka']['qtalk_chat_topic']
qtalk_group_topic = config['kafka']['qtalk_group_topic']
consumer_broker_params = config['kafka']['consumer_broker_params'].split(',')
group_id = config['kafka']['group_id']

"""
获取pinyin-中文
"""
if_name_id = config['kafka']['consumer_broker_params']

TYPE_REGISTER = {
    0: 'user',
    1: 'muc',
    2: 'common_muc',
    3: 'hs_single',
    4: 'hs_muc',
    5: 'hs_file',
}

ACTION_REGISTER = {
    'contact': ['user', 'muc', 'common_muc'],
    'lookback': ['hs_single', 'hs_muc', 'hs_file']
}

"""
elasticsearch相关
"""
if_lookback = config['lookback'].getboolean('lookback')
if_es = config['lookback'].getboolean('if_es')
if if_lookback and if_es:
    es_connstr = config['elasticsearch']['saas']
else:
    es_connstr = ''
# FILTER_PATH = ['', 'timed_out', 'took', 'hits.max_score', 'hits.hits._score', 'hits.hits._source.msg']
AGG_NEED =['raw_body','msgid','from','to','realfrom','realto','extendinfo','date','time','mtype']
FILTER_PATH = ['hits.total', 'hits.hits._source.raw_body', 'hits.hits._source.msgid', 'hits.hits._source.from',
               'hits.hits._source.to', 'hits.hits._source.realfrom', 'hits.hits._source.realto',
               'hits.hits._source.extendinfo', 'hits.hits._source.date', 'hits.hits._source.time',
               'hits.hits._source.mtype']

#AGG_FILTER_PATH = ['aggregations.top_to.buckets.top_to_hits.hits.total',
#                   'aggregations.top_to.buckets.top_to_hits.hits.hits._source']
AGG_FILTER_PATH = ['aggregations.conversation_aggs.buckets']
FILE_FILTER = ['hits.total', 'hits.hits._index','hits.hits._type', 'hits.hits._source.FILEID', 'hits.hits._source.FILEMD5',
               'hits.hits._source.FileName', 'hits.hits._source.FileSize', 'hits.hits._source.HttpUrl', 'hits.hits._id']


MUC_SPLIT_SIZE = 400
REGEX_TAG = '_'

SIMILARITY_THRESHOLD = 0.7
