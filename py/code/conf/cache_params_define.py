#!/usr/bin/env python
# -*- coding:utf-8 -*-
from utils.logger_conf import configure_logger
from utils.get_conf import get_logger_file, get_config_file

config = get_config_file()

if_redis_sentinel = config['cache_redis'].getboolean('if_sentinel')

if if_redis_sentinel:
    pre_rs_hosts = config['cache_redis_sentinel']['hosts'].split(',')
    r_timeout = float(config['cache_edis_sentinel']['timeout'])
    r_master = config['cache_redis_sentinel']['service_name']
    r_password = config['cache_redis_sentinel']['password']
    r_database = int(config['cache_redis_sentinel']['database'])
else:
    r_host = config['cache_redis']['host']
    r_database = config['cache_redis']['database']
    r_timeout = config['cache_redis']['timeout']
    r_port = config['cache_redis']['port']
    r_password = config['cache_redis']['password']

MAX_BUFFER = int(config['cache']['max_buffer'])

SINGLE_KEY = 'searchSingle'  # 指聊天记录 key + '_' + user_id
MUC_KEY = 'searchMuc'
SINGLE_TRACE_KEY = 'singleTrace'  # 指聊天频次
MUC_TRACE_KEY = 'mucTrace'

SINGLE_CACHE = 'singleCache'
MUC_CACHE = 'mucCache'
USER_MUCS = 'userMucs'
ALL_USER_DATA_CACHE = 'allUserData'

LOOKBACK_SINGLE_CACHE = 'hsSingle'
LOOKBACK_MUC_CACHE = 'hsMuc'
LOOKBACK_AGG_CACHE = 'hsAgg'
