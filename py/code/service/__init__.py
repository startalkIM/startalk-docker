# -*- encoding: utf8 -*-
__author__ = 'jingyu.he'
import re
import sys
import conf.constants
from flask import Flask, render_template, jsonify
from service.meeting.meeting_detail import meeting_blueprint
from service.sharemsg.sharemsg import sharemsg_blueprint
from service.search.search import search_blueprint
from service.updatecheck.updatecheck import updatecheck_blueprint
from service.jsontools.json_tools import jsontools_blueprint

# from service.webparser.parser import parser_blueprint

PY_VERSION = re.findall('^([\d\.].*?)\s', sys.version)[0]
conf.constants.PY_VERSION = PY_VERSION
app = Flask(__name__, template_folder='../templates', static_folder='../static', static_url_path='/py/static')

app.register_blueprint(meeting_blueprint, url_prefix='/')
app.register_blueprint(sharemsg_blueprint, url_prefix='/')
app.register_blueprint(search_blueprint, url_prefix='/')
app.register_blueprint(updatecheck_blueprint, url_prefix='/')
app.register_blueprint(jsontools_blueprint, url_prefix='/')


# app.register_blueprint(parser_blueprint, url_prefix='/')


@app.route('/healthcheck.html', methods=['GET'])
def healthcheck():
    return render_template('healthcheck.html')


@app.errorhandler(404)
def handler404(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def handler500(error):
    return jsonify(ret=False, errcode=500, errmsg='{}'.format(error)), 500
