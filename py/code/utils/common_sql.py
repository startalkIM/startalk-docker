#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'
import psycopg2
from psycopg2 import sql
import re
import sys
import time
import json
import asyncpg
from collections import defaultdict
from functools import reduce
from utils.get_conf import get_config_file, get_logger_file
from utils.logger_conf import configure_logger
# import conf.constants
# from conf import constants
from conf.cache_params_define import SINGLE_KEY, MUC_KEY, SINGLE_TRACE_KEY, MUC_TRACE_KEY, SINGLE_CACHE, MUC_CACHE
from conf.search_params_define import REGEX_TAG
from utils.redis_utils import redis_cli
from utils.pinyin_util import PinyinUtil
from utils.common_utils import TextHandler
from utils.regex_utils import chinese_pattern
from utils.redis_utils import RedisUtil
from utils.time_utils import TimeUtils
from utils.similar_util import get_similar_bool

time_utils = TimeUtils()
config = get_config_file()
pgconfig = config['postgresql']
host = pgconfig['host']
port = pgconfig['port']
user = pgconfig['user']
database = pgconfig['database']
password = pgconfig['password']
if_cached = config['cache'].getboolean('if_cache')

log_path = get_logger_file('sql.log')
sql_logger = configure_logger('sql', log_path)
if_async = None
user_data = []
# user_data = defaultdict(dict)
# all_user_data = {}

PY_VERSION = re.findall('^([\d\.].*?)\s', sys.version)[0]
DB_VERSION = None
# DB_VERSION = None
# PY_VERSION = PYTHON_VERSION

pinyin = PinyinUtil()
text_handler = TextHandler()
merge_list_of_dict = text_handler.merge_list_of_dict
formulate_text = text_handler.formulate_text
formulate_text_to_uid = text_handler.formulate_text_to_uid
symbol_to_english = text_handler.symbol_to_english


