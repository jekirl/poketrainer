import collections
from bisect import bisect_left
from itertools import chain

import six
from six import iteritems

if six.PY3:
    from builtins import map as imap
elif six.PY2:
    from itertools import imap


def all_in(candidates, sequence):
    for element in candidates:
        if element not in sequence:
            return False
    return True


def take_closest(my_number, my_list):
    """
    Assumes my_list is sorted. Returns closest value to my_number.

    If two numbers are equally close, return the smallest number.
    """
    pos = bisect_left(my_list, my_number)
    if pos == 0:
        return my_list[0]
    if pos == len(my_list):
        return my_list[-1]
    before = my_list[pos - 1]
    after = my_list[pos]
    if after - my_number < my_number - before:
        return after
    else:
        return before


def dict_merge(dct, merge_dct, filtered_key=None):
    for k, v in iteritems(merge_dct):
        if filtered_key and k == filtered_key:
            continue
        if (
            k in dct and isinstance(dct[k], dict) and
            isinstance(merge_dct[k], collections.Mapping)
        ):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]
    return dct


def flat_map(f, items):
        return list(chain.from_iterable(imap(f, items)))
