#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys
sys.path.append('/startalk/search/')

import uuid
from utils.common_sql import UserLib
from utils.pinyin_util import *
import hashlib

def md5(string):
    m = hashlib.md5()
    m.update(string.encode("utf8"))
    return m.hexdigest()


user_lib = UserLib()
pinyin_util = PinyinUtil()
salt_uuid = uuid.uuid4().hex

"""修改这里"""
custom_params = {
    'host_id': 1,
    'user_id': 'newuser1',
    'user_name': '新用户1',
    'password': '123456',
    'dep': '/测试',
    'department': '/',
    'gender': 1,
    'host': 'qtalk',
    'ps_deptid': 'qtalk',
}
""""""


constant_params = {
    'frozen_flag': 0,
    'version': 1,
    'user_type': 'U',
    'hire_flag': 1,
    'pinyin': '|'.join(pinyin_util.get_all(custom_params.get('user_name'))),
    'pwd_salt': "qtalkadmin_pwd_salt_" + salt_uuid,
    'password': 'CRY:' + md5(md5(md5(custom_params.get('password')) + "qtalkadmin_pwd_salt_"+ salt_uuid)),
    'initialpwd': 1
}
params = {**custom_params, **constant_params}
# user_pinyin = '|'.join(pinyin_util.get_all(user_name))
sql = """insert into host_users (host_id, user_id, user_name, department, dep1, pinyin, frozen_flag, version, user_type, hire_flag, gender, password, initialpwd, pwd_salt, ps_deptid)
 values (%(host_id)s, %(user_id)s, %(user_name)s, %(dep)s, %(department)s, %(pinyin)s, %(frozen_flag)s, %(version)s, %(user_type)s, %(hire_flag)s, %(gender)s, %(password)s, %(initialpwd)s, %(pwd_salt)s, %(ps_deptid)s);"""
conn = user_lib.conn

cursor = conn.cursor()
cursor.execute(sql, params)

vcard_params = {**custom_params, **{
    "version": 1,
    "profile_version": 1,
    "url": "/file/v2/download/avatar/new/daa8a007ae74eb307856a175a392b5e1.png?name=daa8a007ae74eb307856a175a392b5e1.png&file=file/daa8a007ae74eb307856a175a392b5e1.png&fileName=file/daa8a007ae74eb307856a175a392b5e1.png"
}
                }
sql = """insert into vcard_version (username, version, profile_version, gender, host, url) 
values (%(user_id)s, %(version)s, %(profile_version)s, %(gender)s, %(host)s, %(url)s);"""
cursor.execute(sql, vcard_params)
cursor.close()
user_lib.close()


print("用户{}创建完毕".format(custom_params.get('user_id')))

