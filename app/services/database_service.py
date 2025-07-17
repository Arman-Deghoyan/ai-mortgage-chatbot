"""Database service for managing conversations and messages"""

from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.database import Conversation, Message, UserInput
from app.models.mortgage import UserInputs
from app.utils.logger import LoggerMixin


class DatabaseService(LoggerMixin):
    """Service for database operations"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def create_conversation(self, user_id: Optional[str] = None) -> Conversation:
        """Create a new conversation"""
        try:
            conversation = Conversation(user_id=user_id)
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)

            self.logger.info(
                "Created new conversation", conversation_id=conversation.id
            )
            return conversation
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error("Failed to create conversation", error=str(e))
            raise

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        try:
            conversation = (
                self.db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            return conversation
        except SQLAlchemyError as e:
            self.logger.error(
                "Failed to get conversation",
                error=str(e),
                conversation_id=conversation_id,
            )
            return None

    def update_conversation_step(self, conversation_id: str, step: int) -> bool:
        """Update conversation step"""
        try:
            conversation = self.get_conversation(conversation_id)
            if conversation:
                conversation.current_step = step
                self.db.commit()
                self.logger.info(
                    "Updated conversation step",
                    conversation_id=conversation_id,
                    step=step,
                )
                return True
            return False
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error("Failed to update conversation step", error=str(e))
            return False

    def complete_conversation(self, conversation_id: str) -> bool:
        """Mark conversation as completed"""
        try:
            conversation = self.get_conversation(conversation_id)
            if conversation:
                conversation.status = "completed"
                self.db.commit()
                self.logger.info(
                    "Completed conversation", conversation_id=conversation_id
                )
                return True
            return False
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error("Failed to complete conversation", error=str(e))
            return False

    def add_message(
        self, conversation_id: str, role: str, content: str
    ) -> Optional[Message]:
        """Add a message to conversation"""
        try:
            message = Message(
                conversation_id=conversation_id, role=role, content=content
            )
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)

            self.logger.info(
                "Added message", conversation_id=conversation_id, role=role
            )
            return message
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error("Failed to add message", error=str(e))
            return None

    def get_conversation_messages(self, conversation_id: str) -> List[Message]:
        """Get all messages for a conversation"""
        try:
            messages = (
                self.db.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(Message.timestamp)
                .all()
            )
            return messages
        except SQLAlchemyError as e:
            self.logger.error("Failed to get messages", error=str(e))
            return []

    def get_or_create_user_inputs(self, conversation_id: str) -> UserInput:
        """Get or create user inputs for conversation"""
        try:
            user_input = (
                self.db.query(UserInput)
                .filter(UserInput.conversation_id == conversation_id)
                .first()
            )

            if not user_input:
                user_input = UserInput(conversation_id=conversation_id)
                self.db.add(user_input)
                self.db.commit()
                self.db.refresh(user_input)
                self.logger.info("Created user inputs", conversation_id=conversation_id)

            return user_input
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error("Failed to get/create user inputs", error=str(e))
            raise

    def update_user_input_field(self, conversation_id: str, field: str, value) -> bool:
        """Update a specific field in user inputs"""
        try:
            user_input = self.get_or_create_user_inputs(conversation_id)
            setattr(user_input, field, value)
            self.db.commit()

            self.logger.info(
                "Updated user input field",
                conversation_id=conversation_id,
                field=field,
                value=value,
            )
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error("Failed to update user input field", error=str(e))
            return False

    def get_user_inputs(self, conversation_id: str) -> Optional[UserInputs]:
        """Get user inputs as pydantic model"""
        try:
            user_input = (
                self.db.query(UserInput)
                .filter(UserInput.conversation_id == conversation_id)
                .first()
            )

            if user_input:
                return user_input.to_user_inputs_model()
            return None
        except SQLAlchemyError as e:
            self.logger.error("Failed to get user inputs", error=str(e))
            return None

    def get_conversation_history_for_service(self, conversation_id: str) -> List[dict]:
        """Get conversation history in format expected by conversation service"""
        messages = self.get_conversation_messages(conversation_id)
        return [
            {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
            for msg in messages
        ]
