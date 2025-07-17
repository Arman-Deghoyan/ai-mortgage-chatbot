"""Database models for conversation persistence"""

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

from app.models.mortgage import CreditScoreCategory

Base = declarative_base()


class Conversation(Base):
    """Represents a conversation session"""

    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True)  # For future user management
    status = Column(
        String,
        default="in_progress",
        nullable=False,
    )  # in_progress, completed, abandoned
    current_step = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    user_inputs = relationship(
        "UserInput",
        back_populates="conversation",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Message(Base):
    """Represents a single message in a conversation"""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class UserInput(Base):
    """Represents collected user inputs for mortgage assessment"""

    __tablename__ = "user_inputs"

    conversation_id = Column(String, ForeignKey("conversations.id"), primary_key=True)
    annual_income = Column(Float, nullable=True)
    monthly_debt = Column(Float, nullable=True)
    credit_score_category = Column(Enum(CreditScoreCategory), nullable=True)
    property_value = Column(Float, nullable=True)
    down_payment = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="user_inputs")

    def is_complete(self) -> bool:
        """Check if all required inputs are collected"""
        return all(
            [
                self.annual_income is not None,
                self.monthly_debt is not None,
                self.credit_score_category is not None,
                self.property_value is not None,
                self.down_payment is not None,
            ]
        )

    def to_user_inputs_model(self):
        """Convert to UserInputs pydantic model"""
        from app.models.mortgage import UserInputs

        return UserInputs(
            annual_income=self.annual_income,
            monthly_debt=self.monthly_debt,
            credit_score_category=self.credit_score_category,
            property_value=self.property_value,
            down_payment=self.down_payment,
        )


# Database setup
def create_database_engine(database_url: str = "sqlite:///./mortgage_chatbot.db"):
    """Create database engine"""
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        echo=False,  # Set to True for SQL debugging
    )
    return engine


def create_tables(engine):
    """Create all tables"""
    Base.metadata.create_all(bind=engine)


def get_session_maker(engine):
    """Get session maker"""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
