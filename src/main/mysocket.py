import threading
import socket
import logging

from config import Config
from src.main.user_repo import UserRepo

class Listener(threading.Thread):

    def __init__(self, ip, port, new_serverclient):
        threading.Thread.__init__(self)
        self.ip = ip
        self.port = port
        self.new_serverclient = new_serverclient
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._set_socket()

    def _set_socket(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.ip, self.port))
        self.socket.listen(0)
        logging.info('Chat room server is running ...')
        logging.info('Listening IP:%s Port:%d, ' % (self.ip, self.port)) 

    def run(self):
        while True:
            conn, addr = self.socket.accept()
            logging.info('A request from address: (%s:%s)' % addr)
            self.new_serverclient(conn)


class ServerClient(threading.Thread):

    def __init__(self, conn, deal_message, close):
        threading.Thread.__init__(self)
        self.conn = conn
        self.deal_message = deal_message
        self.user_repo = None
        self.close = close
        self.inputs = self.conn.makefile('rb', 0)
        self.outputs = self.conn.makefile('wb', 0)
        self.username = None
        self.login_time = None
        self.logout_time = None

    def run(self):
        self.user_repo = UserRepo(Config.get_DB())
        self.outputs.write('Welcome to Chatroom!\r\n'.encode())
        while True:
            msg = self.inputs.readline().decode().strip()
            if msg:
                self.deal_message(self, msg)
            else:
                self.close(self)
                break