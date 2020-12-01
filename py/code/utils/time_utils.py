#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'

import time
import datetime
import random
from dateutil import relativedelta


class TimeUtils:

    def __init__(self):
        self.msec_now = int(str(time.time() * 1000).split('.')[0])
        self.mon_now = datetime.datetime.now().month
        self.year_now = datetime.datetime.now().year

    def generate_url(self, domain):  # 影响的有种情况： qchat/qtalk 全搜 搜个人/群
        return 'message_2019_1,message_2019_2,message_2019_3,message_2019_4,message_2019_5,message_2019_6,message_2019_7,message_2019_8'
        url = ''
        if domain == 'qtalk':
            mon_this = list(map(lambda x: 'message_' + str(self.year_now) + '_' + str(x),
                                list(filter(lambda x: x <= self.mon_now, range(1, 12)))))
            mon_before = list(map(lambda x: 'message_' + str(self.year_now - 1) + '_' + str(x),
                                  list(filter(lambda x: x > self.mon_now, range(0, 13)))))
            mon = mon_this + mon_before 
            mon = ",".join(str(x) for x in mon)
            url = mon
        if domain == 'qchat':
            mon_this = list(map(lambda x: 'qc_message_' + str(self.year_now) + '_' + str(x),
                                list(filter(lambda x: x > 0, range(self.mon_now - 2, self.mon_now + 1)))))
            mon_before = list(map(lambda x: 'qc_message_' + str(self.year_now - 1) + '_' + str(12 + x),
                                  list(
                                      filter(lambda x: x <= 0, range(self.mon_now - 2, self.mon_now + 1)))))
            mon = mon_this + mon_before
            mon = ",".join(str(x) for x in mon)
            print(url)
            url = mon
        return url

    @staticmethod
    def get_yesterday_timestamp():
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        yesterday_beginning = datetime.datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0, 0)
        yesterday_beginning_time = int(time.mktime(yesterday_beginning.timetuple())) * 1000

        return yesterday_beginning_time

    @staticmethod
    def get_lastweek_timestamp():
        last_week = datetime.datetime.now() - datetime.timedelta(days=7)
        last_week_beginning = datetime.datetime(last_week.year, last_week.month, last_week.day, 0, 0, 0, 0)
        last_week_beginning_time = int(time.mktime(last_week_beginning.timetuple())) * 1000

        return last_week_beginning_time

    @staticmethod
    def get_specific_timestamp(time_str):
        time_array = time.strptime(time_str, "%Y-%m-%d %H:%M:%S")  # 格式有变化的改这个就好
        timestamp = int(time.mktime(time_array))
        return timestamp

    @staticmethod
    def get_specific_ymd(time_str):
        if len(str(time_str)) == 13:
            time_str = str(time_str)[:-3]
        agg = time.localtime(int(time_str))
        return agg.tm_year, agg.tm_mon

    @staticmethod
    def get_ymd_agg(time_str):
        if len(str(time_str)) == 13:
            time_str = str(time_str)[:-3]
        agg = time.localtime(int(time_str))
        return agg

    def get_next_month_index(self):
        nextmonth = datetime.date.today() + relativedelta.relativedelta(months=1)
        index = 'message' + '_' + str(nextmonth.year) + '_' + str(nextmonth.month)
        return index

    def get_date_from_timstamp(self,timestamp):
        if len(str(timestamp)) == 13:
            timestamp = float(str(timestamp)[:10])
        return datetime.datetime.fromtimestamp(timestamp)


if __name__ == '__main__':
    tu = TimeUtils()
    print(tu.get_date_from_timstamp(1562664601))

# decorator 用于计算程序耗时
def timeduration(func):
    def wrapper(*args, **kw):
        s = time.perf_counter()
        result = func(*args, **kw)
        elapsed = time.perf_counter() - s
        if 'logger' in kw:
            kw.get('logger').info(f"{__name__} executed in {elapsed:0.5f} seconds.")
        else:
            print(f"{__name__} executed in {elapsed:0.5f} seconds.")
        return result

    wrapper.__name__ = func.__name__
    return wrapper


def timerfunc(func):
    """
    A timer decorator
    """

    def function_timer(*args, **kwargs):
        """
        A nested function for timing other functions
        """
        start = time.time()
        value = func(*args, **kwargs)
        end = time.time()
        runtime = end - start
        msg = "The runtime for {func} took {time} seconds to complete"
        print(msg.format(func=func.__name__,
                         time=runtime))
        return value

    return function_timer
