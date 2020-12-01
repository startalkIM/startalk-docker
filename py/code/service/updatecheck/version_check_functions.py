#!/usr/bin/env python
# -*- coding:utf-8 -*-

import hashlib
import json
import os
import platform
import sys
# , Flask
from conf.updatecheck_params_define import *

log_path = get_logger_file(name='updatecheck.log')
updatecheck_logger = configure_logger('updatecheck', log_path)

# global_user_white_list = {'lffan.liu@ejabhost1',
#                           'xi.ma@ejabhost1',
#                           'yusy.song@ejabhost1',
#                           'ju.ma@ejabhost1',
#                           'dan.liu@ejabhost1',
#                           'chaocc.wang@ejabhost1',
#                           'botaom.ma@ejabhost1'}

# global_user_black_list = {'lei.lei@ejabhost1', 'xinyu.yang@ejabhost1', 'tengfei.yang@ejabhost1'}


def eprint(*args, **kwargs):
    updatecheck_logger.log(*args, file=sys.stderr, **kwargs)


global_pc64_file_dictionary = dict()
global_pc64_product_file_dictionary = dict()
global_pc32_file_dictionary = dict()
global_pc32_product_file_dictionary = dict()
global_mac_file_dictionary = dict()
global_mac_product_file_dictionary = dict()
global_linux_file_dictionary = dict()
global_linux_product_file_dictionary = dict()


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

def inner_reload_version(base_root, pm, channel_value):
    if channel_value == 2:
        download_root = base_root + ("betadownload/%s/" % pm.lower())
    else:
        download_root = base_root + ("download/%s/" % pm.lower())

    if pm.lower() == "linux":
        worker_dir = linuxDir
        return dict()
    elif pm.lower() == "mac":
        if channel_value == 1:
            worker_dir = macProdDir
        else:
            worker_dir = macDir
        return check_files(worker_dir, download_root)
    elif pm.lower() == "pc32":
        if channel_value == 1:
            worker_dir = windows32ProcDir
        else:
            worker_dir = windows32Dir
        return check_files(worker_dir, download_root)
    elif pm.lower() == "pc64":
        if channel_value == 1:
            worker_dir = windows64ProdDir
        else:
            worker_dir = windows64Dir
        return check_files(worker_dir, download_root)


def running_test():
    import time
    time.sleep(3)
    return {"ret": 200, "err_msg": "coool!"}


def reload_version(base_root, content):
    global global_mac_file_dictionary
    global global_mac_product_file_dictionary
    global global_pc64_file_dictionary
    global global_pc64_product_file_dictionary
    global global_pc32_file_dictionary
    global global_pc32_product_file_dictionary

    channel_value = 0
    if 'channel' in content:
        channel_value = content['channel']

    pm = 'undefined'
    if 'platform' in content:
        pm = content['platform']

    # 2是测试, 0 是无效, 1是生产

    if channel_value == 2:
        if pm.lower() == "linux":
            return {"ret": 500, "err_msg": "platform %s is not support yet..." % platform}
        elif pm.lower() == "mac":
            global_mac_file_dictionary = inner_reload_version(base_root, pm, channel_value)
            return {"ret": 0, 'response': global_mac_file_dictionary}
        elif pm.lower() == "pc32":
            global_pc32_file_dictionary = inner_reload_version(base_root, pm, channel_value)
            return {"ret": 0, 'response': global_pc32_file_dictionary}
        elif pm.lower() == "pc64":
            global_pc64_file_dictionary = inner_reload_version(base_root, pm, channel_value)
            return {"ret": 0, 'response': global_pc64_file_dictionary}
    elif channel_value == 1:
        if pm.lower() == "linux":
            return {"ret": 500, "err_msg": "platform %s is not support yet..." % platform}
        elif pm.lower() == "mac":
            global_mac_product_file_dictionary = inner_reload_version(base_root, pm, channel_value)
            return {"ret": 0, 'response': global_mac_product_file_dictionary}
        elif pm.lower() == "pc32":
            global_pc32_product_file_dictionary = inner_reload_version(base_root, pm, channel_value)
            return {"ret": 0, 'response': global_pc32_product_file_dictionary}
        elif pm.lower() == "pc64":
            global_pc64_product_file_dictionary = inner_reload_version(base_root, pm, channel_value)
            return {"ret": 0, 'response': global_pc64_product_file_dictionary}

    return {"ret": 500, "err_msg": "platform %s is not support yet..." % platform}


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
        return {"errcode": 500, "errmsg": 'server file is not prepared!'}

    if 'files' in content:
        file_dic = content['files']

        if len(file_dic) == 1:
            changed = check_diff(local_dic, file_dic, updater_name)
        else:
            changed = check_diff(local_dic, file_dic, '')
        updatecheck_logger.debug(changed)
        return {"errcode": 200, "errmsg": "OK", "base_url": base_root, "changed": changed}
    else:
        return {"errcode": 200, "errmsg": "OK", "base_url": base_root}


