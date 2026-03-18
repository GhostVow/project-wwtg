"""SQLAlchemy ORM models matching the DB schema in technical design."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wx_openid = Column(String(64), unique=True, nullable=False)
    wx_nickname = Column(String(64))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    sessions = relationship("Session", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    city = Column(String(32))
    context = Column(JSONB)
    state = Column(String(32), default="init")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session")
    plans = relationship("Plan", back_populates="session")

    __table_args__ = (
        Index("idx_sessions_user", "user_id", created_at.desc()),
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONB)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("Session", back_populates="messages")


class Plan(Base):
    __tablename__ = "plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    title = Column(String(128), nullable=False)
    description = Column(Text)
    card_data = Column(JSONB, nullable=False)
    status = Column(String(16), default="presented")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("Session", back_populates="plans")


class PoiCache(Base):
    __tablename__ = "poi_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city = Column(String(32), nullable=False)
    tags = Column(ARRAY(Text), nullable=False)
    poi_data = Column(JSONB, nullable=False)
    source_url = Column(String(512))
    source_likes = Column(Integer)
    fetched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    event_type = Column(String(64), nullable=False)
    event_data = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_events_type", "event_type", created_at.desc()),
    )
