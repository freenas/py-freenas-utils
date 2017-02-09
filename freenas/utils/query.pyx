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
import itertools
from freenas.utils import list_startswith
from freenas.utils.lazy import unlazy
from six import string_types

try:
    from bsd import fnmatch
except ImportError:
    from fnmatch import fnmatch


def op_in(x, y):
    if isinstance(y, (list, tuple)):
        return x in y

    return y in x


def op_nin(x, y):
    if isinstance(y, (list, tuple)):
        return x not in y

    return y not in x


operators_table = {
    '=': lambda x, y: x == y,
    '!=': lambda x, y: x != y,
    '>': lambda x, y: x > y,
    '<': lambda x, y: x < y,
    '>=': lambda x, y: x >= y,
    '<=': lambda x, y: x <= y,
    '~': lambda x, y: re.search(str(y), str(x)),
    'in': op_in,
    'nin': op_nin,
    'contains': lambda x, y: y in x,
    'ncontains': lambda x, y: y not in x,
    'match': lambda x, y: fnmatch(y, x)
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


def pop_filter(filter, prop):
    for i in filter:
        if len(i) == 3:
            name, op, value = i
            if name == prop:
                filter.remove(i)
                return op, value


def test_filter(t, value):
    if not t:
        return True

    op, v = t
    return operators_table[op](v, value)


def exclude_from_filter(filter, *props):
    for i in list(filter):
        if len(i) == 3:
            name, _, _ = i
            for p in props:
                if list_startswith(name.split('.'), p.split('.')):
                    filter.remove(i)
        if len(i) == 2:
            _, pred = i
            exclude_from_filter(pred, *props)


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

    right = s
    left = ''
    while right[pos - 1] == '\\':
        middle, right = right.split('.', 1)
        left += middle.replace('\\', '.')
        pos = right.find('.')
        if pos == -1:
            return left + right, None
        
    middle, right = right.split('.', 1)
    return left + middle, right


def get(obj, path, default=None):
    if not isinstance(path, string_types):
        try:
            return unlazy(obj[path])
        except (KeyError, IndexError):
            return default

    right = path
    ptr = obj
    while right:
        left, right = partition(right)

        if isinstance(ptr, dict):
            ptr = unlazy(ptr.get(left, default))
            continue

        if isinstance(ptr, (list, tuple)):
            left = int(left)
            ptr = unlazy(ptr[left]) if left < len(ptr) else None
            continue

        return default

    return unlazy(ptr)


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
                if left >= l:
                    while left > l:
                        ptr.append(None)
                        l = len(ptr)

                    ll, _ = partition(right)
                    if ll.isdigit():
                        ptr.append([])
                    else:
                        ptr.append({})

                ptr = ptr[left]
                continue

            raise ValueError('Cannot set unsupported object type {0}'.format(type(ptr)))

        if isinstance(ptr, dict):
            ptr[left] = value

        elif isinstance(ptr, (list, tuple)):
            left = int(left)
            l = len(ptr)
            if left < l:
                ptr[left] = value
            else:
                while left > l:
                    ptr.append(None)
                    l = len(ptr)

                ptr.append(value)

        else:
            raise ValueError('Cannot set unsupported object type {0}'.format(type(ptr)))


def delete(obj, path):
    ptr = obj
    left = path
    if isinstance(path, string_types):
        right = path
        while right:
            left, right = partition(right)
            if not right:
                break

            if isinstance(ptr, dict):
                if left in ptr:
                    ptr = unlazy(ptr.get(left))
                    continue

            if isinstance(ptr, (list, tuple)):
                left = int(left)
                if left < len(ptr):
                    ptr = unlazy(ptr[left])
                    continue

            raise ValueError('Enclosing object {0} doesn\'t exist'.format(left))

        if isinstance(ptr, dict):
            del ptr[left]
            return

    del obj[int(left)]


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
    reverse = params.pop('reverse', False)
    postprocess = params.pop('callback', None)
    select = params.pop('select', None)
    exclude = params.pop('exclude', None)
    stream = params.pop('stream', False)
    result = iter(obj)

    def search(data):
        for i in data:
            if matches(i, *rules):
                yield i

    if rules:
        result = search(result)

    if exclude:
        def exclude_fn(fn, obj):
            obj = fn(obj) if fn else obj

            if isinstance(exclude, (list, tuple)):
                for i in exclude:
                    delete(obj, i)

            if isinstance(exclude, str):
                delete(obj, exclude)

            return obj

        before_exclude = postprocess
        postprocess = lambda o: exclude_fn(before_exclude, o)

    if select:
        def select_fn(fn, obj):
            obj = fn(obj) if fn else obj

            if isinstance(select, (list, tuple)):
                return [get(obj, i) for i in select]

            if isinstance(select, str):
                return get(obj, select)

        before_select = postprocess
        postprocess = lambda o: select_fn(before_select, o)

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
                result = sorted(result, key=lambda x: get(x, key), reverse=reverse)
            result = iter(result)

    if offset:
        result = iter(list(result)[offset:])

    if limit:
        result = itertools.islice(result, 0, limit)

    if reverse:
        result = reversed(list(result))

    if postprocess:
        result = filter_and_map(postprocess, result)

    if single:
        return next(result, None)

    if count:
        return len(list(result))

    return result if stream else list(result)
