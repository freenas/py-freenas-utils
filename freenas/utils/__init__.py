#
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
import crypt
import random
import string
import binascii
import hashlib
import threading
import traceback
import contextlib
from datetime import timedelta
from string import Template
from freenas.utils.trace_logger import TraceLogger

try:
    from bsd import fnmatch
except ImportError:
    from fnmatch import fnmatch

ESCAPE_SEQUENCE_RE = re.compile(r'''
    ( \\U........      # 8-digit hex escapes
    | \\u....          # 4-digit hex escapes
    | \\x..            # 2-digit hex escapes
    | \\[0-7]{1,3}     # Octal escapes
    | \\N\{[^}]+\}     # Unicode characters by name
    | \\[\\'"abfnrtv]  # Single-character escapes
    )''', re.UNICODE | re.VERBOSE)

LOGGING_FORMAT = '%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)d %(message)s'

COUNTRY_CODES = {
    "AFGHANISTAN": "AF", "ALAND ISLANDS": "AX", "ALBANIA": "AL", "ALGERIA": "DZ", "AMERICAN SAMOA": "AS",
    "ANDORRA": "AD", "ANGOLA": "AO", "ANGUILLA": "AI", "ANTARCTICA": "AQ", "ANTIGUA AND BARBUDA": "AG",
    "ARGENTINA": "AR", "ARMENIA": "AM", "ARUBA": "AW", "AUSTRALIA": "AU", "AUSTRIA": "AT", "AZERBAIJAN": "AZ",
    "BAHAMAS": "BS", "BAHRAIN": "BH", "BANGLADESH": "BD", "BARBADOS": "BB", "BELARUS": "BY", "BELGIUM": "BE",
    "BELIZE": "BZ", "BENIN": "BJ", "BERMUDA": "BM", "BHUTAN": "BT", "BOLIVIA, PLURINATIONAL STATE OF": "BO",
    "BOSNIA AND HERZEGOVINA": "BA", "BOTSWANA": "BW", "BOUVET ISLAND": "BV", "BRAZIL": "BR",
    "BRITISH INDIAN OCEAN TERRITORY": "IO", "BRUNEI DARUSSALAM": "BN", "BULGARIA": "BG", "BURKINA FASO": "BF",
    "BURUNDI": "BI", "CAMBODIA": "KH", "CAMEROON": "CM", "CANADA": "CA", "CAPE VERDE": "CV", "CAYMAN ISLANDS": "KY",
    "CENTRAL AFRICAN REPUBLIC": "CF", "CHAD": "TD", "CHILE": "CL", "CHINA": "CN", "CHRISTMAS ISLAND": "CX",
    "COCOS (KEELING) ISLANDS": "CC", "COLOMBIA": "CO", "COMOROS": "KM", "CONGO": "CG",
    "CONGO, THE DEMOCRATIC REPUBLIC OF THE": "CD", "COOK ISLANDS": "CK", "COSTA RICA": "CR", "COTE D'IVOIRE": "CI",
    "CROATIA": "HR", "CUBA": "CU", "CYPRUS": "CY", "CZECH REPUBLIC": "CZ", "DENMARK": "DK", "DJIBOUTI": "DJ",
    "DOMINICA": "DM", "DOMINICAN REPUBLIC": "DO", "ECUADOR": "EC", "EGYPT": "EG", "EL SALVADOR": "SV",
    "EQUATORIAL GUINEA": "GQ", "ERITREA": "ER", "ESTONIA": "EE", "ETHIOPIA": "ET", "FALKLAND ISLANDS (MALVINAS)": "FK",
    "FAROE ISLANDS": "FO", "FIJI": "FJ", "FINLAND": "FI", "FRANCE": "FR", "FRENCH GUIANA": "GF",
    "FRENCH POLYNESIA": "PF", "FRENCH SOUTHERN TERRITORIES": "TF", "GABON": "GA", "GAMBIA": "GM", "GEORGIA": "GE",
    "GERMANY": "DE", "GHANA": "GH", "GIBRALTAR": "GI", "GREECE": "GR", "GREENLAND": "GL", "GRENADA": "GD",
    "GUADELOUPE": "GP", "GUAM": "GU", "GUATEMALA": "GT", "GUERNSEY": "GG", "GUINEA": "GN", "GUINEA-BISSAU": "GW",
    "GUYANA": "GY", "HAITI": "HT", "HEARD ISLAND AND MCDONALD ISLANDS": "HM", "HOLY SEE (VATICAN CITY STATE)": "VA",
    "HONDURAS": "HN", "HONG KONG": "HK", "HUNGARY": "HU", "ICELAND": "IS", "INDIA": "IN", "INDONESIA": "ID",
    "IRAN, ISLAMIC REPUBLIC OF": "IR", "IRAQ": "IQ", "IRELAND": "IE", "ISLE OF MAN": "IM", "ISRAEL": "IL",
    "ITALY": "IT", "JAMAICA": "JM", "JAPAN": "JP", "JERSEY": "JE", "JORDAN": "JO", "KAZAKHSTAN": "KZ", "KENYA": "KE",
    "KIRIBATI": "KI", "KOREA, DEMOCRATIC PEOPLE'S REPUBLIC OF": "KP", "KOREA, REPUBLIC OF": "KR", "KUWAIT": "KW",
    "KYRGYZSTAN": "KG", "LAO PEOPLE'S DEMOCRATIC REPUBLIC": "LA", "LATVIA": "LV", "LEBANON": "LB", "LESOTHO": "LS",
    "LIBERIA": "LR", "LIBYAN ARAB JAMAHIRIYA": "LY", "LIECHTENSTEIN": "LI", "LITHUANIA": "LT", "LUXEMBOURG": "LU",
    "MACAO": "MO", "MACEDONIA, THE FORMER YUGOSLAV REPUBLIC OF": "MK", "MADAGASCAR": "MG", "MALAWI": "MW",
    "MALAYSIA": "MY", "MALDIVES": "MV", "MALI": "ML", "MALTA": "MT", "MARSHALL ISLANDS": "MH", "MARTINIQUE": "MQ",
    "MAURITANIA": "MR", "MAURITIUS": "MU", "MAYOTTE": "YT", "MEXICO": "MX", "MICRONESIA, FEDERATED STATES OF": "FM",
    "MOLDOVA, REPUBLIC OF": "MD", "MONACO": "MC", "MONGOLIA": "MN", "MONTENEGRO": "ME", "MONTSERRAT": "MS",
    "MOROCCO": "MA", "MOZAMBIQUE": "MZ", "MYANMAR": "MM", "NAMIBIA": "NA", "NAURU": "NR", "NEPAL": "NP",
    "NETHERLANDS": "NL", "NETHERLANDS ANTILLES": "AN", "NEW CALEDONIA": "NC", "NEW ZEALAND": "NZ", "NICARAGUA": "NI",
    "NIGER": "NE", "NIGERIA": "NG", "NIUE": "NU", "NORFOLK ISLAND": "NF", "NORTHERN MARIANA ISLANDS": "MP",
    "NORWAY": "NO", "OMAN": "OM", "PAKISTAN": "PK", "PALAU": "PW", "PALESTINIAN TERRITORY, OCCUPIED": "PS",
    "PANAMA": "PA", "PAPUA NEW GUINEA": "PG", "PARAGUAY": "PY", "PERU": "PE", "PHILIPPINES": "PH", "PITCAIRN": "PN",
    "POLAND": "PL", "PORTUGAL": "PT", "PUERTO RICO": "PR", "QATAR": "QA", "REUNION": "RE", "ROMANIA": "RO",
    "RUSSIAN FEDERATION": "RU", "RWANDA": "RW", "SAINT BARTHELEMY": "BL",
    "SAINT HELENA, ASCENSION AND TRISTAN DA CUNHA": "SH", "SAINT KITTS AND NEVIS": "KN", "SAINT LUCIA": "LC",
    "SAINT MARTIN": "MF", "SAINT PIERRE AND MIQUELON": "PM", "SAINT VINCENT AND THE GRENADINES": "VC", "SAMOA": "WS",
    "SAN MARINO": "SM", "SAO TOME AND PRINCIPE": "ST", "SAUDI ARABIA": "SA", "SENEGAL": "SN", "SERBIA": "RS",
    "SEYCHELLES": "SC", "SIERRA LEONE": "SL", "SINGAPORE": "SG", "SLOVAKIA": "SK", "SLOVENIA": "SI",
    "SOLOMON ISLANDS": "SB", "SOMALIA": "SO", "SOUTH AFRICA": "ZA",
    "SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS": "GS", "SPAIN": "ES", "SRI LANKA": "LK", "SUDAN": "SD",
    "SURINAME": "SR", "SVALBARD AND JAN MAYEN": "SJ", "SWAZILAND": "SZ", "SWEDEN": "SE", "SWITZERLAND": "CH",
    "SYRIAN ARAB REPUBLIC": "SY", "TAIWAN, PROVINCE OF CHINA": "TW", "TAJIKISTAN": "TJ",
    "TANZANIA, UNITED REPUBLIC OF": "TZ", "THAILAND": "TH", "TIMOR-LESTE": "TL", "TOGO": "TG", "TOKELAU": "TK",
    "TONGA": "TO", "TRINIDAD AND TOBAGO": "TT", "TUNISIA": "TN", "TURKEY": "TR", "TURKMENISTAN": "TM",
    "TURKS AND CAICOS ISLANDS": "TC", "TUVALU": "TV", "UGANDA": "UG", "UKRAINE": "UA", "UNITED ARAB EMIRATES": "AE",
    "UNITED KINGDOM": "GB", "UNITED STATES": "US", "UNITED STATES MINOR OUTLYING ISLANDS": "UM", "URUGUAY": "UY",
    "UZBEKISTAN": "UZ", "VANUATU": "VU", "VENEZUELA, BOLIVARIAN REPUBLIC OF": "VE", "VIET NAM": "VN",
    "VIRGIN ISLANDS, BRITISH": "VG", "VIRGIN ISLANDS, U.S.": "VI", "WALLIS AND FUTUNA": "WF", "WESTERN SAHARA": "EH",
    "YEMEN": "YE", "ZAMBIA": "ZM", "ZIMBABWE": "ZW"
}


