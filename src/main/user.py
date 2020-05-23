"""User"""

from collections import namedtuple

User = namedtuple('User', ['name', 'password', 'create_time', 'online_time'])