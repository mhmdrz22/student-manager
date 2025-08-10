from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .database import Base

event_registration = Table('event_registration', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('event_id', Integer, ForeignKey('events.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user") # Roles: user, member, manager

    articles = relationship("Article", back_populates="owner")
    news = relationship("News", back_populates="owner")
    created_events = relationship("Event", back_populates="owner")
    registered_events = relationship("Event", secondary=event_registration, back_populates="registrants")

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    summary = Column(Text, nullable=True)
    content = Column(Text)
    image_url = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    status = Column(String, default="pending") # pending, approved, rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="articles")


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    summary = Column(Text, nullable=True)
    content = Column(Text)
    image_url = Column(String, nullable=True)
    category = Column(String, index=True, nullable=True)
    status = Column(String, default="pending") # pending, approved, rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="news")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    summary = Column(Text, nullable=True)
    description = Column(Text)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True), nullable=True)
    location = Column(String)
    category = Column(String, index=True)
    status = Column(String, default="pending") # pending, approved, rejected
    image_url = Column(String, nullable=True)
    capacity = Column(Integer, nullable=True)
    registration_deadline = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="created_events")
    registrants = relationship("User", secondary=event_registration, back_populates="registered_events")
