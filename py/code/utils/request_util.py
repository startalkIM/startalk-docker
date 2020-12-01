#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'

import json


class RequestUtil:

    def __init__(self):
        pass

    @staticmethod
    def get_request_args(request):
        if "GET" == request.method:
            args = request.args
        else:
            if request.content_type:
                if "text/plain" in request.content_type:
                    args = json.loads(request.data)
                elif "application/json" in request.content_type:
                    args = request.json
                else:
                    args = request.form
            else:
                try:
                    args = json.loads(request.data)
                except Exception as e:
                    try:
                        args = request.json
                    except Exception as e:
                        args = request.data
        return args

    @staticmethod
    def get_list_args(args, field, delimiter=","):
        value = args.get(field)
        if value:
            return value.split(delimiter)
        else:
            return []

    @staticmethod
    def default_int(str_value, default_value):
        if not str_value:
            return default_value
        try:
            return int(str_value)
        except Exception as e:
            return default_value

    def get_user(self, request):
        args = RequestUtil.get_request_args(request)
        cookies = request.cookies
        user_id = ''
        if 'qtalkId' in args:
            user_id = args.get('qtalkId', '')
        elif 'user' in args:
            user_id = args.get('user', '')
        elif 'username' in args:
            user_id = args.get('username', '')
        elif 'u' in args:
            user_id = args.get('u', '')
        elif '_u' in args:
            user_id = args.get('_u', '')
        elif '_u' in cookies:
            user_id = cookies.get('_u', '')
        return user_id

    def get_ckey(self, request):
        args = RequestUtil.get_request_args(request)
        cookies = request.cookies
        ckey = ''
        if 'cKey' in args:
            ckey = args.get('cKey', '')
        elif 'ckey' in args:
            ckey = args.get('ckey', '')
        elif 'q_ckey' in cookies:
            ckey = cookies.get('q_ckey')
        elif 'ckey' in cookies:
            ckey = cookies.get('ckey')
        elif 'cKey' in cookies:
            ckey = cookies.get('cKey')
        return ckey
