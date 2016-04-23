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

import os
import re
import codecs
import logging
import logging.handlers
import copy
import fnmatch
from datetime import timedelta
from string import Template


ESCAPE_SEQUENCE_RE = re.compile(r'''
    ( \\U........      # 8-digit hex escapes
    | \\u....          # 4-digit hex escapes
    | \\x..            # 2-digit hex escapes
    | \\[0-7]{1,3}     # Octal escapes
    | \\N\{[^}]+\}     # Unicode characters by name
    | \\[\\'"abfnrtv]  # Single-character escapes
    )''', re.UNICODE | re.VERBOSE)

LOGGING_FORMAT = '%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s'


def first_or_default(f, iterable, default=None):
    i = list(filter(f, iterable))
    if i:
        return i[0]

    return default


def best_match(items, name, key=None, default=None):
    def try_match(item):
        pat = key(item) if key else item
        return fnmatch.fnmatch(name, pat)

    def get_length(item):
        i = key(item) if key else i
        return len(i)

    matches = filter(try_match, items)
    if not matches:
        return None

    return max(matches, key=get_length)


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


def yesno_to_bool(v):
    if v == 'yes':
        return True

    return False


def chunks(arr, size):
    for i in range(0, len(arr), size):
        yield arr[i:i+size]


def iter_chunked(iterable, chunksize):
    ret = []
    try:
        while True:
            ret.clear()
            for i in range(chunksize):
                ret.append(next(iterable))

            yield ret.copy()
    except StopIteration:
        if ret:
            yield ret.copy()


def deep_update(source, overrides):
    for key, value in overrides.items():
        if isinstance(value, dict) and value:
            returned = deep_update(source.get(key, {}), value)
            source[key] = returned
        else:
            source[key] = overrides[key]
    return source


def decode_escapes(s):
    def decode_match(match):
        return codecs.decode(match.group(0), 'unicode-escape')

    return ESCAPE_SEQUENCE_RE.sub(decode_match, s)


def process_template(input, output, **kwargs):
    with open(input, 'r') as f:
        t = Template(f.read())

        with open(output, 'w') as dest:
            dest.write(t.substitute(**kwargs))


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


def load_module_from_file(name, path):
    import importlib.machinery

    _, ext = os.path.splitext(path)

    if ext == '.py':
        loader = importlib.machinery.SourceFileLoader(name, path)
        pyc_path = os.path.join(
            os.path.dirname(path),
            '__pycache__',
            '{0}.cpython-34.pyc'.format(os.path.basename(path).split('.', 1)[0])
        )
        if os.path.isfile(pyc_path):
            if os.path.getmtime(pyc_path) > os.path.getmtime(path):
                loader = importlib.machinery.SourcelessFileLoader(name, pyc_path)
    elif ext == '.pyc':
        loader = importlib.machinery.SourcelessFileLoader(name, path)
    elif ext == '.so':
        loader = importlib.machinery.ExtensionFileLoader(name, path)
    else:
        raise ValueError('Invalid module file extension')

    return loader.load_module()


def xsendmsg(sock, buffer, ancdata=None):
    done = 0
    while done < len(buffer):
        try:
            done += sock.sendmsg([buffer[done:]], ancdata or [])
        except InterruptedError:
            continue

        ancdata = None


def xrecvmsg(sock, length, anclength=None):
    done = 0
    message = b''
    ancdata = []

    while done < length:
        try:
            buf, anc, _, _ = sock.recvmsg(length - done, anclength or 0)
        except InterruptedError:
            continue

        if buf == b'':
            return message, ancdata

        done += len(buf)
        message += buf
        ancdata += anc

    return message, ancdata


class FaultTolerantLogHandler(logging.handlers.WatchedFileHandler):
    def emit(self, record):
        try:
            logging.handlers.WatchedFileHandler.emit(self, record)
        except IOError:
            pass


class SmartEventSet(object):
    """
    A small class to enable context manager based event sets.
    i.e. using event set/unset via a 'with' statement.

    Usage:
    with SmartEventSet(threading.Event()):
        do_your_code

    What this will do is that it will set the event supplied to it upon enetering the context
    and upon exit it will clear the event.

    Thus this is equivalent of doing the following:
        evt = threading.Event()
        evt.set()
        your_code_snippet_here
        evt.clear()
    """

    def __init__(self, evt):
        self.evt = evt

    def __enter__(self):
        self.evt.set()
        # Return event just for the purposes of the `with SmartEventSet(foo) as bar`
        return self.evt

    def __exit__(self, type, value, traceback):
        self.evt.clear()
