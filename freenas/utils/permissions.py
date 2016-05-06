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


def modes_to_oct(modes):
    modes = wrap(modes)
    result = 0

    if modes['user.read']:
        result &= stat.S_IRUSR

    if modes['user.write']:
        result &= stat.S_IWUSR

    if modes['user.execute']:
        result &= stat.S_IXUSR

    if modes['group.read']:
        result &= stat.S_IRGRP

    if modes['group.write']:
        result &= stat.S_IWGRP

    if modes['group.execute']:
        result &= stat.S_IXGRP

    if modes['others.read']:
        result &= stat.S_IROTH

    if modes['others.write']:
        result &= stat.S_IWOTH

    if modes['others.execute']:
        result &= stat.S_IXOTH

    return result


def get_type(st):
    if stat.S_ISDIR(st.st_mode):
        return 'DIRECTORY'

    elif stat.S_ISLNK(st.st_mode):
        return 'LINK'

    else:
        return 'FILE'
