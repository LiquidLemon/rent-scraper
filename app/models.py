from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    search_queries = relationship("SearchQuery", back_populates="user")
    notification_settings = relationship("NotificationSetting", back_populates="user")


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Scraping status fields
    last_scraped_at = Column(DateTime, nullable=True)
    last_scrape_count = Column(Integer, nullable=True)  # Number of offers found in last scrape
    last_scrape_status = Column(String, nullable=True)  # 'success', 'error', 'no_results'
    last_scrape_error = Column(Text, nullable=True)  # Error message if scrape failed
    
    user = relationship("User", back_populates="search_queries")
    offers = relationship("Offer", back_populates="query", cascade="all, delete-orphan")


class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    discord_webhook_url = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="notification_settings")


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False, unique=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    query_id = Column(Integer, ForeignKey("search_queries.id", ondelete="CASCADE"), nullable=False)
    
    user = relationship("User")
    query = relationship("SearchQuery", back_populates="offers")