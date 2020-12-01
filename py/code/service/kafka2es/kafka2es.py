#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import json
import datetime
import time
from xml.etree import ElementTree as eTree
import random
import traceback
import collections
from elasticsearch import Elasticsearch, helpers
from kafka import KafkaConsumer
from utils.get_conf import get_logger_file, get_config_file, get_project_dir
from conf.es_params_define import *
from conf.kakfa2es_params_define import *
from utils.regex_utils import *
from utils.time_utils import TimeUtils
from utils.common_sql import UserLib, domain

project_path = get_project_dir()
log_path = get_logger_file(name='es.log')
es_logger = configure_logger('search', log_path)
if not isinstance(domain, str):
    domain = 'UNKNOWN'

time_utils = TimeUtils()

get_specific_ymd = time_utils.get_specific_ymd
get_ymd_agg = time_utils.get_ymd_agg
robot_list = ['']  # 填写不想入库的用户id


def get_msg_queues():
    group_id = GROUP_ID
    qtalk_chat_topic = CHAT_TOPIC
    qtalk_group_topic = GROUP_TOPIC
    consumer_zookeeper_params = CONSUMER_ZOOKEEPER
    consumer = KafkaConsumer(qtalk_chat_topic, qtalk_group_topic,
                             bootstrap_servers=consumer_zookeeper_params.split(","), group_id=group_id,
                             max_partition_fetch_bytes=10 * 1024 * 1024, value_deserializer=lambda m: m.decode(),
                             key_deserializer=lambda m: m.decode())
    for msg in consumer:
        key = msg.key
        if key not in ['chat', 'groupchat', 'revoke', 'consult']:
            continue
        value = msg.value
        value = json.loads(value)
        if key in ['chat', 'groupchat', 'consult']:
            try:
                #  ------------------------------------  找到除id和date以外的参数  ------------------------------------
                _msg_id = value.get("msg_id")
                if key == "groupchat":
                    _tohost = value.get("room_host")
                    if 'ejabhost1' not in _tohost:
                        continue
                    _msg = value.get("packet")  # msg
                    root = eTree.fromstring(_msg)
                    _chattype = root.get('type')
                    body = root.find("body")
                    _from = value.get('realfrom')
                    _to = value.get("muc_room_name") + '@' + value.get("room_host")
                    _time = root.attrib['msec_times']  # time 1542877246165 ms 可能是int
                    _body = body.text
                    _mtype = body.attrib["msgType"]
                    _conversation = _from + '_' + _to
                    doc_type = 'muc_msg'
                elif key in ["chat", "consult"]:
                    _tohost = value.get("to_host", domain)
                    _msg = value.get("m_body")
                    root = eTree.fromstring(_msg)
                    _chattype = root.get('type')
                    _from = value.get("m_from") + '@' + value.get("from_host", domain)
                    _to = value.get("m_to") + '@' + _tohost
                    _time = root.attrib['msec_times']  # time 1542877246165 ms 可能是int
                    body = root.find("body")
                    _body = body.text
                    _mtype = body.attrib["msgType"]
                    _conversation = sorted([_from, _to])[0] + '_' + sorted([_from, _to])[1]
                    doc_type = 'message'
                    if key == "consult":
                        _qchatid = root.attrib.get('qchatid', None)
                else:  # TODO: 应该会有revoke漏掉，kafka那里没判断这里还是撤回一下吧
                    es_logger.exception("WHAT IS THIS: %s,", msg)
                    continue

                #  ------------------------------------  黑名单  ------------------------------------
                if '@' in _from:
                    if _from.split('@')[0] in robot_list:
                        continue
                else:
                    if _from in robot_list:
                        continue

                #  ------------------------------------  查找real和backupextend信息 ------------------------------------
                if 'sendjid' in root.attrib:
                    _realfrom = root.attrib.get('sendjid', _from)
                elif 'realfrom' in root.attrib:
                    _realfrom = root.attrib.get('realfrom', _from)
                else:
                    _realfrom = _from
                if 'realto' in root.attrib:
                    _realto = root.attrib.get('realto', _to)
                else:
                    _realto = _to

                #  ------------------------------------  找id  ------------------------------------
                _id = get_msg_id(_msg_id, doc_type)  # 从取到消息到从db拿到id需要大约4ms
                if not _id:
                    es_logger.error('msg_id : %s FAILED', _msg_id)
                    es_logger.error(msg)
                    if doc_type == 'message':
                        with open(project_path + '/log/{dateformat}_msgidfailed.log'.format(
                                dateformat=datetime.datetime.today().strftime('%Y-%m-%d')), 'a+') as f:
                            f.write('{}\n'.format(_msg_id))
                    elif doc_type == 'muc_msg':
                        with open(project_path + '/log/{dateformat}_mucidfailed.log'.format(
                                dateformat=datetime.datetime.today().strftime('%Y-%m-%d')), 'a+') as f:
                            f.write('{}\n'.format(_msg_id))
                    continue

                #  ------------------------------------  制作dsl  ------------------------------------
                doc_body = {
                    'msg': _msg,
                    'body': _body,
                    'raw_body': _body,
                    'msgid': _msg_id,
                    'id': _id,
                    'from': _from,
                    'to': _to,
                    'conversation': _conversation,
                    'realfrom': _realfrom,
                    'realto': _realto,
                    'mtype': _mtype,
                    'time': _time,
                    'doc_type': doc_type,
                    'chat_type': _chattype
                }
                extendinfo = body.attrib.get("extendInfo", "")
                if extendinfo:
                    extend_dict = {'extendinfo': extendinfo}
                    doc_body = {**doc_body, **extend_dict}
            except Exception as e:
                es_logger.error("DATA ERROR: %s", e)
                es_logger.error("msg : {}".format(msg))
                es_logger.error(traceback.format_exc())
                continue
            handle_body(doc_body)
        elif key == 'revoke':
            try:
                topic = msg.topic
                _tohost = value.get("to_host", domain)
                _msg_id = value.get("msg_id")
                # doc_type = 'muc_msg' if topic == 'custom_vs_hash_hosts_group_message' else 'message'
                doc_type = "muc_msg" if "conference" in value.get("to_host") else "message"
                _id = get_msg_id(_msg_id, doc_type)
                if not _id:
                    es_logger.error('msg_id : %s FAILED', _msg_id)
                    es_logger.error(msg)
                    if doc_type == 'message':
                        with open(project_path + '/log/{dateformat}_msgidfailed.log'.format(
                                dateformat=datetime.datetime.today().strftime('%Y-%m-%d')), 'a+') as f:
                            f.write('{}\n'.format(_msg_id))
                    elif doc_type == 'muc_msg':
                        with open(project_path + '/log/{dateformat}_mucidfailed.log'.format(
                                dateformat=datetime.datetime.today().strftime('%Y-%m-%d')), 'a+') as f:
                            f.write('{}\n'.format(_msg_id))
                    es_logger.error('REVOKE msg_id : %s, time : %s FAILED', _msg_id, time.time())
                    continue
                _msg = value.get("m_body")
                root = eTree.fromstring(_msg)
                _from = value.get("m_from") + '@' + value.get("from_host", domain)
                _to = value.get("m_to") + '@' + _tohost
                _time = root.attrib['msec_times']  # time 1542877246165 ms 可能是int
                _conversation = sorted([_from, _to])[0] + '_' + sorted([_from, _to])[1]
                doc_body = {
                    'msg': _msg,
                    'body': '',
                    'raw_body': '[撤回一条消息]',
                    'msgid': _msg_id,
                    'id': _id,
                    'from': _from,
                    'to': _to,
                    'conversation': _conversation,
                    'mtype': '-1',
                    'time': _time,
                    'doc_type': doc_type,
                    'chat_type': 'revoke'
                }
                year, mon = time_utils.get_specific_ymd(_time)
                es_index = 'message_' + str(year) + '_' + str(mon)
                revoke_es(es_index, doc_body)
            except Exception as e:
                es_logger.exception("REVOKE_DATA ERROR: %s", e)
                continue
    consumer.close()


