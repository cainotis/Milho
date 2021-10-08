from sqlalchemy import Column, Integer, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Server(Base):
	__tablename__ = 'server'

	id = Column('server_id', Integer, primary_key=True, autoincrement=True)
	guild = Column('guild_id', Text, nullable=False, index=True, unique=True)
	chat = Column('chat', Text)
