from scapy.all import *
src_ip="192.168.20.2"
dst_ip="192.168.30.2"
for _ in range(10):
    send(IP(src=src_ip,dst=dst_ip)/ICMP())