def first_or_default(f, iterable, default=None):
    for i in filter(f, iterable):
        return i
    return default


def best_match(items, name, key=None, default=None):
    def try_match(item):
        pat = key(item) if key else item
        return fnmatch(name, pat)

    def get_length(item):
        i = key(item) if key else item
        return len(i)

    matches = list(filter(try_match, items))
    if not matches:
        return default

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

    return d


def list_startswith(l1, l2):
    return l1[:len(l2)] == l2


def force_none(v):
    if not v:
        return None

    return v


def yesno_to_bool(v):
    if v == 'yes':
        return True

    return False


def bool_to_truefalse(v):
    if v:
        return 'true'

    return 'false'


def truefalse_to_bool(v):
    if v == 'true':
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


def remove_unchanged(d1, d2):
    for i in list(d1):
        if i not in d2:
            continue

        if d1[i] == d2[i]:
            del d1[i]


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


def configure_logging(ident_or_path, level, file=False):
    from freenas.logd import LogdLogHandler

    logging.setLoggerClass(TraceLogger)
    logging.basicConfig(
        level=logging.getLevelName(level),
        format=LOGGING_FORMAT,
    )

    if file:
        handler = FaultTolerantLogHandler(ident_or_path)
        handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    else:
        handler = LogdLogHandler(ident=ident_or_path)

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
            '{0}.cpython-36.pyc'.format(os.path.basename(path).split('.', 1)[0])
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
    message = bytearray(length)
    view = memoryview(message)
    ancdata = []

    while done < length:
        try:
            nbytes, anc, _, _ = sock.recvmsg_into([view], anclength or 0)
        except InterruptedError:
            continue

        if nbytes == 0:
            return message[done:], ancdata

        done += nbytes
        ancdata += anc
        view = view[nbytes:]

    return message, ancdata


