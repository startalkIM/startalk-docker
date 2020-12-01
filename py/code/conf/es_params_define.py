#!/usr/bin/env python
# -*- coding:utf-8 -*-

from utils.logger_conf import configure_logger
from utils.get_conf import get_logger_file, get_config_file

config = get_config_file()
saas = config['elasticsearch'].get('saas')
if saas:
        SAAS = tuple(saas.split(','))
else:
        SAAS = None
CREATE_INDEX_DSL  = {
    'mappings': {
        'message': {
            'properties': {
                'msg': {'index': 'not_analyzed', 'type': 'string'},
                'body': {'index': 'analyzed', 'type': 'string', 'analyzer': 'ik_smart', 'search_analyzer': 'ik_smart',
                         'search_quote_analyzer': 'ik_smart'},
                'raw_body': {'index': 'not_analyzed', 'type': 'string'},
                'msgid': {'index': 'not_analyzed', 'type': 'string'},
                'id': {'index': 'not_analyzed', 'type': 'string'},
                'from': {'index': 'not_analyzed', 'type': 'string'},
                'realfrom': {'index': 'not_analyzed', 'type': 'string'},
                'to': {'index': 'not_analyzed', 'type': 'string'},
                'realto': {'index': 'not_analyzed', 'type': 'string'},
                'mtype': {'index': 'not_analyzed', 'type': 'integer'},
                'time': {'index': 'not_analyzed', 'type': 'long'},
                'date': {'index': 'not_analyzed', 'type': 'date', 'format': 'yyyy-MM-dd HH:mm:ss'},
                'tag': {'index': 'not_analyzed', 'type': 'integer'},
                'conversation': {'index': 'not_analyzed', 'type': 'string'},
                'qchatid': {'index': 'not_analyzed', 'type': 'integer'},
            }
        },
        'muc_msg': {
            'properties': {
                'msg': {'index': 'not_analyzed', 'type': 'string'},
                'body': {'index': 'analyzed', 'type': 'string', 'analyzer': 'ik_smart', 'search_analyzer': 'ik_smart',
                         'search_quote_analyzer': 'ik_smart'},
                'raw_body': {'index': 'not_analyzed', 'type': 'string'},
                'msgid': {'index': 'not_analyzed', 'type': 'string'},
                'id': {'index': 'not_analyzed', 'type': 'string'},
                'from': {'index': 'not_analyzed', 'type': 'string'},
                'realfrom': {'index': 'not_analyzed', 'type': 'string'},
                'to': {'index': 'not_analyzed', 'type': 'string'},
                'realto': {'index': 'not_analyzed', 'type': 'string'},
                'mtype': {'index': 'not_analyzed', 'type': 'integer'},
                'time': {'index': 'not_analyzed', 'type': 'long'},
                'date': {'index': 'not_analyzed', 'type': 'date', 'format': 'yyyy-MM-dd HH:mm:ss'},
                'tag': {'index': 'not_analyzed', 'type': 'integer'},
                'conversation': {'index': 'not_analyzed', 'type': 'string'},
            }
        },
        "msggro": {
            "_parent": {
                "type": "message"
            },
            "properties": {
                'from': {'index': 'not_analyzed', 'type': 'string'},
                'realfrom': {'index': 'not_analyzed', 'type': 'string'},
                'to': {'index': 'not_analyzed', 'type': 'string'},
                'realto': {'index': 'not_analyzed', 'type': 'string'},
                'date': {'index': 'not_analyzed', 'type': 'date','format': 'yyyy-MM-dd HH:mm:ss'},
                'time': {'index': 'not_analyzed', 'type': 'long'},
                'conversation': {'index': 'not_analyzed', 'type': 'string'}
            }
        },
        "mucgro": {
            "_parent": {
                "type": "muc_msg"
            },
            "properties": {
                'from': {'index': 'not_analyzed', 'type': 'string'},
                'realfrom': {'index': 'not_analyzed', 'type': 'string'},
                'to': {'index': 'not_analyzed', 'type': 'string'},
                'realto': {'index': 'not_analyzed', 'type': 'string'},
                'date': {'index': 'not_analyzed', 'type': 'date','format': 'yyyy-MM-dd HH:mm:ss'},
                'time': {'index': 'not_analyzed', 'type': 'long'},
                'conversation': {'index': 'not_analyzed', 'type': 'string'}
            }
        },
        "msgext": {
            "_parent": {
                "type": "message"
            },
            "properties": {
                'from': {'index': 'not_analyzed', 'type': 'string'},
                'realfrom': {'index': 'not_analyzed', 'type': 'string'},
                'to': {'index': 'not_analyzed', 'type': 'string'},
                'realto': {'index': 'not_analyzed', 'type': 'string'},
                'date': {'index': 'not_analyzed', 'type': 'date','format': 'yyyy-MM-dd HH:mm:ss'},
                'time': {'index': 'not_analyzed', 'type': 'long'},
                'conversation': {'index': 'not_analyzed', 'type': 'string'}
            }
        },
        "mucext": {
            "_parent": {
                "type": "muc_msg"
            },
            "properties": {
                'from': {'index': 'not_analyzed', 'type': 'string'},
                'realfrom': {'index': 'not_analyzed', 'type': 'string'},
                'to': {'index': 'not_analyzed', 'type': 'string'},
                'realto': {'index': 'not_analyzed', 'type': 'string'},
                'date': {'index': 'not_analyzed', 'type': 'date','format': 'yyyy-MM-dd HH:mm:ss'},
                'time': {'index': 'not_analyzed', 'type': 'long'},
                'conversation': {'index': 'not_analyzed', 'type': 'string'}
            }
        }
    }
}