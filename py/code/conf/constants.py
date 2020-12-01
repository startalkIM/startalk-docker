#!/usr/bin/env python
# -*- coding:utf-8 -*-
import os
from utils.get_conf import get_logger_file, get_config_file
from utils.common_sql import domain
r_domain = domain
DB_VERSION = None
config = get_config_file()
logger_path = get_logger_file()

"""
ckey验证使用
"""
if_redis_sentinel = config['redis'].getboolean('if_sentinel')
auth_ckey_url = config['qtalk']['auth_ckey_url']
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

RESPONSE_ERROR = 'ERROR'
RESPONSE_ROOM_FULL = 'FULL'
RESPONSE_UNKNOWN_ROOM = 'UNKNOWN_ROOM'
RESPONSE_UNKNOWN_CLIENT = 'UNKNOWN_CLIENT'
RESPONSE_DUPLICATE_CLIENT = 'DUPLICATE_CLIENT'
RESPONSE_SUCCESS = 'SUCCESS'
RESPONSE_INVALID_REQUEST = 'INVALID_REQUEST'

IS_DEV_SERVER = os.environ.get('APPLICATION_ID', '').startswith('dev')

if_cached = config['cache'].getboolean('if_cache')
