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

from datetime import timedelta
import logging
import logging.handlers
import copy


LOGGING_FORMAT = '%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s'


def first_or_default(f, iterable, default=None):
    i = list(filter(f, iterable))
    if i:
        return i[0]

    return default


def exclude(d, *keys):
    return {k: v for k, v in list(d.items()) if k not in keys}


def include(d, *keys):
    return {k: v for k, v in list(d.items()) if k in keys}


def extend(d, d2):
    ret = copy.copy(d)
    ret.update(d2)
    return ret


def normalize(d, d2):
    for k, v in list(d2.items()):
        d.setdefault(k, v)


def force_none(v):
    if not v:
        return None

    return v


def materialized_paths_to_tree(lst, separator='.'):
    result = {'children': {}, 'path': []}

    def add(parent, path):
        if not path:
            return

        p = path.pop(0)
        c = parent['children'].get(p)
        if not c:
            c = {'children': {}, 'path': parent['path'] + [p], 'label': p}
            parent['children'][p] = c

        add(c, path)

    for i in lst:
        path = i.split(separator)
        add(result, path)

    return result


def to_timedelta(time_val):
    num = int(time_val[:-1])

    if time_val.endswith('s'):
        return timedelta(seconds=num)

    elif time_val.endswith('m'):
        return timedelta(minutes=num)

    elif time_val.endswith('h'):
        return timedelta(hours=num)

    elif time_val.endswith('d'):
        return timedelta(days=num)

    elif time_val.endswith('y'):
        return timedelta(days=(365 * num))


def configure_logging(path, level):
    logging.basicConfig(
        level=logging.getLevelName(level),
        format=LOGGING_FORMAT,
    )

    if path:
        handler = FaultTolerantLogHandler(path)
        handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        logging.root.removeHandler(logging.root.handlers[0])
        logging.root.addHandler(handler)


class FaultTolerantLogHandler(logging.handlers.WatchedFileHandler):
    def emit(self, record):
        try:
            logging.handlers.WatchedFileHandler.emit(self, record)
        except IOError:
            pass
