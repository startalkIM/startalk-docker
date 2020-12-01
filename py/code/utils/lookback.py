#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'
from utils.common_sql import UserLib
from xml.etree import ElementTree as eTree


class Lookback(UserLib):
    def __init__(self, user, args):
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
             "M": "muctest123123",						#群名
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

