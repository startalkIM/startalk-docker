#!/usr/bin/env python
# -*- coding:utf-8 -*-
from utils.get_conf import get_logger_file, get_config_file

config = get_config_file()

# service_host = config['sharemsg']['app_host']
# service_port = config['sharemsg']['app_port']

NOT_FOUND_ERROR = "未找到分享记录"
OUTDATED_ERROR = "分享记录已过期"
CANT_SHARE_MSG = "无法分享此类型消息"
MAX_TIME_INVAL = 10 * 60

MESSAGE_TYPE = {
    1: 'parse_im_obj',
    2: 'parse_im_voice',
    5: 'parse_im_file',
    12: 'parse_im_obj',
    32: 'parse_im_video',
    16: 'parse_im_location',
    30: 'parse_im_obj',
    666: 'parse_im_666card'
}

FILE_URL = config['sharemsg']['file_url']
