#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'

import json
from utils.common_sql import UserLib
from xml.etree import ElementTree as eTree
from conf.search_params_define import if_lookback, if_es
from conf.cache_params_define import SINGLE_KEY, MUC_KEY, SINGLE_TRACE_KEY, MUC_TRACE_KEY, SINGLE_CACHE, MUC_CACHE, \
    ALL_USER_DATA_CACHE, USER_MUCS
from utils.redis_utils import RedisUtil
from utils.logger_conf import get_logger_file, configure_logger
from utils.redis_utils import redis_cli
from utils.common_sql import UserLib, AsyncLib, if_async
from utils.time_utils import TimeUtils
time_utils = TimeUtils()
log_path = get_logger_file('search.log')
lookback_logger = configure_logger('search', log_path)
cache_redis_cli = RedisUtil()


class LookbackLib:
    def __init__(self, args, user_id, timeout=5):
       
        # 参数获取
        self.timeout=timeout
        userlib = None
        self.args = args
        self.user = user_id
        self.group_id = args.get("groupid", "")
        self.offset = int(args.get("start", 0))
        self.limit = int(args.get("length", 5))
        # 关键词处理， 控制长度在2-20个字符之间
        self.term = args.get('key', '').strip()
        if self.term:
            if len(self.term) < 2:
                raise ValueError("LENGTH OF KEY ({}) LESS THAN 2".format(self.term))
            elif len(self.term) > 20:
                self.term = self.term[:20]
        self.to_user = args.get('to_user')
        self.to_muc = args.get('to_muc')
        self.time_range = []
        if args.get('starttime') or args.get('endtime'):
            self.time_range = [args.get('starttime', ''), args.get('endtime', '')]

        # 按照是否异步获取数据库实例
        if if_async:
            try:
                userlib = AsyncLib(user_id)
            except ConnectionError as e:
                # TODO 这里可能抓不到
                lookback_logger.error(e)
                try:
                    userlib = UserLib(user_id)
                except Exception as e:
                    lookback_logger.exception("POSTGRESQL INITIALIZATION FAILED {}".format(e))
                    return
            except Exception as e:
                lookback_logger.exception("POSTGRESQL INITIALIZATION FAILED {}".format(e))
                exit()
        else:
            userlib = UserLib(user_id)

        self.userlib = userlib

        self.user_data = {}
        if user_id and '@' in user_id:
            __domain = user_id.split('@')[1]
            # 制作redis里所有用户的缓存
            if not self.user_data and self.user_data is not None:
                cache_redis_cli = RedisUtil()
                self.user_data = cache_redis_cli.get_all_user_data(domain=__domain)
                if not self.user_data:
                    lookback_logger.info("no user data in redis, making one into it..")
                    self.user_data = userlib.get_user_data(domain=__domain)
                    if self.user_data:
                        cache_redis_cli.set_all_user_data(data=self.user_data, domain=__domain)
                        lookback_logger.info("redis user data set..")
                    else:
                        lookback_logger.error("NO USER FOUND IN POSTGRESQL!!")
                        self.user_data = None
            if self.user_data is None:
                lookback_logger.error("POSTGRESQL STILL NOT SET, IF SET, PLEASE RESTART SERVICE")
                raise ConnectionError("POSTGRESQL IS NOT CONNECTED BECAUSE NO USER FOUND")
        else:
            raise ValueError("NO USERID FOUND IN LOOKBACK SQL")

        # 功能注册
        self.router = {
            'hs_single': self.history_user,
            'hs_muc': self.history_muc,
            'hs_file': self.history_file,
            'ELSE': lambda x: lookback_logger.exception("COMMAND {} NOT FOUND ".format(x))
        }

    async def get_user_mucs(self, user_id):
        if not if_es:
            user_mucs = self.userlib.get_user_mucs(user_id)
        else:
            if if_async:
                __userlib = AsyncLib()
                user_mucs = await __userlib.get_user_mucs(user_id)
            else:
                __userlib = UserLib(user_id)
                user_mucs = __userlib.get_user_mucs(user_id)
        redis_cli.set(name=USER_MUCS + '_' + user_id, value=user_mucs)
        return user_mucs

    async def history_user(self, user_id):
        """
                :param user_id:
                :param term:
                :param pagesize:
                :param offset:
                :return:

                """
        agg_tag = False if self.to_user else True
        if if_async:
            single_array = await self.userlib.history_user(user_id=user_id, term=self.term, offset=self.offset,
                                                           limit=self.limit + 1, to_user=self.to_user,
                                                           time_range=self.time_range,
                                                           agg_tag=agg_tag)
        else:
            single_array = self.userlib.history_user(user_id=user_id, term=self.term, offset=self.offset,
                                                     limit=self.limit + 1, to_user=self.to_user,
                                                     time_range=self.time_range,
                                                     agg_tag=agg_tag)
        if not self.user_data:
            __userlib = UserLib(user_id)
            self.user_data = __userlib.get_user_data(user_id.split('@')[1])
            __userlib.close()
            if self.user_data:
                cache_redis_cli.set_all_user_data(data=self.user_data, domain=user_id.split('@')[1])
                lookback_logger.info("redis user data set..")

        if single_array:
            for arr in single_array:
                root = eTree.fromstring(arr['msg'])
                body = root.find('body')
                #if body.attrib.get('msgType','') == '5':
                #    single_array.remove(arr)
                #    continue
                arr['body'] = body.text if body.text else ''
                arr['extendinfo'] = body.find('extendinfo') if body.find('extendinfo') else ''
                _u = arr['from'] if arr['to'] == user_id else arr['to']
                __match_dict = self.user_data.get(_u)
                arr['icon'] = self.user_data.get(_u, {}).get('u', '')
                arr['label'] = self.user_data.get(_u, {}).get('n', '')
                if not arr['label']:
                    arr['label'] = _u.split('@')[0]
                arr['msgid'] = body.attrib.get('id', '')
                arr['mtype'] = body.attrib.get('msgType', '')
                arr['time'] = root.attrib.get('msec_times', '')
                if not arr['date']:
                    arr['date'] = time_utils.get_date_from_timstamp(arr['time'])
                if 'conversation' in arr.keys():
                    arr.pop('conversation')
                if 'msg' in arr.keys():
                    arr.pop('msg')
                if 'id' in arr.keys():
                    arr.pop('id')

                arr['todoType'] = 8
            single_array = self.make_result(label='单人历史', todo_type=8, resultType=8, info=single_array)
        return single_array

    async def history_muc(self, user_id):
        agg_tag = False if self.to_muc else True
        if if_async:
            muc_array = await self.userlib.history_muc(user_id=user_id, term=self.term, offset=self.offset,
                                                       limit=self.limit + 1, to_muc=self.to_muc,
                                                       time_range=self.time_range,
                                                       agg_tag=agg_tag)
        else:
            muc_array = self.userlib.history_muc(user_id=user_id, term=self.term, offset=self.offset,
                                                 limit=self.limit + 1, to_muc=self.to_muc,
                                                 time_range=self.time_range,
                                                 agg_tag=agg_tag)
        if muc_array:
            for arr in muc_array:
                root = eTree.fromstring(arr['msg'])
                body = root.find('body')
 
                #if body.attrib.get('msgType','') == '5':
                #    muc_array.remove(arr)
                #    continue
                arr['body'] = body.text if body.text else ''
                arr['extendinfo'] = body.find('extendinfo') if body.find('extendinfo') else ''
                arr['msgid'] = body.attrib.get('id', '')
                arr['mtype'] = body.attrib.get('msgType', '')
                arr['time'] = root.attrib.get('msec_times', '')
                if not arr['from']:
                    if 'realfrom' in root.attrib:
                        arr['from'] = root.attrib.get('realfrom', '')
                    elif 'sendjid' in root.attrib:
                        arr['from'] = root.attrib.get('sendjid', '')
                    elif 'from' in root.attrib:
                        _from = root.attrib.get('from', '')
                        if '/' in _from:
                            arr['from'] = _from.split('/')[0]
                    else:
                        arr['from'] = ''
                if 'realfrom' not in arr.keys() or not arr['realfrom']:
                    if 'realfrom' in root.attrib:
                        arr['realfrom'] = root.attrib.get('realfrom', '')
                    elif 'sendjid' in root.attrib:
                        arr['realfrom'] = root.attrib.get('sendjid', '')
                    elif arr['from']:
                        arr['realfrom'] = arr['from']
                    else:
                        arr['realfrom'] = ''
                        lookback_logger.error("CANT FIND REALFROM {}".format(arr))
                if 'realto' not in arr.keys() or not arr['realto']:
                    if 'realto' in root.attrib:
                        arr['realto'] = root.attrib.get('realto','')
                    elif 'to' in root.attrib:
                        arr['realto'] = root.attrib.get('to','')
                    elif arr['to']:
                        arr['realto'] = arr['to']
                    else:
                        arr['realto'] = ''
                        lookback_logger.error("CANT FIND REALTO {}".format(arr))
                if not arr['date']:
                    arr['date'] = time_utils.get_date_from_timstamp(arr['time'])
                if 'conversation' in arr.keys():
                    arr.pop('conversation')
                if 'msg' in arr.keys():
                    arr.pop('msg')
                if 'id' in arr.keys():
                    arr.pop('id')
                arr['todoType'] = 16
            muc_array = self.make_result(label='聊天记录', todo_type=16, resultType=16, info=muc_array)
        return muc_array

    async def history_file(self, user_id):
        # 如果以后要加群组和单人限制 修改sql限制部分为format即可
        if if_async:
            file_array = await self.userlib.history_file(user_id=user_id, term=self.term, offset=self.offset,
                                                        limit=self.limit + 1,
                                                        time_range=self.time_range)
        else:
            file_array = self.userlib.history_file(user_id=user_id, term=self.term, offset=self.offset,
                                                  limit=self.limit + 1,
                                                  time_range=self.time_range)
        if file_array:
            for arr in file_array:
                root = eTree.fromstring(arr['msg'])
                body = root.find('body')
                if not arr['from']:
                    if 'realfrom' in root.attrib:
                        arr['from'] = root.attrib.get('realfrom', '')
                    elif 'sendjid' in root.attrib:
                        arr['from'] = root.attrib.get('sendjid', '')
                    elif 'from' in root.attrib:
                        _from = root.attrib.get('from', '')
                        if '/' in _from:
                            arr['from'] = _from.split('/')[0]
                    else:
                        arr['from'] = ''
                if 'realfrom' not in arr.keys() or not arr['realfrom']:
                    if 'realfrom' in root.attrib:
                        arr['realfrom'] = root.attrib.get('realfrom', '')
                    elif 'sendjid' in root.attrib:
                        arr['realfrom'] = root.attrib.get('sendjid', '')
                    elif arr['from']:
                        arr['realfrom'] = arr['from']
                    else:
                        arr['realfrom'] = ''
                        lookback_logger.error("CANT FIND REALFROM {}".format(arr))
                if 'realto' not in arr.keys() or not arr['realto']:
                    if 'realto' in root.attrib:
                        arr['realto'] = root.attrib.get('realto','')
                    elif 'to' in root.attrib:
                        arr['realto'] = root.attrib.get('to','')
                    elif arr['to']:
                        arr['realto'] = arr['to']
                    else:
                        arr['realto'] = ''
                        lookback_logger.error("CANT FIND REALTO {}".format(arr))


                if not arr['date']:
                    arr['date'] = time_utils.get_date_from_timstamp(arr['time'])
                arr['body'] = body.text if body.text else ''
                arr['extendinfo'] = body.find('extendinfo') if body.find('extendinfo') else ''
                arr['msgid'] = body.attrib.get('id', '')
                arr['mtype'] = body.attrib.get('msgType', '')
                arr['time'] = root.attrib.get('msec_times', '')
                arr['todoType'] = 32
                if 'conversation' in arr.keys():
                    arr.pop('conversation')
                if 'msg' in arr.keys():
                    arr.pop('msg')
                if 'id' in arr.keys():
                    arr.pop('id')

            file_array = self.make_result(label='文件', todo_type=32, resultType=32, info=file_array)
        return file_array

    def make_result(self, label, todo_type, info, resultType):
        if not info:
            info = ''
        if len(info) > self.limit:
            hasmore = True
            info = info[:self.limit]
        else:
            hasmore = False
        final_result = {}
        final_result['info'] = info
        final_result['groupLabel'] = label
        final_result['resultType'] = resultType
        final_result['todoType'] = todo_type
        final_result['hasMore'] = hasmore

        return final_result

    @staticmethod
    def get_hasmore(array, limit=5, habit_tag=False):
        """
        habit tag用于如果从habit中获取的 如果为True则返回has_more=True
        :param array:
        :param limit:
        :param habit_tag:
        :return:
        """
        if habit_tag:
            has_more = True
            return has_more, array[:limit]
        has_more = False
        if array:
            item_count = len(array)
            if item_count > limit:
                has_more = True
                array = array[:limit]
            return has_more, array
        else:
            return has_more, array


