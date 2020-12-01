#!/usr/bin/env python
# -*- coding:utf-8 -*-
from utils.logger_conf import configure_logger
from utils.get_conf import get_logger_file, get_config_file

config = get_config_file()


if_redis_sentinel = config['redis'].getboolean('if_sentinel')
is_check_ckey = config['qtalk'].getboolean('ckey_check')

info_onlineUrl = config['meeting_detail']['info_url']
action_onlineUrl = config['meeting_detail']['action_url']

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