class UserLib:
    def __init__(self, user_id=None):
        # global all_user_data
        global domain
        self.conn = psycopg2.connect(host=host, database=database, user=user, password=password, port=port)
        self.conn.autocommit = True
        __domain = None
        self.user_data = {}
        if user_id and '@' in user_id:
            __domain = user_id.split('@')[1]
            # user_data = all_user_data.get(__domain, {})
            # 制作redis里所有用户的缓存
            if not self.user_data and self.user_data is not None:
                cache_redis_cli = RedisUtil()
                self.user_data = cache_redis_cli.get_all_user_data(domain=__domain)
                if not self.user_data:
                    sql_logger.info("no user data in redis, making one into it..")
                    self.user_data = self.get_user_data(domain=__domain)
                    if self.user_data:
                        cache_redis_cli.set_all_user_data(data=self.user_data, domain=__domain)
                        sql_logger.info("redis user data set..")
                    else:
                        sql_logger.error("NO USER FOUND IN POSTGRESQL!!")
                        self.user_data = None
            if self.user_data is None:
                sql_logger.error("POSTGRESQL STILL NOT SET, IF SET, PLEASE RESTART SERVICE")
                raise ConnectionError("POSTGRESQL IS NOT CONNECTED BECAUSE NO USER FOUND")
        else:
            if isinstance(domain, str):
                __domain = domain
            elif isinstance(domain, list):
                __domain = None
            else:
                raise ValueError("GET FIND DOMAIN FOR USER {}".format(user_id))

        self.domain = __domain

    def get_msg_id(self, msgid, msgtype):
        res = None
        conn = self.conn
        msg_table = 'msg_history' if msgtype == 'message' else 'muc_room_history'
        sql = """SELECT id FROM {} where msg_id = %(msgid)s limit 1;""".format(msg_table)
        cursor = conn.cursor()
        cursor.execute(sql, {'msgid': msgid})
        rs = cursor.fetchall()
        if len(rs):
            res = rs[0][0]
        else:
            for i in range(0, 4):
                time.sleep(0.5)
                sql_logger.info('waiting .. {}'.format(i))
                cursor.execute(sql, {'msgid': msgid})
                rs = cursor.fetchall()
                if not len(rs):
                    if i == 3:
                        res = None
                        break
                    continue
                res = rs[0][0]
                if res:
                    break
        cursor.close()
        return res

    def get_msg_by_msg_ids(self, msgids, msgtype):
        res = None
        s_result = []
        conn = self.conn
        if msgtype in ['chat', 'consult']:
            sql = """select m_body, id, msg_id from msg_history where msg_id = ANY(%(msgids)s) order by id asc"""
        else:
            sql = """select packet, id, msg_id from muc_room_history where msg_id = ANY(%(msgids)s) order by id asc"""
        cursor = conn.cursor()
        cursor.execute(sql, {'msgids': msgids})
        rs = cursor.fetchall()
        for row in rs:
            row = ['' if x is None else x for x in row]
            res = dict()
            res['body'] = row[0]
            res['id'] = row[1]
            res['msg_id'] = row[2]
            s_result.append(res)
        cursor.close()
        return s_result

    def get_domain(self):
        res = []
        conn = self.conn
        sql = """select host from host_info"""
        cursor = conn.cursor()
        cursor.execute(sql)
        rs = cursor.fetchall()
        for row in rs:
            if len(row) == 1:
                res.append(row[0])
        cursor.close()
        return res

    def get_user_data(self, domain=''):
        s_result = defaultdict(dict)
        conn = self.conn
        sql = """select b.username || '@' || b.host as user_id, user_name, pinyin, b.url,a.department,b.mood from host_users a left join vcard_version b on a.user_id = b.username where a.hire_flag = 1 and a.host_id = ANY(select id from host_info where host = %(domain)s )"""
        cursor = conn.cursor()
        cursor.execute(sql, {'domain': domain})
        rs = cursor.fetchall()
        for row in rs:
            row = ['' if x is None else x for x in row]
            res = dict()
            res['i'] = row[0]
            res['n'] = row[1]
            res['p'] = row[2]
            res['u'] = row[3]
            res['d'] = row[4]
            res['m'] = row[5]
            s_result[row[0]] = res
        cursor.close()
        return s_result

    def get_user_mucs(self, user_id, user_domain=''):
        if '@' in user_id:
            user_s_name = user_id.split('@')[0]
            user_domain = user_id.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        s_result = []
        conn = self.conn
        sql = "SELECT muc_name||'@'||domain from user_register_mucs where username = %(user_s_name)s and registed_flag = 1 and host = %(user_domain)s"
        cursor = conn.cursor()
        cursor.execute(sql, {'user_s_name': user_s_name, 'user_domain': user_domain})
        rs = cursor.fetchall()
        for row in rs:
            row = ['' if x is None else x for x in row]
            s_result.append(row[0])
        cursor.close()
        return user_data

    def close(self):
        if self.conn:
            self.conn.close()

    def get_db_version(self):
        _version = False
        conn = self.conn
        sql = "SELECT version();"
        cursor = conn.cursor()
        cursor.execute(sql)
        rs = cursor.fetchall()
        for row in rs:
            row = ['' if x is None else x for x in row]
            _version = row[0]
        _result = re.findall('postgresql\s(\d.*?)\son', _version.lower())
        if _result and len(_result) != 0:
            _version = _result[0]
        else:
            _version = False
        cursor.close()
        return _version

    def get_habit(self, key, habit, form, user, origin=False, common=False):
        if '@' in user:
            user_s_name = user.split('@')[0]
            user_domain = user.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        if not self.user_data:
            self.user_data = self.get_user_data(user_domain)
            if self.user_data:
                cache_redis_cli = RedisUtil()
                cache_redis_cli.set_all_user_data(data=self.user_data, domain=user_domain)
                sql_logger.info("redis user data set..")
        raw_key = key
        key = symbol_to_english(key)
        result = []
        # 搜人的拼音和userid
        if form == 'single':
            _k = SINGLE_CACHE + '_' + user
            __user_data = redis_cli.get(_k)
            if __user_data:
                __user_data = json.loads(__user_data)
            elif habit[SINGLE_TRACE_KEY] or habit[SINGLE_KEY]:
                # user_list = set(habit[SINGLE_TRACE_KEY] + habit[SINGLE_KEY])  # 这里只要userid 不要domain
                user_list = habit[SINGLE_KEY] + list(
                    filter(lambda x: x not in habit[SINGLE_KEY], habit[SINGLE_TRACE_KEY]))
                __user_data = self.single_habit_data(data=user_list, user_domain=user_domain)
                try:
                    __user_data = sorted(__user_data, key=lambda x: user_list.index(x.get('uri', '')))
                    # __user_data = sorted(__user_data, key=lambda x: user_list.index(x.get('qtalkname', '')))
                except ValueError:
                    sql_logger.exception("ORDER PROBLEM : NOT IN LIST")
                redis_cli.set(name=_k, value=json.dumps(__user_data, ensure_ascii=False), ex=60)

            if __user_data:
                sql_logger.debug('user data {}'.format(__user_data))
                # 纯中文
                if not chinese_pattern.sub('', key):
                    sql_logger.debug('修正前 {}'.format(key))
                    key = formulate_text(key)  # 只保留中文
                    sql_logger.debug('修正为标点 {}'.format(key))
                    _r1 = list((filter(lambda x: key in x['name'], __user_data)))
                    # 这里x['name'] 需要是string
                    _r2 = list(filter(lambda x: get_similar_bool(key, x['name']), __user_data))
                    result = merge_list_of_dict(_r1, _r2)
                # 搜索userid 此处不考虑相似度 只全匹配
                elif ('.' in key) or ('_' in key) or ('-' in key):
                    sql_logger.debug('修正前 {}'.format(key))
                    # key = formulate_text_to_uid(key)
                    sql_logger.debug('修正为标点 {}'.format(key))

                    sql_logger.debug('user data {}'.format(__user_data))
                    # result = set(filter(lambda x: key in x['qtalkname'], __user_data))
                    result = merge_list_of_dict(list((filter(lambda x: key in x['qtalkname'], __user_data))))

                elif chinese_pattern.findall(formulate_text(key)) and chinese_pattern.sub('', formulate_text(key)):  # 中英符号结合
                    key = formulate_text(key)
                    _r1 = list(filter(lambda x: key in formulate_text(x['name']), __user_data))  # 何靖宇
                    _r2 = list(filter(lambda x: get_similar_bool(a=key, b=x['name']), __user_data))
                    chinese_words = chinese_pattern.findall(key)
                    sql_logger.debug('中文结果 {}'.format(chinese_words))
                    __k = list(map(lambda x: pinyin.get_pinyin(x), chinese_words))
                    test = {f: t for f, t in zip(chinese_words, __k)}.items()
                    for i in test:
                        key = key.replace(i[0], i[1])
                    sql_logger.debug('转换后 {}'.format(key))
                    _r3 = list(filter(lambda x: key in formulate_text(x['pinyin']), __user_data))
                    result = merge_list_of_dict(_r1, _r2, _r3)
                else: # 纯英文
                    sql_logger.debug('修正前 {}'.format(key))
                    key = formulate_text(key)
                    sql_logger.debug('修正为标点 {}'.format(key))
                    sql_logger.debug('JU RAN YOU user data {}'.format(__user_data))
                    _r1 = list(filter(lambda x: key in x['qtalkname'], __user_data))  # jingyu.he
                    _r2 = list(filter(lambda x: key in formulate_text(x['pinyin']), __user_data))
                    _r3 = list(filter(lambda x: get_similar_bool(a=key, b=x['qtalkname']), __user_data))
                    _r4 = list(filter(lambda x: get_similar_bool(a=key, b=x['pinyin']), __user_data))
                    result = merge_list_of_dict(_r1, _r2, _r3, _r4)
                    sql_logger.debug('user data for result {}'.format(result))
                    sql_logger.debug('PUTTING INTO REDIS {}'.format(__user_data))

        # 搜群的id 和拼音 和 title
        elif form == 'muc':
            # key = formulate_text_to_uid(key)
            _k = MUC_CACHE + '_' + user
            __muc_data = redis_cli.get(_k)
            if __muc_data:
                __muc_data = json.loads(__muc_data)
            elif habit[MUC_TRACE_KEY] or habit[MUC_KEY]:
                # muc_list = set(habit[MUC_TRACE_KEY] + habit[MUC_KEY])  # 这里只要userid 不要domain
                muc_list = habit[MUC_KEY] + list(filter(lambda x: x not in habit[MUC_KEY], habit[MUC_TRACE_KEY]))
                __muc_data = self.muc_habit_data(muc_list, user=user)
                try:
                    __muc_data = sorted(__muc_data, key=lambda x: muc_list.index(x.get('uri')))
                except ValueError as e:
                    sql_logger.exception("ORDER PROBLEM : NOT IN LIST")
                redis_cli.set(name=_k, value=json.dumps(__muc_data, ensure_ascii=False), ex=60)

            if __muc_data:
                sql_logger.debug('muc data {}'.format(__muc_data))
                # 纯中文
                __muc_list = [x.get('uri') for x in __muc_data]
                if not chinese_pattern.sub('', key):
                    # result = set(filter(lambda x: key in x['label'], __muc_data))
                    _r1 = list(filter(lambda x: get_similar_bool(a=key, b=x['label']), __muc_data))
                    if common:
                        _r2 = list((filter(lambda x: key in x['label'], __muc_data)))
                        _r3 = self.search_group(user_id=user, username=raw_key, limit=len(__muc_list), offset=0,
                                                habit='', exclude=__muc_list, origin=origin, common=common,
                                                from_habit=True)
                        _r3 = sorted(_r2, key=lambda x: __muc_list.index(x.get('uri')))
                        result = merge_list_of_dict(_r1, _r2, _r3)
                    else:
                        _r2 = list((filter(lambda x: key in x['label'], __muc_data)))
                        result = merge_list_of_dict(_r1, _r2)
                # 搜索userid
                # 搜索群id
                elif chinese_pattern.sub('', formulate_text(key)):
                    key = formulate_text(key)
                    for __d in __muc_data:
                        __d['label'] = formulate_text(__d['label'])
                    _r1 = list(filter(lambda x: key in x['label'], __muc_data))
                    sql_logger.debug('R1 {}'.format(_r1))
                    # 群名称的拼音 后续撤掉
                    # 先取每个结果的label 得到[拼音,首字母]的结果 之后用map分别得到key是否在里 再用reduce进行或操作
                    _r2 = list(filter(lambda x: reduce(lambda a, b: a + b, list(
                        map(lambda x: True if key in x else False, pinyin.get_all(x['label'])))),
                                      __muc_data))
                    chinese_words = chinese_pattern.findall(key)
                    __k = list(map(lambda x: pinyin.get_pinyin(x), chinese_words))
                    test = {f: t for f, t in zip(chinese_words, __k)}.items()
                    for i in test:
                        key = key.replace(i[0], i[1])
                    _r3 = list(filter(lambda x: reduce(lambda a, b: a + b, list(
                        map(lambda x: True if key in x else False, pinyin.get_all(x['label'])))),
                                      __muc_data))
                    if common:
                        _r4 = self.search_group(user_id=user, username=raw_key, limit=len(__muc_list), offset=0,
                                                habit='', exclude=__muc_list, origin=origin, common=common,
                                                from_habit=True)
                        result = merge_list_of_dict(_r1, _r2, _r3, _r4)
                    else:
                        result = merge_list_of_dict(_r1, _r2, _r3)
                else:
                    for __d in __muc_data:
                        __d['label'] = formulate_text(__d['label'])
                    _r1 = list(filter(lambda x: key in x['label'], __muc_data))
                    sql_logger.debug('R1 {}'.format(_r1))
                    _r2 = list(filter(lambda x: key in x['uri'], __muc_data))
                    sql_logger.debug('R2 {}'.format(_r2))
                    # 群名称的拼音 后续撤掉
                    # 先取每个结果的label 得到[拼音,首字母]的结果 之后用map分别得到key是否在里 再用reduce进行或操作
                    _r3 = list(filter(lambda x: reduce(lambda a, b: a + b, list(
                        map(lambda x: True if key in x else False, pinyin.get_all(x['label'])))),
                                      __muc_data))
                    if common:
                        _r4 = self.search_group(user_id=user, username=raw_key, limit=len(__muc_list), offset=0,
                                                habit='', exclude=__muc_list,
                                                from_habit=True)
                        result = merge_list_of_dict(_r1, _r2, _r3, _r4)
                    else:
                        result = merge_list_of_dict(_r1, _r2, _r3)
                    sql_logger.debug(
                        'PINYIN {}'.format([pinyin.get_all(x['label']) for x in __muc_data]))
                    sql_logger.debug('R3 {}'.format(_r3))
        # self.close()
        sql_logger.debug('returning result {}'.format(list(result)))
        return list(result)

    def single_habit_data(self, data, user_domain=''):
        s_result = list()
        conn = self.conn
        data = list(map(lambda x: x.split('@')[0] if '@' in x else x, data))
        sql = """SELECT aa.user_id, aa.department, aa.icon, aa.user_name, aa.mood,aa.pinyin FROM ( SELECT a.user_id, a.department, b.url AS icon, a.user_name, b.mood,a.pinyin FROM host_users a LEFT JOIN vcard_version b ON a.user_id = b.username WHERE a.hire_flag = 1 AND LOWER(a.user_type) != 's' AND a.user_id = ANY(%(user_lists)s) and a.host_id = ANY(select id from host_info where host = %(domain)s) ) aa """
        cursor = conn.cursor()
        cursor.execute(sql, {'user_lists': data, 'domain': user_domain})
        rs = cursor.fetchall()
        for row in rs:
            res = dict()
            row = ['' if x is None else x for x in row]
            res['qtalkname'] = row[0]
            res['uri'] = row[0] + '@' + domain
            res['content'] = row[1]
            res['icon'] = row[2]
            res['name'] = row[3]
            res['label'] = row[3] + '(' + row[0] + ')'
            if row[4]:
                res['label'] = res['label'] + ' - ' + row[4]
            res['pinyin'] = row[5]

            s_result.append(res)
        cursor.close()
        sql_logger.debug('SINGLE HABIT RESULT {}'.format(s_result))

        return s_result

    def muc_habit_data(self, data, user, user_domain=''):
        s_result = list()
        conn = self.conn
        if '@' in user:
            user_s_name = user.split('@')[0]
            user_domain = user.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []

        # s_data = set(map(lambda x: x + '@conference.' + domain, data))
        s_data = data
        sql = """select a.muc_name, a.domain, b.show_name, b.muc_title, b.muc_pic from user_register_mucs as a left join muc_vcard_info as b on concat(a.muc_name, '@', a.domain) = b.muc_name where a.registed_flag != 0 and a.username = %(user_id)s and (b.muc_name = ANY(%(muc_list)s)) and a.host = %(domain)s"""
        cursor = conn.cursor()
        cursor.execute(sql, {'muc_list': s_data, 'user_id': user_s_name, 'domain': user_domain})
        rs = cursor.fetchall()
        for row in rs:
            row = ['' if x is None else x for x in row]
            res = dict()
            res['uri'] = row[0] + '@' + row[1]
            res['label'] = row[2]
            res['content'] = row[3]
            res['icon'] = row[4]
            s_result.append(res)
        cursor.close()
        sql_logger.debug('MUC HABIT {}'.format(s_result))

        return s_result

    def search_user(self, username, user_id, limit=5, offset=0, habit='', exclude=None):
        s_result = list()
        conn = self.conn
        exclude_list = []
        if '@' in user_id:
            user_s_name = user_id.split('@')[0]
            user_domain = user_id.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return
        regex_tag = username.startswith(REGEX_TAG)
        if regex_tag:
            search_model = '~'
            username = username[1:]
        else:
            search_model = 'ilike'
            username = '%{}%'.format(username)
        if exclude:
            exclude_list = {'{}'.format(x.get('qtalkname')) for x in exclude}
            offset = offset - len(exclude)
            if offset < 0:
                offset = 0
        if if_cached:
            sql = """SELECT aa.user_id, aa.department, bb.url as icon, CASE WHEN aa.nick != '' THEN aa.nick ELSE aa.user_name END, bb.mood , aa.pinyin
                     FROM (
                        SELECT a.user_id, b.department, b.user_name, b.pinyin, a.nick 
                        FROM (
                            SELECT uu.user_id || '@' || hh.host as user_id,'' as nick, uu.host_id as hostid
                            FROM host_users uu
                            LEFT JOIN host_info hh
                            ON uu.host_id = hh.id
                            WHERE uu.hire_flag = 1 AND LOWER(uu.user_type) != 's' AND uu.user_id  <> ALL(%(exclude_list)s) AND (uu.user_id ILIKE %(username)s OR uu.user_name {search_model} %(username)s OR uu.pinyin ILIKE %(username)s) AND uu.host_id = ANY(select id from host_info where host = %(domain)s)
                            UNION 
                            SELECT cc.subkey AS user_id, cc.configinfo as nick, hh.id as hostid
                            FROM client_config_sync cc
                            LEFT JOIN host_info hh
                            ON cc.host = hh.host
                            WHERE split_part(cc.subkey,'@',1) <> ALL(%(exclude_list)s) AND cc.username = %(user_s_name)s AND cc.configkey = 'kMarkupNames' AND cc.configinfo {search_model} %(username)s AND cc.host = %(domain)s
                            ) a 
                        LEFT JOIN host_users b 
                        ON split_part(a.user_id,'@',1) = b.user_id AND a.hostid = b.host_id
                        ) aa 
                     LEFT JOIN vcard_version bb 
                     ON aa.user_id = bb.username || '@' || bb.host
                     ORDER BY aa.user_id ASC LIMIT %(limit)s OFFSET %(offset)s"""
            sql = sql.format(search_model=search_model)
            injection = {'username': username, 'user_id': user_id, 'limit': limit, 'offset': offset,
                         'exclude_list': exclude_list, 'domain': user_domain, 'user_s_name': user_s_name}
        else:
            sql = """SELECT aa.user_id, aa.department, bb.url as icon, CASE WHEN aa.nick != '' THEN aa.nick ELSE aa.user_name END, bb.mood , aa.pinyin
                     FROM 
                     (
                         SELECT a.user_id, b.department, b.user_name, b.pinyin, a.nick
                         FROM (
                             SELECT uu.user_id || '@' || hh.host as user_id,'' as nick, uu.host_id as hostid
                             FROM host_users uu
                             LEFT JOIN host_info hh
                             ON uu.host_id = hh.id
                             WHERE uu.hire_flag = 1 AND LOWER(uu.user_type) != 's'  AND 
                             ( uu.user_id ILIKE %(username)s OR uu.user_name {search_model} %(username)s OR uu.pinyin ILIKE %(username)s ) AND uu.host_id = ANY(select id from host_info where host = %(domain)s )
                             UNION 
                             SELECT cc.subkey AS user_id, cc.configinfo as nick, hh.id as hostid
                             FROM client_config_sync cc
                             LEFT JOIN host_info hh
                             ON cc.host = hh.host
                             WHERE cc.username = %(user_s_name)s AND cc.configkey = 'kMarkupNames' AND cc.configinfo {search_model} %(username)s  AND cc.host =  %(domain)s
                         ) a 
                         LEFT JOIN host_users b 
                         ON split_part(a.user_id, '@', 1)  = b.user_id AND a.hostid = b.host_id
                     ) aa 
                     LEFT JOIN vcard_version bb 
                     ON aa.user_id = bb.username || '@' || bb.host
                     LEFT JOIN 
                     (
                     SELECT CASE WHEN m_from || '@' || from_host = %(user_id)s THEN m_to || '@' || to_host ELSE m_from || '@' || from_host END AS contact, max(create_time) mx 
                         FROM msg_history 
                         WHERE (m_from = %(user_s_name)s and from_host =  %(domain)s ) or (m_to = %(user_s_name)s and to_host = %(domain)s  )
                         GROUP BY contact
                     ) cc 
                     ON aa.user_id = cc.contact 
                     ORDER BY cc.mx DESC nulls last 
                     LIMIT %(limit)s
                     OFFSET %(offset)s"""
            sql = sql.format(search_model=search_model)
            injection = {'username': username, 'user_id': user_id, 'limit': limit, 'offset': offset,
                         'domain': user_domain, 'user_s_name': user_s_name}
        cursor = conn.cursor()
        cursor.execute(sql, injection)
        rs = cursor.fetchall()
        for row in rs:
            res = dict()
            row = ['' if x is None else x for x in row]
            res['qtalkname'] = row[0].split('@')[0]
            res['uri'] = row[0]
            res['content'] = row[1]
            res['icon'] = row[2]
            res['name'] = row[3]
            res['label'] = row[3] + '(' + row[0] + ')'
            if row[4]:
                res['label'] = res['label'] + ' - ' + row[4]
            res['pinyin'] = row[5]
            s_result.append(res)
        cursor.close()
        if if_cached and habit:
            sql_logger.debug('BEFORE HABIT REARRANGE {}\n HABIT {}'.format(s_result, habit))
            s_result = self.sort_by_habit(data=s_result, habit=habit[SINGLE_KEY], name_key='qtalkname',
                                          search_key=username)

            sql_logger.debug('AFTER HABIT REARRANGE {}'.format(s_result))
        elif if_cached and not habit:
            sql_logger.error("CACHED BUT NO HABIT, userid : {user_id}, username : {username}}".format(user_id=user_id,
                                                                                                      username=username))

        if '.' in username and s_result:
            tag = False
            username = username + '@' + user_domain
            for x in s_result:
                if username == x.get('uri'):
                    __ = s_result.pop(x)
                    s_result = [__] + s_result
                    tag = True
            if not tag and self.user_data:
                __complete_match = self.user_data.get(username)
                if __complete_match:
                    res = dict()
                    res['qtalkname'] = __complete_match['i'].split('@')[0]
                    res['uri'] = __complete_match['i']
                    res['content'] = __complete_match['d']
                    res['icon'] = __complete_match['u']
                    res['name'] = __complete_match['n']
                    res['label'] = __complete_match['n'] + '(' + __complete_match['i'] + ')'
                    if __complete_match['m']:
                        res['label'] = res['label'] + ' - ' + __complete_match['m']
                    res['pinyin'] = __complete_match['p']
                    s_result = [res] + s_result

        sql_logger.debug('SINGLE HABIT {}'.format(s_result))
        return s_result

    def search_group(self, user_id, username, limit=5, offset=0, habit='', exclude=None, origin=True,
                     common=True, from_habit=False):
        # todo 这里写的很丑 有时间可以优化一下
        if '@' in user_id:
            user = user_id
            user_s_name = user_id.split('@')[0]
            user_domain = user_id.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        raw_key = username.strip()
        regex_tag = username.startswith(REGEX_TAG)
        if regex_tag:
            search_model = '~'
            username = username[1:]

        else:
            search_model = 'ilike'
            username = '%{}%'.format(username)
            raw_key = '%{}%'.format(raw_key)

        __start_time = time.time()
        s_result = list()
        key = None
        if not exclude:
            exclude = []
        if common:
            key = username
            key = key.split()
            _key_list = []
            for _k in key:
                if not chinese_pattern.sub('', _k):
                    if len(_k) >= 2:
                        _key_list.append(_k)
                else:
                    if len(_k) > 3:
                        _key_list.append(_k)
            # key = list(filter(lambda x: len(x) >= 2, key))
            key = _key_list
            if key:
                if user_s_name in key:
                    if not key.remove(user_id):
                        return None
            else:
                return None

            # 根据key来返回命中高亮是返回汉子还是id TODO: 需要直接通过优化sql选择
            if not chinese_pattern.findall(''.join(key)):
                ret_user_name = False
            else:
                ret_user_name = True
        if not exclude:
            exclude = []
        offset = offset - len(exclude)
        if offset < 0:
            offset = 0
        if from_habit:
            sql = self.make_common_sql(keys=key, origin=False, common=True, habit_tag=True)
            exclude_list = list(map(lambda x: x.split('@')[0], exclude))

        else:
            sql = self.make_common_sql(keys=key, origin=origin, common=common)
            exclude_list = {'{}'.format(x.get('uri', '')) for x in exclude}
            exclude_list = list(map(lambda x: x.split('@')[0], exclude_list))
        sql = sql.format(search_model=search_model, searcher_domain_index=user_domain)
        key_injection = {
            'user_id': user_id,
            'offset': offset,
            'limit': limit,
            'exclude_list': exclude_list,
            'user_domain': user_domain,
            'raw_key': raw_key,
            'user_s_name': user_s_name
        }
        for _i, _k in enumerate(key):
            __ = 'key_{}'.format(_i + 1)
            key_injection = {**key_injection, **{__: _k}}

        if from_habit:
            injection = [*key, user_id, offset, limit, exclude_list, user_domain]
        elif common and origin:
            injection = [*key, user_id, offset, limit, exclude_list, username, user_domain]
        elif common and not origin:
            injection = [*key, user_id, offset, limit, exclude_list, user_domain]
        elif not common and origin:
            injection = [user_id, username, limit, offset, exclude_list, user_domain]
        conn = self.conn
        cursor = conn.cursor()
        cursor.execute(sql, key_injection)
        rs = cursor.fetchall()
        for row in rs:
            row = ['' if x is None else x for x in row]
            res = dict()
            # res['uri'] = row[0] + '@' + row[1]
            res['uri'] = row[0]
            res['label'] = row[2]
            res['content'] = row[3]
            res['icon'] = row[4]
            __hits = []
            from_common = False
            from_name = False
            if row[5]:
                if isinstance(row[5], list):
                    for i in row[5]:
                        if i == ['']:
                            from_name = True
                            continue
                        if not i:
                            continue
                        if isinstance(i, str):
                            if '|' in i:
                                __hits.extend(i.split('|'))
                            else:
                                __hits.append(i)
                        elif isinstance(i, list):
                            for u in i:
                                if isinstance(u, str):
                                    if '|' in u:
                                        __hits.extend(u.split('|'))
                                    else:
                                        __hits.append(u)
                                elif isinstance(u, list):
                                    for k in u:
                                        if '|' in k:
                                            __hits.extend(k.split('|'))
                                        else:
                                            __hits.append(k)
                        else:
                            raise TypeError("WRONG COMMON MEMBER HITS {}".format(row[5]))
                # 应该不会出现是str的情况, 如果出现基本上也过不去长度的检测
                elif isinstance(row[5], str):
                    if '|' in row[5]:
                        __hits.extend(row[5].split('|'))
                    else:
                        __hits.append(row[5])
            else:
                from_name = True
            if __hits and len(__hits) >= len(key):
                from_common = True
                res['hit'] = __hits
            elif __hits and len(__hits) < len(key):
                from_common = False
                if not from_name:
                    continue
            if from_common and from_name:
                res['todoType'] = 6
            elif from_common and not from_name:
                res['todoType'] = 4
            elif not from_common and from_name:
                res['todoType'] = 2
            s_result.append(res)

        cursor.close()
        if not from_habit:
            if if_cached and habit:
                _habit = list(map(lambda x: x + '@conference.' + domain, habit[MUC_KEY]))
                sql_logger.debug('BEFORE HABIT REARRANGE {}\n HABIT {}'.format(s_result, habit))
                s_result = self.sort_by_habit(data=s_result, habit=_habit, name_key='uri')
                sql_logger.debug('AFTER HABIT REARRANGE {}'.format(s_result))
                # s_result = self.sort_by_habit(data=s_result, habit=habit[MUC_KEY], name_key='uri')
            elif if_cached and not habit:
                sql_logger.error(
                    "CACHED BUT NO HABIT, userid : {user_id}, username : {username}}".format(user_id=user_id,
                                                                                             username=username))
        else:
            _habit = list(map(lambda x: x + '@conference.' + domain, exclude_list))
            # s_result = sorted(s_result, key=lambda x: [x for x in exclude_list].index(x))
            sql_logger.debug('BEFORE HABIT REARRANGE {}\n HABIT {}'.format(s_result, habit))
            s_result = self.sort_by_habit(data=s_result, habit=_habit, name_key='uri')
            sql_logger.debug('AFTER HABIT REARRANGE {}'.format(s_result))
        if common and ret_user_name and self.user_data:
            for _r in s_result:
                hits = _r.get('hit', '')
                if not hits:
                    break
                if isinstance(hits, list):
                    # name = [x.get('n') for x in user_data if x.get('i') in hits]
                    # name = [user_data.get(x.split('@')[0]).get('n', '') for x in hits]
                    name = [self.user_data.get(x, {}).get('n', '') for x in hits]
                else:
                    # name = [x.get('n') for x in user_data if x.get('i') == hits]
                    name = [self.user_data.get(x, {}).get('n', '') for x in hits]
                _r['hit'] = name

        sql_logger.debug('GROUP RESULT {}'.format(s_result))
        __end_time = time.time()
        sql_logger.info("SEARCH GROUP USED {}".format(__end_time - __start_time))
        return s_result

    def search_group_by_single(self, user_id, key, limit=5, offset=0, habit='', exclude=None):
        if not isinstance(conference_str, str):
            if '@' in user_id:
                conference_str = 'conference.' + user_id.split('@')[1]
            else:
                raise TypeError("CANT DETERMINE DOMAIN FOR SEARCH conference_str {}".format(conference_str))
        key = key.split()
        key = list(filter(lambda x: len(x) > 2, key))
        if key:
            if user_id in key:
                if not key.remove(user_id):
                    return None
        else:
            return None
        key_count = len(key)
        s_result = list()
        conn = self.conn
        if if_cached:
            sql = """SELECT A.muc_name, A.domain, B.show_name, B.muc_title, B.muc_pic FROM ( SELECT muc_name, domain FROM user_register_mucs WHERE username = %(user_id)s AND registed_flag != 0 AND muc_name IN ( SELECT muc_name FROM user_register_mucs WHERE username IN ( SELECT user_id FROM host_users WHERE hire_flag = 1 AND (user_id ~ ANY(array[%(key_str)s]) OR user_name ~ ANY(array[%(key_str)s]) OR pinyin ~ ANY(array[%(key_str)s]))) GROUP BY muc_name HAVING COUNT(*) = %(key_count)s )) A JOIN muc_vcard_info B ON (A.muc_name || %(conference_str)s) = b.muc_name LIMIT %(limit)s OFFSET %(offset)s"""
        else:
            sql = """SELECT A.muc_room_name, B.show_name, B.muc_title, B.muc_pic FROM (SELECT muc_room_name, MAX(create_time) as max FROM muc_room_history aa RIGHT JOIN (SELECT muc_name FROM user_register_mucs WHERE username = %(user_id)s AND registed_flag != 0 AND muc_name in (SELECT muc_name FROM user_register_mucs WHERE username IN (SELECT user_id FROM host_users WHERE hire_flag = 1 AND (user_id ~ any(array[%(key_str)s]) OR user_name ~ any(array[%(key_str)s]) OR pinyin ~ any(array[%(key_str)s]))) GROUP BY muc_name HAVING COUNT(*) = %(key_count)s)) bb ON aa.muc_room_name = bb.muc_name GROUP BY muc_room_name ORDER BY max DESC nulls last LIMIT %(limit)s OFFSET %(offset)s) A JOIN muc_vcard_info B ON (a.muc_room_name || %(conference_str)s) = b.muc_name"""
        cursor = conn.cursor()
        cursor.execute(sql,
                       {'user_id': user_id, 'limit': limit, 'offset': offset, 'conference_str': '@' + conference_str,
                        'key_str': key, 'key_count': key_count})
        rs = cursor.fetchall()
        for row in rs:
            row = ['' if x is None else x for x in row]
            res = dict()
            res['uri'] = row[0] + '@' + conference_str
            res['label'] = row[1]
            res['content'] = row[2]
            res['icon'] = row[3]
            s_result.append(res)
        cursor.close()
        if if_cached and habit:
            _habit = list(map(lambda x: x + '@conference.' + domain, habit[MUC_KEY]))
            sql_logger.debug('BEFORE HABIT REARRANGE {}\n HABIT {}'.format(s_result, habit))
            s_result = self.sort_by_habit(data=s_result, habit=_habit, name_key='uri')
            sql_logger.debug('AFTER HABIT REARRANGE {}'.format(s_result))

            # s_result = self.sort_by_habit(data=s_result, habit=habit[MUC_KEY], name_key='uri')
        elif if_cached and not habit:
            sql_logger.error("CACHED BUT NO HABIT, userid : {user_id}, username : {username}}".format(user_id=user_id,
                                                                                                      username=key))

        sql_logger.debug('COMMON RESULT {}'.format(s_result))
        return s_result

    def history_user(self, user_id, term, offset, limit, to_user=None, time_range=None, agg_tag=False):
        s_result = list()
        conn = self.conn
        if '@' in user_id:
            user_s_name = user_id.split('@')[0]
            user_domain = user_id.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        regex_tag = term.startswith(REGEX_TAG)
        if regex_tag:
            search_model = '~'
            term = term[1:]

        else:
            search_model = 'ilike'
            term = '%{}%'.format(term)
        if not agg_tag and to_user:
            sql = """SELECT create_time as date, m_from, from_host as fromhost, realfrom, m_to , to_host as tohost, realto as realto, m_body as msg, msg_id
                     FROM msg_history 
                     WHERE  xpath('/message/body/text()',m_body::xml)::text {search_model} %(term)s {user_limit} {time_limit_start} {time_limit_end}
                     ORDER BY create_time DESC
                     OFFSET  %(offset)s
                     LIMIT  %(limit)s"""
            sub_injection = {}
            if to_user:
                if isinstance(to_user, list):
                    user_limit = """AND (
    (m_from = %(user_s_name)s and from_host = %(user_domain)s and m_to || '@' || to_host = ANY(%(to_user)s) 
    OR 
    (m_to = %(user_s_name)s and to_host = %(user_domain)s and m_from || '@' || from_host = ANY(%(to_user)s) 
    )"""
                    sub_injection['to_user'] = to_user
                    sub_injection['user_s_name'] = user_s_name
                    sub_injection['user_domain'] = user_domain
                elif isinstance(to_user, str):
                    to_user_s_name = to_user.split('@')[0]
                    to_user_domain = to_user.split('@')[1]
                    user_limit = """AND (
    (m_from = %(user_s_name)s and from_host = %(user_domain)s and m_to = %(to_user_s_name)s and to_host = %(to_user_domain)s ) 
    OR 
    (m_to = %(user_s_name)s and to_host = %(user_domain)s and m_from = %(to_user_s_name)s and from_host = %(to_user_domain)s ) 
    )"""
                    sub_injection['user_s_name'] = user_s_name
                    sub_injection['user_domain'] = user_domain
                    sub_injection['to_user_s_name'] = to_user_s_name
                    sub_injection['to_user_domain'] = to_user_domain
                else:
                    user_limit = ''
            else:
                user_limit = "AND ((m_from = %(user_s_name)s and from_host = %(user_domain)s) or(m_to = %(user_s_name)s and to_host = %(user_domain)s))"
                sub_injection['user_s_name'] = user_s_name
                sub_injection['user_domain'] = user_domain

            time_limit_start = ''
            time_limit_end = ''
            if time_range and isinstance(time_range, list):
                if time_range[0]:
                    time_limit_start = "AND create_time > %(time_limit_starts)s"
                    sub_injection['time_limit_start'] = time_range[0]
                if time_range[1]:
                    time_limit_end = "AND create_time < %(time_limit_starts)s"
                    sub_injection['time_limit_end'] = time_range[1]
            sql = sql.format(user_limit=user_limit, time_limit_start=time_limit_start, time_limit_end=time_limit_end,
                             search_model=search_model)
            cursor = conn.cursor()
            cursor.execute(sql,
                           {**{'term': term, 'limit': limit, 'offset': offset, 'user_id': user_id},
                            **sub_injection})
            rs = cursor.fetchall()
            for row in rs:
                row = ['' if x is None else x for x in row]
                res = dict()
                if row[0]:
                    res['date'] = row[0].strftime('%Y-%m-%d %H:%M:%S')
                else:
                    res['date'] = ''
                res['from'] = row[1] + '@' + row[2]
                res['realfrom'] = row[3] if row[3] else res['from']
                res['to'] = row[4] + '@' + row[5]
                res['realto'] = row[6] if row[6] else res['to']
                res['msg'] = row[7]
                res['msgid'] = row[8]
                s_result.append(res)
            cursor.close()
        else:
            sql = """SELECT a.count, b.create_time as date, b.m_from, b.from_host as fromhost, b.realfrom, b.m_to, b.to_host as tohost, b.realto, b.m_body as msg, a.conversation, b.msg_id, a.id FROM
                    (
                    SELECT count(1) as count, MAX(id) as id, m_from||'@'||from_host || '_' || m_to||'@'||to_host as conversation
                    FROM msg_history
                    WHERE xpath('/message/body/text()',m_body::xml)::text {search_model} %(term)s AND ( (m_from = %(user_s_name)s and from_host = %(user_domain)s) or (m_to = %(user_s_name)s and to_host = %(user_domain)s) {time_limit_start} {time_limit_end})
                    GROUP BY m_from||'@'||from_host || '_' || m_to||'@'||to_host
                    ORDER BY id desc 
                    OFFSET  %(offset)s
                    LIMIT  %(limit)s
                    ) a
                    LEFT JOIN msg_history b
                    ON a.id = b.id"""
            sub_injection = {'user_s_name': user_s_name, 'user_domain': user_domain}
            time_limit_start = ''
            time_limit_end = ''
            if time_range and isinstance(time_range, list):
                if time_range[0]:
                    time_limit_start = "AND b.create_time > %(time_limit_starts)s"
                    sub_injection['time_limit_start'] = time_range[0]
                if time_range[1]:
                    time_limit_end = "AND b.create_time < %(time_limit_starts)s"
                    sub_injection['time_limit_end'] = time_range[1]
            sql = sql.format(time_limit_start=time_limit_start, time_limit_end=time_limit_end,
                             search_model=search_model)
            cursor = conn.cursor()
            cursor.execute(sql,
                           {**{'term': term, 'limit': limit, 'offset': offset, 'user_id': user_id},
                            **sub_injection})
            rs = cursor.fetchall()
            for row in rs:
                row = ['' if x is None else x for x in row]
                res = dict()
                res['count'] = row[0]
                if row[1]:
                    res['date'] = row[1].strftime('%Y-%m-%d %H:%M:%S')
                else:
                    res['date'] = ''
                res['from'] = row[2] + '@' + row[3]
                res['realfrom'] = row[4] if row[4] else res['from']
                res['to'] = row[5] + '@' + row[6]
                res['realto'] = row[7] if row[7] else res['to']
                res['msg'] = row[8]
                res['conversation'] = row[9]
                res['msgid'] = row[10]
                res['id'] = row[11]
                s_result.append(res)
            cursor.close()
            s_result = self.handle_sql_result(data=s_result)
        return s_result

    def history_muc(self, user_id, term, offset, limit, to_muc=None, time_range=None, agg_tag=False):
        """

        :param user_id:
        :param user_mucs:
        :param term:
        :param offset:
        :param limit:
        :param to_muc:
        :param time_range:
        :param agg_tag:
        :return:

        """
        s_result = list()
        conn = self.conn
        if '@' in user_id:
            user_s_name = user_id.split('@')[0]
            user_domain = user_id.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        regex_tag = term.startswith(REGEX_TAG)
        if regex_tag:
            search_model = '~'
            term = term[1:]
        else:
            search_model = 'ilike'
            term = '%{}%'.format(term)
        if not agg_tag and to_muc:
            sql = """SELECT a.create_time as date, b.muc_name as _to, a.packet as msg, a.msg_id as msgid, b.show_name as label, b.muc_pic as icon
                                 FROM muc_room_history a left join muc_vcard_info b
                                 on a.muc_room_name = split_part(b.muc_name,'@',1)
                                 WHERE  xpath('/message/body/text()',packet::xml)::text {search_model} %(term)s {muc_limit} {time_limit_start} {time_limit_end}
                                 ORDER BY create_time
                                 OFFSET  %(offset)s
                                 LIMIT  %(limit)s"""
            sub_injection = {}
            if to_muc:
                if isinstance(to_muc, list):
                    muc_s_name = list(map(lambda x: x.split('@')[0], to_muc))
                    muc_limit = "AND muc_room_name = ANY(%(muc_s_name)s)"
                    sub_injection['muc_s_name'] = muc_s_name
                elif isinstance(to_muc, str):
                    muc_s_name = to_muc.split('@')[0]
                    muc_limit = "AND muc_room_name = %(muc_s_name)s"
                    sub_injection['muc_s_name'] = muc_s_name
                else:
                    muc_limit = ''
            else:
                muc_limit = "AND muc_room_name in (SELECT muc_name FROM user_register_mucs where username = %(user_s_name)s and registed_flag = 1 AND domain = 'conference.'||%(user_domain)s )"
                sub_injection['user_s_name'] = user_s_name
                sub_injection['user_domain'] = user_domain

            time_limit_start = ''
            time_limit_end = ''
            if time_range and isinstance(time_range, list):
                if time_range[0]:
                    time_limit_start = "AND create_time > %(time_limit_starts)s"
                    sub_injection['time_limit_start'] = time_range[0]
                if time_range[1]:
                    time_limit_end = "AND create_time < %(time_limit_starts)s"
                    sub_injection['time_limit_end'] = time_range[1]
            sql = sql.format(muc_limit=muc_limit, time_limit_start=time_limit_start, time_limit_end=time_limit_end,
                             search_model=search_model)
            cursor = conn.cursor()
            cursor.execute(sql,
                           {**{'term': term, 'limit': limit, 'offset': offset, 'user_id': user_id},
                            **sub_injection})
            rs = cursor.fetchall()
            for row in rs:
                row = ['' if x is None else x for x in row]
                res = dict()
                if row[0]:
                    res['date'] = row[0].strftime('%Y-%m-%d %H:%M:%S')
                else:
                    res['date'] = ''
                res['to'] = row[1]
                res['msg'] = row[2]
                res['msgid'] = row[3]
                res['from'] = ''
                res['label'] = row[4]
                res['icon'] = row[5]
                s_result.append(res)
            cursor.close()
        else:
            sql = """SELECT count, c.muc_name, b.msg_id, b.create_time as date, b.packet, c.show_name as label, c.muc_pic as icon , a.id FROM
                    (
                    SELECT count(1) as count, MAX(id) as id, muc_room_name
                    FROM muc_room_history
                    WHERE xpath('/message/body/text()',packet::xml)::text {search_model} %(term)s AND muc_room_name = ANY(SELECT muc_name FROM user_register_mucs where username = %(user_s_name)s and registed_flag = 1  AND host = %(user_domain)s and domain = 'conference.' || %(user_domain)s ) {time_limit_start} {time_limit_end}
                    GROUP BY muc_room_name
                    ORDER BY id desc 
                    OFFSET %(offset)s
                    LIMIT %(limit)s
                    )a 
                    LEFT JOIN muc_room_history b 
                    ON a.id = b.id
                    LEFT JOIN muc_vcard_info c
                    on a.muc_room_name = split_part(c.muc_name,'@',1)"""

            sub_injection = {'user_s_name': user_s_name, 'user_domain': user_domain}
            time_limit_start = ''
            time_limit_end = ''
            if time_range and isinstance(time_range, list):
                if time_range[0]:
                    time_limit_start = "AND create_time > %(time_limit_starts)s"
                    sub_injection['time_limit_start'] = time_range[0]
                if time_range[1]:
                    time_limit_end = "AND create_time < %(time_limit_starts)s"
                    sub_injection['time_limit_end'] = time_range[1]
            sql = sql.format(time_limit_start=time_limit_start, time_limit_end=time_limit_end,
                             search_model=search_model)
            cursor = conn.cursor()
            cursor.execute(sql,
                           {**{'term': term, 'limit': limit, 'offset': offset, 'user_id': user_id},
                            **sub_injection})
            rs = cursor.fetchall()
            for row in rs:
                row = ['' if x is None else x for x in row]
                res = dict()
                res['count'] = row[0]
                res['to'] = row[1]
                res['msgid'] = row[2]
                if row[3]:
                    res['date'] = row[3].strftime('%Y-%m-%d %H:%M:%S')
                else:
                    res['date'] = ''
                res['msg'] = row[4]
                res['from'] = ''
                res['label'] = row[5]
                res['icon'] = row[6]
                s_result.append(res)
            cursor.close()
            # s_result = self.handle_sql_result(data=s_result)
        return s_result

    def history_file(self, user_id, term, offset=0, limit=5, time_range=None):

        s_result = list()
        conn = self.conn
        if '@' in user_id:
            user_s_name = user_id.split('@')[0]
            user_domain = user_id.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        regex_tag = term.startswith(REGEX_TAG)
        if regex_tag:
            search_model = '~'
            term = term[1:]
        else:
            search_model = 'ilike'
            term = '%{}%'.format(term)
        sql = """SELECT file, from_, pfv.muc_name as to_, date, msgid, pfv.show_name as label, pfv.muc_pic as icon, msg
                 FROM (
                     SELECT json(unnest(xpath('//body[@msgType="5"]/text()', packet::xml))::text) AS file, '' AS from_, muc_room_name AS to_, create_time AS date, msg_id AS msgid,packet as msg
                     FROM muc_room_history
                     WHERE muc_room_name IN (
                         SELECT muc_name
                         FROM user_register_mucs
                         WHERE username = %(user_s_name)s
                            AND registed_flag = 1
                            AND host = %(user_domain)s
                     )
                 ) pfc left join muc_vcard_info pfv
                 on pfc.to_= split_part(pfv.muc_name,'@',1)
                 UNION ALL
                 SELECT file, from_, to_, date, msgid, pfb.user_name as label, pfv.url as icon, msg
                 FROM (
                     SELECT json(unnest(xpath('/message/body[@msgType="5"]/text()', m_body::xml))::text) AS file, m_from || '@' || from_host as from_
                         , m_to || '@' || to_host as to_, create_time AS date
                         , msg_id AS msgid, m_body as msg
                     FROM msg_history
                     WHERE (m_from = %(user_s_name)s AND from_host = %(user_domain)s )
                         OR (m_to = %(user_s_name)s AND to_host = %(user_domain)s )
                 ) pfx left join vcard_version pfv
                 on split_part(pfx.from_,'@',1) = pfv.username
                 left join host_users pfb
                 on pfv.username = pfb.user_id and pfv.host = ANY(SELECT host from host_info WHERE id = pfb.host_id)
                 WHERE file ->> 'FileName' {search_model} %(term)s {time_limit_start} {time_limit_end}
                 ORDER BY date desc
                 OFFSET %(offset)s
                 LIMIT %(limit)s
"""
        sub_injection = {'user_s_name': user_s_name, 'user_domain': user_domain}
        time_limit_start = ''
        time_limit_end = ''
        if time_range and isinstance(time_range, list):
            if time_range[0]:
                time_limit_start = "AND create_time > %(time_limit_starts)s"
                sub_injection['time_limit_start'] = time_range[0]
            if time_range[1]:
                time_limit_end = "AND create_time < %(time_limit_starts)s"
                sub_injection['time_limit_end'] = time_range[1]
        sql = sql.format(time_limit_start=time_limit_start, time_limit_end=time_limit_end, search_model=search_model)
        cursor = conn.cursor()
        cursor.execute(sql,
                       {**{'term': term, 'limit': limit, 'offset': offset, 'user_id': user_id},
                        **sub_injection})
        rs = cursor.fetchall()
        for row in rs:
            row = ['' if x is None else x for x in row]
            res = dict()
            res['fileinfo'] = row[0]
            res['from'] = row[1]
            res['to'] = row[2]
            if row[3]:
                res['date'] = row[3].strftime('%Y-%m-%d %H:%M:%S')
            else:
                res['date'] = ''
            res['msgid'] = row[4]
            res['source'] = row[5] if row[5] else row[1]
            res['icon'] = row[6]
            res['msg'] = row[7]
            res['mtype'] = 5
            s_result.append(res)
        cursor.close()
        # s_result = self.handle_sql_result(data=s_result)
        return s_result

    def history_single_file(self, user_id, term, offset=0, limit=5):
        s_result = list()
        conn = self.conn
        sql = """SELECT * from ( SELECT unnest(xpath('//body[@msgType="5"]/text()',m_body::xml))::text::json as file, m_from, m_to,create_time as epo, msg_id as msgid from msg_history where m_from = %(user_id)s or m_to = %(user_id)s) as pfx where pfx.file->>'FileName' ~ %(term)s order by pfx.time desc offset %(offset)s limit %(limit)s"""

        cursor = conn.cursor()
        cursor.execute(sql,
                       {'user_id': user_id, 'term': term, 'offset': offset, 'limit': limit})
        rs = cursor.fetchall()
        for row in rs:
            row = ['' if x is None else x for x in row]
            res = dict()
            res['file'] = row[0]
            res['from'] = row[1]
            res['to'] = row[2]
            res['time'] = row[3]
            res['msgid'] = row[4]
            res['domain'] = domain
            res['chattype'] = 'chat'  # chat groupchat
            s_result.append(res)
        # s_result = self.sort_by_habit(data=s_result, habit=_habit, name_key='uri') TODO sort by time, 返回之后添加count
        cursor.close()
        return s_result

    def history_muc_file(self, user_id, term, muc_list, offset=0, limit=5):
        s_result = list()
        conn = self.conn

        # sql = """SELECT * from ( SELECT unnest(xpath('//body[@msgType="5"]/text()',packet::xml))::text::json as file, nick as from, muc_room_name as to,create_time as time from muc_room_history where muc_room_name in ('dba632082f6b4c7f89159c47537df561')) as pfx where pfx.file->>'FileName' ~ '.apk' order by pfx.time desc offset 0 limit 2;"""
        sql = """SELECT * from ( SELECT unnest(xpath('//body[@msgType="5"]/text()',packet::xml))::text::json as file, nick, muc_room_name, create_time as time from muc_room_history where muc_room_name in %(muc_list)s ) as pfx where pfx.file->>'FileName' ~  %(term)s order by pfx.time desc offset %(offset)s limit %(limit)s"""

        cursor = conn.cursor()
        cursor.execute(sql,
                       {'muc_lists': set(muc_list), 'term': term, 'offset': offset, 'limit': limit})
        rs = cursor.fetchall()
        for row in rs:
            row = ['' if x is None else x for x in row]
            res = dict()
            res['file'] = row[0]
            res['from'] = row[1]
            res['to'] = row[2]
            res['time'] = row[3]
            res['msgid'] = row[4]
            res['domain'] = domain
            res['chattype'] = 'groupchat'  # chat groupchat
            s_result.append(res)
        # s_result = self.sort_by_habit(data=s_result, habit=_habit, name_key='uri') TODO sort by time
        cursor.close()
        return s_result

    def get_person_info(self, person):
        result = {}
        if '@' in person:
            person = person.split('@')[0]
        sql = """ select a.user_name,b.url from host_users a join vcard_version b on a.user_id = %(person)s and a.user_id = b.username;"""
        conn = self.conn
        cursor = conn.cursor()
        cursor.execute(sql, {'person': person})
        rs = cursor.fetchall()
        for row in rs:
            row = ['' if x is None else x for x in row]
            result['show_name'] = row[0]
            result['url'] = row[1]
        cursor.close()
        return result

    def get_mucs_info(self, muc):
        result = {}
        if '@' not in muc and isinstance(conference_str, str):
            muc = muc + '@' + conference_str
        sql = """select show_name,muc_pic from muc_vcard_info where muc_name = %(muc)s"""
        conn = self.conn
        cursor = conn.cursor()
        cursor.execute(sql, {'muc': muc})
        rs = cursor.fetchall()
        for row in rs:
            row = ['' if x is None else x for x in row]
            result['show_name'] = row[0]
            result['muc_pic'] = row[1]
        # TODO SORT!!!!
        cursor.close()
        return result

    @staticmethod
    def handle_sql_result(data):
        result = {}
        for hit in data:
            a = hit['conversation'].split('_')[0]
            b = hit['conversation'].split('_')[1]
            conv = sorted([a, b])[0] + '_' + sorted([a, b])[1]
            if conv in result.keys():
                _temp = result[conv]
                if _temp['id'] > hit['id']:
                    result[conv]['count'] += hit['count']
                else:
                    result[conv] = hit
                    result[conv]['count'] += _temp['count']
            else:
                result[conv] = hit
        result = sorted(list(result.values()), key=lambda x: x.get('id'))
        return result

    @staticmethod
    def sort_by_habit(data, habit, name_key, search_key=''):
        if not name_key:
            sql_logger.warning("NO NAME_KEY FOUND :{}".format(data))
        if not isinstance(data, list):
            sql_logger.error("DATA NOT A LIST :{data}".format(data=data))
            return data
        if not isinstance(habit, (set, list)):
            sql_logger.error("HABIT NOT A LIST :{habit}".format(habit=habit))
            return data
        for _h in habit:
            # for _h in habit[::-1]:
            name_list = [x[name_key] for x in data]
            if search_key:
                if search_key in _h and _h not in name_list:
                    sql_logger.warning("SHOULD ADD {} TO KEY {} RESULT {}".format(_h, search_key, data))
            # if name_key == ''
            if _h in name_list:
                _t = data.pop(name_list.index(_h))
                data = [_t] + data
        return data

    @staticmethod
    def make_common_sql(keys, origin=True, common=True, habit_tag=False):
        sql = ""
        if common:
            if not keys:
                return
            case_pattern = []
            union_pattern = []
            key_len = len(keys)
            for i, k in enumerate(keys):
                case_pattern.append(
                    """SELECT %(key_{i})s, user_id
                       FROM host_users 
                       WHERE  hire_flag = 1 AND user_id != %(user_s_name)s AND ( user_id ilike %(key_{i})s OR user_name {search_model} %(key_{i})s OR pinyin ilike %(key_{i})s ) AND host_id = ANY(SELECT id FROM host_info WHERE host = %(user_domain)s )""".format(
                        i=i + 1, search_model='{search_model}'))
                union_pattern.append("""SELECT a.muc_name|| '@' || a.domain as muc_name, string_agg(a.username||'@'||a.host, '|') as hit, max(a.created_at) as time
                                        FROM user_register_mucs a JOIN tmp2 b ON a.muc_name = b.muc_name
                                        WHERE username IN (select user_id from tmp where key =  %(key_{i})s ) and a.registed_flag != 0 AND a.domain = 'conference.' || %(user_domain)s
                                        group by a.muc_name || '@' || a.domain""".format(i=i + 1))

        # keys 对应 $1 ... ${len(keys)}
        # 之后是searcher_index 序号为len + 1
        # 然后是群组字符串 len + 2
        # 然后是offset len + 3
        # limit len + 4
        # 排除在 len + 5
        # 名字查询的key 在 len + 6
        # domain 在 len + 7
        if habit_tag:
            sql = """
                    WITH tmp (key, user_id) AS (
                        {keys_pattern}
                    ), 
                    tmp2 (muc_name, domain, created_at) AS (
                        SELECT split_part(muc_name || '@' || domain,'@',1) ,split_part(muc_name || '@' || domain,'@',2), max(created_at) as created_at
                        FROM user_register_mucs
                        WHERE username = %(user_s_name)s AND host = %(user_domain)s
                        AND registed_flag != 0 AND muc_name = ANY(%(exclude_list)s) AND domain = 'conference.' || %(user_domain)s
                        GROUP BY muc_name || '@' || domain 
                    )
                    SELECT 
                        aa.mucname, 
                        split_part(bb.muc_name, '@', 2) AS domain,
                        bb.show_name, 
                        bb.muc_title, 
                        bb.muc_pic, 
                        aa.tag
                    FROM (
                        SELECT mucname, tag from (
                        SELECT muc_name AS mucname, array_agg(hit) AS tag
                        FROM (
                           {select_pattern}
                        ) foo 
                        GROUP BY muc_name
                        HAVING COUNT(muc_name) = {length}
                        ) boo

                    ) aa
                    JOIN muc_vcard_info bb 
                    ON (aa.mucname) = bb.muc_name 
                    offset %(offset)s limit %(limit)s""".format(
                keys_pattern=' union all '.join(case_pattern),
                select_pattern=' union all '.join(union_pattern),
                length=key_len, search_model='{search_model}')
            return sql
        if origin and common:
            # format 填空
            sql = """
                    WITH tmp (key, user_id) AS (
                        {keys_pattern}
                    ), 
                    tmp2 (muc_name, domain, created_at) AS (
                        SELECT split_part(muc_name || '@' || domain,'@',1) ,split_part(muc_name || '@' || domain,'@',2), max(created_at) as created_at
                        FROM user_register_mucs
                        WHERE username = %(user_s_name)s AND host = %(user_domain)s
                        AND registed_flag != 0 AND muc_name <> ALL (%(exclude_list)s) AND domain = 'conference.' || %(user_domain)s
                        GROUP BY muc_name || '@' || domain 
                    )
                    SELECT 
                        aa.mucname, 
                        split_part(bb.muc_name, '@', 2) AS domain,
                        bb.show_name, 
                        bb.muc_title, 
                        bb.muc_pic, 
                        aa.tag
                    FROM (
                    	SELECT mucname, array_agg(tag) AS tag, MAX(time) as time
	                    FROM(
                            SELECT mucname, tag, time from (
                            SELECT muc_name AS mucname, array_agg(hit) AS tag, max(time) as time
                            FROM (
                               {select_pattern}
                            ) foo 
                            GROUP BY muc_name
                            HAVING COUNT(muc_name) = {length}
                            ) boo
                            union all 
                            select a.muc_name|| '@' || a.domain as muccname, array[''] as hit, a.created_at as time
                            from tmp2 a join muc_vcard_info b on concat(a.muc_name, '@', a.domain) = b.muc_name
                            where (b.show_name {search_model} %(raw_key)s or b.muc_name ilike  %(raw_key)s )
                            ) poo
                        GROUP BY mucname 
                    ) aa
                    JOIN muc_vcard_info bb 
                    ON aa.mucname  = bb.muc_name 
                    ORDER BY time DESC 
                    offset %(offset)s limit %(limit)s""".format(
                keys_pattern=' union all '.join(case_pattern),
                select_pattern=' union all '.join(union_pattern),
                length=key_len, search_model='{search_model}')

        elif common and not origin:
            sql = """
                    WITH tmp (key, user_id) AS (
                        {keys_pattern}
                    ), 
                    tmp2 (muc_name, domain, created_at) AS (
                        SELECT split_part(muc_name || '@' || domain,'@',1) ,split_part(muc_name || '@' || domain,'@',2), max(created_at) as created_at
                        FROM user_register_mucs
                        WHERE username = %(user_s_name)s AND host = %(user_domain)s
                        AND registed_flag != 0 AND muc_name <> ALL ( %(exclude_list)s ) AND domain = 'conference.' || %(user_domain)s
                        GROUP BY muc_name || '@' || domain 
                    )
                    SELECT 
                        aa.mucname, 
                        split_part(bb.muc_name, '@', 2) AS domain,
                        bb.show_name, 
                        bb.muc_title, 
                        bb.muc_pic, 
                        aa.tag
                    FROM (
                        SELECT mucname, tag, time from (
                        SELECT muc_name AS mucname, array_agg(hit) AS tag, max(time) as time
                        FROM (
                           {select_pattern}
                        ) foo 
                        GROUP BY muc_name
                        HAVING COUNT(muc_name) = {length}
                        ) boo

                    ) aa
                    JOIN muc_vcard_info bb 
                    ON aa.mucname = bb.muc_name 
                    ORDER BY time DESC 
                    offset %(offset)s limit %(limit)s""".format(
                keys_pattern=' union all '.join(case_pattern),
                select_pattern=' union all '.join(union_pattern),
                search_model='{search_model}', length=key_len)

        elif not common and origin:
            sql = """SELECT
                        b.muc_name as mucname, split_part(b.muc_name,'@',2) as domain, b.show_name, b.muc_title, b.muc_pic, array['']
                     FROM
                        user_register_mucs as a left join muc_vcard_info as b 
                     ON 
                        concat(a.muc_name, '@', a.domain) = b.muc_name
                     WHERE 
                        a.registed_flag != 0 and a.username = %(user_s_name)s and a.host = %(user_domain)s and (b.show_name {search_model} %(raw_key)s or b.muc_name ~ %(raw_key)s) and b.muc_name <> ALL (%(exclude_list)s) AND domain = {searcher_domain_index}
                     order by b.update_time desc offset %(offset)s limit %(limit)s"""
        return sql


