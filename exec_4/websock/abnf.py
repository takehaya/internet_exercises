import numpy
import threading
import struct
from util_http import *


# closing frame status codes.
STATUS_NORMAL = 1000
STATUS_GOING_AWAY = 1001
STATUS_PROTOCOL_ERROR = 1002
STATUS_UNSUPPORTED_DATA_TYPE = 1003
STATUS_STATUS_NOT_AVAILABLE = 1005
STATUS_ABNORMAL_CLOSED = 1006
STATUS_INVALID_PAYLOAD = 1007
STATUS_POLICY_VIOLATION = 1008
STATUS_MESSAGE_TOO_BIG = 1009
STATUS_INVALID_EXTENSION = 1010
STATUS_UNEXPECTED_CONDITION = 1011
STATUS_BAD_GATEWAY = 1014
STATUS_TLS_HANDSHAKE_ERROR = 1015


class ABNF(object):
    """
    ABNF frame class.
    see http://tools.ietf.org/html/rfc5234
    and http://tools.ietf.org/html/rfc6455#section-5.2
    """

    # operation code values.
    OPCODE_CONT = 0x0
    OPCODE_TEXT = 0x1
    OPCODE_BINARY = 0x2
    OPCODE_CLOSE = 0x8
    OPCODE_PING = 0x9
    OPCODE_PONG = 0xa

    # available operation code value tuple
    OPCODES = (OPCODE_CONT, OPCODE_TEXT, OPCODE_BINARY, OPCODE_CLOSE,
               OPCODE_PING, OPCODE_PONG)

    # opcode human readable string
    OPCODE_MAP = {
        OPCODE_CONT: "cont",
        OPCODE_TEXT: "text",
        OPCODE_BINARY: "binary",
        OPCODE_CLOSE: "close",
        OPCODE_PING: "ping",
        OPCODE_PONG: "pong"
    }

    # data length threshold.
    LENGTH_7 = 0x7e
    LENGTH_16 = 1 << 16
    LENGTH_63 = 1 << 63

    def __init__(self, fin=0, rsv1=0, rsv2=0, rsv3=0,
                 opcode=OPCODE_TEXT, mask=1, data=""):
        """
        Constructor for ABNF.
        please check RFC for arguments.
        """
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3
        self.opcode = opcode
        self.mask = mask
        if data is None:
            data = ""
        self.data = data
        self.get_mask_key = os.urandom
    
    def formating(self):
        if any(x not in (0, 1) for x in [self.fin, self.rsv1, self.rsv2, self.rsv3]):
            raise ValueError("not 0 or 1")
        if self.opcode not in ABNF.OPCODES:
            raise ValueError("Invalid OPCODE")   
        length = len(self.data)
        if length >= ABNF.LENGTH_63:
            raise ValueError("data is too long")
        frame_header = (self.fin << 7| self.rsv1 << 6 | self.rsv2 << 5 | self.rsv3 << 4| self.opcode).to_bytes(1, byteorder='big')
        if length < ABNF.LENGTH_7:
            frame_header += (self.mask << 7 | length).to_bytes(1, byteorder='big')
        elif length < ABNF.LENGTH_16:
            # 0x7e == 126
            # ペイロードの長さが16bitよりも長いのでそのときはpayload lenを126にして
            # extend payloadを利用すること示さなくてはいけない。
            #  If 126, the following 2 bytes interpreted as a 16-bit unsigned integer are the payload length.
            frame_header += (self.mask << 7| 0x7e).to_bytes(1, byteorder='big')
            frame_header += struct.pack("!H", length)
        else:
            # 0x7f == 127
            # ペイロードの長さが16bitよりも長いのでそのときはpayload lenを127にして
            # extend payloadと extend payload length conttinuedを利用すること示さなくてはいけない。
            # If 127, the following 8 bytes interpreted as a 64-bit unsigned integer (the most significant bit MUST be 0)
            frame_header += (self.mask << 7 | 0x7f).to_bytes(1, byteorder='big')
            frame_header += struct.pack("!Q", length)
    
        if not self.mask:
            return frame_header + self.data
        else:
            mask_key = self.get_mask_key(4)
            ms = self._get_masked(mask_key)

            return frame_header + ms
    
    def _get_masked(self, mask_key):
        s = ABNF.mask(mask_key, self.data)
        # mask_key = mask_key.hex()
        return mask_key + s

    @staticmethod
    def mask(mask_key, data):
        if data is None:
            data=""
        
        origlen = len(data)
        _mask_key = mask_key[3] << 24 | mask_key[2] << 16 | mask_key[1] << 8 | mask_key[0]
    
        # We need data to be a multiple of four...
        data += bytes(" " * (4 - (len(data) % 4)), "us-ascii")
        a = numpy.frombuffer(data, dtype="uint32")
        masked = numpy.bitwise_xor(a, [_mask_key]).astype("uint32")
        if len(data) > origlen:
            return masked.tobytes()[:origlen]
        
        return masked.tobytes()

    @staticmethod
    def create_frame(data, opcode, fin=1):
        """
        create frame to send text, binary and other data.
        data: data to send. This is string value(byte array).
            if opcode is OPCODE_TEXT and this value is unicode,
            data value is converted into unicode string, automatically.
        opcode: operation code. please see OPCODE_XXX.
        fin: fin flag. if set to 0, create continue fragmentation.
        """
        if opcode == ABNF.OPCODE_TEXT:
            data = data.encode("utf-8")
        # mask must be set if send data from client
        return ABNF(fin, 0, 0, 0, opcode, 1, data)

