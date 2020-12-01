#!/usr/bin/env python
# -*- coding:utf-8 -*-
from utils.logger_conf import configure_logger
from utils.get_conf import get_logger_file, get_config_file

# windows32Dir = "/home/q/www/qtalk.updater/windows/pc32/"
# windows64Dir = "/home/q/www/qtalk.updater/windows/pc64/"
#
# windows64_startalk_dir = "/home/q/www/startalk.updater/windows/pc64/"
# linuxDir = "/home/q/www/qtalk.updater/linux/"
# macDir = '/home/q/www/qtalk.updater/mac/'


windows32Dir = "/home/q/www/qtalk.updater/windows/pc32/"
windows32ProcDir = "/home/q/www/qtalk.updater_product/windows/pc32/"
windows64Dir = "/home/q/www/qtalk.updater/windows/pc64/"
windows64ProdDir = "/home/q/www/qtalk.updater_product/windows/pc64/"
macDir = '/home/q/www/qtalk.updater/mac/'
macProdDir = '/home/q/www/qtalk.updater_product/mac/'

windows64_startalk_dir = "/home/q/www/startalk.updater/windows/pc64/"
linuxDir = "/home/q/www/qtalk.updater/linux/"

current_updater_version = 10001
pc32_link = 'https://qim.qunar.com/win_2_0/downloads/qtalk_online.exe'
pc64_link = 'https://qim.qunar.com/win_2_0/downloads/qtalk_online.exe'
linux_link = 'https://qim.qunar.com/win_2_0/downloads/qtalk_linux_laster.run'
macos_link = 'https://qim.qunar.com/win_2_0/downloads/qtalk_mac_online.dmg'

global_user_white_list = {'lffan.liu@ejabhost1',
                          # 'xi.ma@ejabhost1',
                          # 'yusy.song@ejabhost1',
                          # 'ju.ma@ejabhost1',
                          'dan.liu@ejabhost1',
                          # 'chaocc.wang@ejabhost1',
                          'botaom.ma@ejabhost1',
                          'binz.zhang@ejabhost1'
                            ,'hubin.hu@ejabhost1'
                            ,'weiping.he@ejabhost1'
                            ,'hubo.hu@ejabhost1'
                            ,'jingyu.he@ejabhost1'
                            ,'juanf.feng@ejabhost1'
                            ,'kaiming.zhang@ejabhost1'
                            ,'lffan.liu@ejabhost1'
                            ,'lihaibin.li@ejabhost1'
                            ,'lilulucas.li@ejabhost1'
                            ,'malin.ma@ejabhost1'
                            ,'wenhui.fan@ejabhost1'
                            ,'xi.guo@ejabhost1'
                            ,'yuelin.liu@ejabhost1'}

global_user_black_list = {'lei.lei@ejabhost1', 'xinyu.yang@ejabhost1', 'tengfei.yang@ejabhost1'}