def revoke_es(index, doc_body):
    try:
        # index = 'pythontest'
        es = conn_es()
        id = doc_body['id']
        type = doc_body.pop('doc_type')
        exists = es.exists(index=index, doc_type=type, id=id)
        if exists:
            rev_doc = {
                "doc": {
                    "body": "[撤回一条消息]"
                }
            }
            es.update(index=index, doc_type=type, id=id, body=rev_doc)  # TODO:改成 index
        else:
            try:
                es.index(index=index, doc_type=type, id=id, body=doc_body)
            except Exception as e:
                doc_body.pop('msg')
                es.index(index=index, doc_type=type, id=id, body=doc_body)
    except Exception as e:
        es_logger.error("es_revoke ERROR: %s", e)


def msg2es(index, type, id, body):
    try:
        es = conn_es()
        res = es.index(index=index, doc_type=type, id=id, body=body)
        return res
    except Exception as e:
        es_logger.error("es ERROR: %s", e)
        es_logger.error("es ERROR, body: %s", body)
        return None


def conn_es():
    rand = random.randint(0, 2)
    url = SAAS[rand]
    _es = Elasticsearch(url)
    _es.cluster.health(wait_for_status='yellow', request_timeout=1)
    return Elasticsearch(url)


def get_last_line(file):
    with open(file, 'r') as f:
        try:
            return f.read().splitlines()[-1]
        except:
            return None


