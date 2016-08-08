"""
pgoapi - Pokemon Go API
Copyright (c) 2016 tjado <https://github.com/tejado>
Modifications Copyright (c) 2016 Brad Smith <https://github.com/infinitewarp>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
OR OTHER DEALINGS IN THE SOFTWARE.

Author: tjado <https://github.com/tejado>
Modifications by: Brad Smith <https://github.com/infinitewarp>
"""

import struct
import time
from binascii import unhexlify
from bisect import bisect_left

import xxhash


def f2i(float):
    return struct.unpack('<Q', struct.pack('<d', float))[0]


def f2h(float):
    return hex(struct.unpack('<Q', struct.pack('<d', float))[0])


def h2f(hex):
    return struct.unpack('<d', struct.pack('<Q', int(hex, 16)))[0]


def to_camel_case(value):
    def camelcase():
        while True:
            yield str.capitalize

    c = camelcase()
    return "".join(next(c)(x) if x else '_' for x in value.split("_"))


def all_in(candidates, sequence):
    for element in candidates:
        if element not in sequence:
            return False
    return True


def take_closest(my_number, my_list):
    """
    Assumes my_list is sorted. Returns closest value to my_number.

    If two numbers are equally close, return the smallest number.
    """
    pos = bisect_left(my_list, my_number)
    if pos == 0:
        return my_list[0]
    if pos == len(my_list):
        return my_list[-1]
    before = my_list[pos - 1]
    after = my_list[pos]
    if after - my_number < my_number - before:
        return after
    else:
        return before


def get_time(ms=False):
    if ms:
        return int(round(time.time() * 1000))
    else:
        return int(round(time.time()))


def get_format_time_diff(low, high, ms=True):
    diff = (high - low)
    if ms:
        m, s = divmod(diff / 1000, 60)
    else:
        m, s = divmod(diff, 60)
    h, m = divmod(m, 60)

    return (h, m, s)


def parse_api_endpoint(api_url):
    if not api_url.startswith("https"):
        api_url = 'https://{}/rpc'.format(api_url)

    return api_url


class Rand48(object):
    def __init__(self, seed):
        self.n = seed

    def seed(self, seed):
        self.n = seed

    def srand(self, seed):
        self.n = (seed << 16) + 0x330e

    def next(self):
        self.n = (25214903917 * self.n + 11) & (2**48 - 1)
        return self.n

    def drand(self):
        return self.next() / 2**48

    def lrand(self):
        return self.next() >> 17

    def mrand(self):
        n = self.next() >> 16
        if n & (1 << 31):
            n -= 1 << 32
        return n


def long_to_bytes(val, endianness='big'):
    """
    Use :ref:`string formatting` and :func:`~binascii.unhexlify` to
    convert ``val``, a :func:`long`, to a byte :func:`str`.

    :param long val: The value to pack

    :param str endianness: The endianness of the result. ``'big'`` for
      big-endian, ``'little'`` for little-endian.

    If you want byte- and word-ordering to differ, you're on your own.

    Using :ref:`string formatting` lets us use Python's C innards.
    """
    # one (1) hex digit per four (4) bits
    width = val.bit_length()

    # unhexlify wants an even multiple of eight (8) bits, but we don't
    # want more digits than we need (hence the ternary-ish 'or')
    width += 8 - ((width % 8) or 8)

    # format width specifier: four (4) bits per hex digit
    fmt = '%%0%dx' % (width // 4)

    # prepend zero (0) to the width, to zero-pad the output
    s = unhexlify(fmt % val)

    if endianness == 'little':
        # see http://stackoverflow.com/a/931095/309233
        s = s[::-1]

    return s


def generateLocation1(authticket, lat, lng, alt):
    firstHash = xxhash.xxh32(authticket, seed=0x1B845238).intdigest()
    locationBytes = d2h(lat) + d2h(lng) + d2h(alt)
    if not alt:
        alt = "\x00\x00\x00\x00\x00\x00\x00\x00"
    return xxhash.xxh32(locationBytes, seed=firstHash).intdigest()


def generateLocation2(lat, lng, alt):
    locationBytes = d2h(lat) + d2h(lng) + d2h(alt)
    if not alt:
        alt = "\x00\x00\x00\x00\x00\x00\x00\x00"
    return xxhash.xxh32(locationBytes, seed=0x1B845238).intdigest()  # Hash of location using static seed 0x1B845238


def generateRequestHash(authticket, request):
    firstHash = xxhash.xxh64(authticket, seed=0x1B845238).intdigest()
    return xxhash.xxh64(request, seed=firstHash).intdigest()


def d2h(f):
    hex = f2h(f)[2:].replace('L', '')
    hex = ("0" * (len(hex) % 2)) + hex
    return hex.decode("hex")
