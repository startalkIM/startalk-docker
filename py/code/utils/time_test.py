#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'jingyu.he'
import time


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
