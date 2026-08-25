from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    message = Column(String, nullable=False)
    response = Column(String, nullable=False)

    state = Column(String, default=None)  # for multi-turn chatbot

    timestamp = Column(DateTime, default=datetime.utcnow)