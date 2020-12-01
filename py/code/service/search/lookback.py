#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'
import time
import json
import random
import asyncio
import collections
# from elasticsearch import Elasticsearch, helpers
from elasticsearch_async import AsyncElasticsearch
from xml.etree import ElementTree as eTree
from functools import reduce
from conf.constants import *
from conf.search_params_define import *
from utils.dsl import DSL
from utils.time_utils import TimeUtils
from utils.common_utils import TextHandler
# from service.search.lookback_es import LookbackLib
import utils.common_sql
from utils.redis_utils import RedisUtil

log_path = get_logger_file('search.log')
lookback_logger = configure_logger('search', log_path)

if if_es:
    lookback_logger.info("USING ES LOOKBACK..")
    from service.search.lookback_es import LookbackLib
else:
    lookback_logger.info("USING SQL LOOKBACK..")
    from service.search.lookback_sql import LookbackLib

# if if_lookback and if_es:
#     lookback_logger.info("USING ES LOOKBACK..")
#     from service.search.lookback_es import LookbackLib
# elif if_lookback and not if_es:
#     lookback_logger.info("USING SQL LOOKBACK..")
#     from service.search.lookback_sql import LookbackLib
# else:
#     Lookback = None

if utils.common_sql.if_async:
    lookback_logger.info('USING AYNC USERLIB FOR LOOKBACK')
    from utils.common_sql import AsyncLib as Userlib_
else:
    lookback_logger.info('USING SYNC USERLIB FOR LOOKBACK')
    from utils.common_sql import UserLib as Userlib_
domain = utils.common_sql.domain
# 生成logger
time_util = TimeUtils()
text_handler = TextHandler()
redis_cli = RedisUtil()

"""
聚合请求（action = 24)
    因为聚合请求请求了单人和群聊， 在两方结果集返回之前无法确定最终数据集。 所以第一次请求是根据两方返回的请求集，按照时间排序之后，取出对应长度的数据， 其余的放入redis， 对应redis需要考虑数据的清除， 所以应该以用户-关键词为索引，值存放剩余的结果集， 即info字段内容
    每一次请求首先请求redis， 有则比对长度 无则去取
非聚合请求 （action = 8 / 16 / 32)
"""


