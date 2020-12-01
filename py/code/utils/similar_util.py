#!/usr/bin/env python
# -*- coding:utf-8 -*-

try:
    import Levenaashtein as edUtil
except Exception as e:
    from difflib import SequenceMatcher as edUtil
from conf.search_params_define import SIMILARITY_THRESHOLD


def get_similar_bool(a: str, b: str) -> bool:
    if not a or not b:
        return False
    try:
        difference = edUtil.ratio(a, b)
    except:
        difference = edUtil(None, a, b).ratio()

    if difference > SIMILARITY_THRESHOLD:
        return True
    else:
        return False


if __name__ == '__main__':
    res = get_similar_bool('qtalk后端裙', 'qtalk后端群')
    print(res)
