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

import platform
import signal
import threading
from ctypes import CDLL, Structure, sizeof, c_ulong, pointer, util as libcutil

SIG_BLOCK = 1
SIG_UNBLOCK = 2
SIG_SETMASK = 3
SIGSET_NWORDS = int(1024 / (8 * sizeof(c_ulong)))
THREAD_MASK_ENABLE = True if platform.system() in ('FreeBSD', 'Darwin', 'Linux') else False
LIBC = CDLL(libcutil.find_library('c')) if THREAD_MASK_ENABLE else None


class SIGSET(Structure):
    _fields_ = [
         ('val', c_ulong * SIGSET_NWORDS)
    ]

pointer_old_sigset = pointer(SIGSET())


class MaskedThread(threading.Thread):
    """
    MaskedThread is a subclass of threading.Thread that
    provides fine grained control over the signals that
    are blocked in the spawned thread.
    """

    def __init__(self, *args, **kwargs):
        """
        Mask signals using 'sigmask' (list).
        If this list is empty then it defaults to blocking all signals in the spawned thread.
        The rest of the args the same as were for threading.Thread class's constructor.
        Note: This subclass will only block signals for unix and/or any posix-compliant systems
        """
        self.sigmask = kwargs.pop('sigmask', range(1, signal.NSIG))
        set_daemon = kwargs.pop('daemon', False)
        super(MaskedThread, self).__init__(*args, **kwargs)
        self.setDaemon(set_daemon)

    def run(self):
        if THREAD_MASK_ENABLE and LIBC is not None:
            sigset = SIGSET()
            LIBC.sigemptyset(pointer(sigset))
            for i in self.sigmask:
                LIBC.sigaddset(pointer(sigset), i)
            LIBC.pthread_sigmask(SIG_BLOCK, pointer(sigset), pointer_old_sigset)
        super(MaskedThread, self).run()
