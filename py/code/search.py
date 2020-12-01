# -*- encoding:utf-8 -*-

from flask import Flask, request, jsonify
import json
from utils.request_util import RequestUtil
from utils.common_sql import UserLib
from utils.get_conf import get_config_file, get_logger_file
from utils.logger_conf import configure_logger

app = Flask(__name__)
app.debug = True

# -------------------------- 生成logger --------------------------
log_path = get_logger_file()
log_path = log_path + '_search.log'
logger = configure_logger('main', log_path)

# -------------------------- 读取默认配置 --------------------------
config = get_config_file()
is_check_ckey = config['qtalk'].getboolean('ckey_check')
if is_check_ckey:
    logger.info("CKEY AUTHORIZATION INITIALING...")
    from utils.authorization import check_ckey
single_portrait = config['qtalk']['single_portrait']
muc_portrait = config['qtalk']['muc_portrait']
service_host = config['qtalk']['app_host']
service_port = config['qtalk']['app_port']

# -------------------------- 既定的配置 --------------------------
userGroup = 'Q01'
groupGroup = 'Q02'
singlekeywordGroup = 'Q05'
muckeywordGroup = 'Q06'
commonGroup = 'Q07'
GroupDetail = 'Q10'

QTALK_OPEN_USER_VCARD = 0  # 打开单人名片
QTALK_OPEN_GROUP_VCARD = 1  # 打开群组聊天
QTALK_OPEN_FRIENDS_VC = 2  # 打开好友
QTALK_OPEN_GROUPS_VC = 3  # 打开群组
QTALK_OPEN_UNREAD_MESSAGE = 4  # 打开未读消息
QTALK_OPEN_PUBLIC_ACCOUNT = 5  # 打开公众号
QTALK_WEBVIEW = 6  # 打开webview，渲染url
QTALK_OPEN_USER_CHAT = 7  # 打开单人聊天
QTALK_OPEN_PUBLIC_VCARD = 8  # 打开公众号名片

ip = str()
s_args = dict()


@app.route('/search.py', methods=['GET', 'POST'])
def main():
    global ip, s_args
    args = RequestUtil.get_request_args(request)
    if not s_args:
        s_args = args
    try:
        username = args["key"].strip()
        user_id = args["qtalkId"].strip()
    except KeyError:
        return jsonify(ret=0, message="wrong parameters")
    if len(username) < 2:
        return jsonify(ret=0, message="length of key should greater than two")
    ckey = args.get("cKey", "")
    group_id = args.get("groupid", "")
    offset = int(args.get("start", 0))
    limit = int(args.get("length", 5))
    if is_check_ckey:
        res = check_ckey(ckey, user_id)
        if not res:
            logger.error('{} login FAILED. ckey : {}'.format(user_id, ckey))
            return jsonify(ret=0, message="ckey failed")

    request_ip = request.remote_addr
    if ip != request_ip:
        ip = request_ip
        logger.info(ip + ' :  {}'.format(json.dumps(s_args)))
    s_args = args
    result = list()
    data_array = list()
    userlib = UserLib()
    if group_id:
        if group_id == userGroup:
            user_array = userlib.search_user(username, user_id, limit + 1, offset)
            has_more, user_array = get_hasmore(user_array, limit)
            if user_array:
                result = make_result(label='联系人列表', groupid=userGroup, group_priority=0, todo_type=QTALK_OPEN_USER_VCARD,
                                 portrait=single_portrait, hasmore=has_more, info=user_array)
        elif group_id == groupGroup:
            group_array = userlib.search_group(user_id, username, limit + 1, offset)
            has_more, group_array = get_hasmore(group_array, limit)
            if group_array:
                result = make_result(label='群组列表', groupid=groupGroup, group_priority=0, todo_type=QTALK_OPEN_GROUP_VCARD,
                                 portrait=muc_portrait, hasmore=has_more, info=group_array)
        elif group_id == commonGroup:
            commonmuc_array = userlib.search_group_by_single(user_id, username, limit + 1, offset)
            has_more, commonmuc_array = get_hasmore(commonmuc_array, limit)
            if commonmuc_array:
                result = make_result(label='共同群组', groupid=commonGroup, group_priority=0, todo_type=QTALK_OPEN_GROUP_VCARD,
                                 portrait=muc_portrait, hasmore=has_more, info=commonmuc_array)
        else:
            return jsonify(errcode=500, msg='无法预期的groupId')
        userlib.conn.close()
        return jsonify(errcode=0, msg='', data=result)
    else:
        user_array = userlib.search_user(username, user_id, limit + 1, offset)
        group_array = userlib.search_group(user_id, username, limit + 1, offset)
        commonmuc_array = userlib.search_group_by_single(user_id, username, limit + 1, offset)
        if user_array:
            has_more, user_array = get_hasmore(array=user_array, limit=limit)
            result = make_result(label='联系人列表', groupid=userGroup, group_priority=0, todo_type=QTALK_OPEN_USER_VCARD,
                                 portrait=single_portrait, hasmore=has_more, info=user_array)
            data_array.append(result)
        if group_array:
            has_more, group_array = get_hasmore(array=group_array, limit=limit)
            result = make_result(label='群组列表', groupid=groupGroup, group_priority=0, todo_type=QTALK_OPEN_GROUP_VCARD,
                                 portrait=muc_portrait, hasmore=has_more, info=group_array)
            data_array.append(result)
        if commonmuc_array:
            has_more, commonmuc_array = get_hasmore(commonmuc_array, limit)
            result = make_result(label='共同群组', groupid=commonGroup, group_priority=0, todo_type=QTALK_OPEN_GROUP_VCARD,
                                 portrait=muc_portrait, hasmore=has_more, info=commonmuc_array)
            data_array.append(result)
        userlib.conn.close()
        return jsonify(errcode=0, msg='', data=data_array)


def make_result(label, groupid, group_priority, todo_type, portrait, hasmore, info):
    if not info:
        info = ''
    _result = {
        'groupLabel': label,
        'groupId': groupid,
        'groupPriority': group_priority,
        'todoType': todo_type,
        'defaultportrait': portrait,
        'hasMore': hasmore,
        'info': info
    }
    return _result


def get_hasmore(array, limit=5):
    has_more = False
    if array:
        item_count = len(array)
        if item_count > limit:
            has_more = True
            array.pop()
        return has_more, array
    else:
        return has_more, array


if __name__ == '__main__':
    app.run(host=service_host, port=service_port, debug=True)
