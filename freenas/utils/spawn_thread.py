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

import threading
import logging


def gevent_monkey_patched():
    try:
        from gevent import monkey
    except ImportError:
        return False
    else:
        return bool(monkey.saved)


def wrapper(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except:
        logging.exception('Exception in thread {0}'.format(threading.current_thread().name))
        raise


if not gevent_monkey_patched():
    from concurrent.futures import ThreadPoolExecutor
    _thread_pool = ThreadPoolExecutor(10)
    _gevent = False
else:
    import gevent
    _gevent = True


def spawn_thread(*args, **kwargs):
    if _gevent:
        kwargs.pop('threadpool', None)
        return gevent.spawn(*args, **kwargs)

    if kwargs.pop('threadpool', None):
        return _thread_pool.submit(wrapper, *args, **kwargs)

    t = threading.Thread(target=wrapper, args=args, daemon=True)
    t.start()
    return t


def kill_thread(td):
    if not _gevent:
        raise RuntimeError('Unkillable thread')

    gevent.kill(td, block=False)