def handle_body(content):
    raw_body = content['body']
    if not raw_body:
        es_logger.warning(content)
        return
    body_length = len(raw_body)
    if body_length > 60000:
        return
    elif body_length > 20000:
        content['body'] = '…'
        content['raw_body'] = '…'
        content['msg'] = content['msg'][:20000] + '…'
    body = raw_body
    gros = ''
    msec_time = content['time']
    timeagg = time_utils.get_ymd_agg(msec_time)
    _date = time.strftime("%Y-%m-%d %H:%M:%S", timeagg)
    es_index = 'message_' + str(timeagg.tm_year) + '_' + str(timeagg.tm_mon)
    es = conn_es()
    doc_type = content.pop('doc_type')
    extendinfo = content.get("extendinfo", "")
    if extendinfo:
        if isinstance(extendinfo, str):
            if '[obj' in extendinfo:
                extendinfo = ''
            else:
                try:
                    extendinfo = json.loads(extendinfo, strict=False)
                except:
                    es_logger.info('MSG {} LOADS EXTENDINFO FALIED'.format(content['id']))
                    es_logger.exception(extendinfo)
                    extendinfo = ''

    # -------------------------------  按照msgtype分类处理  -------------------------------
    if content['mtype'] in ['1', '30']:
        tag, body, gros = handle_normal(raw_body)  # gros是一个以名字为分类里面有很多dict的list
    elif content['mtype'] == '2':
        child_type = 'voice'
        tag, body, gros = handle_voice(raw_body)
    elif content['mtype'] == '5':
        child_type = 'file'
        tag, body, gros = handle_file(raw_body)
    elif content['mtype'] == '32':
        if url_pattern.search(raw_body):
            child_type = 'video'
            tag, body, gros = handle_video(raw_body)
        else:
            tag = 0
    elif content['mtype'] == '64':
        child_type = 'code'
        content['msg'] = ''
        content['extendinfo'] = ''
        tag, body, gros = handle_code(raw_body)
    elif content['mtype'] in ['666', '667']:  # TODO: 666消息种类实在太多了， 需要看extendinfo和body结合起来啥样
        try:
            _extendinfo = content.get('extendinfo', '')
            child_type = 'ball'
            tag, _extendinfo, gros = handle_ball(_extendinfo)
        except Exception as e:
            es_logger.exception('{}'.format(content))


    else:
        tag = 0
    # -------------------------------  先插父消息再插子消息  -------------------------------
    content['date'] = _date
    content['body'] = body
    content['tag'] = tag
    res = msg2es(index=es_index, type=doc_type, id=content['id'], body=content)
    if not res:  # todo 这里改为失败而不是
        es_logger.error("INDEX MSG TO ES FALIED, content : {}, response {}".format(content, res))
    if tag:
        try:
            if not len(gros):
                es_logger.warning('gros lens is 0')
                es_logger.warning(content['msg'])
            _type = 'msggro' if doc_type == 'message' else 'mucgro'
            if tag == 1:
                for child_type, value in gros.items():
                    to_be_bulk = list()
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                item['type'] = child_type
                                item['conversation'] = content['conversation']
                                item['from'] = content['from']
                                item['to'] = content['to']
                                item['time'] = content['time']
                                item['date'] = content['date']
                                if 'widhth' in item or 'height' in item:
                                    if isinstance(item['width'], str):
                                        item['width'] = item['width'].split('.')[0]
                                    if isinstance(item['height'], str):
                                        item['height'] = item['height'].split('.')[0]
                                to_be_bulk.append(item)
                                resource = [
                                    {'_index': es_index, '_type': _type, '_parent': content['id'], '_id': content['id'],
                                     '_source': k} for k in to_be_bulk]  # gros是一个list里有一堆字典
                                helpers.bulk(es, resource)
                            else:
                                es_logger.exception('gros collections content type error not dict')
            else:
                try:
                    gros['type'] = child_type
                    gros['conversation'] = content['conversation']
                    gros['from'] = content['from']
                    gros['to'] = content['to']
                    gros['time'] = content['time']
                    gros['date'] = content['date']
                    es.index(index=es_index, doc_type=_type, parent=content['id'], id=content['id'], body=gros)
                except:
                    es_logger.error('dict-gro indexed failed')
                    return None
        except Exception as e:
            es_logger.error('insert tag∑ error')
            es_logger.exception(e)
    # -------------------------------  处理extend和backupinfo  -------------------------------
    if extendinfo:
        _type = 'msgext' if doc_type == 'message' else 'mucext'
        if isinstance(extendinfo, dict):
            if not extendinfo.get('title', '') in ['报警']:
                try:
                    extendinfo['conversation'] = content['conversation']
                    extendinfo['from'] = content['from']
                    extendinfo['to'] = content['to']
                    extendinfo['time'] = content['time']
                    extendinfo['date'] = content['date']
                    es.index(index=es_index, doc_type=_type, parent=content['id'], id=content['id'],
                             body=extendinfo)
                except:
                    return 'extendinfo indexed failed'
        elif isinstance(extendinfo, list):
            for _extend in extendinfo:
                if isinstance(_extend, dict):
                    _extend['conversation'] = content['conversation']
                    _extend['from'] = content['from']
                    _extend['to'] = content['to']
                    _extend['time'] = content['time']
                    _extend['date'] = content['date']
                    try:
                        es.index(index=es_index, parent=content['id'], doc_type=_type, id=content['id'], body=_extend)
                    except Exception as e:
                        es_logger.exception('EXTEND INFO INDEX FAILED {}'.format(extendinfo))
                        es_logger.warning('list extendinfo has wrong content')
                        es_logger.warning(_extend)
                else:
                    print('list extendinfo has wrong content')
                    print(_extend)


