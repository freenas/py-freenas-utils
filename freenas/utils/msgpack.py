#
# Copyright 2017 iXsystems, Inc.
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

import enum
import uuid
import re
from datetime import datetime
from dateutil.parser import parse
from msgpack import ExtType


class ExtTypes(enum.IntEnum):
    UUID = 1
    DATETIME = 2
    REGEX = 3


def default(obj):
    if type(obj) is uuid.UUID:
        return ExtType(ExtTypes.UUID, obj.bytes)

    if type(obj) is datetime:
        return ExtType(ExtTypes.DATETIME, str(obj).encode('utf-8'))

    if type(obj) is re._pattern_type:
        return ExtType(ExtTypes.REGEX, obj.pattern.encode('utf-8'))

    if type(obj) is set:
        return list(obj)

    if hasattr(obj, '__getstate__'):
        return obj.__getstate__()

    return str(obj)


def ext_hook(code, data):
    if code == ExtTypes.UUID:
        return uuid.UUID(bytes=data)

    if code == ExtTypes.DATETIME:
        return parse(data.decode('utf-8'))

    if code == ExtTypes.REGEX:
        return re.compile(data.decode('utf-8'))
