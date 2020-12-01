#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'

import logging
import logging.config
import logging.handlers
from utils.get_conf import get_config_file, get_logger_file

config = get_config_file()
level = config['log']['level'].lower()
router = {
    'critical': logging.CRITICAL,
    'fatal': logging.FATAL,
    'error': logging.ERROR,
    'warning': logging.WARNING,
    'warn': logging.WARN,
    'info': logging.INFO,
    'debug': logging.DEBUG,
    'notset': logging.NOTSET
}
log_level = router.get(level, logging.INFO)
log_root = get_logger_file()
logger_register = {
    'root': '',
    'search': '',
    'sharemsg': '',
    'meetingdetail': '',
    'updatecheck': '',
    'cache': '',
    'sql': '',
    'jsontools': '',
    'rtc': '',
    'error': ''
}
for _k, _v in logger_register.items():
    logger_register[_k] = log_root + _k + '.log'


def configure_logger(name, log_path=''):
    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'default': {'format': '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s - %(message)s',
                        'datefmt': '%Y-%m-%d %H:%M:%S'},
            'normal': {'format': '%(asctime)s - %(levelname)s - %(message)s',
                       'datefmt': '%Y-%m-%d %H:%M:%S'}
        },
        'handlers': {
            'console': {
                'level': log_level,
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'stream': 'ext://sys.stdout'
            },
            'root': {
                'level': log_level,
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': logger_register['root'],
                'encoding': 'utf-8',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 3
            },
            'error': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': logger_register['error'],
                'encoding': 'utf-8',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 3
            },
            'search': {
                'level': log_level,
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': logger_register['search'],
                'encoding': 'utf-8',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 3
            },
            'sharemsg': {
                'level': log_level,
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': logger_register['sharemsg'],
                'encoding': 'utf-8',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 3
            },
            'meetingdetail': {
                'level': log_level,
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': logger_register['meetingdetail'],
                'encoding': 'utf-8',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 3
            },
            'updatecheck': {
                'level': log_level,
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': logger_register['updatecheck'],
                'encoding': 'utf-8',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 3
            },
            'cache': {
                'level': log_level,
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': logger_register['cache'],
                'encoding': 'utf-8',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 3
            },
            'sql': {
                'level': log_level,
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': logger_register['sql'],
                'encoding': 'utf-8',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 3
            },
            'jsontools': {
                'level': log_level,
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': logger_register['jsontools'],
                'encoding': 'utf-8',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 3
            },
            'rtc': {
                'level': log_level,
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': logger_register['rtc'],
                'encoding': 'utf-8',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 3
            },
        },
        'loggers': {
            'root': {
                'level': log_level,
                'handlers': ['console', 'root', 'error']
            },
            'search': {
                'level': log_level,
                'handlers': ['console', 'search', 'error']
            },
            'sharemsg': {
                'level': log_level,
                'handlers': ['console', 'sharemsg', 'error']
            },
            'meetingdetail': {
                'level': log_level,
                'handlers': ['console', 'meetingdetail', 'error']
            },
            'updatecheck': {
                'level': log_level,
                'handlers': ['console', 'updatecheck', 'error']

            },
            'cache': {
                'level': log_level,
                'handlers': ['console', 'cache', 'error']
            },
            'sql': {
                'level': log_level,
                'handlers': ['console', 'sql', 'error']
            },
            'rtc': {
                'level': log_level,
                'handlers': ['console', 'rtc', 'error']
            },
            'jsontools': {
                'level': log_level,
                'handlers': ['console', 'jsontools', 'error']
            }
        },
        'disable_existing_loggers': False
    })
    return logging.getLogger(name)