def handle_normal(body):
    """
    :param body: 原文内容
    :return:
        tag - int
        gros - collection.defaultdict(list) (key - [value1, value2])
        body - string
    """
    cata_dicts = collections.defaultdict(list)
    res = spe_pattern.findall(body)
    tag = 0
    if res:
        try:
            for gro_num, i in enumerate(res):
                ii = i.strip('[]')
                grotype = type_pattern.findall(ii)
                if len(grotype) == 1:
                    grotype = grotype[0]
                    if grotype == 'emoticon':
                        value = value_pattern.findall(ii)
                        if value:
                            value = value[0]
                        width = width_pattern.findall(ii)
                        if width:
                            width = width[0]
                        body = body.replace(i, '[emo_{value}_{width}]'.format(value=value, width=width))
                    else:
                        tag = 1
                        r_dicts = filter(lambda x: '=' in x, ii.split())
                        # r_dicts = filter(lambda x: '=' in x and 'width' not in x and 'height' not in x, ii.split())
                        attrib_dict = {}
                        for e in r_dicts:
                            e = e.strip('["]')
                            attrib_dict[e.split('=', 1)[0].strip('["]')] = \
                                e.split('=', 1)[1].strip('["]')
                        attrib_dict['order'] = gro_num + 1
                        try:
                            if 'width' in attrib_dict:
                                attrib_dict['width'] = float(attrib_dict['width'])
                            if 'height' in attrib_dict:
                                attrib_dict['width'] = float(attrib_dict['height'])
                        except Exception as e:
                            es_logger.exception(e)
                        cata_dicts[grotype].append(attrib_dict)
                        body = body.replace(i, '[{}_{}]'.format(grotype, str(gro_num + 1)))
                else:
                    es_logger.error("get normal error %s", body)
        except Exception as e:
            es_logger.exception('handle_normal error, origin \n {}'.format(body))

    else:
        cata_dicts = None
    return tag, body, cata_dicts


