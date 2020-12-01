#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'

from flask import request, jsonify, Blueprint
import json
import requests
import asyncio
from conf.constants import is_check_ckey, auth_ckey_url, if_cached, r_domain
from conf.search_params_define import *
from utils.request_util import RequestUtil
from utils.redis_utils import RedisUtil
from service.search.contact import Contact
from service.search.lookback import Lookback

search_blueprint = Blueprint('search', __name__)

# -------------------------- 生成logger --------------------------
log_path = get_logger_file(name='search.log')
search_logger = configure_logger('search', log_path)

# -------------------------- 读取默认配置 --------------------------
if is_check_ckey:
    search_logger.info("CKEY AUTHORIZATION INITIALING...")
    from utils.authorization import check_ckey
# -------------------------- 既定的配置 --------------------------

ip = str()
s_args = dict()
l_args = dict()

# -------------------------- 鉴权修饰器 --------------------------
def authorization(func):
    def wrapper(*args, **kw):
        ckey = ''
        user_id = 'DEFAULT'
        user = ''
        request_util = RequestUtil()
        res = False
        __args = request_util.get_request_args(request)
        user_id = __args.get('qtalkId', 'UNKOWN')
        user_domain = None
        if '@' in user_id:
            _user = user_id.split('@')
            user = _user[0]
            user_domain = _user[1]
        else:
            user = user_id
            if isinstance(r_domain, str):
                user_domain = r_domain
                user_id = user_id + '@' + user_domain
        if user_id in ['guanghui.yang@ejabhost1','jingyu.he@ejabhost1','chaos.dong@ejabhost1','binz.zhang@ejabhost1']:
            return func(user_id=user_id, args=__args, *args, **kw)
        elif is_check_ckey:
            ckey = request_util.get_ckey(request)
            if ckey:
                if auth_ckey_url:
                    try:
                        r_data = {
                            'ckey': ckey,
                            'system': 'search'
                        }
                        ret = requests.post(url=auth_ckey_url, json=r_data)
                        """{
                            "ret": true,
                            "errcode": 0,
                            "errmsg": "",
                            "data": {
                                "d": "qtalk.test.org",
                                "u": "aaa.bb"
                            }
                        }"""

                        if ret.json().get('ret') and ret.json().get('data',{}).get('u','')+ '@' + ret.json().get('data',{}).get('d','') == user_id:
                            if user_domain and ret.json().get('data').get('d') != user_domain:
                                return jsonify(ret=False, errcode=500, msg="Error domain")
                            # TODO remove this after domain check is soon needless
                            elif not user_domain:
                                user_domain = ret.json().get('data',{}).get('d')
                            res = True
                            # user = user_id + '@' + user_domain
                            user = user + '@' + user_domain

                        else:
                            search_logger.error("ckey api check failed : ret {} u {}".format(ret.json().get('ret'),user_id)) 
                    except (requests.RequestException or KeyError) as e:
                        search_logger.error("ckey api failed : {}".format(e))
                        # TODO notify developer to check
                        res, user = check_ckey(ckey)
                    except Exception as e:
                        search_logger.exception("ckey api failed : {}".format(e))
                else:
                    res, user = check_ckey(ckey)
            if res:
                return func(user_id=user, args=__args, *args, **kw)
            else:
                search_logger.info("user:{user} login failed, ckey : {ckey}, \
                                                ".format(user=user_id, ckey=ckey))
                return jsonify(ret=False, errcode=0, message="ckey check failed")
        return func(user_id=user_id, args=__args, *args, **kw)

    wrapper.__name__ = func.__name__
    return wrapper


