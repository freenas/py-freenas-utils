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


def use_freenas(sdist, keyword, value):

    assert keyword == 'use_freenas'

    sdist.version = get_version()
