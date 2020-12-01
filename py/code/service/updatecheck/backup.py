#!/usr/bin/env python
# -*- coding:utf-8 -*-

import hashlib
import os
import platform
import sys

from flask import Blueprint, request, jsonify, send_from_directory, abort, make_response
# , Flask
from conf.updatecheck_params_define import *

updatecheck_blueprint = Blueprint('updatecheck', __name__)

log_path = get_logger_file(name='updatecheck.log')
updatecheck_logger = configure_logger('updatecheck', log_path)

global_user_white_list = {'lffan.liu@ejabhost1', 'xi.ma@ejabhost1', 'yusy.song@ejabhost1',
                          'ju.ma@ejabhost1', 'dan.liu@ejabhost1', 'chaocc.wang@ejabhost1'}

global_user_black_list = {'lei.lei@ejabhost1', 'xinyu.yang@ejabhost1'}


# app = Flask(__name__)


def eprint(*args, **kwargs):
    updatecheck_logger.log(*args, file=sys.stderr, **kwargs)


global_pc64_file_dictionary = dict()
global_pc32_file_dictionary = dict()
global_mac_file_dictionary = dict()
global_linux_file_dictionary = dict()


def md5_file(filename):
    try:
        return hashlib.md5(open(filename, 'rb').read()).hexdigest()
    except:
        return "file can not be open."


def check_files(path_dir, base_root):
    result = {}
    if not os.path.isdir(path_dir):
        return result
    list_dirs = os.walk(path_dir)

    for root, dirs, files in list_dirs:
        for d in dirs:
            updatecheck_logger.debug('this is a dir.' + os.path.join(root, d))
        for f in files:
            full_path = os.path.join(root, f)
            md5 = md5_file(full_path).upper()
            file_name = full_path.replace(path_dir, '', 1)

            result[file_name.lower()] = {
                'key': file_name,
                'url': '%s%s' % (base_root, full_path.replace(path_dir, '', 1)),
                'md5': md5}
    return result


def check_diff(local, remote, updater_name):
    changed = list()
    changed_set = set()

    removed = list()
    removed_set = set()

    added = list()
    added_set = set()

    for key in remote:
        local_key = key.lower()

        if len(updater_name) > 0:
            if local_key != updater_name:
                continue
        if local_key in local:
            if local[local_key]['md5'].lower() != remote[key].lower():
                if key not in changed_set:
                    changed.append({key: local[local_key]['url']})
                    changed_set.add(key)
        else:
            if local_key not in removed_set:
                removed_set.add(local_key)
                removed.append({key: remote[key]})

    for key in local:
        if len(updater_name) > 0:
            if key.lower() != updater_name:
                continue
        if local[key]['key'] in remote:
            if local[key]['md5'].lower() != remote[local[key]['key']].lower():
                if key not in changed_set:
                    changed_set.add(local[key]['key'])
                    changed.append({local[key]['key']: local[key]['url']})
        else:
            if local[key]['key'] not in added_set:
                add_key = local[key]['key']
                added_set.add(add_key)
                added.append({add_key: local[key]['url']})
    result = {'added': list(added), 'removed': list(removed), 'changed': list(changed)}

    return result


# app = Flask(__name__)

# localDir = '/Users/may/workspace/qt/qtalk_v2/cmake-build-debug/bin/'

# localDir = '/Users/may/workspace/qt/qtalk_v2/cmake-build-debug/bin/'

def inner_reload_version(base_root, pm):
    download_root = base_root + ("download/%s/" % pm.lower())
    if pm.lower() == "linux":
        worker_dir = linuxDir
        return dict()
    elif pm.lower() == "mac":
        worker_dir = macDir
        return check_files(worker_dir, download_root)
    elif pm.lower() == "pc32":
        worker_dir = windows32Dir
        return check_files(worker_dir, download_root)
    elif pm.lower() == "pc64":
        worker_dir = windows64Dir
        return check_files(worker_dir, download_root)


def running_test():
    import time
    time.sleep(3)
    return jsonify({"ret": 200, "err_msg": "coool!"})


def reload_version(base_root, pm):
    global global_mac_file_dictionary
    global global_pc64_file_dictionary
    global global_pc32_file_dictionary

    if pm.lower() == "linux":
        return jsonify({"ret": 500, "err_msg": "platform %s is not support yet..." % platform})
    elif pm.lower() == "mac":
        global_mac_file_dictionary = inner_reload_version(base_root, pm)
        return jsonify({"ret": 0, 'response': global_mac_file_dictionary})
    elif pm.lower() == "pc32":
        global_pc32_file_dictionary = inner_reload_version(base_root, pm)
        return jsonify({"ret": 0, 'response': global_pc32_file_dictionary})
    elif pm.lower() == "pc64":
        global_pc64_file_dictionary = inner_reload_version(base_root, pm)
        return jsonify({"ret": 0, 'response': global_pc64_file_dictionary})

    return jsonify({"ret": 500, "err_msg": "platform %s is not support yet..." % platform})


def check_user_can_update_new(content):
    has_channel = 0
    if 'channel' in content:
        channel_value = content['channel']
        if channel_value == 1 or channel_value == 2:
            return 1
    return 0


def check_user_in_blacklist(content, user_list):
    has_users = 0
    if 'users' in content:
        has_users = 1

    if 'files' in content:
        file_dic = content['files']
        if len(file_dic) <= 0:
            return 0

    if has_users:
        user_string = content['users']
        users = user_string.split('|')
        for u in users:
            if u in user_list:
                return 1
    return 0


