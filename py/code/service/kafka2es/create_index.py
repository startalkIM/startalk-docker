#!/usr/bin/env python
# -*- coding:utf-8 -*-
import random
import time
import elasticsearch
from elasticsearch import Elasticsearch
from conf.es_params_define import SAAS, CREATE_INDEX_DSL
from utils.time_utils import TimeUtils


def conn_es():
    rand = random.randint(0, 2)
    url = SAAS[rand]
    _es = Elasticsearch(url)
    _es.cluster.health(wait_for_status='yellow', request_timeout=1)

    return Elasticsearch(url)


def get_index_name():
    time_utils = TimeUtils()
    index = time_utils.get_next_month_index()
    indexes = ['qc' + '_' + index, index]
    return indexes


if __name__ == '__main__':
    es = conn_es()
    es_index = get_index_name()
    for index in es_index:
        try:
            res = es.indices.create(index=index, body=CREATE_INDEX_DSL)
            print('{}'.format(res))
            if res.get('acknowledged', False):
                print('create index {} success!'.format(index))
        except elasticsearch.exceptions.RequestError as e:
            print('create index {} failed! error : '.format(index, e.error))