class asdfLookback(UserLib):
    def __init__(self):
        super().__init__()
        self.router = {}

    def get_name(self):
        pinyin_name = dict()
        conn = self.conn
        sql = "select user_id, user_name from host_users;"
        cursor = conn.cursor()
        cursor.execute(sql)
        rs = cursor.fetchall()
        for row in rs:
            if row[0] and row[1]:
                pinyin_name[row[0]] = row[1]
            else:
                continue
        return pinyin_name

    def search_single(self, user_id, term, pagesize=5, offset=0):
        """

        :param user_id:
        :param term:
        :param pagesize:
        :param offset:
        :return:
            F from
            T to
            D timestamp(10 bit)
            B xml msg
            body match phrase with <em> highlight pattern
        """
        count = 0
        s_result = []
        has_more = False
        key = term.strip()
        conn = self.conn
        sql_count = "SELECT count(*) from msg_history where (m_from = '" + user_id + "' or m_to = '" + user_id + "') and xpath('/message/body/text()',m_body::xml)::text like '%" + key + "%' ;"
        sql = "SELECT m_from, m_to, m_body from msg_history where (m_from = '" + user_id + "' or m_to = '" + user_id + "') and xpath('/message/body/text()',m_body::xml)::text like '%" + key + "%' limit " + '{}'.format(
            pagesize) + " offset " + '{}'.format(offset) + ";"
        cursor = conn.cursor()
        cursor.execute(sql_count)
        rs = cursor.fetchall()
        for row in rs:
            count = int(row[0]) if row[0] else 0
        if count > pagesize + offset:
            has_more = True
        if count:
            cursor.execute(sql)
            rs = cursor.fetchall()
            for row in rs:
                res = dict()
                res['F'] = row[0]
                res['T'] = row[1]
                res['B'] = row[2]
                m_body = row[2]
                msg = eTree.fromstring(m_body)
                res['body'] = msg.find('body').text.replace(key, ' <em>' + key + '</em>')
                res['D'] = msg.attrib.get('msec_times')  # [:10]
                s_result.append(res)
        cursor.close()
        return has_more, count, s_result

    def search_muc(self, user_id, term, pagesize=5, offset=0):
        """

        :param user_id:
        :param term:
        :param pagesize:
        :param offset:
        :return:
             "N": "Billl",								#发言人
             "M": "muctest123123",				    	#群名
             "D": "1542788224",							#时间戳
             "B": "test<\/body><\/message>",		    #内容
             "body": "test<\/em>",
             "R": "123123123"
        """
        count = 0
        m_result = []
        has_more = False
        key = term.strip()
        conn = self.conn
        sql_count = "select count(*) from muc_room_history where muc_room_name in (select muc_name from user_register_mucs where username = '" + user_id + "') and xpath('/message/body/text()',packet::xml)::text like '%" + key + "%' ;"
        sql = "select nick, packet, muc_room_name from muc_room_history where muc_room_name in (select muc_name from user_register_mucs where username = '" + user_id + "') and xpath('/message/body/text()',packet::xml)::text like '%" + key + "%' limit " + '{}'.format(
            pagesize) + " offset " + '{}'.format(offset) + ";"
        cursor = conn.cursor()
        cursor.execute(sql_count)
        rs = cursor.fetchall()
        for row in rs:
            count = int(row[0]) if row[0] else 0
        if count > pagesize + offset:
            has_more = True
        if count:
            cursor.execute(sql)
            rs = cursor.fetchall()
            for row in rs:
                res = dict()
                res['N'] = row[1]
                res['M'] = row[2]
                res['B'] = row[2]
                m_body = row[2]
                msg = eTree.fromstring(m_body)
                res['body'] = msg.find('body').text.replace(key, ' <em>' + key + '<\/em>')
                res['D'] = msg.attrib.get('msec_times')  # [:10]
                m_result.append(res)
        cursor.close()
        return has_more, count, m_result