def in_directory(d1, d2):
    d1 = os.path.join(os.path.realpath(d1), '')
    d2 = os.path.join(os.path.realpath(d2), '')
    if d1 == d2:
        return True

    return os.path.commonprefix([d1, d2]) == d2


def is_ascii(s):
    return len(s) == len(s.encode())


def remove_non_printable(s):
    return ''.join(x for x in s if x in string.printable)


def sha256(fname, b_size=65536):
    hash_sha256 = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(b_size), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def crypted_password(cleartext):
    return crypt.crypt(cleartext, '$6$' + ''.join([
        random.choice(string.ascii_letters + string.digits) for _ in range(16)]))


def nt_password(cleartext):
    nthash = hashlib.new('md4', cleartext.encode('utf-16le')).digest()
    return binascii.hexlify(nthash).decode('utf-8').upper()


def serialize_traceback(tb):
    iter_tb = tb if isinstance(tb, (list, tuple)) else traceback.extract_tb(tb)
    return [
        {
            'filename': f[0],
            'lineno': f[1],
            'method': f[2],
            'code': f[3]
        }
        for f in iter_tb
    ]


def serialize_exception(exception, tb=None):
    return {
        'frames': tb or serialize_traceback(exception.__traceback__),
        'exception': {
            'class': exception.__class__.__name__,
            'message': str(exception)
        }
    }


class threadsafe_iterator(object):
    def __init__(self, it):
        self.it = it
        self.lock = threading.Lock()

    def __iter__(self):
        return self

    def __next__(self):
        with self.lock:
            return self.it.__next__()


@contextlib.contextmanager
def create_with_mode(path, mode):
    umask = os.umask(0)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
        with open(fd, 'w') as f:
            yield f
    finally:
        os.umask(umask)


class FaultTolerantLogHandler(logging.handlers.WatchedFileHandler):
    def emit(self, record):
        try:
            logging.handlers.WatchedFileHandler.emit(self, record)
        except IOError:
            pass


def human_readable_bytes(num, suffix=''):
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
