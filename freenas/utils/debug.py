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

import errno
import sys
import gc
import traceback
import tracemalloc
from freenas.dispatcher.rpc import RpcService, RpcException, private


sys.path.append('/usr/local/lib/dispatcher/pydev')


class DebugService(RpcService):
    def __init__(self, gevent=False, builtins=None):
        self.gevent = gevent
        self.backdoor_locals = builtins or {}
        self.backdoor_server = None

    @private
    def attach(self, host, port):
        import pydevd
        pydevd.settrace(host, port=port, stdoutToServer=True, stderrToServer=True)

    @private
    def detach(self):
        import pydevd
        pydevd.stoptrace()

    @private
    def dump_stacks(self):
        if self.gevent:
            from greenlet import greenlet

            # If greenlet is present, let's dump each greenlet stack
            dump = []
            for ob in gc.get_objects():
                if not isinstance(ob, greenlet):
                    continue
                if not ob:
                    continue   # not running anymore or not started

                dump.append(''.join(traceback.format_stack(ob.gr_frame)))

            return dump
        else:
            dump = []
            for frame in list(sys._current_frames().values()):
                dump.append(''.join(traceback.format_stack(frame)))

            return dump

    @private
    def start_backdoor(self):
        if not self.gevent:
            raise RpcException(errno.ENOTSUP, 'Not supported')

        from gevent import spawn
        from gevent.backdoor import BackdoorServer
        self.backdoor_server = BackdoorServer(
            ('127.0.0.1', 9999),
            banner='DebugService backdoor server',
            locals=self.backdoor_locals
        )

        spawn(self.backdoor_server.serve_forever())

    @private
    def stop_backdoor(self):
        if not self.gevent:
            raise RpcException(errno.ENOTSUP, 'Not supported')

        if self.backdoor_server:
            self.backdoor_server.close()
            self.backdoor_server = None

    @private
    def start_tracemalloc(self):
        tracemalloc.start()

    @private
    def stop_tracemalloc(self):
        tracemalloc.stop()

    @private
    def snapshot_tracemalloc(self):
        snap = tracemalloc.take_snapshot()
        return [str(i) for i in snap.statistics('lineno')[:100]]
