#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'
import json
import time
import random
import asyncio
# from elasticsearch import Elasticsearch, helpers
from elasticsearch_async import AsyncElasticsearch
from xml.etree import ElementTree as eTree
from functools import reduce
from conf.constants import *
from conf.search_params_define import *
from conf.cache_params_define import LOOKBACK_MUC_CACHE, LOOKBACK_SINGLE_CACHE
from utils.redis_utils import RedisUtil
from utils.dsl import DSL
from utils.authorization import md5
from utils.time_utils import TimeUtils
from utils.common_utils import TextHandler
import utils.common_sql

user_data = utils.common_sql.user_data
domain = utils.common_sql.domain
dsl = DSL()
time_util = TimeUtils()
text_handler = TextHandler()
# 生成logger
log_path = get_logger_file('search.log')
lookback_logger = configure_logger('search', log_path)
redis_util = RedisUtil()

COMMON_DSL = {
    "conversation_aggs": {
        "terms": {
            "field": "conversation",
            "size": 80,
            "collect_mode": "breadth_first"

        },
        "aggs": {
            "top_conversation_hits": {
                "top_hits": {
                    "sort": [
                        {
                            "id": {
                                "order": "desc"
                            }
                        }
                    ],
                    "_source": {
                        "includes": ["raw_body", "msgid", "from", "to", "realfrom", "realto", "extendinfo", "date",
                                     "time", "mtype"]
                    },
                    "size": 1
                }
            }
        }
    }
}


