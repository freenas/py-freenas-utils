#+
# Copyright 2016 iXsystems, Inc.
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
from freenas.utils.query import wrap
import stat
import re


def modes_to_oct(modes):
    modes = wrap(modes)
    result = 0

    if modes['user.read']:
        result |= stat.S_IRUSR

    if modes['user.write']:
        result |= stat.S_IWUSR

    if modes['user.execute']:
        result |= stat.S_IXUSR

    if modes['group.read']:
        result |= stat.S_IRGRP

    if modes['group.write']:
        result |= stat.S_IWGRP

    if modes['group.execute']:
        result |= stat.S_IXGRP

    if modes['others.read']:
        result |= stat.S_IROTH

    if modes['others.write']:
        result |= stat.S_IWOTH

    if modes['others.execute']:
        result |= stat.S_IXOTH

    return result


def get_type(st):
    if stat.S_ISDIR(st.st_mode):
        return 'DIRECTORY'

    elif stat.S_ISLNK(st.st_mode):
        return 'LINK'

    else:
        return 'FILE'


def perm_to_oct_string(perm_obj):
    def to_oct(val):
        return oct(val).split('o')[-1].zfill(3)

    value = perm_obj.get('value')
    if value:
        return to_oct(value)
    return to_oct(modes_to_oct(perm_obj))


def get_unix_permissions(value):
    return {
        'value': value,
        'user': {
            'read': bool(value & stat.S_IRUSR),
            'write': bool(value & stat.S_IWUSR),
            'execute': bool(value & stat.S_IXUSR)
        },
        'group': {
            'read': bool(value & stat.S_IRGRP),
            'write': bool(value & stat.S_IWGRP),
            'execute': bool(value & stat.S_IXGRP)
        },
        'others': {
            'read': bool(value & stat.S_IROTH),
            'write': bool(value & stat.S_IWOTH),
            'execute': bool(value & stat.S_IXOTH)
        },
    }


def get_integer(perm_obj):
    value = perm_obj.get('value')
    if value:
        return int(value)
    else:
        return modes_to_oct(perm_obj)


def int_to_string(value):
    result = ''
    for i in range(0, 9):
        if value & (1 << i):
            if not i % 3:
                result += 'x'
                continue
            if not i % 2:
                result += 'r'
                continue
            result += 'w'
        else:
            result += '-'

    return result[::-1]


def string_to_int(value):
    if not re.match(r'[r-][w-][x-][r-][w-][x-][r-][w-][x-]', value):
        raise ValueError('Invalid permissions format')
    result = 0
    value = value[::-1]
    for idx, i in enumerate(value):
        if i != '-':
            result |= 1 << idx

    return result