def check_version(base_root, content):
    global localDir

    global global_linux_file_dictionary
    global global_linux_product_file_dictionary
    global global_pc64_file_dictionary
    global global_pc64_product_file_dictionary
    global global_pc32_file_dictionary
    global global_pc32_product_file_dictionary
    global global_mac_file_dictionary
    global global_mac_product_file_dictionary
    global global_user_white_list
    localDir = ''

    # check blacklist
    check_update = check_user_in_blacklist(content, global_user_black_list)

    if check_update == 1:
        return {"ret": 0, "err_msg": "black list user."}

    at_white_list = check_user_can_update(content, global_user_white_list)

    if not check_update:
        check_update = check_user_can_update_new(content)

    if check_update == 0:
        if 'files' in content:
            file_dic = content['files']

            if len(file_dic) != 1:
                return {"ret": 0, "err_msg": "platform %s is not support yet..." % platform}
    channel_value = 0

    if at_white_list:
        channel_value = 2 # beta
    else:
        if 'channel' in content:
            channel_value = content['channel']
        else:
            channel_value = 1 # product

    my_dic = {}

    pm = content['platform'].lower()

    if pm == "linux":
        if channel_value == 2:
            if len(global_linux_file_dictionary) <= 0:
                my_dic = inner_reload_version(base_root, pm, channel_value)
                global_linux_file_dictionary = my_dic
            else:
                my_dic = global_linux_file_dictionary
        elif channel_value == 1:
            if len(global_linux_product_file_dictionary) <= 0:
                my_dic = inner_reload_version(base_root, pm, channel_value)
                global_linux_product_file_dictionary = my_dic
            else:
                my_dic = global_linux_product_file_dictionary
        updater_name = 'updater'
    elif pm == "mac":
        if channel_value == 2:
            if len(global_mac_file_dictionary) <= 0:
                my_dic = inner_reload_version(base_root, pm, channel_value)
                global_mac_file_dictionary = my_dic
            else:
                my_dic = global_mac_file_dictionary
        elif channel_value == 1:
            if len(global_mac_product_file_dictionary) <= 0:
                my_dic = inner_reload_version(base_root, pm, channel_value)
                global_mac_product_file_dictionary = my_dic
            else:
                my_dic = global_mac_product_file_dictionary
        updater_name = 'updater'
    elif pm == "pc32":
        if channel_value == 2:
            if len(global_pc32_file_dictionary) <= 0:
                my_dic = inner_reload_version(base_root, pm, channel_value)
                global_pc32_file_dictionary = my_dic
            else:
                my_dic = global_pc32_file_dictionary
        elif channel_value == 1:
            if len(global_pc32_product_file_dictionary) <= 0:
                my_dic = inner_reload_version(base_root, pm, channel_value)
                global_pc32_product_file_dictionary = my_dic
            else:
                my_dic = global_pc32_product_file_dictionary
        updater_name = 'updater.exe'
    elif pm == "pc64":
        if channel_value == 2:
            if len(global_pc64_file_dictionary) <= 0:
                my_dic = inner_reload_version(base_root, pm, channel_value)
                global_pc64_file_dictionary = my_dic
            else:
                my_dic = global_pc64_file_dictionary
        elif channel_value == 1:
            if len(global_pc64_product_file_dictionary) <= 0:
                my_dic = inner_reload_version(base_root, pm, channel_value)
                global_pc64_product_file_dictionary = my_dic
            else:
                my_dic = global_pc64_product_file_dictionary
        updater_name = 'updater.exe'
    else:
        return {"ret": 0, "err_msg": "platform %s is not support yet..." % platform}

    if len(my_dic) == 0:
        #updatecheck_logger.error(
        #    'my_dic size is 0.' + "base root is: " + base_root + " content is: " + content + "updater_name is:" +
        #    updater_name)
        updatecheck_logger.error(
            f"my_dic size is 0. base root is: {base_root} content is {content} updater_name is:{updater_name}")


    return inner_check_version(base_root, content, updater_name, my_dic)


