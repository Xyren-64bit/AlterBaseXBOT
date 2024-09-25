import threading

from datetime import datetime, timedelta
from sqlalchemy import TEXT, Column, Numeric, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from config import DB_URI


def start() -> scoped_session:
    engine = create_engine(DB_URI, client_encoding="utf8")
    BASE.metadata.bind = engine
    BASE.metadata.create_all(engine)
    return scoped_session(sessionmaker(bind=engine, autoflush=False))


BASE = declarative_base()
SESSION = start()

INSERTION_LOCK = threading.RLock()


class Broadcast(BASE):
    __tablename__ = "broadcast"
    id = Column(Numeric, primary_key=True)
    user_name = Column(TEXT)

    def __init__(self, id, user_name):
        self.id = id
        self.user_name = user_name


Broadcast.__table__.create(checkfirst=True)


#  Add user details -
async def add_user(id, user_name):
    with INSERTION_LOCK:
        msg = SESSION.query(Broadcast).get(id)
        if not msg:
            usr = Broadcast(id, user_name)
            SESSION.add(usr)
            SESSION.commit()


async def delete_user(id):
    with INSERTION_LOCK:
        SESSION.query(Broadcast).filter(Broadcast.id == id).delete()
        SESSION.commit()


async def full_userbase():
    users = SESSION.query(Broadcast).all()
    SESSION.close()
    return users


async def query_msg():
    try:
        return SESSION.query(Broadcast.id).order_by(Broadcast.id)
    finally:
        SESSION.close()

class ScheduledPost(BASE):
    __tablename__ = "scheduled_post"
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Numeric)
    scheduled_time = Column(DateTime)

    def __init__(self, message_id, scheduled_time):
        self.message_id = message_id
        self.scheduled_time = scheduled_time


ScheduledPost.__table__.create(checkfirst=True)


async def add_scheduled_post(message_id, scheduled_time):
    with INSERTION_LOCK:
        post = ScheduledPost(message_id, scheduled_time)
        SESSION.add(post)
        SESSION.commit()


async def get_scheduled_posts():
    try:
        return SESSION.query(ScheduledPost).all()
    finally:
        SESSION.close()


async def delete_scheduled_post(message_id):
    with INSERTION_LOCK:
        SESSION.query(ScheduledPost).filter(ScheduledPost.message_id == message_id).delete()
        SESSION.commit()
