#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'
import os
import configparser


def get_config_file():
    project_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
    conf_path = project_dir + '/conf/configure.ini'
    config = configparser.ConfigParser()
    config.read(conf_path, 'utf-8')
    return config


def get_logger_file(name=''):
    project_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
    logger_path = project_dir + '/log/' + name
    return logger_path


def get_conf_dir(name=''):
    project_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
    logger_path = project_dir + '/conf/' + name
    return logger_path


def get_project_dir():
    return os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