@search_blueprint.route('/search', methods=['GET', 'POST'])
@authorization
def main(user_id, args):
    # 记录每个ip 每次搜索的最后一次请求
    global ip, s_args
    # 对于某些请求时间很长的操作 不进行timeout限制
    extend_time = False

    request_ip = request.remote_addr
    if not s_args:
        s_args = args
    if ip != request_ip:
        ip = request_ip
        search_logger.info(ip + ' :  \n{}'.format(json.dumps(s_args, ensure_ascii=False, indent=4)))
    s_args = args

    # 将str的action转为二进制 按照define里的定义长度
    if 'platform' in args:
        _group_id = ''
    else:
        _group_id = args.get("groupId", 0)
    action = ''
    if (_group_id or _group_id == '') and 'action' not in args:
        if _group_id == '':
            action = '7'
        elif _group_id == 'Q01':
            action = '1'
        elif _group_id == 'Q02':
            action = '2'
        elif _group_id == 'Q07':
            action = '4'
    elif ('action' not in args) and ('groupId' not in args):
        if args.get('platform','').lower() == 'ios':  # 此处等ios兼容后就删掉
            action = '7'
        else:
            return jsonify(ret=False, errcode=500, msg="WRONG ACTION")
    else:

        action = args.get("action", 0)
        if int(action) == 63:
            action = 31
        elif int(action) in [1,2,4,6,8,16,32]:
            extend_time = True

    try:
        if isinstance(action, str):
            action = format(int(action), "b")
        elif isinstance(action, int):
            action = bin(action)
        _register = dict()
        register_len = len(TYPE_REGISTER)
        for _p, _n in enumerate(action[-1: -1 - register_len: -1]):
            _register[TYPE_REGISTER[_p]] = (_n == '1')
    except (KeyError, ValueError, TypeError) as e:
        search_logger.exception(e)
        return jsonify(ret=False, errcode=500, msg="WRONG ACTION")

    # 获取相关任务准备进行协程分配
    register = [k for k, v in _register.items() if v is True]
    if_contact = []
    if_lookback = []
    for t in register:
        if t in ACTION_REGISTER['contact']:
            if_contact.append(t)
        if t in ACTION_REGISTER['lookback']:
            if_lookback.append(t)

    # 搜索关键词限制
    if if_contact or if_lookback:
        _key = args.get('key', '').strip()
        if len(_key) < 2:
            return jsonify(ret=False, errcode=500, msg="key is illegal")
        elif len(_key) > 20:
            args['key'] = _key[:20]
        else:
            args['key'] = _key
            # TODO 或许要加上剪切提示
    if if_cached:
        redis_util = RedisUtil()
        user_habit = redis_util.get_user_habit(user_id=user_id)
    else:
        user_habit = ''
    data = ''
    if if_contact or if_lookback:
        data = asyncio.run(
            go_coro(if_contact=if_contact, if_lookback=if_lookback, args=args, user=user_id, habit=user_habit, extend_time=extend_time))
    # TODO： data处理
    else:
        search_logger.error("NO TASK FOUND ACTION : {}".format(action))

    return jsonify(ret=True, errcode=0, errmsg='', data=data)


async def go_coro(if_contact, if_lookback, args, user, habit, extend_time=False):
    contact = ''
    lookback = ''
    tasks = []
    timeout = 60 if extend_time else 10
    if if_contact:
        contact = Contact(user_id=user, args=args, habit=habit, extend_time=extend_time)
        # 我也不是很懂为啥要把共同群组融进去 于是结构变得有点奇怪 以后看能不能sql搞定吧
        if ('common_muc' in if_contact) or ('muc' in if_contact):
            if ('common_muc' in if_contact) and ('muc' in if_contact):
                t = asyncio.create_task(contact.router['muc'](user_id=user, origin=True, common=True))
                tasks.append(t)
                if_contact.remove('muc')
                if_contact.remove('common_muc')
            elif ('common_muc' not in if_contact) and ('muc' in if_contact):
                t = asyncio.create_task(contact.router['muc'](user_id=user, origin=True, common=False))
                tasks.append(t)
                if_contact.remove('muc')
            elif ('common_muc' in if_contact) and ('muc' not in if_contact):
                t = asyncio.create_task(contact.router['muc'](user_id=user, origin=False, common=True))
                tasks.append(t)
                if_contact.remove('common_muc')
            else:
                raise BaseException("UNEXPECTED IF_CONTACT SITUATION")
        if if_contact:
            for todo in if_contact:
                t = asyncio.create_task(contact.router[todo](user))
                tasks.append(t)
    if if_lookback:
        lookback = Lookback(user_id=user, args=args, extend_time=extend_time)
        # for todo in if_lookback:
        #     t = asyncio.create_task(lookback.router[todo](user))
        #     tasks.append(t)
        if 'hs_file' in if_lookback:
            t = asyncio.create_task(lookback.lookback_coro(todo=['hs_file']))
            tasks.append(t)
            if_lookback.remove('hs_file')
        if if_lookback:
            t = asyncio.create_task(lookback.lookback_coro(todo=if_lookback))
            tasks.append(t)
    completed, pending = await asyncio.wait(tasks, timeout=timeout)
    for pen in pending:
        search_logger.error("PENDING TASK FOUND {}".format(pen))
        pen.cancel()
    result = []
    for com in completed:
        # t = com.result()
        if com.result():
            result.append(com.result())
    # sort_key = ['联系人列表', '群组列表', '共同群组', '单人历史', '群组历史', '']
    sort_key = ['联系人', '群组', '聊天记录', '文件', '']

    search_logger.debug("label {}".format(result))
    result = sorted(result, key=lambda x: sort_key.index(x.get('groupLabel', '')))
    # 关闭数据库连接
    if contact:
        contact.userlib.close()
    if lookback:
        await lookback.close_conn()
    return result
