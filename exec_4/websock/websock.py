from util_http import *
from handshark import *
from abnf import *

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
        self.frame_buffer = frame_buffer(self._recv)
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

    def _recv(self, bufsize):
        try:
            return recv(self.sock, bufsize)
        except Exception as e:
            if self.sock:
                self.sock.close()
            self.sock = None
            self.connected = False
            raise e

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
        data = frame.formating()
        length = len(data)
        print("send_frame")
        print(data)

        print("lock")
        with self.lock:
            while data:
                print(type(data))
                print(data)
                l = self._send(data)
                data = data[l:]

        return length


def create_connection(url, timeout=None, **options):
    set_timeout(timeout)
    websock = WebSocket()
    websock.connect(url, **options)

    return websock

