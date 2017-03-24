# coding:utf-8
import sys
import socket

if __name__ == '__main__':
    socket.setdefaulttimeout(1)  # 1s
    host = sys.argv[1]
    port = int(sys.argv[2])
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # noinspection PyBroadException
    try:
        sock.connect((host, int(port)))
        print(True)
    except Exception:
        print(False)
    sock.close()
