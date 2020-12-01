#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'
import json
from flask import request, jsonify, render_template, Blueprint
import base64
import requests
import asyncio
import time
from utils.utility import Utility
from conf.constants import *
from utils.authorization import check_ckey
from utils.request_util import RequestUtil
from utils.get_conf import *
from conf.sharemsg_params_define import *
from utils.logger_conf import configure_logger

log_path = get_logger_file()
log_path = log_path + 'sharemsg.log'
logger = configure_logger('sharemsg', log_path)

sharemsg_blueprint = Blueprint('sharemsg', __name__, template_folder='../../templates', static_folder='../../static')


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
                            'system': 'sharemsg'
                        }
                        ret = requests.post(url=auth_ckey_url, json=r_data)
                        if ret.json().get('ret'):
                            if ret.json().get('data').get('d') != r_domain:
                                return jsonify(ret=0, message="Error domain")
                            res = True
                            user_id = ret.json().get('data').get('u')
                    except (requests.RequestException or KeyError) as e:
                        logger.error("ckey api failed : {}".format(e))
                        # TODO notify developer to check
                        # res = check_ckey(ckey, user_id)
                        res, user_id = check_ckey(ckey)

                    except Exception as e:
                        logger.error("ckey api failed : {}".format(e))
                else:
                    res, user_id = check_ckey(ckey)
            if res:
                return func(user_id=user_id, *args, **kw)
            else:
                logger.info("user:{user} login failed, ckey : {ckey}, \
                                                ".format(user=user_id, ckey=ckey))
                return jsonify(ret=0, message="ckey check failed")
        return func(user_id=user_id, *args, **kw)

    wrapper.__name__ = func.__name__
    return wrapper


@sharemsg_blueprint.route('sharemsg')
@authorization
def main(user_id):
    logger.info("Get request from " + user_id)
    handler = GenerateShareMsg()
    content = handler.show()
    return render_template('sharemsg_template.html', content=content)


class GenerateShareMsg:
    def __init__(self):
        pass

    @staticmethod
    def pad_data(_data):
        _data = _data + '=' * (len(_data) % 4)
        return _data

    @staticmethod
    def form_data(_data):
        """
        - -> +
        _ -> /
        . -> +
        :param _data:
        :return:
        """
        if '-' in _data:
            _data = _data.replace('-', '+')
        if '_' in _data:
            _data = _data.replace('_', '/')
        if '.' in _data:
            _data = _data.replace('.', '+')
        return _data

    def show(self):
        jdata = request.args.get('jdata', '')
        if not jdata:  # TODO 更好的处理方式
            return NOT_FOUND_ERROR
        if ('-' in jdata) or ('_' in jdata) or ('.' in jdata):
            jdata = self.form_data(jdata)
        try:
            data_url = base64.b64decode(jdata)
        except:
            jdata = self.pad_data(jdata)
            try:
                data_url = base64.b64decode(jdata)
            except Exception as e:
                logger.error(e)
                logger.error("Cant decode base64 :" + jdata)
                return
        result = requests.get(data_url)
        if not result.ok:
            return OUTDATED_ERROR
        try:
            content = json.loads(result.text)
        except Exception as e:
            logger.error("Json load failed \n {}".format(e))
            return
        main_region = ""
        content.sort(key=lambda x: x['s'])
        util = Utility()
        content = util.handle_sharemsg_timeinterval(content)
        for item in content:
            msg = util.handle_sharemsg(item)
            main_region += "<div>" + item.get('time_html', '')
            speaker_div = util.handle_sharemsg_speaker(item).format(content=msg, name=item.get('n', ''))
            main_region += speaker_div + "</div>"
        return main_region
