from util_http import *
from handshark import *

import numpy
import threading
import struct
class WebSocket():
    def __init__(self):
        self.handshake_response = None
        self.sock = None
        self.connected = False
        self.get_mask_key = None
        self.lock = threading.Lock()
        self.readlock = threading.Lock()

    def connect(self, url, **options):
        self.sock, addrs = connect(url)
        try:
            self.handshake_response = handshake(self.sock, *addrs, **options)
            self.connected = True
        except Exception as e:
            if self.sock:
                self.sock.close()
                self.sock = None
            raise e

    def ping(self, payload=""):
        """
        send ping data.
        payload: data payload to send server.
        """
        payload = payload.encode("utf-8")
        self.send(payload, ABNF.OPCODE_PING)

    def pong(self, payload):
        """
        send pong data.
        payload: data payload to send server.
        """
        payload = payload.encode("utf-8")
        self.send(payload, ABNF.OPCODE_PONG)

    def recv(self):
        """
        Receive string data(byte array) from the server.
        return value: string(byte array) value.
        """
        with self.readlock:
            opcode, data = self.recv_data()

        if opcode == ABNF.OPCODE_TEXT:
            return data.decode("utf-8")
        elif opcode == ABNF.OPCODE_TEXT or opcode == ABNF.OPCODE_BINARY:
            return data
        else:
            return ''

    def recv_data(self, control_frame=False):
        """
        Receive data with operation code.
        control_frame: a boolean flag indicating whether to return control frame
        data, defaults to False
        return  value: tuple of operation code and string(byte array) value.
        """
        opcode, frame = self.recv_data_frame(control_frame)
        return opcode, frame.data
        
    def recv_data_frame(self, control_frame=False):
        """
        Receive data with operation code.
        control_frame: a boolean flag indicating whether to return control frame
        data, defaults to False
        return  value: tuple of operation code and string(byte array) value.
        """
        while True:
            frame = self.recv_frame()
            if not frame:
                # handle error:
                # 'NoneType' object has no attribute 'opcode'
                raise Exception("Not a valid frame %s" % frame)
            elif frame.opcode in (ABNF.OPCODE_TEXT, ABNF.OPCODE_BINARY, ABNF.OPCODE_CONT):
                self.cont_frame.validate(frame)
                self.cont_frame.add(frame)

                if self.cont_frame.is_fire(frame):
                    return self.cont_frame.extract(frame)

            elif frame.opcode == ABNF.OPCODE_CLOSE:
                self.send_close()
                return frame.opcode, frame
            elif frame.opcode == ABNF.OPCODE_PING:
                if len(frame.data) < 126:
                    self.pong(frame.data)
                else:
                    raise Exception("Ping message is too long")
                if control_frame:
                    return frame.opcode, frame
            elif frame.opcode == ABNF.OPCODE_PONG:
                if control_frame:
                    return frame.opcode, frame
    
    def recv_frame(self):
        """
        receive data as frame from server.
        return value: ABNF frame object.
        """
        return self.frame_buffer.recv_frame()

    def send(self, payload, opcode=ABNF.OPCODE_TEXT):
        frame = ABNF.create_frame(payload, opcode)
        return self.send_frame(frame)
    
    def _send(self, data):
        return send(self.sock, data)
    
    def send_frame(self, frame):
        if self.get_mask_key:
            frame.get_mask_key = self.get_mask_key
        data = frame.format()
        length = len(data)

        with self.lock:
            while data:
                l = self._send(data)
                data = data[l:]

        return length


def create_connection(url, timeout=None, **options):
    set_timeout(timeout)
    websock = WebSocket()
    websock.connect(url, **options)

    return websock


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
        frame_header = chr(
            self.fin << 7
            | self.rsv1 << 6 
            | self.rsv2 << 5 
            | self.rsv3 << 4
            | self.opcode
        )

        if length < ABNF.LENGTH_7:
            frame_header += chr(self.mask << 7 | length)
        elif length < ABNF.LENGTH_16:
            # 0x7e == 126
            # ペイロードの長さが16bitよりも長いのでそのときはpayload lenを126にして
            # extend payloadを利用すること示さなくてはいけない。
            #  If 126, the following 2 bytes interpreted as a 16-bit unsigned integer are the payload length.
            frame_header += chr(self.mask << 7| 0x7e)
            frame_header += struct.pack("!H", length)
        else:
            # 0x7f == 127
            # ペイロードの長さが16bitよりも長いのでそのときはpayload lenを127にして
            # extend payloadと extend payload length conttinuedを利用すること示さなくてはいけない。
            # If 127, the following 8 bytes interpreted as a 64-bit unsigned integer (the most significant bit MUST be 0)
            frame_header += chr(self.mask << 7 | 0x7f)
            frame_header += struct.pack("!Q", length)
        
        if not self.mask:
            return frame_header + self.data
        else:
            mask_key = self.get_mask_key(4)
            return frame_header + self._get_masked(mask_key)
    
    def _get_masked(self, mask_key):
        s = ABNF.mask(mask_key, self.data)

        if isinstance(mask_key, six.text_type):
            mask_key = mask_key.encode('utf-8')

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
        if opcode == ABNF.OPCODE_TEXT and isinstance(data, six.text_type):
            data = data.encode("utf-8")
        # mask must be set if send data from client
        return ABNF(fin, 0, 0, 0, opcode, 1, data)

class frame_buffer():

    def __init__(self, recv_fn):
        self.recv = recv_fn
        self.recv_buffer = []
        self.clear
        self.lock = threading.Lock()

    def clear(self):
        self.header = None
        self.length = None
        self.mask = None
    
    def recv_frame(self):
        with self.lock:
            pass
            # header read

            # frame len read

            # mask read

            # payload

            # reset for next frame