class AsyncLib:
    def __init__(self, user_id):
        global PY_VERSION, DB_VERSION, if_async
        self.conn_str = 'postgres://{user}:{password}@{host}:{port}/{database}'.format(host=host,
                                                                                       database=database,
                                                                                       user=user,
                                                                                       password=password,
                                                                                       port=port)

        self.user_data = {}
        if user_id and '@' in user_id:
            __domain = user_id.split('@')[1]
        else:
            raise ValueError("NO DOMAIN FOUND IN ASYNC PG CONSTRUCTOR USERID {}".format(user_id))
        if not self.user_data and self.user_data is not None:
            cache_redis_cli = RedisUtil()
            self.user_data = cache_redis_cli.get_all_user_data(domain=__domain)
            if not self.user_data:
                __user_lib = UserLib()
                self.user_data = __user_lib.get_user_data(domain=__domain)
                __user_lib.close()
                if self.user_data:
                    cache_redis_cli.set_all_user_data(data=self.user_data, domain=__domain)
                    sql_logger.info("redis user data set..")
                sql_logger.info("no user data in redis, making one into it..")
                if self.user_data:
                    cache_redis_cli.set_all_user_data(data=self.user_data, domain=__domain)
                    sql_logger.info("redis user data set..")
                else:
                    sql_logger.error("NO USER FOUND IN POSTGRESQL!!")
                    self.user_data = None
        if self.user_data is None:
            sql_logger.error("POSTGRESQL STILL NOT SET, IF SET, PLEASE RESTART SERVICE")
            raise ConnectionError("POSTGRESQL IS NOT CONNECTED BECAUSE NO USER FOUND")

    def close(self):
        return

    async def get_user_data(self, domain=''):
        """
        aa.user_id, aa.department, aa.icon, aa.user_name, aa.mood, aa.pinyin
        :return:
        i n p u d m
        id name pinyin url department mood
        """
        s_result = defaultdict(dict)
        sql = """select b.username || '@' || b.host as user_id, a.user_name,a.pinyin, b.url, a.department, b.mood from host_users a left join vcard_version b on a.user_id = b.username where a.hire_flag = 1 and a.host_id = ANY(select id from host_info where host = $1)"""
        pgconn = await asyncpg.connect(self.conn_str)
        stmt = await pgconn.prepare(sql)
        for (user_id, user_name, pinyin, url, department, mood) in await stmt.fetch(domain):
            row = [user_id, user_name, pinyin, url, department, mood]
            row = ['' if x is None else x for x in row]
            res = dict()
            res['i'] = row[0]
            res['n'] = row[1]
            res['p'] = row[2]
            res['u'] = row[3]
            res['d'] = row[4]
            res['m'] = row[5]
            s_result[row[0]] = res
        await pgconn.close()
        return s_result

    async def get_user_mucs(self, user_id, user_domain=''):
        if '@' in user_id:
            user_s_name = user_id.split('@')[0]
            user_domain = user_id.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        s_result = []
        sql = "SELECT muc_name||'@'||domain from user_register_mucs where username = $1 and registed_flag = 1 and host = $2"
        pgconn = await asyncpg.connect(self.conn_str)
        injection = [user_s_name, user_domain]
        stmt = await pgconn.prepare(sql)
        for (_muc) in await stmt.fetch(*injection):
            s_result.append(_muc[0])
        await pgconn.close()
        return s_result

    async def get_habit(self, key, habit, form, user, origin=False, common=False):
        if '@' in user:
            user_s_name = user.split('@')[0]
            user_domain = user.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        if not self.user_data:
            self.user_data = await self.get_user_data(user_domain)
            if self.user_data:
                cache_redis_cli = RedisUtil()
                cache_redis_cli.set_all_user_data(data=self.user_data, domain=user_domain)
                sql_logger.info("redis user data set..")
        raw_key = key
        # 圆角转半角
        key = symbol_to_english(key)
        result = []
        # 搜人的拼音和userid
        if form == 'single':
            _k = SINGLE_CACHE + '_' + user
            __user_data = redis_cli.get(_k)
            if __user_data:
                __user_data = json.loads(__user_data)
            elif habit[SINGLE_TRACE_KEY] or habit[SINGLE_KEY]:
                # user_list = set(habit[SINGLE_TRACE_KEY] + habit[SINGLE_KEY])  # 这里只要userid 不要domain
                user_list = habit[SINGLE_KEY] + list(
                    filter(lambda x: x not in habit[SINGLE_KEY], habit[SINGLE_TRACE_KEY]))
                sql_logger.debug('WATCH ORDER {}'.format(user_list))
                __user_data = await self.single_habit_data(user_list, user_domain)
                try:
                    # __user_data = sorted(__user_data, key=lambda x: user_list.index(x.get('qtalkname', '')))
                    __user_data = sorted(__user_data, key=lambda x: user_list.index(x.get('uri', '')))
                except ValueError:
                    sql_logger.exception("ORDER PROBLEM : NOT IN LIST")
                sql_logger.debug('WATCH ORDER {}'.format(__user_data))
                redis_cli.set(name=_k, value=json.dumps(__user_data, ensure_ascii=False), ex=60)

            if __user_data:
                sql_logger.debug('user data {}'.format(__user_data))
                # 纯中文
                if not chinese_pattern.sub('', key):
                    sql_logger.debug('修正前 {}'.format(key))
                    key = formulate_text(key)  # 只保留中文
                    sql_logger.debug('修正为标点 {}'.format(key))
                    _r1 = list((filter(lambda x: key in x['name'], __user_data)))
                    # 这里x['name'] 需要是string
                    _r2 = list(filter(lambda x: get_similar_bool(key, x['name']), __user_data))
                    result = merge_list_of_dict(_r1, _r2)
                # 搜索userid 此处不考虑相似度 只全匹配
                elif ('.' in key) or ('_' in key) or ('-' in key):
                    sql_logger.debug('修正前 {}'.format(key))
                    # key = formulate_text_to_uid(key)
                    sql_logger.debug('修正为标点 {}'.format(key))

                    sql_logger.debug('user data {}'.format(__user_data))
                    # result = set(filter(lambda x: key in x['qtalkname'], __user_data))
                    result = merge_list_of_dict(list((filter(lambda x: key in x['qtalkname'], __user_data))))

                elif chinese_pattern.findall(formulate_text(key)) and chinese_pattern.sub('', formulate_text(key)):  # 中英符号结合
                    key = formulate_text(key)
                    _r1 = list(filter(lambda x: key in formulate_text(x['name']), __user_data))  # 何靖宇
                    _r2 = list(filter(lambda x: get_similar_bool(a=key, b=x['name']), __user_data))
                    sql_logger.debug('r1 {}'.format(_r1))
                    sql_logger.debug('r2 {}'.format(_r2))
                    chinese_words = chinese_pattern.findall(key)
                    sql_logger.debug('中文结果 {}'.format(chinese_words))
                    __k = list(map(lambda x: pinyin.get_pinyin(x), chinese_words))
                    test = {f: t for f, t in zip(chinese_words, __k)}.items()
                    for i in test:
                        key = key.replace(i[0], i[1])
                    sql_logger.debug('转换后 {}'.format(key))
                    _r3 = list(filter(lambda x: key in formulate_text(x['pinyin']), __user_data))
                    result = merge_list_of_dict(_r1, _r2, _r3)
                else: # 纯英文
                    sql_logger.debug('修正前 {}'.format(key))
                    key = formulate_text(key)
                    sql_logger.debug('修正为标点 {}'.format(key))
                    sql_logger.debug('JU RAN YOU user data {}'.format(__user_data))
                    _r1 = list(filter(lambda x: key in x['qtalkname'], __user_data))  # jingyu.he
                    _r2 = list(filter(lambda x: key in formulate_text(x['pinyin']), __user_data))
                    _r3 = list(filter(lambda x: get_similar_bool(a=key, b=x['qtalkname']), __user_data))
                    _r4 = list(filter(lambda x: get_similar_bool(a=key, b=x['pinyin']), __user_data))
                    result = merge_list_of_dict(_r1, _r2, _r3, _r4)
                    sql_logger.debug('user data for result {}'.format(result))
                    sql_logger.debug('PUTTING INTO REDIS {}'.format(__user_data))
        # 搜群的id 和拼音 和 title
        elif form == 'muc':
            # key = formulate_text_to_uid(key)
            _k = MUC_CACHE + '_' + user
            __muc_data = redis_cli.get(_k)
            if __muc_data:
                __muc_data = json.loads(__muc_data)
            elif habit[MUC_TRACE_KEY] or habit[MUC_KEY]:
                # muc_list = set(habit[MUC_TRACE_KEY] + habit[MUC_KEY])  # 这里只要userid 不要domain
                muc_list = habit[MUC_KEY] + list(filter(lambda x: x not in habit[MUC_KEY], habit[MUC_TRACE_KEY]))
                sql_logger.debug('WATCH ORDER {}'.format(muc_list))
                __muc_data = await self.muc_habit_data(data=muc_list, user=user)
                try:
                    __muc_data = sorted(__muc_data, key=lambda x: muc_list.index(x.get('uri')))
                except ValueError:
                    sql_logger.exception("ORDER PROBLEM : NOT IN LIST")
                sql_logger.debug('WATCH ORDER {}'.format(__muc_data))
                redis_cli.set(name=_k, value=json.dumps(__muc_data, ensure_ascii=False), ex=60)
            if __muc_data:
                sql_logger.debug('muc data {}'.format(__muc_data))
                __muc_list = [x.get('uri') for x in __muc_data]
                # 纯中文
                if not chinese_pattern.sub('', key):
                    key = formulate_text(key)
                    # __muc_data中包含每个群组有的用户 根据中文还是英文 可以分别依靠user_data做一次判断

                    if common:
                        _r1 = list((filter(lambda x: key in x['label'], __muc_data)))
                        _r2 = await self.search_group(user_id=user, username=raw_key, limit=len(__muc_list), offset=0,
                                                      habit='', exclude=__muc_list, origin=origin, common=common,
                                                      from_habit=True)
                        _r2 = sorted(_r2, key=lambda x: __muc_list.index(x.get('uri')))
                        _r3 = list((filter(lambda x: get_similar_bool(a=raw_key, b=x['label']), __muc_data)))
                        result = merge_list_of_dict(_r1, _r2, _r3)
                    else:
                        _r1 = list((filter(lambda x: key in x['label'], __muc_data)))
                        _r2 = list((filter(lambda x: get_similar_bool(a=raw_key, b=x['label']), __muc_data)))
                        result = merge_list_of_dict(_r1, _r2)
                elif chinese_pattern.findall(formulate_text(key)) and chinese_pattern.sub('', formulate_text(key)):
                    key = formulate_text(key)
                    for __d in __muc_data:
                        __d['label'] = formulate_text(__d['label'])
                    _r1 = list(filter(lambda x: key in x['label'], __muc_data))
                    sql_logger.debug('R1 {}'.format(_r1))
                    # 群名称的拼音 后续撤掉
                    # 先取每个结果的label 得到[拼音,首字母]的结果 之后用map分别得到key是否在里 再用reduce进行或操作
                    _r2 = list(filter(lambda x: reduce(lambda a, b: a + b, list(
                        map(lambda x: True if key in x else False, pinyin.get_all(x['label'])))),
                                      __muc_data))
                    _r3 = list(filter(lambda x: get_similar_bool(key, x['label']), __muc_data))

                    chinese_words = chinese_pattern.findall(key)
                    __k = list(map(lambda x: pinyin.get_pinyin(x), chinese_words))
                    test = {f: t for f, t in zip(chinese_words, __k)}.items()
                    for i in test:
                        key = key.replace(i[0], i[1])
                    _r4 = list(filter(lambda x: reduce(lambda a, b: a + b, list(
                        map(lambda x: True if key in x else False, pinyin.get_all(x['label'])))),
                                      __muc_data))

                    if common:
                        _r5 = await self.search_group(user_id=user, username=raw_key, limit=len(__muc_list), offset=0,
                                                      habit='', exclude=__muc_list, origin=origin, common=common,
                                                      from_habit=True)
                        result = merge_list_of_dict(_r1, _r2, _r3, _r4, _r5)
                    else:
                        result = merge_list_of_dict(_r1, _r2, _r3, _r4)


                else:
                    key = formulate_text(key)
                    for __d in __muc_data:
                        __d['label'] = formulate_text(__d['label'])
                    _r1 = list(filter(lambda x: key in x['label'], __muc_data))
                    sql_logger.debug('R1 {}'.format(_r1))
                    _r2 = list(filter(lambda x: key in x['uri'], __muc_data))
                    sql_logger.debug('R2 {}'.format(_r2))
                    # 群名称的拼音 后续撤掉
                    # 先取每个结果的label 得到[拼音,首字母]的结果 之后用map分别得到key是否在里 再用reduce进行或操作
                    _r3 = list(filter(lambda x: reduce(lambda a, b: a + b, list(
                        map(lambda x: True if key in x else False, pinyin.get_all(x['label'])))),
                                      __muc_data))
                    _r4 = list(filter(lambda x: get_similar_bool(key, x['label']), __muc_data))
                    if common:
                        _r5 = await self.search_group(user_id=user, username=raw_key, limit=len(__muc_list), offset=0,
                                                      habit='', exclude=__muc_list,
                                                      from_habit=True)
                        result = merge_list_of_dict(_r1, _r2, _r3, _r4, _r5)
                    else:
                        result = merge_list_of_dict(_r1, _r2, _r3, _r4)
                    sql_logger.debug(
                        'PINYIN {}'.format([pinyin.get_all(x['label']) for x in __muc_data]))
                    sql_logger.debug('R3 {}'.format(_r3))
        # self.close()
        sql_logger.debug('returning result {}'.format(list(result)))
        return list(result)

    async def single_habit_data(self, data, user_domain):
        s_result = list()
        s_data = list(map(lambda x: x.split('@')[0], data))
        sql = """SELECT aa.user_id, aa.department, aa.icon, aa.user_name, aa.mood, aa.pinyin FROM ( SELECT a.user_id, a.department, b.url AS icon, a.user_name, b.mood, a.pinyin FROM host_users a LEFT JOIN vcard_version b ON a.user_id = b.username WHERE a.hire_flag = 1 AND LOWER(a.user_type) != 's' AND a.user_id = ANY($1) and a.host_id = ANY(select id from host_info where host = $2  )) aa """

        pgconn = await asyncpg.connect(self.conn_str)
        stmt = await pgconn.prepare(sql)
        for (user_id, department, icon, user_name, mood, __pinyin) in await stmt.fetch(s_data, user_domain):
            res = dict()
            row = [user_id, department, icon, user_name, mood, __pinyin]
            row = ['' if x is None else x for x in row]
            res['qtalkname'] = row[0]
            res['uri'] = row[0] + '@' + domain
            res['content'] = row[1]
            res['icon'] = row[2]
            res['name'] = row[3]
            res['label'] = row[3] + '(' + row[0] + ')'
            if row[4]:
                res['label'] = res['label'] + ' - ' + row[4]
            res['pinyin'] = row[5]
            s_result.append(res)
        await pgconn.close()
        sql_logger.debug('SINGLE HABIT {}'.format(s_result))
        return s_result

    async def muc_habit_data(self, data, user):
        if '@' in user:
            user_s_name = user.split('@')[0]
            user_domain = user.split('@')[1]
            if isinstance(conference_str, str):
                muc_domain = conference_str
            else:
                muc_domain = 'conference.' + user_domain
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        s_result = list()
        s_data = list(map(lambda x: x.split('@')[0], data))
        # s_data = ','.join(list(map(lambda x: x + '@conference.' + domain, data)))
        sql = """select a.muc_name, a.domain, b.show_name, b.muc_title, b.muc_pic, b.show_name_pinyin from user_register_mucs as a left join muc_vcard_info as b on concat(a.muc_name, '@', a.domain) = b.muc_name where a.registed_flag != 0 and a.username = $2 and a.host = $3 and a.muc_name = ANY($1)"""
        injection = [s_data, user_s_name, user_domain]
        # 下面这个注解可取回群成员
        # sql = """SELECT a.muc,a.user_list, b.show_name, b.muc_title, b.muc_pic, b.show_name_pinyin as pinyin FROM (SELECT (muc_name || '@' || domain )as muc, array_agg(username) as user_list  FROM user_register_mucs WHERE registed_flag != 0 AND muc_name = ANY($1) GROUP BY muc_name ||'@'|| domain )a LEFT JOIN muc_vcard_info b on a.muc = b.muc_name"""
        # injection = [s_data]
        pgconn = await asyncpg.connect(self.conn_str)
        stmt = await pgconn.prepare(sql)
        for (url, s_domain, show_name, muc_title, muc_pic, __pinyin) in await stmt.fetch(*injection):
            row = [url, s_domain, show_name, muc_title, muc_pic, __pinyin]
            # if user not in row[1]:
            #    continue
            row = ['' if x is None else x for x in row]
            res = dict()
            res['uri'] = row[0] + '@' + row[1]
            # res['member_list'] = row[1]
            res['label'] = row[2]
            res['content'] = row[3]
            res['icon'] = row[4]
            res['pinyin'] = row[5]
            s_result.append(res)
        await pgconn.close()
        sql_logger.debug('MUC HABIT {}'.format(s_result))
        return s_result

    async def search_user(self, username, user_id, limit=5, offset=0, habit='', exclude=None):
        s_result = list()
        exclude_list = []
        if '@' in user_id:
            user_s_name = user_id.split('@')[0]
            user_domain = user_id.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        if exclude:
            exclude_list = {'{}'.format(x.get('qtalkname')) for x in exclude}
            offset = offset - len(exclude)
            if offset < 0:
                offset = 0
        regex_tag = username.startswith(REGEX_TAG)
        if regex_tag:
            search_model = '~'
            username = username[1:]
        else:
            search_model = 'ilike'
            username = '%{}%'.format(username)
        if if_cached:
            sql = """SELECT aa.user_id, aa.department, bb.url as icon, CASE WHEN aa.nick != '' THEN aa.nick ELSE aa.user_name END, bb.mood , aa.pinyin
                     FROM (
                        SELECT a.user_id, b.department, b.user_name, b.pinyin, a.nick 
                        FROM (
                            SELECT uu.user_id || '@' || hh.host as user_id,'' as nick, uu.host_id as hostid
                            FROM host_users uu
                            LEFT JOIN host_info hh
                            ON uu.host_id = hh.id
                            WHERE uu.hire_flag = 1 AND LOWER(uu.user_type) != 's' AND uu.user_id  <> ALL($4) AND (uu.user_id ILIKE $1 OR uu.user_name {search_model} $1 OR uu.pinyin ILIKE $1 ) AND uu.host_id = ANY(select id from host_info where host = $6 )
                            UNION 
                            SELECT cc.subkey AS user_id, cc.configinfo as nick, hh.id as hostid
                            FROM client_config_sync cc
                            LEFT JOIN host_info hh
                            ON cc.host = hh.host
                            WHERE split_part(cc.subkey,'@',1) <> ALL($4) AND cc.username = $5 AND cc.configkey = 'kMarkupNames' AND cc.configinfo {search_model} $1 AND cc.host = $6
                            ) a 
                        LEFT JOIN host_users b 
                        ON split_part(a.user_id,'@',1) = b.user_id AND a.hostid = b.host_id
                        ) aa 
                     LEFT JOIN vcard_version bb 
                     ON aa.user_id = bb.username || '@' || bb.host
                     ORDER BY aa.user_id ASC LIMIT $2 OFFSET $3"""
            sql = sql.format(search_model=search_model)
            injection = [username, limit, offset, exclude_list, user_s_name, user_domain]
        else:
            sql = """SELECT aa.user_id, aa.department, bb.url as icon, CASE WHEN aa.nick != '' THEN aa.nick ELSE aa.user_name END, bb.mood , aa.pinyin
                     FROM 
                     (
                         SELECT a.user_id, b.department, b.user_name, b.pinyin, a.nick
                         FROM (
                             SELECT uu.user_id || '@' || hh.host as user_id,'' as nick, uu.host_id as hostid
                             FROM host_users uu
                             LEFT JOIN host_info hh
                             ON uu.host_id = hh.id
                             WHERE uu.hire_flag = 1 AND LOWER(uu.user_type) != 's'  AND 
                             ( uu.user_id ILIKE $1 OR uu.user_name {search_model} $1 OR uu.pinyin ILIKE $1 ) AND uu.host_id = ANY(select id from host_info where host = $5 )
                             UNION 
                             SELECT cc.subkey AS user_id, cc.configinfo as nick, hh.id as hostid
                             FROM client_config_sync cc
                             LEFT JOIN host_info hh
                             ON cc.host = hh.host
                             WHERE cc.username = $4 AND cc.configkey = 'kMarkupNames' AND cc.configinfo {search_model} $1  AND cc.host = $5
                         ) a 
                         LEFT JOIN host_users b 
                         ON split_part(a.user_id, '@', 1)  = b.user_id AND a.hostid = b.host_id
                     ) aa 
                     LEFT JOIN vcard_version bb 
                     ON aa.user_id = bb.username || '@' || bb.host
                     LEFT JOIN 
                     (
                     SELECT CASE WHEN m_from || '@' || from_host = $6 THEN m_to || '@' || to_host ELSE m_from || '@' || from_host END AS contact, max(create_time) mx 
                         FROM msg_history 
                         WHERE (m_from = $4 and from_host = $5 ) or (m_to = $4  and to_host = $5  )
                         GROUP BY contact
                     ) cc 
                     ON aa.user_id = cc.contact 
                     ORDER BY cc.mx DESC nulls last 
                     LIMIT $2
                     OFFSET $3"""
            sql = sql.format(search_model=search_model)
            injection = [username, limit, offset, user_s_name, user_domain, user_id]
        pgconn = await asyncpg.connect(self.conn_str)
        stmt = await pgconn.prepare(sql)
        for (user_id, department, icon, user_name, mood, __pinyin) in await stmt.fetch(*injection):
            res = dict()
            row = [user_id, department, icon, user_name, mood, __pinyin]
            row = ['' if x is None else x for x in row]
            res['qtalkname'] = row[0].split('@')[0]
            res['uri'] = row[0]
            res['content'] = row[1]
            res['icon'] = row[2]
            res['name'] = row[3]
            res['label'] = row[3] + '(' + row[0] + ')'
            if row[4]:
                res['label'] = res['label'] + ' - ' + row[4]
            res['pinyin'] = row[5]
            s_result.append(res)
        if if_cached and habit:
            sql_logger.debug('BEFORE HABIT REARRANGE {}\n HABIT {}'.format(s_result, habit))
            s_result = self.sort_by_habit(data=s_result, habit=habit[SINGLE_KEY], name_key='qtalkname',
                                          search_key=username)
            sql_logger.debug('AFTER HABIT REARRANGE {}'.format(s_result))
        elif if_cached and not habit:
            sql_logger.error("CACHED BUT NO HABIT, userid : {user_id}, username : {username}}".format(user_id=user_id,
                                                                                                      username=username))

        # 将完全匹配放在第一, todo:以后应该从userdata取 同时增加更新机制
        if '.' in username and s_result:
            username = username + '@' + user_domain
            tag = False
            for x in s_result:
                if username == x.get('uri'):
                    __ = s_result.pop(x)
                    s_result = [__] + s_result
                    tag = True
            if not tag and self.user_data:
                __complete_match = self.user_data.get(username)
                if __complete_match:
                    res = dict()
                    res['qtalkname'] = __complete_match['i'].split('@')[0]
                    res['uri'] = __complete_match['i']
                    res['content'] = __complete_match['d']
                    res['icon'] = __complete_match['u']
                    res['name'] = __complete_match['n']
                    res['label'] = __complete_match['n'] + '(' + __complete_match['i'] + ')'
                    if __complete_match['m']:
                        res['label'] = res['label'] + ' - ' + __complete_match['m']
                    res['pinyin'] = __complete_match['p']
                    s_result = [res] + s_result
        await pgconn.close()

        sql_logger.debug('SINGLE RESULT {}'.format(s_result))
        return s_result

    async def search_group(self, user_id, username, limit=5, offset=0, habit='', exclude=None, origin=True,
                           common=True, from_habit=False):
        # todo 这里写的很丑 有时间可以优化一下
        if '@' in user_id:
            user_s_name = user_id.split('@')[0]
            user_domain = user_id.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        regex_tag = username.startswith(REGEX_TAG)
        if regex_tag:
            search_model = '~'
            username = username[1:]
        else:
            search_model = 'ilike'
            username = '%{}%'.format(username)
        raw_key = username.strip()
        __start_time = time.time()
        s_result = list()
        key = None
        if not exclude:
            exclude = []
        if common:
            key = username
            key = key.split()
            _key_list = []
            for _k in key:
                # 纯中文
                if not chinese_pattern.sub('', _k):
                    if len(_k) >= 2:
                        if not regex_tag:
                            _k = '%{}%'.format(_k)
                        _key_list.append(_k)
                else:
                    if len(_k) > 3:
                        if not regex_tag:
                            _k = '%{}%'.format(_k)
                        _key_list.append(_k)
            # key = list(filter(lambda x: len(x) >= 2, key))
            key = _key_list
            if key:
                if user_s_name in key:
                    if not key.remove(user_id):
                        common = False
                        # return None
            else:
                common = False

            # 根据key来返回命中高亮是返回汉子还是id TODO: 需要直接通过优化sql选择
            if common:
                if not chinese_pattern.findall(''.join(key)):
                    ret_user_name = False
                else:
                    ret_user_name = True
        if not exclude:
            exclude = set()
        offset = offset - len(exclude)
        if offset < 0:
            offset = 0
        if from_habit:
            # 此处只是为了从缓存cache提供的群组踵查找组内用户 如果key不是查找用户的话应该直接返回空
            if key:
                sql = self.make_common_sql(keys=key, origin=False, common=common, habit_tag=True)
            else:
                return []
            exclude_list = list(map(lambda x: x.split('@')[0], exclude))
        else:
            sql = self.make_common_sql(keys=key, origin=origin, common=common)
            exclude_list = {'{}'.format(x.get('uri', '')) for x in exclude}
            exclude_list = list(map(lambda x: x.split('@')[0], exclude_list))
        sql = sql.format(search_model=search_model)
        if from_habit:
            injection = [*key, user_id, offset, limit, exclude_list, user_domain]
        elif common and origin:
            injection = [*key, user_s_name, offset, limit, exclude_list, username, user_domain]
        elif common and not origin:
            injection = [*key, user_s_name, offset, limit, exclude_list, user_domain]
        elif not common and origin:
            injection = [user_s_name, username, limit, offset, exclude_list, user_domain]
        else:
            return []
        pgconn = await asyncpg.connect(self.conn_str)
        stmt = await pgconn.prepare(sql)
        for (muc_name, s_domain, show_name, muc_title, muc_pic, users) in await stmt.fetch(*injection):
            row = [muc_name, s_domain, show_name, muc_title, muc_pic, users]
            row = ['' if x is None else x for x in row]
            res = dict()
            # res['uri'] = row[0] + '@' + row[1]
            res['uri'] = row[0]
            res['label'] = row[2]
            res['content'] = row[3]
            res['icon'] = row[4]
            __hits = []
            from_common = False
            from_name = False
            if row[5]:
                if isinstance(row[5], list):
                    for i in row[5]:
                        if i == ['']:
                            from_name = True
                            continue
                        if not i:
                            continue
                        if isinstance(i, str):
                            if '|' in i:
                                __hits.extend(i.split('|'))
                            else:
                                __hits.append(i)
                        elif isinstance(i, list):
                            for u in i:
                                if isinstance(u, str):
                                    if '|' in u:
                                        __hits.extend(u.split('|'))
                                    else:
                                        __hits.append(u)
                                elif isinstance(u, list):
                                    for k in u:
                                        if '|' in k:
                                            __hits.extend(k.split('|'))
                                        else:
                                            __hits.append(k)
                        else:
                            raise TypeError("WRONG COMMON MEMBER HITS {}".format(row[5]))
                # 应该不会出现是str的情况, 如果出现基本上也过不去长度的检测
                elif isinstance(row[5], str):
                    if '|' in row[5]:
                        __hits.extend(row[5].split('|'))
                    else:
                        __hits.append(row[5])
            else:
                from_name = True
            if __hits and len(__hits) >= len(key):
                from_common = True
                res['hit'] = __hits
            elif __hits and len(__hits) < len(key):
                from_common = False
                if not from_name:
                    continue
            if from_common and from_name:
                res['todoType'] = 6
            elif from_common and not from_name:
                res['todoType'] = 4
            elif not from_common and from_name:
                res['todoType'] = 2
            s_result.append(res)

        await pgconn.close()
        if not from_habit:
            if if_cached and habit:
                _habit = list(map(lambda x: x + '@conference.' + domain, habit[MUC_KEY]))
                sql_logger.debug('BEFORE HABIT REARRANGE {}\n HABIT {}'.format(s_result, habit))
                s_result = self.sort_by_habit(data=s_result, habit=_habit, name_key='uri')
                sql_logger.debug('AFTER HABIT REARRANGE {}'.format(s_result))
                # s_result = self.sort_by_habit(data=s_result, habit=habit[MUC_KEY], name_key='uri')
            elif if_cached and not habit:
                sql_logger.error(
                    "CACHED BUT NO HABIT, userid : {user_id}, username : {username}}".format(user_id=user_id,
                                                                                             username=username))
        else:
            _habit = list(map(lambda x: x + '@conference.' + domain, exclude_list))
            # s_result = sorted(s_result, key=lambda x: [x for x in exclude_list].index(x))
            sql_logger.debug('BEFORE HABIT REARRANGE {}\n HABIT {}'.format(s_result, habit))
            s_result = self.sort_by_habit(data=s_result, habit=_habit, name_key='uri')
            sql_logger.debug('AFTER HABIT REARRANGE {}'.format(s_result))
        if common and ret_user_name and self.user_data:
            for _r in s_result:
                hits = _r.get('hit', '')
                if not hits:
                    break
                if isinstance(hits, list):
                    # name = [x.get('n') for x in user_data if x.get('i') in hits]
                    # name = [user_data.get(x.split('@')[0]).get('n', '') for x in hits]
                    name = [self.user_data.get(x, {}).get('n', '') for x in hits]
                else:
                    # name = [x.get('n') for x in user_data if x.get('i') == hits]
                    name = [self.user_data.get(x, {}).get('n', '') for x in hits]
                _r['hit'] = name

        sql_logger.debug('GROUP RESULT {}'.format(s_result))
        __end_time = time.time()
        sql_logger.info("SEARCH GROUP USED {}".format(__end_time - __start_time))
        return s_result

    async def search_group_by_single(self, user_id, key, limit=5, offset=0, habit='', exclude=None):
        if '@' in user:
            user_s_name = user.split('@')[0]
            user_domain = user.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        if not isinstance(conference_str, str):
            if '@' in user_id:
                conference_str = 'conference.' + user_id.split('@')[1]
            else:
                raise TypeError("CANT DETERMINE DOMAIN FOR SEARCH conference_str {}".format(conference_str))
        if not exclude:
            exclude = []
        key = key.split()
        key = list(filter(lambda x: len(x) > 2, key))
        if key:
            if user_id in key:
                if not key.remove(user_id):
                    return None
        else:
            return None
        # 根据key来返回命中高亮是返回汉子还是id TODO: 需要直接通过优化sql选择
        if not chinese_pattern.findall(''.join(key)):
            ret_user_name = False
        else:
            ret_user_name = True

        key_count = len(key)
        s_result = list()
        if if_cached:
            # sql = """SELECT A.muc_name, A.domain, B.show_name, B.muc_title, B.muc_pic FROM ( SELECT muc_name, domain FROM user_register_mucs WHERE username = $1 AND registed_flag != 0 AND muc_name IN ( SELECT muc_name FROM user_register_mucs WHERE username IN ( SELECT user_id FROM host_users WHERE hire_flag = 1 AND (user_id ~ ANY($2) OR user_name ~ ANY($2) OR pinyin ~ ANY($2))) GROUP BY muc_name HAVING COUNT(*) = $3 )) A JOIN muc_vcard_info B ON (A.muc_name || $6) = b.muc_name LIMIT $4 OFFSET $5"""
            sql = self.make_common_sql(key)
            exclude_list = {'{}'.format(x.get('uri', '')) for x in exclude}
            injection = [*key, user_id, '@' + conference_str, offset, limit, exclude_list]
        else:
            sql = """SELECT A.muc_room_name, split_part(b.muc_name, '@', 2) as domain, B.show_name, B.muc_title, B.muc_pic FROM (SELECT muc_room_name, MAX(create_time) as max FROM muc_room_history aa RIGHT JOIN (SELECT muc_name FROM user_register_mucs WHERE username = $1 AND registed_flag != 0 AND muc_name in (SELECT muc_name FROM user_register_mucs WHERE username IN (SELECT user_id FROM host_users WHERE hire_flag = 1 AND (user_id ~ any($2) OR user_name ~ any($2) OR pinyin ~ any($2))) GROUP BY muc_name HAVING COUNT(*) = $3)) bb ON aa.muc_room_name = bb.muc_name GROUP BY muc_room_name ORDER BY max DESC nulls last LIMIT $4 OFFSET $5) A JOIN muc_vcard_info B ON (a.muc_room_name || $6) = b.muc_name"""
            injection = [user_id, key, key_count, limit, offset, '@' + conference_str]
        pgconn = await asyncpg.connect(self.conn_str)
        stmt = await pgconn.prepare(sql)
        for (muc_name, s_domain, show_name, muc_title, muc_pic, users) in await stmt.fetch(*injection):
            row = [muc_name, s_domain, show_name, muc_title, muc_pic, users]
            row = ['' if x is None else x for x in row]
            res = dict()
            res['uri'] = row[0] + '@' + row[1]
            res['label'] = row[2]
            res['content'] = row[3]
            res['icon'] = row[4]
            res['hit'] = row[5] if isinstance(row[5], list) else [row[5]]
            s_result.append(res)
        await pgconn.close()
        if ret_user_name and user_data:
            for _r in s_result:
                hits = _r.get('hit', '')
                if isinstance(hits, list):
                    # name = [x.get('n') for x in user_data if x.get('i') in hits]
                    name = [user_data.get(x).get('n', '') for x in hits]
                else:
                    # name = [x.get('n') for x in user_data if x.get('i') == hits]
                    name = [user_data.get(x).get('n', '') for x in hits]
                _r['hit'] = name

        if if_cached and habit:
            _habit = list(map(lambda x: x + '@conference.' + domain, habit[MUC_KEY]))
            sql_logger.debug('BEFORE HABIT REARRANGE {}\n HABIT {}'.format(s_result, habit))
            s_result = self.sort_by_habit(data=s_result, habit=_habit, name_key='uri')
            sql_logger.debug('AFTER HABIT REARRANGE {}'.format(s_result))
        elif if_cached and not habit:
            sql_logger.error("CACHED BUT NO HABIT, userid : {user_id}, username : {username}}".format(user_id=user_id,
                                                                                                      username=key))
        sql_logger.debug('COMMON RESULT {}'.format(s_result))
        return s_result

    async def history_user(self, user_id, term, offset, limit, to_user=None, time_range=None, agg_tag=False):
        s_result = list()
        if '@' in user_id:
            user_s_name = user_id.split('@')[0]
            user_domain = user_id.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        regex_tag = term.startswith(REGEX_TAG)
        if regex_tag:
            search_model = '~'
            term = term[1:]
        else:
            search_model = 'ilike'
            term = '%{}%'.format(term)
        if not agg_tag and to_user:
            sql = """SELECT create_time as date, m_from, from_host as fromhost, realfrom, m_to , to_host as tohost, realto as realto, m_body as msg, msg_id
                     FROM msg_history 
                     WHERE  xpath('/message/body/text()',m_body::xml)::text {search_model} $1 {user_limit} {time_limit_start} {time_limit_end}
                     ORDER BY create_time DESC
                     OFFSET  $3
                     LIMIT  $2"""
            injection = [term, limit, offset, user_s_name, user_domain]
            if to_user:
                if isinstance(to_user, list):
                    # TODO: 这里可能要做prepare 不然在没有realto的时候拼接字段会导致慢查询
                    user_limit = """AND (
                        (m_from = $4 and from_host = $5 and m_to || '@' || to_host = ANY($6) 
                        OR 
                        (m_to = $4 and to_host = $5 and m_from || '@' || from_host = ANY($6) 
                        )"""
                    injection += [to_user]
                elif isinstance(to_user, str):
                    to_user_s_name = to_user.split('@')[0]
                    to_user_domain = to_user.split('@')[1]
                    user_limit = """AND (
                       (m_from = $4 and from_host = $5 and m_to = $6 and to_host = $7 ) 
                       OR 
                       (m_to = $4 and to_host = $5 and m_from = $6 and from_host =$7 ) 
                       )"""
                    injection += [to_user_s_name, to_user_domain]

                else:
                    user_limit = ''
            else:
                # user_limit = "AND (m_from = $4 or m_to = $4)"
                user_limit = "AND ((m_from = $4 and from_host = $5) or(m_to = $4 and to_host = $5))"

            time_limit_start = ''
            time_limit_end = ''
            if time_range and isinstance(time_range, list):
                first_index = len(injection) + 1
                second_index = len(injection) + 2
                if time_range[0] and time_range[1]:
                    time_limit_start = "AND create_time > ${} AND create_time < ${}".format(first_index, second_index)
                    injection += time_range
                elif time_range[0] and not time_range[1]:
                    time_limit_start = "AND create_time > ${}".format(first_index)
                    injection += [time_range[0]]
                elif time_range[1] and not time_range[0]:
                    time_limit_end = "AND create_time < ${}".format(first_index)
                    injection += [time_range[1]]
            sql = sql.format(user_limit=user_limit, time_limit_start=time_limit_start, time_limit_end=time_limit_end,
                             search_model=search_model)
            pgconn = await asyncpg.connect(self.conn_str)
            stmt = await pgconn.prepare(sql)
            for (date, m_from, fromhost, realfrom, m_to, tohost, realto, msg, msg_id) in await stmt.fetch(*injection):
                res = dict()
                row = [date, m_from, fromhost, realfrom, m_to, tohost, realto, msg, msg_id]
                row = ['' if x is None else x for x in row]
                if row[0]:
                    res['date'] = row[0].strftime('%Y-%m-%d %H:%M:%S')
                else:
                    res['date'] = ''
                res['from'] = row[1] + '@' + row[2]
                res['realfrom'] = row[3] if row[3] else res['from']
                res['to'] = row[4] + '@' + row[5]
                res['realto'] = row[6] if row[6] else res['to']
                res['msg'] = row[7]
                res['msgid'] = row[8]
                s_result.append(res)
            await pgconn.close()
        else:

            sql = """SELECT a.count, b.create_time as date, b.m_from, b.from_host as fromhost, b.realfrom, b.m_to, b.to_host as tohost, b.realto, b.m_body as msg, a.conversation, b.msg_id, a.id FROM
                    (
                    SELECT count(1) as count, MAX(id) as id, m_from||'@'||from_host || '_' || m_to||'@'||to_host as conversation
                    FROM msg_history
                    WHERE xpath('/message/body/text()',m_body::xml)::text {search_model} $1 AND ( (m_from = $4 and from_host = $5 ) or (m_to = $4 and to_host = $5) {time_limit_start} {time_limit_end})
                    GROUP BY m_from||'@'||from_host || '_' || m_to||'@'||to_host
                    ORDER BY id desc 
                    OFFSET $3
                    LIMIT $2
                    ) a
                    LEFT JOIN msg_history b
                    ON a.id = b.id"""
            injection = [term, limit, offset, user_s_name, user_domain]
            time_limit_start = ''
            time_limit_end = ''
            if time_range and isinstance(time_range, list):
                if time_range[0] and time_range[1]:
                    time_limit_start = "AND b.create_time > $6 AND b.create_time < $7 "
                    injection += time_range
                elif time_range[1] and not time_range[0]:
                    time_limit_end = "AND b.create_time < $6"
                    injection += time_range[1]
                elif time_range[0] and not time_range[1]:
                    time_limit_end = "AND b.create_time > $6"
                    injection += time_range[0]
            sql = sql.format(time_limit_start=time_limit_start, time_limit_end=time_limit_end,
                             search_model=search_model)
            pgconn = await asyncpg.connect(self.conn_str)
            stmt = await pgconn.prepare(sql)
            for (count, date, m_from, fromhost, realfrom, m_to, tohost, realto, msg, conversation,
                 msg_id, _id) in await stmt.fetch(*injection):
                row = [count, date, m_from, fromhost, realfrom, m_to, tohost, realto, msg, conversation, msg_id, _id]
                row = ['' if x is None else x for x in row]
                res = dict()
                res['count'] = row[0]
                if row[1]:
                    res['date'] = row[1].strftime('%Y-%m-%d %H:%M:%S')
                else:
                    res['date'] = ''
                res['from'] = row[2] + '@' + row[3]
                res['realfrom'] = row[4] if row[4] else res['from']
                res['to'] = row[5] + '@' + row[6]
                res['realto'] = row[7] if row[7] else res['to']
                res['msg'] = row[8]
                res['conversation'] = row[9]
                res['msgid'] = row[10]
                res['id'] = row[11]
                s_result.append(res)
            s_result = self.handle_sql_result(data=s_result)
            await pgconn.close()
        return s_result

    async def history_muc(self, user_id, term, offset, limit, to_muc=None, time_range=None, agg_tag=False):
        """

        :param user_id:
        :param user_mucs:
        :param term:
        :param offset:
        :param limit:
        :param to_muc:
        :param time_range:
        :param agg_tag:
        :return:
        """
        s_result = list()
        if '@' in user_id:
            user_s_name = user_id.split('@')[0]
            user_domain = user_id.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return
        regex_tag = term.startswith(REGEX_TAG)
        if regex_tag:
            search_model = '~'
            term = term[1:]
        else:
            search_model = 'ilike'
            term = '%{}%'.format(term)
        if not agg_tag and to_muc:
            sql = """SELECT a.create_time as date, b.muc_name as _to, a.packet as msg, a.msg_id as msgid, b.show_name as label, b.muc_pic as icon
                                 FROM muc_room_history a left join muc_vcard_info b
                                 on a.muc_room_name = split_part(b.muc_name,'@',1)
                                 WHERE  xpath('/message/body/text()',packet::xml)::text {search_model} $1 {muc_limit} {time_limit_start} {time_limit_end}
                                 ORDER BY create_time DESC
                                 OFFSET  $3
                                 LIMIT $2"""
            injection = [term, limit, offset, user_s_name]
            time_limit_start = ''
            time_limit_end = ''
            if to_muc:
                if isinstance(to_muc, list):
                    to_muc = list(map(lambda x: x.split('@')[0], to_muc))
                    muc_limit = "AND muc_room_name = ANY(SELECT muc_name FROM user_register_mucs WHERE username = $4 AND muc_name = ANY($5) )"
                    injection += [to_muc]
                elif isinstance(to_muc, str):
                    to_muc = to_muc.split('@')[0]
                    muc_limit = "AND muc_room_name = ANY(SELECT muc_name FROM user_register_mucs WHERE username = $4 AND muc_name = $5)"
                    injection += [to_muc]
                else:
                    return []

                if time_range and isinstance(time_range, list):
                    if time_range[0] and time_range[1]:
                        time_limit_start = "AND create_time > $6"
                        time_limit_end = "AND create_time < $7"
                        injection += time_range
                    if time_range[0] and not time_range[1]:
                        time_limit_start = "AND create_time > $6"
                        injection += [time_range[0]]
                    if time_range[1] and not time_range[0]:
                        time_limit_end = "AND create_time < $6"
                        injection += [time_range[1]]
            else:
                muc_limit = "AND muc_room_name in (SELECT muc_name FROM user_register_mucs where username = $4 and registed_flag = 1)"
                if time_range and isinstance(time_range, list):
                    if time_range[0] and time_range[1]:
                        time_limit_start = "AND create_time > $5"
                        time_limit_end = "AND create_time < $6"
                        injection += time_range
                    if time_range[0] and not time_range[1]:
                        time_limit_start = "AND create_time > $5"
                        injection += [time_range[0]]
                    if time_range[1] and not time_range[0]:
                        time_limit_end = "AND create_time < $5"

            sql = sql.format(muc_limit=muc_limit, time_limit_start=time_limit_start, time_limit_end=time_limit_end,
                             search_model=search_model)
            pgconn = await asyncpg.connect(self.conn_str)
            stmt = await pgconn.prepare(sql)
            for (date, _to, msg, msgid, label, icon) in await stmt.fetch(*injection):
                row = [date, _to, msg, msgid, label, icon]
                row = ['' if x is None else x for x in row]
                res = dict()
                if row[0]:
                    res['date'] = row[0].strftime('%Y-%m-%d %H:%M:%S')
                else:
                    res['date'] = ''
                res['to'] = row[1]
                res['msg'] = row[2]
                res['msgid'] = row[3]
                res['from'] = ''
                res['label'] = row[4]
                res['icon'] = row[5]
                s_result.append(res)
            await pgconn.close()

        else:
            sql = """SELECT count, c.muc_name, b.msg_id, b.create_time as date, b.packet, c.show_name as label, c.muc_pic as icon , a.id FROM
                    (
                    SELECT count(1) as count, MAX(id) as id, muc_room_name
                    FROM muc_room_history
                    WHERE xpath('/message/body/text()',packet::xml)::text {search_model} $1 AND muc_room_name = ANY(SELECT muc_name FROM user_register_mucs where username = $4 and registed_flag = 1  AND host = $5 and domain = 'conference.' || $5 ) {time_limit_start} {time_limit_end}
                    GROUP BY muc_room_name
                    ORDER BY id desc 
                    OFFSET $3
                    LIMIT $2
                    )a 
                    LEFT JOIN muc_room_history b 
                    ON a.id = b.id
                    LEFT JOIN muc_vcard_info c
                    on a.muc_room_name = split_part(c.muc_name,'@',1)"""
            injection = [term, limit, offset, user_s_name, user_domain]
            time_limit_start = ''
            time_limit_end = ''
            if time_range and isinstance(time_range, list):
                if time_range[0] and time_range[1]:
                    time_limit_start = "AND create_time > $7"
                    time_limit_end = "AND create_time < $8"
                    injection += time_range
                if time_range[0] and not time_range[1]:
                    time_limit_start = "AND create_time > $7"
                    injection += [time_range[0]]
                if time_range[1] and not time_range[0]:
                    time_limit_end = "AND create_time < $7"
            sql = sql.format(time_limit_start=time_limit_start, time_limit_end=time_limit_end,
                             search_model=search_model)
            pgconn = await asyncpg.connect(self.conn_str)
            stmt = await pgconn.prepare(sql)
            for (count, muc_room_name, msg_id, date, packet, label, icon, __id) in await stmt.fetch(*injection):
                row = [count, muc_room_name, msg_id, date, packet, label, icon, __id]
                row = ['' if x is None else x for x in row]
                res = dict()
                res['count'] = row[0]
                res['to'] = row[1]
                res['msgid'] = row[2]
                if row[3]:
                    res['date'] = row[3].strftime('%Y-%m-%d %H:%M:%S')
                else:
                    res['date'] = ''
                res['msg'] = row[4]
                res['from'] = ''
                res['label'] = row[5]
                res['icon'] = row[6]
                s_result.append(res)
            await pgconn.close()
            # s_result = self.handle_sql_result(data=s_result)
        return s_result

    async def history_file(self, user_id, term, offset=0, limit=5, time_range=None):
        """

        :param user_id:
        :param term:
        :param offset:
        :param limit:
        :param time_range:
        :return:
        """
        s_result = list()
        if '@' in user_id:
            user_s_name = user_id.split('@')[0]
            user_domain = user_id.split('@')[1]
        else:
            sql_logger.error('SEARCH USER WITHOUT DOMAIN')
            return []
        regex_tag = term.startswith(REGEX_TAG)
        if regex_tag:
            search_model = '~'
            term = term[1:]

        else:
            search_model = 'ilike'
            term = '%{}%'.format(term)
        sql = """SELECT file, from_, pfv.muc_name as to_, date, msgid, pfv.show_name as label, pfv.muc_pic as icon, msg
                     FROM (
                         SELECT json(unnest(xpath('//body[@msgType="5"]/text()', packet::xml))::text) AS file, '' AS from_, muc_room_name AS to_, create_time AS date, msg_id AS msgid,packet as msg
                         FROM muc_room_history
                         WHERE muc_room_name IN (
                             SELECT muc_name
                             FROM user_register_mucs
                             WHERE username = $4
                                AND registed_flag = 1
                                AND host= $5 
                         )
                     ) pfc left join muc_vcard_info pfv
                     on pfc.to_= split_part(pfv.muc_name,'@',1)
                     UNION ALL
                     SELECT file, from_, to_, date, msgid, pfb.user_name as label, pfv.url as icon, msg
                     FROM (
                         SELECT json(unnest(xpath('/message/body[@msgType="5"]/text()', m_body::xml))::text) AS file, m_from || '@' || from_host as from_
                             , m_to || '@' || to_host as to_, create_time AS date
                             , msg_id AS msgid, m_body as msg
                         FROM msg_history
                         WHERE (m_from = $4 AND from_host = $5 )
                         OR (m_to = $4 AND to_host = $5 )
                     ) pfx left join vcard_version pfv
                     on split_part(pfx.from_,'@',1) = pfv.username
                     left join host_users pfb
                     on pfv.username = pfb.user_id and pfv.host = ANY(SELECT host from host_info WHERE id = pfb.host_id)
                     WHERE file ->> 'FileName' {search_model} $1 {time_limit_start} {time_limit_end}
                     ORDER BY date desc
                     OFFSET $3
                     LIMIT $2
    """

        injection = [term, limit, offset, user_s_name, user_domain]
        time_limit_start = ''
        time_limit_end = ''
        if time_range and isinstance(time_range, list):
            if time_range[0] and time_range[1]:
                time_limit_start = "AND create_time > $5"
                time_limit_end = "AND create_time < $6"
                injection += time_range
            if time_range[0] and not time_range[1]:
                time_limit_start = "AND create_time > $5"
                injection += [time_range[0]]
            if time_range[1] and not time_range[0]:
                time_limit_end = "AND create_time < $5"
        sql = sql.format(time_limit_start=time_limit_start, time_limit_end=time_limit_end, search_model=search_model)
        pgconn = await asyncpg.connect(self.conn_str)
        stmt = await pgconn.prepare(sql)
        for (file, from_, to_, date, msgid, label, icon, msg) in await stmt.fetch(*injection):
            row = [file, from_, to_, date, msgid, label, icon, msg]
            row = ['' if x is None else x for x in row]
            res = dict()
            res['fileinfo'] = json.loads(row[0])
            res['from'] = row[1]
            res['to'] = row[2]
            if row[3]:
                res['date'] = row[3].strftime('%Y-%m-%d %H:%M:%S')
            else:
                res['date'] = ''
            res['msgid'] = row[4]
            res['source'] = row[5] if row[5] else row[1]
            res['icon'] = row[6]
            res['msg'] = row[7]
            res['mtype'] = 5
            s_result.append(res)
        await pgconn.close()
        return s_result

    async def history_single_file(self, user_id, term, offset=0, limit=5):
        s_result = list()
        sql = """SELECT * from ( SELECT unnest(xpath('//body[@msgType="5"]/text()',m_body::xml))::text::json as file, m_from, m_to,create_time as epo, msg_id as msgid from msg_history where m_from = $1 or m_to = $1) as pfx where pfx.file->>'FileName' ~ $2 order by pfx.time desc offset $3 limit $4"""
        pgconn = await asyncpg.connect(self.conn_str)
        stmt = await pgconn.prepare(sql)
        injection = [user_id, term, offset, limit]
        for (_file, _from, _to, _time, _msgid) in await stmt.fetch(*injection):
            res = dict()
            row = [_file, _from, _to, _time, _msgid]
            row = ['' if x is None else x for x in row]
            res['file'] = row[0]
            res['from'] = row[1]
            res['to'] = row[2]
            res['time'] = row[3]
            res['msgid'] = row[4]
            res['domain'] = domain
            res['chattype'] = 'chat'  # chat groupchat
            s_result.append(res)
        # TODO SORT!!!!
        await pgconn.close()
        sql_logger.debug('FILE SINGLE RESULT {}'.format(s_result))
        return s_result

    async def history_muc_file(self, user_id, term, muc_list, offset=0, limit=5):
        s_result = list()
        sql = """SELECT * from ( SELECT unnest(xpath('//body[@msgType="5"]/text()',packet::xml))::text::json as file, nick, muc_room_name, create_time as time from muc_room_history where muc_room_name in $1 ) as pfx where pfx.file->>'FileName' ~  $2 order by pfx.time desc offset $3 limit $4"""
        pgconn = await asyncpg.connect(self.conn_str)
        stmt = await pgconn.prepare(sql)
        injection = [muc_list, term, offset, limit]
        for (_file, _from, _to, _time, _msgid) in await stmt.fetch(*injection):
            res = dict()
            row = [_file, _from, _to, _time, _msgid]
            row = ['' if x is None else x for x in row]
            res['file'] = row[0]
            res['from'] = row[1]
            res['to'] = row[2]
            res['time'] = row[3]
            res['msgid'] = row[4]
            res['domain'] = domain
            res['chattype'] = 'groupchat'  # chat groupchat
            s_result.append(res)
        # TODO SORT!!!!
        await pgconn.close()
        sql_logger.debug('FILE MUC RESULT {}'.format(s_result))
        return s_result

    async def get_mucs_info(self, muc):
        result = {}
        if '@' not in muc:
            muc = muc + '@' + conference_str
        sql = """select show_name,muc_pic from muc_vcard_info where muc_name = $1"""
        pgconn = await asyncpg.connect(self.conn_str)
        stmt = await pgconn.prepare(sql)
        injection = [muc]
        for (muc_name, pic) in await stmt.fetch(*injection):
            row = [muc_name, pic]
            row = ['' if x is None else x for x in row]
            result['show_name'] = row[0]
            result['muc_pic'] = row[1]

        # TODO SORT!!!!
        await pgconn.close()
        return result

    async def get_person_info(self, person):
        result = {}
        if '@' in person:
            person = person.split('@')[0]
        sql = """ select a.user_name,b.url from host_users a join vcard_version b on a.user_id = $1 and a.user_id = b.username;"""
        pgconn = await asyncpg.connect(self.conn_str)
        stmt = await pgconn.prepare(sql)
        injection = [person]
        for (name, pic) in await stmt.fetch(*injection):
            row = [name, pic]
            row = ['' if x is None else x for x in row]
            result['show_name'] = row[0]
            result['url'] = row[1]
        # TODO SORT!!!!
        await pgconn.close()
        return result

    @staticmethod
    def sort_by_habit(data, habit, name_key, search_key=''):
        if not data:
            return []
        if not name_key:
            sql_logger.warning("NO NAME_KEY FOUND :{}".format(data))
        if not isinstance(data, list):
            sql_logger.error("DATA NOT A LIST :{data}".format(data=data))
            return data
        if not isinstance(habit, (set, list)):
            sql_logger.error("HABIT NOT A LIST :{habit}".format(habit=habit))
            return data
        # 取出result里所有的相关字段组成list
        name_list = [x[name_key] for x in data]
        for _h in habit[::-1]:
            # for _h in habit[::-1]:
            # sql_logger.info("name_list {},\n origin data {},\n habit {}".format(name_list, data, habit[::-1]))
            # if search_key:
            #     if search_key in _h and _h not in name_list:
            #         sql_logger.warning("SHOULD ADD {} TO KEY {} RESULT {}".format(_h, search_key, data))
            # if name_key == ''
            # 如果habit里的人/群组在结果集里， 放在第一个
            if _h in name_list and name_list.index(_h) != 0:
                _t = data.pop(name_list.index(_h))
                data = [_t] + data
                _t = data.pop([x.get('uri') for x in data].index(_h))
                data = [_t] + data
                # data.remove(_)
                # data = [_] + data
        return data

    @staticmethod
    def handle_sql_result(data):
        result = {}
        for hit in data:
            a = hit['conversation'].split('_')[0]
            b = hit['conversation'].split('_')[1]
            conv = sorted([a, b])[0] + '_' + sorted([a, b])[1]
            if conv in result.keys():
                _temp = result[conv]
                if _temp['id'] > hit['id']:
                    result[conv]['count'] += hit['count']
                else:
                    result[conv] = hit
                    result[conv]['count'] += _temp['count']
            else:
                result[conv] = hit
        result = sorted(list(result.values()), key=lambda x: x.get('id'))
        return result

    @staticmethod
    def make_common_sql(keys, origin=True, common=True, habit_tag=False):
        """
        origin代表搜群名、 群id
        common代表搜群内成员
        habit_tag代表从缓存里搜索群内成员，所以有特定的组范围，sql有所不同
        :param keys:
        :param origin:
        :param common:
        :param habit_tag:
        :return:
        """
        sql = ""
        if common:
            if not keys:
                return
            case_pattern = []
            union_pattern = []
            key_len = len(keys)
            for i, k in enumerate(keys):
                case_pattern.append(
                    """SELECT ${i}, user_id
                       FROM host_users 
                       WHERE  hire_flag = 1 AND user_id != ${searcher_index} AND ( user_id ilike ${i} OR user_name {search_model} ${i} OR pinyin ilike ${i} ) AND host_id = ANY(SELECT id FROM host_info WHERE host = ${searcher_domain_index})""".format(
                        i=i + 1, searcher_index='{searcher_index}', search_model='{search_model}',
                        searcher_domain_index='{searcher_domain_index}'))
                union_pattern.append("""SELECT a.muc_name|| '@' || a.domain as muc_name, string_agg(a.username||'@'||a.host, '|') as hit, max(a.created_at) as time
                                        FROM user_register_mucs a JOIN tmp2 b ON a.muc_name = b.muc_name
                                        WHERE username IN (select user_id from tmp where key = ${i}) and a.registed_flag != 0 AND a.domain =  'conference.' || ${searcher_domain_index}
                                        group by a.muc_name || '@' || a.domain""".format(i=i + 1,
                                                                                         searcher_domain_index='{searcher_domain_index}'))

        # keys 对应 $1 ... ${len(keys)}
        # 之后是searcher_index 序号为len + 1
        # 然后是群组字符串 len + 2
        # 然后是offset len + 3
        # limit len + 4
        # 排除在 len + 5
        # 名字查询的key 在 len + 6
        # domain 在 len + 7
        if habit_tag and common:
            sql = """
                    WITH tmp (key, user_id) AS (
                        {keys_pattern}
                    ), 
                    tmp2 (muc_name, domain, created_at) AS (
                        SELECT split_part(muc_name || '@' || domain,'@',1) ,split_part(muc_name || '@' || domain,'@',2), max(created_at) as created_at
                        FROM user_register_mucs
                        WHERE username = ${searcher_index} AND host = ${searcher_domain_index}
                        AND registed_flag != 0 AND muc_name = ANY(${exclude}) AND domain = 'conference.' || ${searcher_domain_index}
                        GROUP BY muc_name || '@' || domain 
                    )
                    SELECT 
                        aa.mucname, 
                        split_part(bb.muc_name, '@', 2) AS domain,
                        bb.show_name, 
                        bb.muc_title, 
                        bb.muc_pic, 
                        aa.tag
                    FROM (
                        SELECT mucname, tag from (
                        SELECT muc_name AS mucname, array_agg(hit) AS tag
                        FROM (
                           {select_pattern}
                        ) foo 
                        GROUP BY muc_name
                        HAVING COUNT(muc_name) = {length}
                        ) boo

                    ) aa
                    JOIN muc_vcard_info bb 
                    ON (aa.mucname) = bb.muc_name 
                    offset ${offset} limit ${limit}""".format(
                # keys_pattern=' union all '.join(case_pattern),
                # select_pattern=' union all '.join(union_pattern),
                # length=key_len, conference_str_index=key_len + 2, offset=key_len + 3,
                # limit=key_len + 4, exclude=key_len + 5, searcher_index=key_len + 1, searcher_domain_index=key_len + 6,search_model='{search_model}')
                keys_pattern=' union all '.join(case_pattern),
                select_pattern=' union all '.join(union_pattern),
                searcher_index='{searcher_index}', searcher_domain_index='{searcher_domain_index}',
                length=key_len, offset=key_len + 2,
                limit=key_len + 3, exclude=key_len + 4).format(searcher_index=key_len + 1,
                                                               searcher_domain_index=key_len + 5,
                                                               search_model='{search_model}')
            return sql
        if origin and common:
            # format 填空
            sql = """
                    WITH tmp (key, user_id) AS (
                        {keys_pattern}
                    ), 
                    tmp2 (muc_name, domain, created_at) AS (
                        SELECT split_part(muc_name || '@' || domain,'@',1) ,split_part(muc_name || '@' || domain,'@',2), max(created_at) as created_at
                        FROM user_register_mucs
                        WHERE username = ${searcher_index} AND host = ${searcher_domain_index}
                        AND registed_flag != 0 AND muc_name <> ALL (${exclude}) AND domain = 'conference.' || ${searcher_domain_index}
                        GROUP BY muc_name || '@' || domain 
                    )
                    SELECT 
                        aa.mucname, 
                        split_part(bb.muc_name, '@', 2) AS domain,
                        bb.show_name, 
                        bb.muc_title, 
                        bb.muc_pic, 
                        aa.tag
                    FROM (
                    	SELECT mucname, array_agg(tag) AS tag, MAX(time) as time
	                    FROM(
                            SELECT mucname, tag, time from (
                            SELECT muc_name AS mucname, array_agg(hit) AS tag, max(time) as time
                            FROM (
                               {select_pattern}
                            ) foo 
                            GROUP BY muc_name
                            HAVING COUNT(muc_name) = {length}
                            ) boo
                            union all 
                            select a.muc_name|| '@' || a.domain as muccname, array[''] as hit, a.created_at as time
                            from tmp2 a join muc_vcard_info b on concat(a.muc_name, '@', a.domain) = b.muc_name
                            where (b.show_name {search_model} ${like_key} or b.muc_name ilike ${like_key})
                            ) poo
                        GROUP BY mucname 
                    ) aa
                    JOIN muc_vcard_info bb 
                    ON aa.mucname  = bb.muc_name 
                    ORDER BY time DESC 
                    OFFSET ${offset} LIMIT ${limit}""".format(
                # keys_pattern=' union all '.join(case_pattern),
                # select_pattern=' union all '.join(union_pattern),
                # searcher_index=key_len + 1, length=key_len, conference_str_index=key_len + 2, offset=key_len + 3,
                # limit=key_len + 4, exclude=key_len + 5, like_key=key_len + 6, searcher_domain_index=key_len + 7,
                # search_model='{search_model}')
                keys_pattern=' union all '.join(case_pattern),
                select_pattern=' union all '.join(union_pattern),
                searcher_index='{searcher_index}', length=key_len, offset=key_len + 2,
                limit=key_len + 3, exclude=key_len + 4, like_key='{like_key}',
                searcher_domain_index='{searcher_domain_index}', search_model='{search_model}').format(
                searcher_index=key_len + 1,
                like_key=key_len + 5,
                search_model='{search_model}', searcher_domain_index=key_len + 6)

        elif common and not origin:
            sql = """
                    WITH tmp (key, user_id) AS (
                        {keys_pattern}
                    ), 
                    tmp2 (muc_name, domain, created_at) AS (
                        SELECT split_part(muc_name || '@' || domain,'@',1) ,split_part(muc_name || '@' || domain,'@',2), max(created_at) as created_at
                        FROM user_register_mucs
                        WHERE username = ${searcher_index}  AND host = ${searcher_domain_index}
                        AND registed_flag != 0 AND muc_name <> ALL (${exclude}) AND domain = 'conference.' || ${searcher_domain_index}
                        GROUP BY muc_name || '@' || domain 
                    )
                    SELECT 
                        aa.mucname, 
                        split_part(bb.muc_name, '@', 2) AS domain,
                        bb.show_name, 
                        bb.muc_title, 
                        bb.muc_pic, 
                        aa.tag
                    FROM (
                        SELECT mucname, tag, time from (
                        SELECT muc_name AS mucname, array_agg(hit) AS tag, max(time) as time
                        FROM (
                           {select_pattern}
                        ) foo 
                        GROUP BY muc_name
                        HAVING COUNT(muc_name) = {length}
                        ) boo
                        
                    ) aa
                    JOIN muc_vcard_info bb 
                    ON aa.mucname = bb.muc_name 
                    ORDER BY time DESC 
                    offset ${offset} limit ${limit}""".format(
                # keys_pattern=' union all '.join(case_pattern),
                # select_pattern=' union all '.join(union_pattern),
                # length=key_len, conference_str_index=key_len + 2, offset=key_len + 3,
                # limit=key_len + 4, exclude=key_len + 5, searcher_index=key_len + 1, searcher_domain_index=key_len + 6,
                # search_model='{search_model}')
                keys_pattern=' union all '.join(case_pattern),
                select_pattern=' union all '.join(union_pattern),
                searcher_index='{searcher_index}', searcher_domain_index='{searcher_domain_index}',
                length=key_len, offset=key_len + 2,
                limit=key_len + 3, exclude=key_len + 4).format(searcher_index=key_len + 1,
                                                               searcher_domain_index=key_len + 5,
                                                               search_model='{search_model}')

        elif not common and origin:
            sql = """SELECT
                        b.muc_name as mucname, split_part(b.muc_name,'@',2) as domain, b.show_name, b.muc_title, b.muc_pic, array['']
                     FROM
                        user_register_mucs as a left join muc_vcard_info as b 
                     ON 
                        concat(a.muc_name, '@', a.domain) = b.muc_name
                     WHERE 
                        a.registed_flag != 0 and a.username = $1 and (b.show_name {search_model} $2 or b.muc_name ~ $2) and b.muc_name <> ALL ($5) AND a.host = $6 
                     order by b.update_time desc limit $3 offset $4"""
        return sql


