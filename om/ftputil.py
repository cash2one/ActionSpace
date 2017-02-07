# coding=utf-8
from ftplib import FTP
from base64 import b85decode as pw


class Ftp(object):
    def __init__(self):
        self.ftp = FTP()
        self.ftp.set_pasv(True)
        self.ftp.connect('10.17.162.58', 8088)
        self.ftp.login('wls81', pw('O=)CgKyY$o').decode())

    def list(self):
        return self.ftp.nlst()

    def upload(self, server_name, client_path_name):
        with open(client_path_name, 'rb') as f:
            self.ftp.storbinary('STOR ' + server_name, f)

    def upload_stream(self, server_name, client_stream):
        self.ftp.storbinary('STOR ' + server_name, client_stream)

    def download(self, server_name, client_path_name):
        with open(client_path_name, 'wb') as f:
            self.ftp.retrbinary('RETR ' + server_name, f)

    def quit(self):
        self.ftp.quit()
