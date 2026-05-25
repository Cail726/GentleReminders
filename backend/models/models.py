from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, func
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(128), nullable=False)
    nickname = Column(String(50), default="", nullable=False)
    create_time = Column(DateTime, default=func.now(), nullable=False)


class CheckIn(Base):
    __tablename__ = "checkins"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    emotion = Column(String(10), nullable=False)
    content = Column(String(2000), default="")
    create_time = Column(DateTime, default=func.now(), nullable=False, index=True)


class Tree(Base):
    __tablename__ = "trees"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    health = Column(Integer, default=100)


class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(128), nullable=False)
    must_change_password = Column(Boolean, default=True, nullable=False)


class ScaleResponse(Base):
    __tablename__ = "scale_responses"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    scale_type = Column(String(50), default="simplified_wellbeing")
    answers = Column(String, nullable=False)
    dimension_scores = Column(String, nullable=False)
    total_score = Column(Float, default=0.0)
    create_time = Column(DateTime, default=func.now(), nullable=False)


class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    dimension_scores = Column(String, nullable=False)
    suggestions = Column(String, nullable=False)
    feature_summary = Column(String, nullable=False)
    confidence = Column(String(20), default="low")
    create_time = Column(DateTime, default=func.now(), nullable=False)


class Letter(Base):
    __tablename__ = "letters"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tree_level = Column(Integer, nullable=False)
    title = Column(String(100), nullable=False)
    content = Column(String(3000), nullable=False)
    emotion_summary = Column(String(200), default="")
    create_time = Column(DateTime, default=func.now(), nullable=False)