if DB_VERSION is None:
    domain = ''
    __user_lib = UserLib()
    DB_VERSION = __user_lib.get_db_version()
    domain = __user_lib.get_domain()
    if len(domain) == 1:
        domain = domain[0]
        conference_str = 'conference.' + domain
    else:
        conference_str = {}
        for d in domain:
            conference_str[d] = 'conference.' + d
    __user_lib.conn.close()
    sql_logger.info('PGSQL VERSION : {}'.format(DB_VERSION))

# 判断数据库能否async
if if_async is None:
    if_async = False
    if PY_VERSION and isinstance(PY_VERSION, str):
        if not PY_VERSION.startswith('3') or int(PY_VERSION.split('.')[1]) < 5:
            sql_logger.warning("UNSATISFIED PYTHON VERSION {}".format(PY_VERSION))
        else:
            if DB_VERSION and isinstance(DB_VERSION, str):
                if int(DB_VERSION.split('.')[0]) < 9 or int(DB_VERSION.split('.')[0]) > 10:
                    sql_logger.warning("UNSATISFIED PSQL VERSION {}".format(DB_VERSION))
                else:
                    if_async = True
    if if_async == None:
        sql_logger.error("asyncpg module work in wrong environment")
        raise ConnectionError("asyncpg module work in wrong environment")
sql_logger.info('USE ASYNC : {}'.format(if_async == True))