class LookbackLib:
    def __init__(self, args, conn, user_lib, user_id, timeout=5):
        global user_data
        #可能不用
        user_data = utils.common_sql.user_data
        self.timeout = timeout
        self.user_lib = user_lib
        if not user_data:
            userlib__ = utils.common_sql.UserLib(user_id)
            user_data = userlib__.get_user_data()
            userlib__.close()
        self.user_data = user_data
        self.args = args
        self.user = user_id
        self.offset = int(args.get("start", 0))
        self.limit = int(args.get("length", 5))
        self.term = args.get('key')
        self.to_user = self.args.get('to_user')

        to_muc = self.args.get('to_muc')
        if isinstance(to_muc, str):
            self.to_muc = [to_muc]
        elif isinstance(to_muc, list):
            self.to_muc = to_muc
        elif not to_muc:
            self.to_muc = None
        else:
            raise TypeError("WRONG TO_MUC {}".format(to_muc))
        self.starttime = self.args.get('starttime')
        self.endtime = self.args.get('endtime')
        self.conn = conn
        self.conn.cluster.health(wait_for_status='yellow', request_timeout=1)
        self.userlib = user_lib
        self.user_mucs = None
        self.indexes = time_util.generate_url(domain='qtalk')
        self.filter_path = FILTER_PATH if (args.get('to_user') or args.get('to_muc')) else AGG_FILTER_PATH


    async def history_user(self, user):
        result = None
        agg_tag = False if self.to_user else True
        if '@' in user:
            user_s_name = user.split('@')[0]
            user_domain = user.split('@')[1]
        else:
            lookback_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        # default_extra = {
        #     "from": 0,
        #     "size": 5
        # }
        _query = dsl.make_query(method='match_phrase', field='body', term=self.term)
        _filter = dsl.make_filter(qtalkid=user, domain=user_domain, to_user=self.to_user,
                                  starttime=self.starttime, endtime=self.endtime, _type='message')
        _aggs = COMMON_DSL
        _dsl = {
            "query": {
                "filtered": {
                    "query": _query,
                    "filter": _filter
                }
            },
        }
        if agg_tag:
            _aggs['conversation_aggs']['terms']['field'] = 'conversation'
            _dsl['aggs'] = _aggs
            _limit = 0
            _offset = 0
            res = redis_util.get_single_lookback(user=user, term=self.term)
            if not res:
                res = await self.conn.search(index=self.indexes, body=_dsl,
                                             sort=['id:desc'], timeout='{}s'.format(self.timeout), from_=_offset, size=_limit)
                redis_util.set_single_lookback(user=user, term=self.term, data=res)

        else:
            _limit = self.limit + 1
            _offset = self.offset
            res = await self.conn.search(index=self.indexes, body=_dsl,
                                         sort=['id:desc'], timeout='{}s'.format(self.timeout), from_=_offset, size=_limit)
        lookback_logger.debug('history user dsl {}\n'.format(_dsl))
        if res.get('hits'):
            if res.get('hits').get('total'):
                result = await self.make_result(response=res, label='单人历史', offset=self.offset, limit=self.limit + 1,
                                                resultType=8, todoType=8, agg_tag=agg_tag)
                if result:
                    for _r in result.get('info'):
                        if agg_tag:
                            _to = _r.get('to').split('@')[0] if _r.get('from').split('@')[0] == user else \
                                _r.get('from').split('@')[0]
                            # __todict = [x for x in user_data if x.get('i') == _to][0]
                            if utils.common_sql.if_async:
                                __todict = await self.userlib.get_person_info(_to)
                            else :
                                __todict = self.userlib.get_person_info(_to)
                            _r['icon'] = __todict.get('url', '')
                            _r['label'] = '{name}({id})'.format(name=__todict.get('show_name', ''), id=_to)
                            # result['info'][result['info'].index(_r)] = _r
                        else:
                            if not self.user_data:
                                if utils.common_sql.if_async:
                                    self.user_data = await self.userlib.get_user_data()
                                else:
                                    self.user_data = self.userlib.get_user_data()
                                # userlib.close()

                            _target = _r.get('from')
                            if '@' in _target:
                                _target = _target.split('@')[0]
                            __dict = self.user_data.get(_target, {})
                            _r['icon'] = __dict.get('u', '')
                            _r['label'] = __dict.get('n', _target)

        return result

    async def history_muc(self, user):
        #breakpoint() 
        result = None
        res = None
        if '@' in user:
            user_s_name = user.split('@')[0]
            user_domain = user.split('@')[1]
        else:
            lookback_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        if self.to_muc:
            agg_tag = False
            check_result = await self.muc_check(user=user, domain=user_domain, check_lists=self.to_muc)  # 看看组限定包含用户不
            if not check_result:
                lookback_logger.error("FOUND FORBIDDEN GROUP IN LIST")
                return None
            user_mucs = self.to_muc
        else:
            agg_tag = True
            res = redis_util.get_muc_lookback(user=user, term=self.term)
            # user_mucs = []
        # 无论有没有特定搜索的群组（如果有特定群组的话不聚合，不需要往redis放）如果没有res的话就需要去搜索
        if not res:
            if self.to_muc:
                user_mucs = self.to_muc
            else:
                if self.user_mucs:
                    user_mucs = self.user_mucs
                else:
                    if utils.common_sql.if_async:
                        user_mucs = await self.userlib.get_user_mucs(self.user)
                    else:
                        user_mucs = self.userlib.get_user_mucs(self.user)
                    self.user_mucs = user_mucs
                    user_mucs = self.handle_user_mucs(user_mucs)
            tasks = []
            for sli in user_mucs:
                _query = dsl.make_query(method='match_phrase', field='body', term=self.term)
                _filter = dsl.make_filter(qtalkid=self.user, domain=user_domain, to_muc=sli,
                                          starttime=self.starttime, endtime=self.endtime, _type='muc_msg')
                _dsl = {
                    "query": {
                        "filtered": {
                            "query": _query,
                            "filter": _filter
                        }
                    }
                }
                if agg_tag:
                    _aggs = COMMON_DSL
                    _aggs['conversation_aggs']['terms']['field'] = 'to'
                    _dsl['aggs'] = _aggs
                    _limit = 0
                    _offset = 0
                    t = self.conn.search(index=self.indexes, df='muc_msg', body=_dsl,
                                         sort=['id:desc'], timeout='{}s'.format(self.timeout), from_=_offset,
                                         size=_limit)
                    tasks.append(t)
                else:
                    _limit = self.limit + 1
                    _offset = self.offset
                    t = self.conn.search(index=self.indexes, df='muc_msg', body=_dsl,
                                         sort=['id:desc'], timeout='{}s'.format(self.timeout), from_=_offset,
                                         size=_limit)
                    tasks.append(t)

            coro_result = await asyncio.gather(*tasks)
            res = self.handle_muc_coro_result(coro_result)
            if agg_tag:
                redis_util.set_muc_lookback(user=user, term=self.term, data=res)
        if res:
            result = await self.make_result(response=res, label='群组历史', offset=self.offset, limit=self.limit + 1,
                                            resultType=16, todoType=16,
                                            agg_tag=agg_tag)  # todo:resulttype固定返16还是根据结果加和？
            if result:
                for _r in result.get('info'):
                    if agg_tag:
                        _target = _r.get('to')
                        # __todict = [x for x in user_data if x.get('i') == _to][0]
                        if utils.common_sql.if_async:
                            __dict = await self.userlib.get_mucs_info(_target)
                        else:
                            __dict = self.userlib.get_mucs_info(_target)
                        _r['icon'] = __dict.get('muc_pic', '')
                        _r['label'] = __dict.get('show_name', '')
                    else:
                        if not self.user_data:
                            if utils.common_sql.if_async:
                                self.user_data = await self.userlib.get_user_data()
                            else:
                                self.user_data = self.userlib.get_user_data()
                            # self.userlib.close()
                        _target = _r.get('from')

                        if '@' in _target:
                            _target = _target.split('@')[0]
                        __dict = self.user_data.get(_target, {})

                        # __todict = [x for x in user_data if x.get('i') == _to][0]
                        # __todict = await userlib.get_mucs_info(_target)
                        _r['icon'] = __dict.get('u', '')
                        _r['label'] = __dict.get('n', _target)

        return result

    async def history_all(self):
        pass

    async def history_file(self, user):
        result = None
        if '@' in user:
            user = user
            user_s_name = user.split('@')[0]
            user_domain = user.split('@')[1]
        else:
            lookback_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []

        if self.to_muc:
            user_mucs = self.to_muc
            check_result = await self.muc_check(user=user, domain=user_domain, check_lists=self.to_muc)  # 看看组限定包含用户不
            if not check_result:
                lookback_logger.error("FOUND FORBIDDEN GROUP IN LIST")
                return None
        elif self.user_mucs:
            user_mucs = self.user_mucs
        else:
            if utils.common_sql.if_async:
                user_mucs = await self.userlib.get_user_mucs(self.user)
            else:
                user_mucs = self.userlib.get_user_mucs(self.user)
            self.user_mucs = user_mucs
        user_mucs = self.handle_user_mucs(user_mucs)
        tasks = []
        for sli in user_mucs:
            _query = dsl.make_query(method='match_phrase', field='FileName', term=self.term)
            _filter = dsl.make_filter(qtalkid=user, domain=user_domain, to_user=self.to_user, to_muc=sli,
                                      starttime=self.starttime, endtime=self.endtime, action=32, filetype='file')

            # _aggs = dsl.make_aggs(name='history_muc', method='top_hits', field='conversation',
            #                       extra=self.args.get('extra', default_extra))
            _dsl = {
                "query": {
                    "filtered": {
                        "query": _query,
                        "filter": _filter
                    }
                }
            }
            _limit = self.limit + 1
            _offset = self.offset
            t = self.conn.search(index=self.indexes, body=_dsl, sort='date:desc', timeout='{}s'.format(self.timeout),
                                 from_=self.offset, size=self.limit + 1)
            tasks.append(t)
        file_res = await asyncio.gather(*tasks)
        if file_res:
            file_res = self.handle_muc_coro_result(file_res)
        if file_res.get('hits'):
            if file_res.get('hits').get('total'):
                __res = await self.handle_file_result(file_res)
                result = await self.make_result(response=__res, label='文件', offset=self.offset, limit=self.limit + 1,
                                                resultType=32, todoType=32, agg_tag=False)
        return result


    async def muc_check(self, user, domain, check_lists):
        if isinstance(check_lists, str):
            check_lists = [check_lists]
        user_registed_mucs = await self.userlib.get_user_mucs(user_id=user)
        if user_registed_mucs:
            self.user_mucs = user_registed_mucs
        return TextHandler.check_subset(user_registed_mucs, check_lists)

    async def handle_file_result(self, file_result):
        ids = []
        pre_search = dict()
        for hits in file_result['hits']['hits']:
            __index = hits['_index']
            __type = 'message' if hits['_type'] == 'msggro' else 'muc_msg'
            __index = __index + '@' + __type
            id = hits['_id']
            if __index not in pre_search.keys():
                pre_search[__index] = [id]
            else:
                pre_search[__index].append(id)
            ids.append({
                "term": {
                    "id": id
                }
            })
        # TODO 用mget测试一下 如果速度够快的话不要用search了 首先要重新导入数据 先导入6月的吧
        dsl = {
            "query": {
                "filtered": {
                    "query": {
                        "match_all": {
                        }
                    },
                    "filter": {
                        "bool": {
                            "should": ids,
                            "must_not": [
                                {
                                    "term": {
                                        "_type": "mucgro"
                                    }
                                }, {
                                    "term": {
                                        "_type": "msggro"
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    }
                }
            }
        }
        tasks = []
        for i, k in pre_search.items():
            _index = i.split('@')[0]
            _type = i.split('@')[1]
            _body = {
                "docs": [{"_id": _k} for _k in k]
            }
            tasks.append(self.conn.mget(index=_index, doc_type=_type, body=_body))
        raw_res = await asyncio.gather(*tasks)
        res = {'hits': {'hits': []}}
        for raw in raw_res:
            res['hits']['hits'] += raw['docs']
        if res['hits']['hits']:
            for t in res.get('hits').get('hits'):
                t['_source']['fileinfo'] = \
                    [x.get('_source') for x in file_result['hits']['hits'] if x.get('_id') == t.get('_id')][0]
                if t.get('_type') in ['muc_msg', 'mucgro']:
                    if utils.common_sql.if_async:
                        __res = await self.userlib.get_mucs_info(muc=t['_source']['realto'])
                    else:
                        __res = self.userlib.get_mucs_info(muc=t['_source']['realto'])
                    t['_source']['source'] = __res['show_name']
                elif t.get('_type') in ['message', 'msggro']:
                    if t['_source']['realfrom'] == self.user:
                        if utils.common_sql.if_async:
                            __res = await self.userlib.get_person_info(self.user)
                        else:
                            __res = self.userlib.get_person_info(self.user)
                        t['_source']['source'] = __res['show_name']
                    else:
                        if utils.common_sql.if_async:
                            __res = await self.userlib.get_person_info(t['_source']['realto'])
                        else:
                            __res = self.userlib.get_person_info(t['_source']['realto'])
                        t['_source']['source'] = __res['show_name']
            return res
        else:
            return None

    async def make_result(self, response, label, resultType, todoType, offset, limit, agg_tag=False):
        result = []
        if agg_tag:
            __response = response['aggregations']['conversation_aggs']['buckets']
            # __response = [x.get('top_conversation_hits').get('hits').get('hits').get('_source') for x in
            #               response['aggregations']['conversation_aggs']['buckets']]
            if len(__response) < offset + limit:
                has_more = False
            else:
                has_more = True
            # for __t in __response[offset:offset + limit - 1]:
            for __t in __response:
                res = __t.get('top_conversation_hits').get('hits').get('hits')[0].get('_source')
                __res = {
                    "body": res.get('raw_body', ''),
                    "msgid": res.get('msgid', ''),
                    "from": res.get('from', ''),
                    "to": res.get('to', ''),
                    # "from": _from,
                    # "to": _to,
                    "realfrom": res.get('realfrom', ''),
                    "realto": res.get('realto', ''),
                    "mtype": res.get('mtype', ''),
                    "time": res.get('time', ''),
                    "date": res.get('date', ''),
                    "extendinfo": res.get('extendinfo', ''),
                    'todoType': todoType
                }
                if label == '单人历史':
                    if res.get('msg'):
                        qchatid = text_handler.get_qchatid(res.get('msg'))
                        if qchatid:
                            __res['qchatid'] = qchatid
                if resultType == 32:
                    __res['fileinfo'] = res.get('fileinfo', '')
                    __res["source"] = res.get("source", "")
                if agg_tag:
                    __res['count'] = __t.get('doc_count')
                result.append(__res)
        else:
            __response = [x.get('_source') for x in response['hits']['hits']]
            has_more = True if len(__response) > self.limit else False
            for res in __response[:limit - 1]:
                __res = {
                    "body": res.get('raw_body', ''),
                    "msgid": res.get('msgid', ''),
                    "from": res.get('from', ''),
                    "to": res.get('to', ''),
                    # "from": _from,
                    # "to": _to,
                    "realfrom": res.get('realfrom', ''),
                    "realto": res.get('realto', ''),
                    "mtype": res.get('mtype', ''),
                    "time": res.get('time', ''),
                    "date": res.get('date', ''),
                    "extendinfo": res.get('extendinfo', ''),
                    'todoType': todoType
                }
                if label == '单人历史':
                    if res.get('chat_type') == 'consult' and res.get('qchatid'):
                        __res['qchatid'] = res.get('qchatid')
                    elif res.get('msg'):
                        qchatid = text_handler.get_qchatid(res.get('msg'))
                        if qchatid:
                            __res['qchatid'] = qchatid
                if resultType == 32:

                    __res['fileinfo'] = res.get('fileinfo', {})
                    # 20190702 视频格式的fileinfo没有fileurl以及MD5， 从extendinfo里补偿
                    if __res['fileinfo'] and ('FILEMD5' not in __res['fileinfo'] or 'HttpUrl' not in __res['fileinfo']):
                        if not __res['extendinfo']:
                            continue
                        try:
                            __extendinfo = json.loads(__res['extendinfo'])
                            if not isinstance(__extendinfo, dict):
                                continue
                        except:
                            continue
                        if 'FileUrl' in __extendinfo.keys():
                            __url = __extendinfo.get('FileUrl')
                            __res['fileinfo']['HttpUrl'] = __url
                            __res['fileinfo']['FILEMD5'] = md5(__url)
                        else:
                            continue

                    __res["source"] = res.get("source", "")
                result.append(__res)

        final_result = {}
        final_result['info'] = result
        final_result['groupLabel'] = label
        final_result['resultType'] = resultType
        final_result['todoType'] = todoType
        final_result['hasMore'] = has_more
        # final_result['groupLabel'] =
        return final_result

    @staticmethod
    def handle_user_mucs(mucs):
        """
        由于es搜索有dsl字数上限， 将群组分开搜索
        :param mucs:
        :return:
        """
        if not isinstance(mucs, list):
            return []
        _len = len(mucs)
        if _len <= MUC_SPLIT_SIZE:
            return [mucs]
        result = []
        splices = (_len // MUC_SPLIT_SIZE) + 1
        for i in range(splices):
            result.append(mucs[i * MUC_SPLIT_SIZE:(i + 1) * MUC_SPLIT_SIZE])
        return result

    @staticmethod
    def handle_muc_coro_result(res):
        hits = []
        aggs = []
        for i in res:
            if i.get('hits', {}).get('total', ''):
                hits.extend(i['hits']['hits'])
            if i.get('aggregations', {}).get('conversation_aggs', {}).get('buckets', {}):
                aggs.extend(i['aggregations']['conversation_aggs']['buckets'])

        result = {}
        # TODO 排序
        if hits:
            result['hits'] = {
                "total": len(hits),
                "hits": hits
            }
        if aggs:
            result['aggregations'] = {
                "conversation_aggs": {
                    "buckets": aggs
                }
            }
        return result
