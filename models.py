from sqlalchemy import Column, Integer
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Server(Base):
    __tablename__ = 'server'

    id = Column('server_id', Integer, primary_key=True, autoincrement=True)
    guild_id = Column('guild_id', Integer, nullable=False, index=True, unique=True)
    channel_id = Column('channel_id', Integer)
