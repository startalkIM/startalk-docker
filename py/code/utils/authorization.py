#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'
import base64
import hashlib
import redis
from redis import sentinel
import traceback
from urllib.parse import parse_qs
from conf.constants import *
from utils.logger_conf import configure_logger
from utils.get_conf import *

log_path = get_logger_file()
log_path = log_path + 'author.log'
author_log = configure_logger('author', log_path)

try:
    if if_redis_sentinel:
        _hosts = [hp.split(':') for hp in pre_rs_hosts]
        hosts = [(hp[0].strip(), int(hp[1].strip())) for hp in _hosts]
        r_sentinel = sentinel.Sentinel(hosts, socket_timeout=r_timeout)
        redis_cli = r_sentinel.master_for(r_master, socket_timeout=r_timeout, password=r_password, db=r_database,
                                          decode_responses=True)
    else:
        redis_cli = redis.StrictRedis(host=r_host, port=r_port, db=r_database, password=r_password,
                                      decode_responses=True)
except (KeyError, ValueError, IndexError) as e:
    author_log.exception('wrong configure pattern')
    exit(0)

author_log.info("REIDS START SUCCESS")
g_user = ''


def check_ckey(ckey,puser=''):
    global g_user
    if not isinstance(ckey, str):
        ckey = str(ckey)
    if len(ckey) <= 0:
        return False
    try:
        ckey_parse = base64.b64decode(ckey).decode('utf-8')
        result = parse_qs(ckey_parse)
        # user = result['u'][0]
        user = result.get('u')
        if isinstance(user, list):
            user = user[0]

        # 判断ckey中的user是否和传入的user相同
        if puser:
            if '@' in puser:
                if user != puser.split('@')[0]:
                    return False, user
            else:
                if user != puser:
                    return False, user
        # domain = result['d'][0]
        __domain = result.get('d')
        if isinstance(__domain, list):
            if len(__domain) == 1:
                __domain = __domain[0]
            else:
                author_log.warning('MORE THAN 1 DOMAIN FOUND {} '.format(__domain))
                __domain = __domain[0]

        if not g_user:
            g_user = user
        # time = result['t'][0]
        _time = result.get('t')
        if isinstance(_time, list):
            _time = _time[0]
        tar = result['k']
        if isinstance(tar, list):
            tar = tar[0]
        if puser and '@' in puser:
            if __domain != puser.split('@')[1]:
                author_log.error("unknown domain {} get for user {}".format(result['d'][0], user))
                return False, user
        user_keys = redis_cli.hkeys(user)
        if isinstance(user_keys, list):
            for i in user_keys:
                i = str(i) + str(_time)
                i = md5(i)
                i = str(i).upper()
                if i == str(tar):
                    if g_user != user:
                        g_user = user
                        author_log.info('user = {} , ckey = {} login success!'.format(result['u'][0], ckey))
                    return True, user + '@' + __domain 
        elif isinstance(user_keys, (str,int)):
            i = str(user_keys) + str(_time)
            i = md5(i)
            i = str(i).upper()
            if i == str(tar):
                if g_user != user:
                    g_user = user
                    author_log.info('user = {} , ckey = {} login success!'.format(result['u'][0], ckey))
            return True, user + '@' + domain
        else:
            return False, user
        return False, user
    except Exception as e:
        author_log.exception("CKEY CHECK FAILED")
        return False, ''


def md5(string):
    m = hashlib.md5()
    m.update(string.encode("utf8"))
    return m.hexdigest()


def md5GBK(string1):
    m = hashlib.md5(string1.encode(encoding='gb2312'))
    return m.hexdigest()


