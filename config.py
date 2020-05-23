import os

class Config:

    IP = '0.0.0.0'

    PORT = 9300

    DB = os.path.join(os.getcwd(), 'db\\chatroom.db')

    @staticmethod
    def get_IP():
        return Config.IP

    @staticmethod
    def get_PORT():
        return Config.PORT

    @staticmethod
    def get_DB():
        return Config.DB