# if __name__ == '__main__':
#
#     for i in range(100):
#         global windows32Dir
#         global windows32ProcDir
#         global windows64Dir
#         global windows64ProdDir
#         global macDir
#         global macProdDir
#
#         windows64Dir = '/Users/may/files'
#         windows32Dir = '/Users/may/files'
#         windows32ProcDir = '/Users/may/files'
#         windows64ProdDir = '/Users/may/files'
#
#         content = (
#             '{	"files":	{		"CustomUi.dll":	"DD33BE42547AFB6A655ABB52B031B422",		"DataBasePlug.dll":	'
#             '"31A37F6A61152106FCB4462D6419B781",		"Emoticon.dll":	"B63EF0CB39058F4F2869636D78BB6D54",	'
#             '	"EventBus.dll":	"719E59ED9EF31884215F56A5C766C1A1",		"LogicCommunication.dll":	'
#             '"FCB0738703A37654E23B4AFA6519BB55",		"LogicLogin.dll":	"1C8B80585C500BC67E2C0BD425720308",	'
#             '	"LogicManager.dll":	"80F51EC45AEA902AA5791DD4506ACCAD",		"Platform.dll":	'
#             '"60700D2FA0A1423726D4B1CB4E14BA06",		"QTalk.exe":	"138B5B7178036BEF434538DA9A3CDA59",	'
#             '	"Qt5Core.dll":	"04DBC71249EE089F79EFCC882A15ED49",		"Qt5Gui.dll":	'
#             '"007F810BDD33DC64D1DC9F3E143997A0",		"Qt5Multimedia.dll":	"3069A8E17C04A4A571371AFF386A00DD",	'
#             '	"Qt5Network.dll":	"49D87C97465D70871DAFB995DEAFC8CC",		"Qt5Positioning.dll":	'
#             '"EF1F973A8D654F7272FC072055FEB0F1",		"Qt5PrintSupport.dll":	"1AEB0C5296CA90495B34C3FAD18DA186",	'
#             '	"Qt5Qml.dll":	"75C6C8A6158C84DEF137B659DB4067B1",		"Qt5Quick.dll":	'
#             '"0AAF31AFE0255C25780BDFBE16E17DBA",		"Qt5QuickWidgets.dll":	"B058684387294A8B2EF288DC66670A31",	'
#             '	"Qt5SerialPort.dll":	"82B5261010754D5E30B8E2FC761BF93C",		"Qt5Svg.dll":	'
#             '"80CACC66A0F71C558702B3D9032ABDFB",		"Qt5WebChannel.dll":	"8C3EB4553E08DE4DE99C3F7F4F695224",	'
#             '	"Qt5WebEngineCore.dll":	"B46B199B9D0CEFC70D9AE8DA99E4A2C2",		"Qt5WebEngineWidgets.dll":	'
#             '"0CFD101F36E3C708A6FA989E756DA284",		"Qt5Widgets.dll":	"3A3A230F9F5C232FEF2BCC7AD4AA8283",	'
#             '	"Qt5Xml.dll":	"7D4A8CF967BF5E0322944875B6DC634D",		"QtUtil.dll":	'
#             '"1B63CA7D2FB76591DEB6C80ABA304CAB",		"QtWebEngineProcess.exe":	'
#             '"F7C7DBFF605E243B896E1073EF0855DF",		"Screenshot.dll":	"11DC9AE89C0972414A2B26062B116555",	'
#             '	"UIAddressBook.dll":	"5699074378A249962CFF96E9AD1FA23C",		"UICardManager.dll":	'
#             '"8C11AF42884D469C759B4CDD35CA4B17",		"UIChatViewPlug.dll":	"6A4D027A4B2973D6279896D14A3BBACD",	'
#             '	"UICom.dll":	"C568949D4B7B9E8CDAFA03A6AAF54898",		"UIGroupManager.dll":	'
#             '"735C06D94C5784FF4678512C68EEB4F3",		"UILoginPlug.dll":	"32405ACB466969217E445FAA69540E7A",	'
#             '	"UINavigationPlug.dll":	"43DD4BB255B6C9CF8E74C42760032B3F",		"UIOAManager.dll":	'
#             '"B704C6A2A65D2E502399F9D7467044A1",		"UIPictureBrowser.dll":	"5EB56BB545AAD7A01A5877E9E7213409",	'
#             '	"UITitlebarPlug.dll":	"32D055875F2AA23E84BB61D39F8DE204",		"Updater.exe":	'
#             '"D2B5713D4255C94AD84BA161479EB25B",		"WebService.dll":	"833AA737928CCA6A0DCC6D63A802C6C1",	'
#             '	"api-ms-win-crt-heap-l1-1-0.dll":	"C3AA45F69CEEEDAE8799C3C71CE4D64B",	'
#             '	"api-ms-win-crt-locale-l1-1-0.dll":	"8F1BF32B70D388EC06393D04E16EEC0A",	'
#             '	"api-ms-win-crt-math-l1-1-0.dll":	"C723F17218F1C0CE46C69B76783BC15A",	'
#             '	"api-ms-win-crt-runtime-l1-1-0.dll":	"DA9CB6B2A96CA5F3D8EF55EF2F7165BA",	'
#             '	"api-ms-win-crt-stdio-l1-1-0.dll":	"5E7BDF944B1C9A987665156393680E01",	'
#             '	"api-ms-win-crt-string-l1-1-0.dll":	"E27CE56B6565C66171F7FA29B240CF98",	'
#             '	"api-ms-win-crt-time-l1-1-0.dll":	"AD41D7793E8E931D6EDB8FE72D70C190",	'
#             '	"api-ms-win-eventing-provider-l1-1-0.dll":	"E9BB03E93162267E3DC00432C95606EB",	'
#             '	"audio/qtaudio_wasapi.dll":	"77941B098E7843BCB6621DEE219FC27C",		"audio/qtaudio_windows.dll":	'
#             '"D7FEBC8EE3223CD29D994C0508D56D7F",		"bearer/qgenericbearer.dll":	'
#             '"610ED32F4A24968FB95BDE4C69C3F348",		"d3dcompiler_47.dll":	"FEA40E5B591127AE3B065389D058A445",	'
#             '	"iconengines/qsvgicon.dll":	"F6DC500211C65D3DFA3F164BAA2E8675",		"imageformats/qgif.dll":	'
#             '"1E3BD6A67DB1AC2AF8EFDF9E41672DAF",		"imageformats/qicns.dll":	'
#             '"12E2714D546BA5791228E856C0086FCA",		"imageformats/qico.dll":	'
#             '"D5C160B59FDC8C4F617F49BCFD3B0D58",		"imageformats/qjpeg.dll":	'
#             '"8E171D478CFCECFA2FBC052CF9D1B85E",		"imageformats/qsvg.dll":	'
#             '"361243A5C30C202CB77554F25331E802",		"imageformats/qtga.dll":	'
#             '"B435DA1DA77BCFD264177500281588A3",		"imageformats/qtiff.dll":	'
#             '"84B524309028195326E39AD29715EBC6",		"imageformats/qwbmp.dll":	'
#             '"3EF768836B04B6720C6588E52F427856",		"imageformats/qwebp.dll":	'
#             '"88A7558F3FEE1D9F7DC07B76E7D41BAD",		"libEGL.dll":	"392A9FFCEFFD24025BBE5D950B867478",	'
#             '	"libGLESV2.dll":	"8D03A9B2E4F224369D9C71C3FDEDE605",		"libcrypto-1_1-x64.dll":	'
#             '"981A58716A7AADD96BAE91056410E331",		"libcurl.dll":	"15C1F0713D35FF0D8468AD0407746CF7",	'
#             '	"libssl-1_1-x64.dll":	"C9B804F884B601D7B96B1FF6F5E5EC5A",		"mediaservice/dsengine.dll":	'
#             '"46C8234B966C0E4D06AF6F7296185793",		"mediaservice/qtmedia_audioengine.dll":	'
#             '"5D7010D262D754F29D2F58D2744F9906",		"mediaservice/wmfengine.dll":	'
#             '"DBFF2186E0EDEC3E17460FE61651F8A8",		"msvcp140.dll":	"5D2728BEDE4841DC65AB364987FDEBE7",	'
#             '	"opengl32sw.dll":	"7DBC97BFEE0C7AC89DA8D0C770C977B6",		"platforms/qwindows.dll":	'
#             '"2743AFC4B92ECF51BA5D64B7270AC552",		"playlistformats/qtmultimedia_m3u.dll":	'
#             '"E8A1AB244B59096192117B05F75C4508",		"position/qtposition_positionpoll.dll":	'
#             '"2FFDC7339689DC93E5BF3C1AA39FD14F",		"position/qtposition_serialnmea.dll":	'
#             '"9D270F8860BD8CC24DC1590ACD9732DD",		"position/qtposition_winrt.dll":	'
#             '"B32C400D136C2AD110B5B611E549EA80",		"printsupport/windowsprintersupport.dll":	'
#             '"AB7B8EE2E89E46B721C1CF35A7816AE5",		"quazip.dll":	"66A1ACF881E453561F26BEFE9146F9E5",	'
#             '	"qzxing.dll":	"AA3752D723C6E4420B4E7D5F6D7812BA",		"resources/icudtl.dat":	'
#             '"8CDA09112153FF6DC3ADED6FFEB6835F",		"resources/qtwebengine_devtools_resources.pak":	'
#             '"0B1CC5D316CBF8C4573DDF703449658A",		"resources/qtwebengine_resources.pak":	'
#             '"E34AA0D2A40A7644670D6738A94C4139",		"resources/qtwebengine_resources_100p.pak":	'
#             '"D561C1F8E1FB501C8D21068D1B1C99A6",		"resources/qtwebengine_resources_200p.pak":	'
#             '"EF2C2645B213B195E7FADAAB3700458E",		"styles/qwindowsvistastyle.dll":	'
#             '"4CE6C52A6AE57B30BCCFD9C49F1409D7",		"translations/qt_ar.qm":	'
#             '"C1929A724FC952FD37F2DE135770BD25",		"translations/qt_bg.qm":	'
#             '"BC6062F83028218D03EF6E7416EBE044",		"translations/qt_ca.qm":	'
#             '"9EADD4A070EF102B265B3E82048B695E",		"translations/qt_cs.qm":	'
#             '"9F597D2C5CE11A6AE1321A3121A2C9A4",		"translations/qt_da.qm":	'
#             '"419678556C456A1C10C9E01C6E5B5735",		"translations/qt_de.qm":	'
#             '"62EDD38B74C245782A57369E3F5FE747",		"translations/qt_en.qm":	'
#             '"4AEF4415F2E976B2CC6F24B877804A57",		"translations/qt_es.qm":	'
#             '"C99CEB6B922E8628D5C44A9090BA4361",		"translations/qt_fi.qm":	'
#             '"2749BC71C3D81B3F571925098880B92F",		"translations/qt_fr.qm":	'
#             '"89368CD58BF9AF6492A8DE9252E27E1A",		"translations/qt_gd.qm":	'
#             '"FD5046C815BC3E89FB327044A29236E4",		"translations/qt_he.qm":	'
#             '"6A8A53D365F564BE4804B3F1167186AD",		"translations/qt_hu.qm":	'
#             '"8B74E4447AAEA1A769B67F4C78B809B2",		"translations/qt_it.qm":	'
#             '"1FD524E5A726201BBCD20A100405F2B5",		"translations/qt_ja.qm":	'
#             '"996B08C0AA6F051F4A783B6D80A01415",		"translations/qt_ko.qm":	'
#             '"54F969FC9478803AEC4D36F010EBC078",		"translations/qt_lv.qm":	'
#             '"5853B11701BEFB45FA2961886DD68294",		"translations/qt_pl.qm":	'
#             '"7C9E3EADB4C2F99E6954C54CC999F552",		"translations/qt_ru.qm":	'
#             '"2ADDC7DB56AB9B12F13166A27127D203",		"translations/qt_sk.qm":	'
#             '"BF005A150EEA6E9FE03C0ACA1605C760",		"translations/qt_uk.qm":	'
#             '"36EA0A88BFB3EDB5EFAB866FF63FD2BB",		"translations/qt_zh_TW.qm":	'
#             '"BA40257AA2E1CD0768178ECA517D111D",		"translations/qtwebengine_locales/am.pak":	'
#             '"92D224DE4674AB2E2086BD534D2083CF",		"translations/qtwebengine_locales/ar.pak":	'
#             '"1B55D1EE81D5F528FEE0F592A4C9E208",		"translations/qtwebengine_locales/bg.pak":	'
#             '"713AA83167D33345A42E7E814BEFD7D2",		"translations/qtwebengine_locales/bn.pak":	'
#             '"A1B4659CCB692882A2A0BF016E1CBE30",		"translations/qtwebengine_locales/ca.pak":	'
#             '"0497078547CA5F026E8CFAD1A1AD7080",		"translations/qtwebengine_locales/cs.pak":	'
#             '"971518BE51D72D75828B4E7F405DAC4D",		"translations/qtwebengine_locales/da.pak":	'
#             '"11A3354BC5B3C82236F2BA31053D34A0",		"translations/qtwebengine_locales/de.pak":	'
#             '"886A017AA622BEB9EFCEFF2858FA4D3C",		"translations/qtwebengine_locales/el.pak":	'
#             '"4DE0618CB3470CC205823CF8AA2F295C",		"translations/qtwebengine_locales/en-GB.pak":	'
#             '"35CCDC2C1F1ECF26DAE7EFA019DC30AE",		"translations/qtwebengine_locales/en-US.pak":	'
#             '"E810E00679CE19EC800F8E845D9ECC2D",		"translations/qtwebengine_locales/es-419.pak":	'
#             '"C39149D5EDF2B54AF574418A9B54418F",		"translations/qtwebengine_locales/es.pak":	'
#             '"0A490A03C4CB1D890F040B09808DC3F5",		"translations/qtwebengine_locales/et.pak":	'
#             '"8A6BE519FC497A8B228BDE492475188B",		"translations/qtwebengine_locales/fa.pak":	'
#             '"2BEB9B0C98E00F1F2DC0675004B7E1AB",		"translations/qtwebengine_locales/fi.pak":	'
#             '"AB620732F3CEB962C7372607CC230ABE",		"translations/qtwebengine_locales/fil.pak":	'
#             '"4DDCDFF05B40E67DF2A2672F16B962FD",		"translations/qtwebengine_locales/fr.pak":	'
#             '"28E8692139A6053C4EEF0FBBC418505B",		"translations/qtwebengine_locales/gu.pak":	'
#             '"299BF128EEA7B27A0F2DDD693DBA8101",		"translations/qtwebengine_locales/he.pak":	'
#             '"2498AEC42A36332D14B726E4D4DBB59C",		"translations/qtwebengine_locales/hi.pak":	'
#             '"94E6D6CCEB1FCC50DEE59F6DCB2E6803",		"translations/qtwebengine_locales/hr.pak":	'
#             '"6AB29303D88DA895FAB310B28AEF50C4",		"translations/qtwebengine_locales/hu.pak":	'
#             '"A12032FBECF2BA7476877FB0F929AC30",		"translations/qtwebengine_locales/id.pak":	'
#             '"1786B9876BB8B60A7DE739B2713AFF2B",		"translations/qtwebengine_locales/it.pak":	'
#             '"3C259061D9126B3AB83A66BF9C1CD0AE",		"translations/qtwebengine_locales/ja.pak":	'
#             '"C6507D79FBD5B53B09B5F395374CC3F7",		"translations/qtwebengine_locales/kn.pak":	'
#             '"8AC322DB8B94523B0ED344793E2CE423",		"translations/qtwebengine_locales/ko.pak":	'
#             '"D1D0095DB49C0D040B84C5A4712DF2D1",		"translations/qtwebengine_locales/lt.pak":	'
#             '"6C661445D998B54696CD8ADC367AE29D",		"translations/qtwebengine_locales/lv.pak":	'
#             '"6D1F4E43B5ABFCC250D8B1DC8DB80B83",		"translations/qtwebengine_locales/ml.pak":	'
#             '"7B808C32D4C5EA8E73BD97B1FD3EDEE9",		"translations/qtwebengine_locales/mr.pak":	'
#             '"A23D5FE191DB414DA18E53C7187BB7BD",		"translations/qtwebengine_locales/ms.pak":	'
#             '"8A7233E75F49DB22D91D7A85256D86D1",		"translations/qtwebengine_locales/nb.pak":	'
#             '"67380DD8BCEC151E764E0C297AD0E383",		"translations/qtwebengine_locales/nl.pak":	'
#             '"EE7F7C042774AE468CDC0076BA8239A1",		"translations/qtwebengine_locales/pl.pak":	'
#             '"EC70423837FC4D06B097EEC68574DB53",		"translations/qtwebengine_locales/pt-BR.pak":	'
#             '"364C0A546484C39BB8233B4E3850D073",		"translations/qtwebengine_locales/pt-PT.pak":	'
#             '"28E50FC30CD7D96C5CF230C319DA41B1",		"translations/qtwebengine_locales/ro.pak":	'
#             '"82597E6A95F9571D874DF6794B07BF60",		"translations/qtwebengine_locales/ru.pak":	'
#             '"84316644CA204E3FE241CDDD49B3DA17",		"translations/qtwebengine_locales/sk.pak":	'
#             '"F43FAF19BB732BA987ED6932006EA910",		"translations/qtwebengine_locales/sl.pak":	'
#             '"65500BB7EBC58F7C7998857F49E8E2D7",		"translations/qtwebengine_locales/sr.pak":	'
#             '"AE619A95F80B98C768F24EE796575C8E",		"translations/qtwebengine_locales/sv.pak":	'
#             '"AF251F8430111733451C500DA90AC5A6",		"translations/qtwebengine_locales/sw.pak":	'
#             '"8C0FFC90157066B299AAF8BD26BED892",		"translations/qtwebengine_locales/ta.pak":	'
#             '"85F1BAA0F4E126C023238689F66581D9",		"translations/qtwebengine_locales/te.pak":	'
#             '"AF601118C187E73398591FA1199BC9B6",		"translations/qtwebengine_locales/th.pak":	'
#             '"5A4026FA426E22E691D7FC00351CFA36",		"translations/qtwebengine_locales/tr.pak":	'
#             '"C2DC4B260FD172C2B3426F74548A86CE",		"translations/qtwebengine_locales/uk.pak":	'
#             '"DFABC723E213F714CDC4BBBDBFBF9FE2",		"translations/qtwebengine_locales/vi.pak":	'
#             '"01F8811CF17F09D51ABB914DC22675DA",		"translations/qtwebengine_locales/zh-CN.pak":	'
#             '"F075DCD9D3242D842B7D511EB07F9B58",		"translations/qtwebengine_locales/zh-TW.pak":	'
#             '"778A8500A8E8516379BE41E1B264934D",		"vc_redist.x64.exe":	"EED05358986AB6A8526BB1844AFC9640",	'
#             '	"vcruntime140.dll":	"D5D9432A97CF932A0CDDD707D4EE2698"	},	"machineId":	"",	"platform":	"pc64",	'
#             '"exec":	"qtalk",	"version":	"0",	"channel":	2,	"users":	"chunxiang.hou@ejabhost1|chaocc.wang@ejabhost1"}')
#
#         root = 'http://qim.qunar.com/updatecheck/'
#
#         json_string = check_version(root, json.loads(content))
#
#         print(json_string)
#     pass
