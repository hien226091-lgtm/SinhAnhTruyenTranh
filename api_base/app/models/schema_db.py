from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from datetime import datetime

from api_base.app.models.base_db import Base 

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True} # <-- Báo cho hệ thống biết là dùng chung bảng cũ
    
    UserID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Username = Column(String(50), unique=True, index=True)
    Email = Column(String(100), unique=True, index=True)
    PasswordHash = Column(String(255))
    Role = Column(String(20), default="user")
    CreatedAt = Column(DateTime, default=datetime.utcnow)
    FullName = Column(String(100), nullable=True)

    comics = relationship("Comic", back_populates="owner")
    Quota = Column(Integer, default=0)

class Comic(Base):
    __tablename__ = "comics"
    __table_args__ = {'extend_existing': True}
    
    # 6 CỘT CHUẨN XÁC THEO ĐÚNG HÌNH BẠN CHỤP:
    ComicID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("users.UserID"), nullable=False)
    Title = Column(String(255), default="Truyện tranh tạo từ AI")
    ScriptContent = Column(Text, nullable=True)
    LayoutJsonPath = Column(Text, nullable=True)
    CreatedAt = Column(DateTime, default=datetime.utcnow)
    
    # Các mối quan hệ (giữ nguyên để nối với bảng users, frames, characters)
    owner = relationship("User", back_populates="comics")
    frames = relationship("Frame", back_populates="comic", cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="comic", cascade="all, delete-orphan")

class Frame(Base):
    __tablename__ = "frames"
    __table_args__ = {'extend_existing': True}
    
    FrameID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ComicID = Column(Integer, ForeignKey("comics.ComicID"), nullable=False)
    FrameOrder = Column(Integer)
    AspectRatio = Column(String(20))
    Resolution = Column(String(20))
    ImageDescription = Column(Text)
    DialogLeft = Column(Text, nullable=True)
    DialogRight = Column(Text, nullable=True)
    SFX = Column(String(100), nullable=True)
    GeneratedImageUrl = Column(String(255), nullable=True)

    comic = relationship("Comic", back_populates="frames")

class Character(Base):
    __tablename__ = "characters"
    __table_args__ = {'extend_existing': True}
    
    CharacterID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ComicID = Column(Integer, ForeignKey("comics.ComicID"), nullable=False)
    ReferenceImages = Column(Text, nullable=True)

    comic = relationship("Comic", back_populates="characters")

class RequestLog(Base):
    __tablename__ = "request_logs"
    
    LogID = Column(Integer, primary_key=True, index=True)
    UserID = Column(Integer, index=True) 
    ModelName = Column(String(50))        
    Timestamp = Column(DateTime, default=func.now())
    Status = Column(String(20))