import sqlite3
import threading

from src.main.user import User


class UserRepo:
    def __init__(self, db):
        self.conn = sqlite3.connect(db)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()

    def insert(self, user):
        self.lock.acquire()
        self.cursor.execute(
            'INSERT INTO user VALUES(?,?,?,?)', list(user._asdict().values()))
        self.conn.commit()
        self.lock.release()

    def update_online_time(self, username, interval):
        self.lock.acquire()
        self.cursor.execute(
            'UPDATE user SET online_time=online_time+? WHERE name=?', (interval, username))
        self.conn.commit()
        self.lock.release()

    def select(self, username):
        self.cursor.execute('SELECT * FROM user WHERE name=?', (username,))
        if self.cursor.arraysize == 1:
            user = User(*self.cursor.fetchone())
            return user
        else:
            raise Exception('db error')
