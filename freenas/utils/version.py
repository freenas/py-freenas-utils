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

import os
import re
import sys


def get_version(ver=None):
    verfile = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'version.txt')
    if ver is None:
        ver = os.environ.get('VERSION')
    if ver:
        version = ver.split('-', 1)[0]
        prerelease = None
        reg = re.search(r'(ALPHA|BETA|RC)(\d+)?', ver, re.I)
        if reg:
            stage = reg.group(1).lower()
            if stage == 'alpha':
                prerelease = 'a'
            elif stage == 'beta':
                prerelease = 'b'
            elif stage == 'rc':
                prerelease = 'rc'
            prerelease += reg.group(2) if reg.group(2) else '1'
        final = '{0}{1}'.format(version, prerelease if prerelease else '')
        with open(verfile, 'w') as f:
            return f.write(final)
        return final
    elif os.path.exists(verfile):
        # If a version.txt file exists, use that as version
        with open(verfile, 'r') as f:
            return f.read().strip('\n').strip('\r')
    else:
        raise ValueError("VERSION could not be parsed")


def use_freenas(dist, keyword, value):
    assert keyword == 'use_freenas'

    version = get_version()
    dist.version = version
    dist.metadata.version = version
