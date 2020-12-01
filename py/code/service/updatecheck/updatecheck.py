#!/usr/bin/env python
# -*- coding:utf-8 -*-


import os
import json
import platform

from flask import Blueprint, request, jsonify, send_from_directory, abort, make_response

# , Flask
from conf.updatecheck_params_define import *
from service.updatecheck import version_check_functions

updatecheck_blueprint = Blueprint('updatecheck', __name__)

log_path = get_logger_file(name='updatecheck.log')
updatecheck_logger = configure_logger('updatecheck', log_path)

# 推送beta版本的qtalk
# global_user_white_list = {'lffan.liu@ejabhost1', 'xi.ma@ejabhost1', 'yusy.song@ejabhost1',
#                           'ju.ma@ejabhost1', 'dan.liu@ejabhost1', 'chaocc.wang@ejabhost1'}

# global_user_black_list = {'lei.lei@ejabhost1', 'xinyu.yang@ejabhost1'}


def download_file(filename, beta=False):
    global localDir

    try:
        params = filename.split("/")

        realname = filename.replace("%s/" % params[0], '', 1)

        if params[0].lower() == "linux":
            workerDir = linuxDir
            updater_name = 'updater'
        elif params[0].lower() == "mac":

            workerDir = macDir if beta else macProdDir
            updater_name = 'updater'
            # return jsonify({"ret": 0, "err_msg": "platform %s is not support yet..." % platform})
        elif params[0].lower() == "pc32":
            workerDir = windows32Dir if beta else windows32ProcDir
            updater_name = 'updater.exe'
        elif params[0].lower() == "pc64":
            workerDir = windows64Dir if beta else windows64ProdDir
            updater_name = 'updater.exe'
        else:
            return {"ret": 0, "err_msg": "platform %s is not support yet..." % platform}

        path = os.path.join(workerDir, realname)
        updatecheck_logger.debug("path is " + path)
        if os.path.isfile(path):
            updatecheck_logger.debug("file exist")
            response = make_response(
                send_from_directory(os.path.join(workerDir, 'static'), filename, as_attachment=True))
            updatecheck_logger.debug("response is {}".format(response))

            response.headers["Content-Disposition"] = "attachment; filename={}".format(
                filename.encode().decode('latin-1'))
            return response
            # return send_from_directory(localDir, filename, as_attachment=True)
    except Exception as e:
        updatecheck_logger.error("path error! " + str(e))
        abort(404)
    abort(405)


def upload_file(filename):
    pass


@updatecheck_blueprint.route('/updatecheck', defaults={'path': ''})
@updatecheck_blueprint.route('/updatecheck/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    root = request.url.replace(path, '')
    if path.startswith("download/"):
        return download_file(path[9:])
    elif path.startswith("betadownload/"):
        return download_file(path[13:],beta=True)
    elif path.startswith("upload/"):
        return upload_file(path[7:])
    elif path == "tools/test":
        return jsonify(version_check_functions.running_test())
    elif path == "version/reload":
        content = request.json
        pm = content['platform']
        return jsonify(version_check_functions.reload_version(root, content))
    elif path == "version/check":
        # platform = request.args.get('platform')
        # filename = request.args.get('f')
        content = request.json
        if not content:
            try:
                content = json.loads(request.data)
            except:
                updatecheck_logger.warning("CANT FIND CONTENT {}".format(request.data))
                content = []

        return jsonify(version_check_functions.check_version(root, content))
    else:
        return "Welcome!"


@updatecheck_blueprint.route('/checkupdater', methods=['GET', 'POST'])
def version_compare():
    args = request.args
    user = args.get('user', '')
    exec = args.get('exec', '').lower()
    version = int(args.get('version', 0))
    __platform = args.get('platform').lower()
    if not __platform or not exec:
        abort(405)
    if exec != "qtalk":
        return jsonify(ret=True, link='')

    if user in global_user_black_list:
        return jsonify(ret=True, link='')
    elif version < current_updater_version:
        if __platform == 'pc32':
            return jsonify(ret=True, link=pc32_link)
        elif __platform == 'pc64':
            return jsonify(ret=True, link=pc64_link)
        elif __platform == 'linux':
            return jsonify(ret=True, link=linux_link)
        elif __platform == 'mac':
            return jsonify(ret=True, link=macos_link)
        else:
            return jsonify(ret=True, link='')
    else:
        return jsonify(ret=True, link='')