def handle_voice(body):
    """
    :param body: 原文内容
    :return:
        tag - int
        gros - dict
        body - string
    """
    tag = 0
    try:
        if isinstance(body, str):
            v_content = json.loads(body)
            body = '[voice]'
            gro = v_content
            tag = 2
    except:
        es_logger.error("get voice error %s", body)
        gro = None
    return tag, body, gro


def handle_file(body):
    """
    :param body: 原文内容
    :return:
        tag - int
        gros - dict
        body - string
    """
    tag = 0
    try:
        if isinstance(body, str):
            v_content = json.loads(body)
            body = '[file]'
            gro = v_content
            tag = 3
    except:
        es_logger.error("get voice error %s", body)
        gro = None
    return tag, body, gro


def handle_video(body):  # TODO:缩略图什么的。。？
    """
    :param body: 原文内容
    :return:
        tag - int
        gros - dict
        body - string
    """
    tag = 0
    try:
        res = spe_pattern.findall(body)
        video_normal = video_pattern.findall(body)
        video_send = send_video_pattern.findall(body)
        video_url = ''
        if res:
            video_url = value_pattern.findall(body)[0]
        elif video_normal:
            video_url = video_normal[0]
        elif video_send:
            video_url = video_send[0]
        gro = {'url': video_url}
        body = '[video]'
        tag = 4
    except Exception as e:
        es_logger.exception("get video error %s", body)  # TODO:
        """
         发送了一段视频. [obj type="url" value="{video_url}"]
        """

        gro = None
    return tag, body, gro


def handle_code(body):
    """
    :param body: 原文内容
    :return:
        tag - int
        gros - dict
        body - string [code]
    """
    tag = 0
    try:
        code = {'code': body}
        body = '[code]'
        tag = 5
    except:
        es_logger.error("get code error %s", body)
        code = None
    return tag, body, code


def handle_ball(body):
    """
    :param body: 原文内容
    :return:
        tag - int
        gros - dict
        body - string [share]
    """
    tag = 0
    try:
        gro = json.loads(body)
        body = '[share]'
        tag = 6
    except:
        gro = None
    return tag, body, gro


if __name__ == '__main__':
    userLib = UserLib()
    get_msg_id = userLib.get_msg_id
    get_msg_queues()
    userLib.close()
