from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.connection import Base



# For Users
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    urls = relationship("ShortURL", back_populates="owner")


# For URLs
class ShortURL(Base):
    __tablename__ = "short_urls"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String(2048), nullable=False)
    short_code = Column(String(20), unique=True, index=True, nullable=False)
    custom_alias = Column(String(50), unique=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = anonymous
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="urls")
    clicks = relationship("Click", back_populates="url", cascade="all, delete-orphan")


# For Clicks
class Click(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True, index=True)
    url_id = Column(Integer, ForeignKey("short_urls.id"), nullable=False)
    ip_address = Column(String(45), nullable=True)       # supports IPv6
    user_agent = Column(String(500), nullable=True)
    referer = Column(String(2048), nullable=True)
    country = Column(String(100), nullable=True)
    device_type = Column(String(50), nullable=True)      # mobile / desktop / tablet
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    clicked_at = Column(DateTime(timezone=True), server_default=func.now())

    url = relationship("ShortURL", back_populates="clicks")
