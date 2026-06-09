"""ORM models for the Comic AI project.

These map to the schema provided by the user: Users, Comics, Characters, Frames.
"""
from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from api_base.app.models.base_db import Base


class Users(Base):
    __tablename__ = "users"

    UserID = Column(Integer, primary_key=True, autoincrement=True)
    Username = Column(String(100), nullable=False)
    Email = Column(String(255), unique=True, nullable=False)
    FullName = Column(String(255), nullable=True)
    PasswordHash = Column(String(255), nullable=False)
    Role = Column(String(50), nullable=True, server_default="user")
    CreatedAt = Column(DateTime, server_default=func.now())

    comics = relationship("Comics", back_populates="user", cascade="all, delete-orphan")


class Comics(Base):
    __tablename__ = "comics"

    ComicID = Column(Integer, primary_key=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("users.UserID", ondelete="CASCADE"), nullable=True)
    Title = Column(String(255), nullable=False)
    ScriptContent = Column(Text, nullable=True)
    ScriptFilePath = Column(String(500), nullable=True)
    LayoutJsonPath = Column(String(500), nullable=True)
    FinalComicUrl = Column(String(500), nullable=True)
    Status = Column(String(50), nullable=False, server_default="Draft")
    CreatedAt = Column(DateTime, server_default=func.now())

    user = relationship("Users", back_populates="comics")
    characters = relationship("Characters", back_populates="comic", cascade="all, delete-orphan")
    frames = relationship("Frames", back_populates="comic", cascade="all, delete-orphan")


class Characters(Base):
    __tablename__ = "characters"

    CharacterID = Column(Integer, primary_key=True, autoincrement=True)
    ComicID = Column(Integer, ForeignKey("comics.ComicID", ondelete="CASCADE"), nullable=False)
    Description = Column(Text, nullable=True)
    ReferenceImages = Column(Text, nullable=True)

    comic = relationship("Comics", back_populates="characters")


class Frames(Base):
    __tablename__ = "frames"

    FrameID = Column(Integer, primary_key=True, autoincrement=True)
    ComicID = Column(Integer, ForeignKey("comics.ComicID", ondelete="CASCADE"), nullable=False)
    FrameOrder = Column(Integer, nullable=False)
    AspectRatio = Column(String(20), nullable=True, server_default="16:9")
    Resolution = Column(String(20), nullable=True, server_default="2K")
    ImageDescription = Column(Text, nullable=True)
    DialogLeft = Column(Text, nullable=True)
    DialogRight = Column(Text, nullable=True)
    SFX = Column(String(255), nullable=True)
    GenerationStatus = Column(String(50), nullable=False, server_default="Pending")
    GeneratedImageUrl = Column(String(500), nullable=True)

    comic = relationship("Comics", back_populates="frames")
