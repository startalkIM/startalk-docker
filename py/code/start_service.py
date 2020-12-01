# -*- encoding:utf-8 -*-
from service import app
from utils.logger_conf import configure_logger
logger = configure_logger('root')

__author__ = 'jingyu.he'

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8884)
