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

log_path = get_logger_file('jsontools.log')
jsontools_logger = configure_logger('jsontools', log_path)

jsontools_blueprint = Blueprint('jsontools', __name__, template_folder='../../templates', static_folder='../../static')


# meeting_blueprint = Blueprint('meeting', __name__)


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
                        jsontools_logger.error("ckey api failed : {}".format(e))
                        # TODO notify developer to check
                        # res = check_ckey(ckey, user_id)
                        res, user_id = check_ckey(ckey)

                    except Exception as e:
                        jsontools_logger.error("ckey api failed : {}".format(e))
                else:
                    res, user_id = check_ckey(ckey)
            if res:
                return func(user_id=user_id, ckey=ckey, *args, **kw)
            else:
                jsontools_logger.info("user:{user} login failed, ckey : {ckey}, \
                                                ".format(user=user_id, ckey=ckey))
                return jsonify(ret=0, message="ckey check failed")
        return func(user_id=user_id, ckey=ckey, *args, **kw)

    wrapper.__name__ = func.__name__
    return wrapper


@jsontools_blueprint.route('/json')
#@authorization
def main():
    return render_template('json_index.html')