class Lookback:
    def __init__(self, args, user_id, extend_time=False):
        self.user = user_id
        self.offset = int(args.get("start", 0))
        self.limit = int(args.get("length", 5))
        self.term = args.get('key')
        self.timeout = 60 if extend_time else 5

        self.userlib = Userlib_(user_id)
        self.conn = None
        self.userlib = Userlib_(user_id)
        if if_es:
            self.conn = self.conn_es()
            self.conn.cluster.health(wait_for_status='yellow', request_timeout=1)
            self.lookback_lib = LookbackLib(args=args, conn=self.conn, user_lib=self.userlib, user_id=user_id,
                                            timeout=self.timeout)
        else:
            self.lookback_lib = LookbackLib(args=args, user_id=user_id)

        self.action = []
        # self.user_mucs = None
        # self.indexes = time_util.generate_url(domain=domain)
        # self.filter_path = FILTER_PATH if (args.get('to_user') or args.get('to_muc')) else AGG_FILTER_PATH
        self.router = {
            'hs_single': self.lookback_lib.history_user,
            'hs_muc': self.lookback_lib.history_muc,
            'hs_file': self.lookback_lib.history_file,
            'ELSE': lambda x: lookback_logger.exception("COMMAND {} NOT FOUND ".format(x))
        }

    @staticmethod
    def conn_es():
        saas = es_connstr.split(',')
        rand = random.randint(0, len(saas) - 1)
        url = saas[rand]
        es = AsyncElasticsearch(url)
        return es

    async def close_conn(self):
        if self.conn:
            await self.conn.transport.close()
        if self.userlib:
            self.userlib.close()
        return

    async def lookback_coro(self, todo):
        if if_es and todo == ['hs_single', 'hs_muc']:
            res = redis_cli.get_agg_cache(user=self.user, term=self.term)
            if not res:
                tasks = []
                for coro in todo:
                    self.action.append(coro)
                    t = asyncio.create_task(self.router[coro](self.user))
                    tasks.append(t)
                completed, pending = await asyncio.wait(tasks, timeout=self.timeout)
                for pen in pending:
                    lookback_logger.error("PENDING TASK FOUND {}".format(pen))
                    pen.cancel()
                result = []
                for com in completed:
                    # t = com.result()
                    if com.result():
                        result.append(com.result())

                res = await self.handle_result(result)
                if not res:
                    return None
                info = res.get('info')
                _all = []
                for __in in info:
                    for i in __in:
                        _all.append(i)
                _all = sorted(_all, key=lambda x: x.get('time'), reverse=True)
                res['info'] = _all
                if if_cached:
                    redis_cli.set_agg_cache(self.user, self.term, res)
            if not res or not isinstance(res, dict) or 'info' not in res.keys():
                return None
            cache_len = len(res['info'])
            if cache_len < self.offset + self.limit + 1:
                res['info'] = res['info'][self.offset:]
                res['hasMore'] = False
                return res
            elif cache_len >= self.offset + self.limit + 1:
                res['info'] = res['info'][self.offset:self.offset + self.limit]
                res['hasMore'] = True
                return res
            else:
                lookback_logger.info('unexpected situation ')
                return None
        else:
            __start = time.time()
            tasks = []
            self.lookback_lib.args = {}

            for coro in todo:
                self.action.append(coro)
                t = asyncio.create_task(self.router[coro](self.user))
                tasks.append(t)
            completed, pending = await asyncio.wait(tasks, timeout=self.timeout)
            for pen in pending:
                lookback_logger.error("PENDING TASK FOUND {}".format(pen))
                lookback_logger.error("PENDING TASK PARAMS {} {}".format(self.user, self.term))
                pen.cancel()
            result = []
            for com in completed:
                # t = com.result()
                if com.result():
                    result.append(com.result())
            res = await self.handle_result(result)
            # 获取了结果之后， 多的放入redis待命，
            __end = time.time()
            lookback_logger.info('LOOKBACK COROS TIME USED {}'.format(__end - __start))
            if float(__end - __start) > 3.0:
                lookback_logger.warning('LOOKBACK TIME TOO LONG {} {}'.format(self.user, self.term))

            if res:
                info = res.get('info')
                _all = []
                for __in in info:
                    for i in __in:
                        _all.append(i)
                _all = sorted(_all, key=lambda x: x.get('time'), reverse=True)
                res['info'] = _all[:self.limit]

            return res

    async def handle_result(self, res):
        if not res:
            return
        file_stack = []
        history_stack = []
        __info = []
        # result_sum = 0
        for stack in res:
            if stack.get('resultType') == 32:
                file_stack.append(stack)
            else:
                history_stack.append(stack)
                # result_sum += stack.get('resultType')
        if history_stack:
            for i in res:
                if i.get('info'):
                    __info.append(i['info'])
            if not __info:
                return None
            hasMore = False
            if 'hs_single' in self.action and 'hs_muc' in self.action:
                result_sum = 24
            elif 'hs_single' in self.action and 'hs_muc' not in self.action:
                result_sum = 8
            elif 'hs_single' not in self.action and 'hs_muc' in self.action:
                result_sum = 16
            else:
                result_sum = 0

            for i in history_stack:
                if i.get('hasMore', False):
                    hasMore = True
                    break

            history_result = {
                'groupLabel': '聊天记录',
                'groupId': 'Q03',
                'info': __info,
                'resultType': result_sum,
                'hasMore': hasMore
            }
            return history_result
        elif file_stack:
            for i in res:
                if i.get('info'):
                    __info.append(i['info'])
            if not __info:
                return None
            hasMore = False
            for i in file_stack:
                if i.get('hasMore', False):
                    hasMore = True
                    break
            file_result = {
                'groupLabel': '文件',
                'groupId': 'Q04',
                'info': __info,
                'resultType': 32,
                'hasMore': hasMore
            }
            return file_result
        else:
            return None
