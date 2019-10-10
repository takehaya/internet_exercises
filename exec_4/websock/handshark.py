import os
from base64 import encodebytes
from util_http import * 
from http import HTTPStatus
# websocket supported version.
VERSION = 13
SUPPORTED_REDIRECT_STATUSES = [HTTPStatus.MOVED_PERMANENTLY, HTTPStatus.FOUND, HTTPStatus.SEE_OTHER]

class handshake_response(object):
    def __init__(self, status, headers, subprotocol):
        self.status = status
        self.headers = headers
        self.subprotocol = subprotocol

def _get_handshake_header(resource, host, port, options):
    headers = [
        "GET %s HTTP/1.1" % resource,
        "Upgrade: websocket",
        "Connection: Upgrade"
    ]
    key = _create_sec_websocket_key()
    hostport = "%s:%d" % (_pack_hostname(host), port)
    headers.append("Host: %s" % hostport)
    headers.append("Sec-WebSocket-Version: %s" % VERSION)
    headers.append("Sec-WebSocket-Key: %s" % key)
    headers.append("Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits")
    if "subprotocols" in options:
        headers.append("Sec-WebSocket-Protocol: %s" % ",".join(options["subprotocols"]))

    return headers, key

def _pack_hostname(hostname):
    # use IPv6 
    if ':' in hostname:
        return '[' + hostname + ']'

    return hostname

def handshake(sock, host, port, resource, **options):
    headers, _ = _get_handshake_header(resource, host, port, options)
    header_str = "\r\n".join(headers)
    header_str += "\r\n\r\n"
    print(header_str)
    send(sock, header_str.encode('utf-8'))
    status, resp = _get_resp_headers(sock)
    print(status)
    print(resp)

    if status in SUPPORTED_REDIRECT_STATUSES:
        return handshake_response(status, resp, None)

    # TODO:: check status validate!
    
    subprotocols = options["subprotocols"] if "subprotocols" in options else None
    return handshake_response(status, resp, subprotocols)

def _create_sec_websocket_key():
    randomness = os.urandom(16)
    return encodebytes(randomness).decode('utf-8').strip()

def _get_resp_headers(sock, success_statuses=(101, 301, 302, 303)):
    print("_get_resp_headers")

    status, resp_headers, status_message = read_headers(sock)
    if status not in success_statuses:
        raise Exception("Handshake status %d %s", status, status_message, resp_headers)
    return status, resp_headers