# send data buffer ¥
class frame_buffer():
    _HEADER_MASK_INDEX = 5
    _HEADER_LENGTH_INDEX = 6

    def __init__(self, recv_fn):
        self.recv = recv_fn
        self.recv_buffer = []
        self.clear()
        self.lock = threading.Lock()

    def clear(self):
        self.header = None
        self.length = None
        self.mask = None
        
    
    def recv_frame(self):
        with self.lock:
            # header read
            if self.has_header():
                self.recv_header()
            (fin, rsv1, rsv2, rsv3, opcode, has_mask, _) = self.header

            # frame len read
            if self.has_length():
                self.recv_length()
            length = self.length

            if has_mask:
                # mask read
                if self.has_mask():
                    self.recv_mask()
                mask = self.mask

            # payload
            payload = self.recv_reader(length)[0]
            if has_mask:
                payload = ABNF.mask(mask, payload)

            # reset for next frame
            self.clear()

            frame = ABNF(fin, rsv1, rsv2, rsv3, opcode, has_mask, payload)

        return frame

    def has_header(self):
        return self.header is None
    
    def recv_header(self):
        header = self.recv_reader(2)

        b1 = header[0][0]

        fin = b1 >> 7 & 1
        rsv1 = b1 >> 6 & 1
        rsv2 = b1 >> 5 & 1
        rsv3 = b1 >> 4 & 1
        opcode = b1 & 0xf

        b2 = header[0][1]
        has_mask = (b2 >> 7) & 1
        length_bits = b2 & 0x7f

        self.header = (fin, rsv1, rsv2, rsv3, opcode, has_mask, length_bits)
    
    def has_length(self):
        return self.length is None
    
    def recv_length(self):
        bits = self.header[frame_buffer._HEADER_LENGTH_INDEX]
        length_bits = bits & 0x7f
        if length_bits == 0x7e:
            r = self.recv_reader(2)
            self.length = struct.unpack("!H", r)[0]
        elif length_bits == 0x7f:
            v = self.recv_reader(8)
            self.length = struct.unpack("!Q", v)[0]
        else:
            self.length = length_bits

    def has_mask(self):
        return self.mask is None
    
    def recv_mask(self):
        if not self.header:
            self.mask = ""
        else:
            self.mask = self.recv_reader(4) 


    def recv_reader(self, bufsize):
        shortage = bufsize - sum(len(x) for x in self.recv_buffer)
        while shortage > 0:
            bytedatas = self.recv(min(16384, shortage))
            self.recv_buffer.append(bytedatas)
            shortage -=len(bytedatas)
        
        unified = self.recv_buffer

        if shortage == 0:
            self.recv_buffer = []
            return unified
        else:
            self.recv_buffer = [unified[bufsize:]]
            return unified[:bufsize]

