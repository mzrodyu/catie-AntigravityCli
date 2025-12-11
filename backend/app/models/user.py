from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    password_hash = Column(String(128))
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    daily_quota = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # 关联
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")


class Token(Base):
    """Antigravity Token"""
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Token信息
    token = Column(Text, nullable=False)  # 加密存储的token
    email = Column(String(255), nullable=True)  # 关联邮箱
    project_id = Column(String(255), nullable=True)  # Google Cloud 项目ID
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)  # 是否捐赠到公共池
    
    # 支持的模型类型
    supports_claude = Column(Boolean, default=False)
    supports_gemini = Column(Boolean, default=False)
    
    # 统计
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    last_error = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    user = relationship("User", back_populates="tokens")


class UsageLog(Base):
    """使用日志"""
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=True)
    
    model = Column(String(100), nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    user = relationship("User", back_populates="usage_logs")


class SystemConfig(Base):
    """系统配置"""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
