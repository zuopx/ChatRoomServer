import sqlite3

from config import Config

conn = sqlite3.connect(Config.get_DB())
cur = conn.cursor()

cur.executescript("""CREATE TABLE user(
    name text,
    password text,
    create_time text,
    online_time integer)""")

cur.close()
conn.commit()
conn.close()
