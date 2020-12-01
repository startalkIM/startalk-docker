#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'
from utils.common_utils import TextHandler
from utils.common_sql import UserLib, AsyncLib, if_async
from conf.constants import if_cached
from conf.search_params_define import *
import asyncio

# from conf.cache_params_define import SINGLE_TRACE_KEY, SINGLE_KEY, MUC_TRACE_KEY, MUC_KEY

log_path = get_logger_file('search.log')
contact_logger = configure_logger('search', log_path)

ip = str()
s_args = dict()
l_args = dict()

text_handler = TextHandler
merge_list_of_dict = text_handler.merge_list_of_dict


class Contact:
    def __init__(self, args, user_id, habit, extend_time=False):
        userlib = None
        # 参数获取
        self.args = args
        self.user = user_id
        self.group_id = args.get("groupid", "")
        self.offset = int(args.get("start", 0))
        self.limit = int(args.get("length", 5))
        # 关键词处理， 控制长度在2-20个字符之间
        self.username = args.get('key', '')
        if self.username:
            if len(self.username) < 2:
                raise ValueError("LENGTH OF KEY ({}) LESS THAN 2".format(self.username))
            elif len(self.username) > 20:
                self.username = self.username[:20]
            self.username = self.username.strip()
        self.timeout = 60 if extend_time else 5

        # 按照是否异步获取数据库实例
        if if_async:
            try:
                userlib = AsyncLib(user_id)
            except ConnectionError as e:
                # TODO 这里可能抓不到
                contact_logger.error(e)
                try:
                    userlib = UserLib(user_id)
                except Exception as e:
                    contact_logger.exception("POSTGRESQL INITIALIZATION FAILED {}".format(e))
                    return
            except Exception as e:
                contact_logger.exception("POSTGRESQL INITIALIZATION FAILED {}".format(e))
                exit()
        else:
            userlib = UserLib(user_id)
        self.userlib = userlib

        # 功能注册
        self.router = {
            'user': self.search_user,
            'muc': self.search_group,
            'common_muc': self.search_common_group,
            'ELSE': lambda x: contact_logger.exception("COMMAND {} NOT FOUND ".format(x))
        }

        # 用户习惯
        self.user_habit = habit

    async def search_user(self, user_id):
        result = {}
        user_array = []
        habit_array = []
        has_more = False
        # 如果要3个就取4个 如果有更多就返回has more
        limit = self.limit + 1
        _all = limit + self.offset
        diff = _all
        # 获取用户habit中的匹配项

        if if_cached:
            contact_logger.debug("habit is {}".format(self.user_habit))
            if if_async:
                habit_array = await self.userlib.get_habit(key=self.username, habit=self.user_habit, form='single',
                                                       user=user_id)
            else:
                habit_array = self.userlib.get_habit(key=self.username, habit=self.user_habit, form='single',
                                                       user=user_id)
        if habit_array:
            contact_logger.debug("Get habit array {}".format(habit_array))
            _len = len(habit_array)
            if _len >= _all:
                has_more, user_array = self.get_hasmore(habit_array, offset=self.offset, limit=self.limit,
                                                        habit_tag=True)
            diff = _all - _len
            # limit = limit - _len

        if diff > 0:
            if if_async:
                # user_array = await self.userlib.search_user(self.username, user_id, limit, self.offset,

                user_array = await self.userlib.search_user(self.username, user_id, diff, self.offset,
                                                            habit=self.user_habit, exclude=habit_array)
            else:
                user_array = self.userlib.search_user(self.username, user_id, diff, self.offset,
                                                      habit=self.user_habit)
            if habit_array:
                _len = len(habit_array)
                if _len > self.offset:
                    habit_array = habit_array[self.offset - _len:]
                elif _len <= self.offset:
                    habit_array = []
                user_array = merge_list_of_dict(habit_array, user_array)
                contact_logger.debug('has habit in, result {}'.format(user_array))
            has_more, user_array = self.get_hasmore(user_array, offset=self.offset, limit=self.limit)
        if user_array:
            # todo resulttype或许应该通过常量定义里的register获取, 而不是写死
            result = self.make_result(label='联系人', groupid=userGroup, group_priority=0,
                                      todo_type=QTALK_OPEN_USER_VCARD,
                                      portrait=single_portrait, hasmore=has_more, info=user_array, resulttype=1)
        return result

    async def search_group(self, user_id, origin=True, common=True):
        result = {}
        group_array = []
        habit_array = []
        has_more = False
        limit = self.limit + 1
        _all = limit + self.offset
        diff = _all
        # 获取用户habit中的匹配项
        if if_cached:
            if if_async:
                habit_array = await self.userlib.get_habit(self.username, habit=self.user_habit, form='muc', user=user_id,
                                                       origin=origin, common=False)
            else:
                habit_array = self.userlib.get_habit(self.username, habit=self.user_habit, form='muc', user=user_id,
                                                       origin=origin, common=False)
      
        if habit_array:
            contact_logger.debug("Get muc habit array {}".format(habit_array))
            _len = len(habit_array)
            if _len >= _all:
                has_more, group_array = self.get_hasmore(habit_array, offset=self.offset, limit=self.limit,
                                                         habit_tag=True)
            diff = _all - _len
        if diff > 0:
            if if_async:
                group_array = await self.userlib.search_group(user_id, self.username, diff, self.offset,
                                                              habit=self.user_habit, exclude=habit_array, origin=origin,
                                                              common=common)
                # group_array = sorted(group_array, key=lambda x: x.get('time'), reverse=True)

            else:
                group_array = self.userlib.search_group(user_id, self.username, diff, self.offset,
                                                        habit=self.user_habit)
            if habit_array:
                _len = len(habit_array)
                if _len > self.offset:
                    habit_array = habit_array[self.offset - _len:]
                elif _len <= self.offset:
                    habit_array = []
                group_array = merge_list_of_dict(habit_array, group_array)
                contact_logger.debug('has habit in {}, result {}'.format(habit_array, group_array))
            has_more, group_array = self.get_hasmore(group_array, offset=self.offset, limit=self.limit)

        if group_array:
            result = self.make_result(label='群组', groupid=groupGroup, group_priority=0,
                                      todo_type=QTALK_OPEN_GROUP_VCARD,
                                      portrait=muc_portrait, hasmore=has_more, info=group_array, resulttype=6)
        return result

    async def handle_group_search(self, user_id, diff, origin=True, common=True, exclude=None):
        res = []
        tasks = []
        if origin and common:
            t1 = asyncio.create_task(self.userlib.search_group_by_single(user_id, self.username, diff,
                                                                         self.offset, habit=self.user_habit,
                                                                         exclude=exclude))
            tasks.append(t1)
            t2 = asyncio.create_task(self.userlib.search_group(user_id, self.username, diff, self.offset,
                                                               habit=self.user_habit, exclude=exclude))
            tasks.append(t2)

        elif origin and not common:
            t1 = asyncio.create_task(self.userlib.search_group(user_id, self.username, diff, self.offset,
                                                               habit=self.user_habit, exclude=exclude))
            tasks.append(t1)

        elif not origin and common:
            t1 = asyncio.create_task(self.userlib.search_group_by_single(user_id, self.username, diff,
                                                                         self.offset, habit=self.user_habit,
                                                                         exclude=exclude))
            tasks.append(t1)

        else:
            return

        completed, pending = asyncio.wait(tasks, timeout=self.timeout)
        for pen in pending:
            contact_logger.error("PENDING TASK FOUND {}".format(pen))
            pen.cancel()
        for com in completed:
            # t = com.result()
            if com.result():
                res.append(com.result())

        return res

    async def search_common_group(self, user_id):
        result = {}
        if if_async:
            commonmuc_array = await self.userlib.search_group_by_single(user_id, self.username, self.limit + 1,
                                                                        self.offset, habit=self.user_habit)
        else:
            commonmuc_array = self.userlib.search_group_by_single(self.username, user_id, self.limit + 1, self.offset,
                                                                  habit=self.user_habit)
        has_more, commonmuc_array = self.get_hasmore(commonmuc_array, offset=self.offset, limit=self.limit)
        if commonmuc_array:
            result = self.make_result(label='共同群组', groupid=commonGroup, group_priority=0,
                                      todo_type=QTALK_OPEN_GROUP_VCARD,
                                      portrait=muc_portrait, hasmore=has_more, info=commonmuc_array, resulttype=4)
        return result

    @staticmethod
    def make_result(label, groupid, group_priority, todo_type, portrait, hasmore, info, resulttype=0):
        if not info:
            info = ''
        if resulttype == 6:
            for i in info:
                if not i.get('todoType'):
                    if i.get('hit'):
                        resulttype = 6
                        i['todoType'] = 4
                    else:
                        i['todoType'] = 2
        _result = {
            'resultType': resulttype,
            'groupLabel': label,
            'groupId': groupid,
            'groupPriority': group_priority,
            'todoType': todo_type,
            'defaultportrait': portrait,
            'hasMore': hasmore,
            'info': info
        }
        return _result

    @staticmethod
    def get_hasmore(array, offset=0, limit=5, habit_tag=False):
        """
        habit tag用于如果从habit中获取的 如果为True则返回has_more=True
        :param array:
        :param limit:
        :param habit_tag:
        :return:
        """
        if habit_tag:
            has_more = True
            return has_more, array[offset:offset + limit]
        has_more = False
        if array:
            item_count = len(array)
            if item_count > limit:
                has_more = True
                array = array[:limit]
            return has_more, array
        else:
            return has_more, array