def check_user_can_update(content, user_list):
    has_users = 0
    if 'users' in content:
        has_users = 1

    has_exec = 0

    has_version = 0

    if 'exec' in content:
        has_exec = 1
    has_platform = 0
    if 'version' in content:
        has_version = 1

    if has_users:
        user_string = content['users']
        users = user_string.split('|')
        for u in users:
            if u in user_list:
                return 1
    # 实际上除了在白名单里之外，只要命中了版本号就应该升级

    if has_version:
        version = content['version']
    return 0


def inner_check_version(base_root, content, updater_name, local_dic):
    if len(local_dic) <= 0:
        return jsonify({"errcode": 500, "errmsg": 'server file is not prepared!'})

    if 'files' in content:
        file_dic = content['files']

        if len(file_dic) == 1:
            changed = check_diff(local_dic, file_dic, updater_name)
        else:
            changed = check_diff(local_dic, file_dic, '')
        updatecheck_logger.debug(changed)
        return jsonify({"errcode": 200, "errmsg": "OK", "base_url": base_root, "changed": changed})
    else:
        return jsonify({"errcode": 200, "errmsg": "OK", "base_url": base_root})


# @app.route('/', methods=['GET', 'POST'])


def check_version(base_root):
    global localDir

    global global_linux_file_dictionary
    global global_pc64_file_dictionary
    global global_pc32_file_dictionary
    global global_mac_file_dictionary

    global global_user_white_list

    content = request.json

    my_dic = dict()

    localDir = ''

    check_update = check_user_in_blacklist(content, global_user_black_list)

    if check_update == 1:
        return jsonify({"ret": 0, "err_msg": "black list user."})

    check_update = check_user_can_update(content, global_user_white_list)

    if not check_update:
        check_update = check_user_can_update_new(content)

    if check_update == 0:
        if 'files' in content:
            file_dic = content['files']

            if len(file_dic) != 1:
                return jsonify({"ret": 0, "err_msg": "platform %s is not support yet..." % platform})

    pm = content['platform']
    if pm.lower() == "linux":
        if len(global_linux_file_dictionary) <= 0:
            global_linux_file_dictionary = inner_reload_version(base_root, pm)
        my_dic = global_linux_file_dictionary
        updater_name = 'updater'
    elif pm.lower() == "mac":
        if len(global_mac_file_dictionary) <= 0:
            global_mac_file_dictionary = inner_reload_version(base_root, pm)
        my_dic = global_mac_file_dictionary
        updater_name = 'updater'
    elif pm.lower() == "pc32":
        if len(global_pc32_file_dictionary) <= 0:
            global_pc32_file_dictionary = inner_reload_version(base_root, pm)
        my_dic = global_pc32_file_dictionary
        updater_name = 'updater.exe'
    elif pm.lower() == "pc64":
        if len(global_pc64_file_dictionary) <= 0:
            global_pc64_file_dictionary = inner_reload_version(base_root, pm)
        my_dic = global_pc64_file_dictionary
        updater_name = 'updater.exe'
    else:
        return jsonify({"ret": 0, "err_msg": "platform %s is not support yet..." % platform})

    # return jsonify({"errcode": 200, "errmsg": "OK", "base_url": base_root})

    # user_string = content['users']

    # download_root = base_root + ("download/%s/" % pm.lower())

    return inner_check_version(base_root, content, updater_name, my_dic)


def download_file(filename):
    global localDir
    # if request.method == "GET":
    # if os.path.isfile(os.path.join(localDir, filename)):

    try:
        params = filename.split("/")

        realname = filename.replace("%s/" % params[0], '', 1)

        if params[0].lower() == "linux":
            workerDir = linuxDir
            updater_name = 'updater'
        elif params[0].lower() == "mac":
            workerDir = macDir
            updater_name = 'updater'
            # return jsonify({"ret": 0, "err_msg": "platform %s is not support yet..." % platform})
        elif params[0].lower() == "pc32":
            workerDir = windows32Dir
            updater_name = 'updater.exe'
        elif params[0].lower() == "pc64":
            workerDir = windows64Dir
            updater_name = 'updater.exe'
        else:
            return jsonify({"ret": 0, "err_msg": "platform %s is not support yet..." % platform})

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
    # pass


def upload_file(filename):
    pass


@updatecheck_blueprint.route('/updatecheck', defaults={'path': ''})
@updatecheck_blueprint.route('/updatecheck/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    root = request.url.replace(path, '')
    if path.startswith("download/"):
        return download_file(path[9:])
    elif path == "tools/test":
        return running_test()
    elif path.startswith("upload/"):
        return upload_file(path[7:])
    elif path == "version/reload":
        content = request.json
        pm = content['platform']
        return reload_version(root, pm)
    elif path == "version/check":
        # platform = request.args.get('platform')
        # filename = request.args.get('f')
        return check_version(root)
    else:
        return "Welcome!"

#
# @app.route('/download/<path:path>', methods=['GET', 'POST'])
# def download(path):
#     return download_file(path)
#     # global localDir
#     # # if request.method == "GET":
#     # # if os.path.isfile(os.path.join(localDir, filename)):
#     # print("path is " + localDir + "file is" + filename)
#     # if '/' in filename or '\\' in filename:
#     #     abort(404)
#     # return send_from_directory(os.join(localDir, folder_name), filename, as_attachment=True)
#     # pass
#
#
# if __name__ == '__main__':
#     app.run(host='0.0.0.0')(backendvenv)
