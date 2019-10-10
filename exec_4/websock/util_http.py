import errno
import os
import socket
import sys
from urllib.parse import urlparse

TIMEOUT = None
DEFAULT_SOCKET_OPTION = [(socket.SOL_TCP, socket.TCP_NODELAY, 1)]

def parse_url(url):
    if ":" not in url:
        raise ValueError("url is invalid")

    scheme, url = url.split(":", 1)
    parsed = urlparse(url, scheme="ws")

    if parsed.hostname:
        hostname = parsed.hostname
    else:
        raise ValueError("hostname is invalid")
    
    port = 0
    if parsed.port:
        port = parsed.port
    if scheme == "ws":
        if not port:
            port = 80
    else:
        raise ValueError("scheme %s is invalid" % scheme)

    if parsed.path:
        resource = parsed.path
    else:
        resource = "/"

    if parsed.query:
        resource += "?" + parsed.query
    return hostname, port, resource

def connect(url, sock=None):
    hostname, port, resource = parse_url(url)

    if sock:
        return sock, (hostname, port, resource)
    
    # dig
    addrinfo_list = socket.getaddrinfo(
        hostname, port, 0, 0, socket.SOL_TCP
    )
    if not addrinfo_list:
        raise ValueError("Host not found.: " + hostname + ":" + str(port))
    
    sock = None

    try:
        sock = _open_socket(addrinfo_list)
        return sock, (hostname, port, resource)
    except Exception as e:
        if sock:
            sock.close()
        raise e


def _open_socket(addrinfo_list):
    sock = None
    for addrinfo in addrinfo_list:
        family, socktype, proto = addrinfo[:3]
        sock = socket.socket(family, socktype, proto)
        sock.settimeout(TIMEOUT)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        
        addr = addrinfo[4]
        err = None
        while not err:
            try:
                sock.connect(addr)
                err = None
            except OSError as error:
                # add err info
                error.remote_ip = str(addr[0])
                try:
                    # errno.WSAECONNREFUSED windows only
                    eConnRefused = (errno.ECONNREFUSED, errno.WSAECONNREFUSED)
                except:
                    eConnRefused = (errno.ECONNREFUSED, )
                if error.errno == errno.EINTR:
                    continue
                elif error.errno in eConnRefused:
                    err = error
                    continue
                else:
                    raise error
            else:
                break
        else:
            continue
    else:
        if err:
            raise err
    return sock

def send(sock, data):
    # data = data.encode('utf-8')
    
    if not sock:
        raise Exception("socket is already closed.")
    try:
        print(data)
        return sock.send(data)
    except socket.timeout as e:
        raise e
    except Exception as e:
            raise e

def recv(sock, bufsize):
    if not sock:
        raise Exception("socket is already closed.")
    try:
        bytedatas = sock.recv(bufsize)
    except socket.timeout as e:
        raise Exception(e)
    except Exception as e:
        raise Exception(e)
    
    if not bytedatas:
        raise Exception("Connection is already closed.")

    return bytedatas

def recv_line(sock):
    line = ""
    while True:
        c = recv(sock, 1)
        line += c.decode('utf-8')
        if c.decode("utf-8") == "\n":
            break
    return line


def read_headers(sock):
    status = None
    status_message = None
    headers = {}

    while True:
        line = recv_line(sock)
        line = line.strip()
        if not line:
            break
        if not status:

            status_info = line.split(" ", 2)
            status = int(status_info[1])
            if len(status_info) > 2:
                status_message = status_info[2]
        else:
            kv = line.split(":", 1)
            if len(kv) == 2:
                key, value = kv
                headers[key.lower()] = value.strip()
            else:
                raise Exception("Invalid header")


    return status, headers, status_message

def set_timeout(time):
    TIMEOUT = time
