# ChatRoom Server
import time
import random
import logging
import threading
from src.main.mysocket import Listener, ServerClient
from config import Config
from src.main.user_repo import UserRepo
from src.main.user import User

log_format = '%(asctime)s --- %(message)s'
datefmt = '%m/%d/%Y %H:%M:%S'
logging.basicConfig(level=logging.DEBUG, format=log_format, datefmt=datefmt)


class ChatRoomServer:
    def __init__(self):
        self.ip = Config.get_IP()
        self.port = Config.get_PORT()
        self.serverclients = []
        self.ingame = False
        self.sec = None
        self.game = {}
        self.gamelock = threading.Lock()

    def start(self):  # start listener
        listener = Listener(self.ip, self.port, self.new_serverclient)
        listener.start()

        self.__rollgame()

    def __rollgame(self):
        while True:
            if self.ingame:
                start_time = time.time()
                while True:
                    if time.time() - start_time >= self.sec:
                        keys = list(self.game.keys())
                        if keys:
                            mk = keys[0]
                            for k in keys[1:]:
                                if self.game[k] > self.game[mk]:
                                    mk = k
                            msg = '>>>%s(%d) win the roll game!\r\n' % (
                                mk, self.game[mk])

                        else:
                            msg = '>>>No one play the roll game!\r\n'
                        self.broadcast(msg)
                        self.ingame = False
                        self.game = {}
                        self.sec = {}
                        break

    def new_serverclient(self, conn):
        logging.info('A connect from address: (%s:%s)' % conn.getpeername())
        serverclient = ServerClient(
            conn, self.deal_message, self.close)
        self.serverclients.append(serverclient)
        serverclient.start()

    def close(self, serverclient):
        self.deal_message(serverclient, 'logout')
        logging.info('Disconnected from address: (%s:%s)' %
                     serverclient.conn.getpeername())
        serverclient.conn.close()
        serverclient.inputs.close()
        serverclient.outputs.close()

    def deal_message(self, serverclient, msg):
        try:
            first_word = msg.split()[0]
            if first_word == 'create':
                self.create_user(serverclient, msg)
            elif first_word == 'login':
                self.login(serverclient, msg)
            elif first_word == 'logout':
                self.logout(serverclient, msg)
            elif first_word == 'chat':
                self.chat(serverclient, msg)
            elif first_word == 'info':
                self.user_info(serverclient, msg)
            elif first_word == 'rollstart':
                self.rollstart(serverclient, msg)
            elif first_word == 'roll':
                self.roll(serverclient, msg)
            else:
                serverclient.outputs.write(
                    '>>>!!! Instruction error !!!\r\n'.encode())
        except Exception as e:
            serverclient.outputs.write(
                '>>>!!! Instruction error or abnormal connection in chat room !!!\r\n'.encode())

    def create_user(self, serverclient, msg):
        words = msg.split()
        assert len(words) == 3
        username, password = words[1], words[2]
        t = time.localtime()
        create_time = '%s-%s-%s %s:%s:%s' % (
            t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
        user = User(username, password, create_time, 0)
        try:
            serverclient.user_repo.insert(user)
            send_msg = '>>>%s has been created successfully!\r\n' % username
            serverclient.outputs.write(send_msg.encode())
            info = '%s has been created from address: ' % username
            logging.info(info + '(%s:%s)' % serverclient.conn.getpeername())
        except Exception:
            serverclient.outputs.write(
                '>>>!!! Database connection problem, or the user already exists !!!\r\n'.encode())

    def login(self, serverclient, msg):
        serverclient.login_time = time.time()
        words = msg.split()
        assert len(words) == 3
        username, password = words[1], words[2]
        serverclient.username = username
        try:
            user = serverclient.user_repo.select(username)
            broadcast_msg = '>>>%s login\r\n' % username
            self.broadcast(broadcast_msg)
            info = '%s login from address: ' % username
            logging.info(info + '(%s:%s)' % serverclient.conn.getpeername())
        except Exception:
            serverclient.outputs.write(
                '>>>!!! Database connection problem, or wrong username and password !!!\r\n'.encode())

    def logout(self, serverclient, msg):
        if serverclient.username:
            assert msg.strip() == 'logout'
            serverclient.logout_time = time.time()
            interval = round(serverclient.logout_time -
                             serverclient.login_time)
            serverclient.user_repo.update_online_time(
                serverclient.username, interval)
            broadcast_msg = '>>>%s logout\r\n' % serverclient.username
            self.broadcast(broadcast_msg)
            info = '%s logout from address: ' % serverclient.username
            logging.info(info + '(%s:%s)' % serverclient.conn.getpeername())
            serverclient.username = None
            serverclient.login_time = None
            serverclient.logout_time = None

        else:
            serverclient.outputs.write(
                '>>>!!! No user login on this terminal !!!\r\n'.encode())

    def chat(self, serverclient, msg):
        if serverclient.username:
            words = msg.split()
            assert len(words) > 1
            first_word = words[0]
            msg = msg.replace(first_word, '').strip()
            broadcast_msg = '>>>%s:%s\r\n' % (serverclient.username, msg)
            self.broadcast(broadcast_msg)
        else:
            serverclient.outputs.write(
                '>>>!!! No user login on this terminal !!!\r\n'.encode())

    def user_info(self, serverclient, msg):
        words = msg.split()
        assert len(words) == 2
        username = words[1]
        interval = 0
        for sc in self.serverclients:
            if sc.username == username:
                interval = round(time.time() - sc.login_time)
        try:
            user = serverclient.user_repo.select(username)
            serverclient.outputs.write(
                '>>>{} info:\r\n'.format(username).encode())
            serverclient.outputs.write(
                '>>>create time: {}\r\n'.format(user.create_time).encode())
            serverclient.outputs.write(
                '>>>online time: {}\r\n'.format(int(user.online_time + interval)).encode())
        except Exception:
            serverclient.outputs.write(
                '>>>!!! Database connection problem, or the user does not exist !!!\r\n'.encode())

    def rollstart(self, serverclient, msg):
        if serverclient.username:
            if not self.ingame:
                words = msg.split()
                assert len(words) == 2
                sec = int(words[1])
                self.ingame = True
                self.sec = sec
                msg = '>>>%s start a roll game!(will end in %d sec)\r\n' % (
                    serverclient.username, sec)
                self.broadcast(msg)
            else:
                serverclient.outputs.write('>>>A roll game is running.\r\n')
        else:
            serverclient.outputs.write(
                '>>>!!! No user login on this terminal !!!\r\n'.encode())

    def roll(self, serverclient, msg):
        if serverclient.username:
            assert msg.strip() == 'roll'
            r = random.randint(1, 100)
            self.gamelock.acquire()
            self.game[serverclient.username] = r
            self.gamelock.release()
            msg = '>>>%s roll: %d\r\n' % (serverclient.username, r)
            self.broadcast(msg)
        else:
            serverclient.outputs.write(
                '>>>!!! No user login on this terminal !!!\r\n'.encode())

    def broadcast(self, msg, exclude=None):
        for serverclient in self.serverclients:
            if serverclient != exclude and serverclient.username:
                serverclient.outputs.write(msg.encode())


if __name__ == "__main__":
    ChatRoomServer().start()
