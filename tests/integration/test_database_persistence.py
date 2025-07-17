"""Integration tests for database persistence functionality"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import create_tables
from app.services.database_service import DatabaseService
from app.services.persistent_conversation_service import PersistentConversationService


@pytest.fixture
def test_db():
    """Create a test database for testing"""
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:", echo=False)
    create_tables(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    yield session

    session.close()


@pytest.fixture
def db_service(test_db):
    """Create a database service for testing"""
    return DatabaseService(test_db)


@pytest.fixture
def conversation_service(db_service):
    """Create a conversation service for testing"""
    # Use a dummy API key for testing
    return PersistentConversationService("test-api-key", db_service)


class TestDatabasePersistence:
    """Test database persistence functionality"""

    def test_create_conversation(self, db_service):
        """Test creating a new conversation"""
        conversation = db_service.create_conversation()

        assert conversation.id is not None
        assert conversation.status == "in_progress"
        assert conversation.current_step == 1

    def test_add_message(self, db_service):
        """Test adding messages to conversation"""
        conversation = db_service.create_conversation()

        # Add user message
        user_msg = db_service.add_message(conversation.id, "user", "Hello")
        assert user_msg.role == "user"
        assert user_msg.content == "Hello"

        # Add assistant message
        assistant_msg = db_service.add_message(
            conversation.id, "assistant", "Hi there!"
        )
        assert assistant_msg.role == "assistant"
        assert assistant_msg.content == "Hi there!"

        # Check message history
        messages = db_service.get_conversation_messages(conversation.id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_user_inputs(self, db_service):
        """Test user input management"""
        conversation = db_service.create_conversation()

        # Update user inputs
        assert db_service.update_user_input_field(
            conversation.id, "annual_income", 75000.0
        )
        assert db_service.update_user_input_field(
            conversation.id, "monthly_debt", 1500.0
        )

        # Get user inputs
        user_inputs = db_service.get_user_inputs(conversation.id)
        assert user_inputs is not None
        assert user_inputs.annual_income == 75000.0
        assert user_inputs.monthly_debt == 1500.0

    def test_conversation_state_management(self, db_service):
        """Test conversation state management"""
        conversation = db_service.create_conversation()

        # Update step
        assert db_service.update_conversation_step(conversation.id, 3)

        # Get conversation
        updated_conversation = db_service.get_conversation(conversation.id)
        assert updated_conversation.current_step == 3

        # Complete conversation
        assert db_service.complete_conversation(conversation.id)

        # Check status
        completed_conversation = db_service.get_conversation(conversation.id)
        assert completed_conversation.status == "completed"

    def test_conversation_history_format(self, db_service):
        """Test conversation history format for service"""
        conversation = db_service.create_conversation()

        # Add some messages
        db_service.add_message(conversation.id, "user", "Hello")
        db_service.add_message(conversation.id, "assistant", "Hi there!")
        db_service.add_message(conversation.id, "user", "How are you?")

        # Get history in service format
        history = db_service.get_conversation_history_for_service(conversation.id)

        assert len(history) == 3
        assert all(
            "role" in msg and "content" in msg and "timestamp" in msg for msg in history
        )
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there!"


@pytest.mark.integration
class TestPersistentConversationService:
    """Test the persistent conversation service"""

    def test_start_new_conversation(self, conversation_service):
        """Test starting a new conversation"""
        # Mock the LLM to avoid API calls in tests
        conversation_service.llm = None

        conversation_id = conversation_service.start_new_conversation()
        assert conversation_id is not None
        assert isinstance(conversation_id, str)

    def test_continue_conversation_check(self, conversation_service):
        """Test checking if conversation can be continued"""
        # Mock the LLM to avoid API calls
        conversation_service.llm = None

        conversation_id = conversation_service.start_new_conversation()

        # Check continuation
        continue_info = conversation_service.continue_conversation(conversation_id)
        assert continue_info is not None
        assert continue_info["conversation_exists"] is True
        assert continue_info["current_step"] == 1
        assert continue_info["message_count"] == 0

    def test_get_conversation_history(self, conversation_service):
        """Test getting conversation history"""
        # Mock the LLM to avoid API calls
        conversation_service.llm = None

        conversation_id = conversation_service.start_new_conversation()

        # Add some messages directly to database
        conversation_service.db.add_message(conversation_id, "user", "Test message")
        conversation_service.db.add_message(
            conversation_id, "assistant", "Test response"
        )

        # Get history
        history = conversation_service.get_conversation_history(conversation_id)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_nonexistent_conversation(self, conversation_service):
        """Test handling of nonexistent conversation"""
        fake_id = str(uuid.uuid4())

        continue_info = conversation_service.continue_conversation(fake_id)
        assert continue_info is None

        history = conversation_service.get_conversation_history(fake_id)
        assert history == []
