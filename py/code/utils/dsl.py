#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'
import random
from conf.es_params_define import saas
from elasticsearch import Elasticsearch, helpers
import re

def escape(a):
    quot_pattern = re.compile(r"&quot;")
    lt_pattern = re.compile(r"&lt;")
    gt_pattern = re.compile(r"&gt;")
    a = quot_pattern.sub("\"", a)
    a = lt_pattern.sub("<", a)
    a = gt_pattern.sub(">", a)
    return a


def conn_es():
    rand = random.randint(0, 2)
    url = saas[rand]
    es = Elasticsearch(url)
    return es


class DSL:

    def __init__(self):
        pass

    def make_filter(self, qtalkid, domain, to_user='', to_muc='', starttime='', endtime='', action=0, _type='',filetype=''):
        """
            "filter": {
                    "bool": {
                        "must":[{
                                "range": {
                                    "time": {
                                        "gte": 154469680207
                                    }
                                }
                            }],
                        "should": [{
                                "term": {
                                    "from": "jingyu.he"
                                }
                            },
                            {
                                "term": {
                                    "to": "asdf"
                                }
                            }
                        ],
                       "minimum_should_match": "1"
                    }
                }
        :param qtalkid: 搜索者
        :param to_user: 人（们）
        :param to_muc: 群（们）#需要添加人是否在群的验证
        :param starttime: 开始时间 (long / string)
        :param endtime: 结束时间
        :return:es filtered请求的部分

        """
        filter_bool_must = list()
        filter_bool_should = list()
        must_time = dict()
        _filter = dict()
        # qtalkid = qtalkid + '@' + domain
        # 制作单人filter
        if action == 32:
            if to_muc:
                filter_bool_should.extend([{'term': {'to': i}} for i in to_muc])
            if to_user:

                if isinstance(to_user, list):
                    # raw_user_arr = [to_user]
                    user_arr = map(lambda x: sorted([qtalkid, x])[0] + '_' + sorted([qtalkid, x])[1], to_user)
                    filter_bool_should.extend([{'term': {'conversation': i}} for i in user_arr])
                elif isinstance(to_user, str):
                    user_arr = sorted([qtalkid, to_user])[0] + '_' + sorted([qtalkid, to_user])[1]
                    filter_bool_should.extend([{'term': {'conversation': user_arr}} ])
                else:
                    raise TypeError("TO USER ILLEGAL {}".format(to_user))
            if qtalkid:
                filter_bool_should.extend([{'term': {'from': qtalkid}}, {'term': {'to': qtalkid}}])
        else:
            if to_user and not to_muc:
                if isinstance(to_user, list):
                    # raw_user_arr = [to_user]
                    user_arr = map(lambda x: sorted([qtalkid, x])[0] + '_' + sorted([qtalkid, x])[1], to_user)
                    filter_bool_should.extend([{'term': {'conversation': i}} for i in user_arr])
                elif isinstance(to_user, str):
                    user_arr = sorted([qtalkid, to_user])[0] + '_' + sorted([qtalkid, to_user])[1]
                    filter_bool_should.extend([{'term': {'conversation': user_arr}} ])
                else:
                    raise TypeError("TO USER ILLEGAL {}".format(to_user))

            # 制作群filter 不应与单人同时制作
            elif not to_user and to_muc:

                if isinstance(to_muc, str):
                    filter_bool_should.extend([{'term': {'to': to_muc}} ])
                elif isinstance(to_muc, list):
                    filter_bool_should.extend([{'term': {'to': i}} for i in to_muc])
            elif qtalkid:
                filter_bool_should = [{'term': {'from': qtalkid}}, {'term': {'to': qtalkid}}]

        if starttime:
            must_time['gte'] = starttime
        if endtime:
            must_time['lte'] = endtime
        if must_time or _type or filetype:
            filter_bool_must = []
            if filetype:
                filter_bool_must.append({
                    'term': {
                        'type': filetype
                    }
                })
            if _type:
                filter_bool_must.append({
                    'term': {
                        '_type': _type
                    }
                })

            if must_time:
                filter_bool_must.append({
                    'range': {
                        'time': must_time
                    }
                })
        filter_bool = dict()
        if filter_bool_must:
            filter_bool['must'] = filter_bool_must
        if filter_bool_should:
            filter_bool['should'] = filter_bool_should
            filter_bool['minimum_should_match'] = 1
        if filter_bool:
            _filter['bool'] = filter_bool
        return _filter

    def make_aggs(self, name, method, field, extra):
        """
        python versiton must greater >= 3.5
        :param name: agg名
        :param method: min, max, sum, avg, stats, top_hits, terms, range, date_range, histogram, date_histogram
        :param field: from / conversation / date ...
        :param extra: 特定method所需要
        :return:aggs
        """
        aggs = dict()
        if method in ['min', 'max', 'sum', 'avg', 'stats']:
            aggs = {
                name: {
                    method: {
                        "field": field
                    }
                }
            }
        elif method == 'top_hits':
            aggs = {
                name: {
                    method: extra
                }
            }
        elif method == 'terms':
            temp = {
                'field': field,
                "execution_hint": "map"
            }
            if isinstance(extra, dict):
                temp = {**temp, **extra}
            aggs = {
                name: {
                    method: temp
                }
            }
        elif method in ['range', 'date_range', 'histogram', 'date_histogram']:
            temp = {
                'field': field
            }
            if isinstance(extra, dict):
                temp = {**temp, **extra}
            aggs = {
                name: {
                    method: temp
                }
            }
        else:
            if isinstance(extra, dict):
                temp = {
                    'field': field
                }
                temp = {**temp, **extra}
                aggs = {
                    name: {
                        method: {
                            temp
                        }
                    }
                }
        return aggs

    def make_query(self, method, field, term):
        """
        for example:
            "query": {
                            "wildcard": {
                                "body": "*{}*".format(keyword)
                            }
                        },
        :param method:
        :param field:
        :param term:
        :return:
        """
        if method == 'wildcard':
            term = '*{}*'.format(term)
        query = {
            method: {
                field: term
            }
        }
        return query

    def mget(self, offset, limit=20):
        """
            for example:
                # offset = 403171186
                # limit = 5
                # fromUser = 'jingyu.he'
                # ids = [dict(_id=i, _from=fromUser) for i in range(offset, offset + limit)]
                # dsl = {
                #     "docs": ids
                # }
                # result = es.mget(index="first_index", doc_type="message", body=dsl)
                # print(result)
        :param offset:
        :param limit:
        :return:
        """
        ids = [dict(_id=i) for i in range(offset, offset + limit)]
        dsl = {
            "docs": ids
        }
        return dsl

    def multi_index(self):

        dsl = {
            "query": {
                "bool": {
                    "must": {
                        "range": {
                            "id": {"lte": 403171183}
                        }
                    },
                    "should": [
                        {"term": {"from": "jingyu.he"}},
                        {"term": {"to": "jingyu.he"}}
                    ],
                    "minimum_should_match": 1
                }
            },
            "sort": [
                {"_id": {"order": "desc"}}
            ],
            "size": 10
        }
        indexes = ["aaa_{}".format(i) for i in range(4, 12)]

    def single_wildcard(self, keyword, _from, size, offset):
        """

        :param keyword: 关键词
        :param _from: 群id/
        :param size:
        :param offset:
        :return:
        """
        dsl = {
            "query": {
                "filtered": {
                    "query": {
                        "wildcard": {
                            "body": "*{}*".format(keyword)
                        }
                    },
                    "filter": {
                        "bool": {
                            "should": [
                                {"term": {"from": "{}".format(_from)}},
                            ]
                        }
                    }
                }
            },
            "from": offset,
            "size": size
        }
        return dsl

