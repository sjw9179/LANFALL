"""Bounded msgpack messages, version validation and partial TCP frame handling."""
import math
import struct
import msgpack
from game.config import MAGIC, VERSION

MAX_FRAME = 262144
MAX_UDP = 1400

def encode(kind, **fields):
    return msgpack.packb(dict(m=MAGIC, v=VERSION, t=kind, **fields), use_bin_type=True)

def decode(data):
    if not data or len(data) > MAX_FRAME:
        raise ValueError('Invalid packet size')
    try:
        p = msgpack.unpackb(data, raw=False, strict_map_key=True)
    except Exception as e:
        raise ValueError('Invalid message') from e
    if not isinstance(p, dict) or p.get('m') != MAGIC or p.get('v') != VERSION or not isinstance(p.get('t'), str):
        raise ValueError('Different game / protocol version')
    return p

def frame(kind, **fields):
    data = encode(kind, **fields)
    if len(data) > MAX_FRAME:
        raise ValueError('Message too large')
    return struct.pack('!I', len(data)) + data

class Framer:
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data):
        self.buffer.extend(data)
        result = []
        while len(self.buffer) >= 4:
            size = struct.unpack_from('!I', self.buffer)[0]
            if size < 1 or size > MAX_FRAME:
                raise ValueError('Invalid frame length')
            if len(self.buffer) < size + 4:
                break
            result.append(decode(bytes(self.buffer[4:4+size])))
            del self.buffer[:4+size]
        return result

def finite_vector(value, length=3, limit=100000):
    return isinstance(value, (list, tuple)) and len(value) == length and all(type(v) in (int,float) and math.isfinite(v) and abs(v) <= limit for v in value)
