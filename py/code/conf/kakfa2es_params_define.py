#!/usr/bin/env python
# -*- coding:utf-8 -*-

from utils.get_conf import get_config_file

config = get_config_file()
GROUP_ID = config['kafka']['group_id']
CHAT_TOPIC = config['kafka']['qtalk_chat_topic']
GROUP_TOPIC = config['kafka']['qtalk_group_topic']
CONSUMER_ZOOKEEPER = config['kafka']['consumer_broker_params']
