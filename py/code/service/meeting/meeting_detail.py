#!/usr/bin/env python
# -*- coding:utf-8 -*-

# import json
from flask import request, jsonify, render_template, Blueprint
import datetime
import requests
from conf.constants import *
from utils.authorization import check_ckey
from utils.request_util import RequestUtil
from conf.meetingdetail_params_define import *
from utils.logger_conf import configure_logger

log_path = get_logger_file('meetingdetail.log')
meeting_logger = configure_logger('meetingdetail', log_path)

meeting_blueprint = Blueprint('meeting', __name__, template_folder='../../templates', static_folder='../../static')


def authorization(func):
    def wrapper(*args, **kw):
        ckey = ''
        user_id = 'DEFAULT'
        request_util = RequestUtil()
        res = False
        if is_check_ckey:
            ckey = request_util.get_ckey(request)
            if ckey:
                if auth_ckey_url:
                    try:
                        r_data = {
                            'ckey': ckey,
                            'system': 'meeting'
                        }
                        ret = requests.post(url=auth_ckey_url, json=r_data)
                        if ret.json().get('ret'):
                            if ret.json().get('data').get('d') != r_domain:
                                return jsonify(ret=0, message="Error domain")
                            res = True
                            user_id = ret.json().get('data').get('u')
                    except (requests.RequestException or KeyError) as e:
                        meeting_logger.error("ckey api failed : {}".format(e))
                        # TODO notify developer to check
                        # res = check_ckey(ckey, user_id)
                        res, user_id = check_ckey(ckey)

                    except Exception as e:
                        meeting_logger.error("ckey api failed : {}".format(e))
                else:
                    res, user_id = check_ckey(ckey)
            if res:
                return func(user_id=user_id, ckey=ckey, *args, **kw)
            else:
                meeting_logger.info("user:{user} login failed, ckey : {ckey}, \
                                                ".format(user=user_id, ckey=ckey))
                return jsonify(ret=0, message="ckey check failed")
        return func(user_id=user_id, ckey=ckey, *args, **kw)

    wrapper.__name__ = func.__name__
    return wrapper


@meeting_blueprint.route('/meeting')
@authorization
def main(user_id, ckey):
    meeting_logger.info("Get request from " + user_id)
    params = request.args.to_dict()
    # 验证是否可行， 是否json
    ckey_cookie = {
        "q_ckey": ckey
    }
    response = requests.post(url=info_onlineUrl, json=params, cookies=ckey_cookie)
    is_creator = response.json().get('data').get('canceled')
    content = make_content(creator=is_creator, response=response)
    return render_template('meeting_detail.html', content=content, params=params, user_id=user_id, q_ckey=ckey)


def make_content(creator, response):
    # 可能出现拼接int的问题
    content = ''
    response_data = response.json().get('data')
    if not response_data or 'begin_time' not in response_data.keys() or 'end_time' not in response_data.keys():
        return
    meeting_name = response_data.get('meeting_name', '')
    meeting_inviter = response_data.get('inviter', '')
    meeting_date = response_data.get('meeting_date', '')
    meeting_locale = response_data.get('meeting_locale', '') + response_data.get('meeting_room', '')
    meeting_action = response_data.get('action_reason', '')
    mem_action = response_data.get('mem_action', '')

    def get_status(mem_action):
        isShowButton = True
        r = ''
        mem_action = int(mem_action)
        if mem_action == 0:
            r = "未选择或暂定"
        elif mem_action == 1:
            isShowButton = False
            r = "已接受"
        elif mem_action == 2:
            isShowButton = False
            r = "已拒绝"
        else:
            r = "未知异常"
        return isShowButton, r

    isShowButton, r = get_status(mem_action)

    try:
        meeting_begin = response_data.get('begin_time')
        begin_time = datetime.datetime.strptime(meeting_begin, '%Y-%m-%d %H:%M:%S')
        begin_time.time().strftime('%H:%M')
        start = str(begin_time.hour) + ' : ' + str(begin_time.minute)
        start = begin_time.time().strftime('%H:%M')
        meeting_end = response_data.get('end_time')
        end_time = datetime.datetime.strptime(meeting_end, '%Y-%m-%d %H:%M:%S')
        end = str(end_time.hour) + ' : ' + str(end_time.minute)
        end = end_time.time().strftime('%H:%M')
    except ValueError:
        start = ''
        end = ''
    meeting_members = ', '.join(response_data.get('member'))

    if not creator:
        content += '<span class="meetingItem">您有一个行程邀请: </span>'
        content += '<span class="meetingItem">行程名称: ' + meeting_name + '</span>'
        content += '<span class="meetingItem">行程邀请人: ' + meeting_inviter + '</span>'
        content += '<span class="meetingItem">行程日期: ' + meeting_date + '</span>'
        content += '<span class="meetingItem">开始时间: ' + start + '</span>'
        content += '<span class="meetingItem">结束时间: ' + end + '</span>'
        content += '<span class="meetingItem">行程室地点: ' + meeting_locale + ' </span>'
        content += '<span class="meetingItem">行程被邀请人: ' + meeting_members + ' </span>'
        content += '<span class="meetingItem">行程备注: ' + meeting_action + '</span>'
        content += '</br>'
        content += '<span class="meetingItem">当前状态:' + r + '</span>'
        content += '</br>'
        if isShowButton:
            content += '<textarea id="remark" class="remarkText" type="text" placeholder="如有需要请添加备注"></textarea>'
            content += """<div class="buttonDiv"><a class="button" id="jieshou">接受</a><a class="button" id="zanding">暂定</a><a class="button" id="jujue">拒绝</a></div>"""
    else:
        content += '<span class="meetingItem">当前行程已取消! </span>'
        content += '<span class="meetingItem">行程名称: ' + meeting_name + '</span>'
        content += '<span class="meetingItem">行程邀请人: ' + meeting_inviter + '</span>'
        content += '<span class="meetingItem">行程日期: ' + meeting_date + '</span>'
        content += '<span class="meetingItem">开始时间: ' + start + '</span>'
        content += '<span class="meetingItem">结束时间: ' + end + '</span>'
        content += '<span class="meetingItem">行程室地点: ' + meeting_locale + ' </span>'
        content += '<span class="meetingItem">行程被邀请人: ' + meeting_members + ' </span>'
    return content


@meeting_blueprint.route('/meetingajaxhelp', methods=['POST'])
@authorization
def ajax_help(user_id, ckey):
    ckey_cookie = {
        "q_ckey": ckey
    }
    response = requests.post(url=action_onlineUrl, json=request.json, cookies=ckey_cookie, timeout=10)
    return response.content  # 不知道是不是应该返回这个

