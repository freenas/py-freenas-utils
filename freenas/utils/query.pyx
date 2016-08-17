#+
# Copyright 2015 iXsystems, Inc.
# All rights reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted providing that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
#####################################################################

import re
import dateutil.parser
from six import string_types


operators_table = {
    '=': lambda x, y: x == y,
    '!=': lambda x, y: x != y,
    '>': lambda x, y: x > y,
    '<': lambda x, y: x < y,
    '>=': lambda x, y: x >= y,
    '<=': lambda x, y: x <= y,
    '~': lambda x, y: re.search(str(y), str(x)),
    'in': lambda x, y: x in y,
    'nin': lambda x, y: x not in y
}


conversions_table = {
    'timestamp': lambda v: dateutil.parser.parse(v)
}


def eval_logic_and(item, lst):
    for i in lst:
        if not eval_tuple(item, i):
            return False

    return True


def eval_logic_or(item, lst):
    for i in lst:
        if eval_tuple(item, i):
            return True

    return False


def eval_logic_nor(item, lst):
    for i in lst:
        if eval_tuple(item, i):
            return False

    return True


def eval_logic_operator(item, t):
    op, lst = t
    return globals()['eval_logic_{0}'.format(op)](item, lst)


def eval_field_operator(item, t):
    left, op, right = t

    if len(t) == 4:
        right = conversions_table[t[3]](right)

    return operators_table[op](get(item, left), right)


def eval_tuple(item, t):
    if len(t) == 2:
        return eval_logic_operator(item, t)

    if len(t) in (3, 4):
        return eval_field_operator(item, t)


def matches(obj, *rules):
    fail = False
    for r in rules:
        if not eval_tuple(obj, r):
            fail = True
            break

    return not fail


def filter_and_map(fn, items):
    for i in items:
        result = fn(i)
        if result is None:
            continue

        yield result


def partition(s):
    pos = s.find('.')
    if pos == -1:
        return s, None

    if s[pos - 1] == '\\':
        right = None
        left, middle = s.split('.', 1)
        left = left.replace('\\', '.')
        if '.' in middle:
            middle, right = middle.split('.', 1)
        return left + middle, right
    else:
        return s.split('.', 1)


def get(obj, path, default=None):
    if not isinstance(path, string_types):
        try:
            return obj[path]
        except (KeyError, IndexError):
            return default

    right = path
    ptr = obj
    while right:
        left, right = partition(right)

        if isinstance(ptr, dict):
            ptr = ptr.get(left)
            continue

        if isinstance(ptr, (list, tuple)):
            left = int(left)
            ptr = ptr[left] if left < len(ptr) else None
            continue

        return default

    return ptr


def set(obj, path, value):
    if not isinstance(path, string_types):
        obj[path] = value
    else:
        right = path
        ptr = obj
        while right:
            left, right = partition(right)
            if not right:
                break

            if isinstance(ptr, dict):
                if left not in ptr:
                    ll, _ = partition(right)
                    if ll.isdigit():
                        ptr[left] = []
                    else:
                        ptr[left] = {}

                ptr = ptr[left]
                continue

            if isinstance(ptr, (list, tuple)):
                left = int(left)
                l = len(ptr)
                if left <= l:
                    if left == l:
                        ll, _ = partition(right)
                        if ll.isdigit():
                            ptr.append([])
                        else:
                            ptr.append({})

                    ptr = ptr[left]
                    continue
                else:
                    raise IndexError('Index {0} is out of set/append range'.format(left))

            raise ValueError('Cannot set unsupported object type {0}'.format(type(ptr)))

        if isinstance(ptr, dict):
            ptr[left] = value

        elif isinstance(ptr, (list, tuple)):
            left = int(left)
            l = len(ptr)
            if left < l:
                ptr[left] = value
            elif left == l:
                ptr.append(value)
            else:
                raise IndexError('Index {0} is out of set/append range'.format(left))

        else:
            raise ValueError('Cannot set unsupported object type {0}'.format(type(ptr)))


def delete(obj, path):
    if isinstance(path, string_types):
        right = path
        ptr = obj
        while right:
            left, right = partition(right)
            if not right:
                break

            if isinstance(ptr, dict):
                if left in ptr:
                    ptr = ptr.get(left)
                    continue

            if isinstance(ptr, (list, tuple)):
                left = int(left)
                if left < len(ptr):
                    ptr = ptr[left]
                    continue

            raise ValueError('Enclosing object {0} doesn\'t exist'.format(left))
        del ptr[left]
    else:
        del obj[path]


def contains(obj, path):
    right = path
    ptr = obj
    while right:
        left, right = partition(right)
        if isinstance(ptr, dict):
            if left in ptr:
                ptr = ptr.get(left)
                continue

            return False

        if isinstance(ptr, (list, tuple)):
            left = int(left)
            if left < len(ptr):
                ptr = ptr[left]
                continue

            return False

    return True


def query(obj, *rules, **params):
    single = params.pop('single', False)
    count = params.pop('count', None)
    offset = params.pop('offset', None)
    limit = params.pop('limit', None)
    sort = params.pop('sort', None)
    postprocess = params.pop('callback', None)
    select = params.pop('select', None)
    stream = params.pop('stream', False)
    result = iter(obj)

    def search(data):
        for i in data:
            if matches(i, *rules):
                yield i

    if rules:
        result = search(result)

    if select:
        def select_fn(fn, obj):
            obj = fn(obj) if fn else obj

            if isinstance(select, (list, tuple)):
                return [get(obj, i) for i in select]

            if isinstance(select, str):
                return get(obj, select)

        old = postprocess
        postprocess = lambda o: select_fn(old, o)

    if sort:
        def sort_transform(result, key):
            reverse = False
            if key.startswith('-'):
                key = key[1:]
                reverse=True
            result.append((key, reverse))

        _sort = []
        if isinstance(sort, string_types):
            sort_transform(_sort, sort)
        elif isinstance(sort, (tuple, list)):
            for s in sort:
                sort_transform(_sort, s)
        if _sort:
            for key, reverse in reversed(_sort):
                result = sorted(result, key=lambda x: x[key], reverse=reverse)

    if offset:
        result = iter(list(result)[offset:])

    if limit:
        result = iter(list(result)[:limit])

    if postprocess:
        result = filter_and_map(postprocess, result)

    if single:
        return next(result, None)

    if count:
        return len(list(result))

    return result if stream else list(result)
