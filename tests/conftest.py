"""Pytest configuration and fixtures for the AI Mortgage Advisor Chatbot."""

import os
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.mortgage import ChatRequest, ChatResponse


@pytest.fixture
def mock_conversation_service():
    """Create a comprehensive mock for conversation service."""
    mock_service = AsyncMock()

    # Mock the process_message method
    def create_chat_response(*args, **kwargs):
        user_message = kwargs.get("user_message", "Hello")

        # Simulate different responses based on user input
        if (
            "income" in user_message.lower()
            or "80000" in user_message
            or "75000" in user_message
        ):
            return {
                "response": "What are your total monthly debt payments?",
                "conversation_complete": False,
                "assessment_result": None,
            }
        elif "debt" in user_message.lower() or "1500" in user_message:
            return {
                "response": "What is your credit score category? (Excellent/Good/Fair/Poor)",
                "conversation_complete": False,
                "assessment_result": None,
            }
        elif "credit" in user_message.lower() or "good" in user_message.lower():
            return {
                "response": "What is the value of the property you want to purchase?",
                "conversation_complete": False,
                "assessment_result": None,
            }
        elif "property" in user_message.lower() or "400000" in user_message:
            return {
                "response": "How much down payment do you have saved?",
                "conversation_complete": False,
                "assessment_result": None,
            }
        elif "down payment" in user_message.lower() or "85000" in user_message:
            return {
                "response": "Thank you! Here's your assessment:",
                "conversation_complete": True,
                "assessment_result": {
                    "user_inputs": {
                        "annual_income": 80000,
                        "monthly_debt": 1500,
                        "credit_score_category": "Good",
                        "property_value": 400000,
                        "down_payment": 85000,
                    },
                    "calculated_metrics": {"dti_ratio": 0.225, "ltv_ratio": 0.7875},
                    "assessment": {
                        "outcome": "Approved",
                        "notes": "User meets all preliminary criteria for a standard mortgage.",
                    },
                },
            }
        else:
            # Default greeting response
            return {
                "response": "Hello! I'm here to assist you with your mortgage assessment. Could you please share your total gross annual income with me in dollars?",
                "conversation_complete": False,
                "assessment_result": None,
            }

    mock_service.process_message.side_effect = create_chat_response
    mock_service.reset_conversation.return_value = None

    return mock_service


@pytest.fixture
def mock_llm_service():
    """Create a comprehensive mock for LLM service."""
    mock_service = AsyncMock()

    # Mock the process_message method
    def create_chat_response(*args, **kwargs):
        user_message = kwargs.get("user_message", "Hello")

        # Simulate different responses based on user input
        if "income" in user_message.lower():
            return ChatResponse(
                message="What is your annual gross income?",
                conversation_complete=False,
                assessment_result=None,
            )
        elif "debt" in user_message.lower():
            return ChatResponse(
                message="What are your total monthly debt payments?",
                conversation_complete=False,
                assessment_result=None,
            )
        elif "credit" in user_message.lower():
            return ChatResponse(
                message="What is your credit score category? (Excellent/Good/Fair/Poor)",
                conversation_complete=False,
                assessment_result=None,
            )
        elif "property" in user_message.lower():
            return ChatResponse(
                message="What is the value of the property you want to purchase?",
                conversation_complete=False,
                assessment_result=None,
            )
        elif "down payment" in user_message.lower():
            return ChatResponse(
                message="How much down payment do you have saved?",
                conversation_complete=False,
                assessment_result=None,
            )
        else:
            # Simulate final assessment
            return ChatResponse(
                message="Thank you! Here's your assessment:",
                conversation_complete=True,
                assessment_result={
                    "user_inputs": {
                        "annual_income": 80000,
                        "monthly_debt": 1500,
                        "credit_score_category": "Good",
                        "property_value": 400000,
                        "down_payment": 85000,
                    },
                    "calculated_metrics": {"dti_ratio": 0.225, "ltv_ratio": 0.7875},
                    "assessment": {
                        "outcome": "Approved",
                        "notes": "User meets all preliminary criteria for a standard mortgage.",
                    },
                },
            )

    mock_service.process_message.side_effect = create_chat_response
    mock_service.get_conversation_state.return_value = {"step": "greeting"}
    mock_service.reset_conversation.return_value = None

    return mock_service


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Create an HTTP client for testing the API."""
    # Trigger app startup event to create database tables
    from app.main import startup_event

    await startup_event()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_chat_request() -> ChatRequest:
    """Create a sample chat request for testing."""
    return ChatRequest(
        message="Hello, I want to check my mortgage eligibility",
        conversation_history=[],
    )


@pytest.fixture
def sample_assessment_result() -> dict[str, Any]:
    """Create a sample assessment result for testing."""
    return {
        "user_inputs": {
            "annual_income": 80000,
            "monthly_debt": 1500,
            "credit_score_category": "Good",
            "property_value": 400000,
            "down_payment": 85000,
        },
        "calculated_metrics": {"dti_ratio": 0.225, "ltv_ratio": 0.7875},
        "assessment": {
            "outcome": "Approved",
            "notes": "User meets all preliminary criteria for a standard mortgage.",
        },
    }


@pytest.fixture(autouse=True)
def mock_openai_api():
    """Mock OpenAI API calls to avoid real API calls during testing."""
    with patch("openai.AsyncOpenAI") as mock_openai:
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        # Mock the chat completion
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = "Mocked response from OpenAI"
        mock_response.usage.total_tokens = 100

        mock_client.chat.completions.create.return_value = mock_response

        yield mock_openai


@pytest.fixture(autouse=True)
def mock_langchain_openai():
    """Mock LangChain OpenAI calls to avoid real API calls during testing."""
    with patch("langchain_openai.ChatOpenAI") as mock_chat_openai:
        mock_llm = AsyncMock()
        mock_chat_openai.return_value = mock_llm

        # Mock the invoke method
        mock_response = AsyncMock()
        mock_response.content = "Mocked response from LangChain OpenAI"
        mock_llm.invoke.return_value = mock_response

        yield mock_chat_openai


@pytest.fixture(autouse=True)
def mock_conversation_service_dependency():
    """Mock the conversation service dependency to avoid real API calls."""
    with patch("app.main.get_conversation_service") as mock_get_service:
        mock_service = AsyncMock()

        # Mock the process_message method with fast responses
        def create_fast_response(*args, **kwargs):
            user_message = kwargs.get("user_message", "Hello")

            # Simple mock responses without any LLM calls
            if (
                "income" in user_message.lower()
                or "80000" in user_message
                or "75000" in user_message
            ):
                return {
                    "response": "What are your total monthly debt payments?",
                    "conversation_complete": False,
                    "assessment_result": None,
                }
            elif "debt" in user_message.lower() or "1500" in user_message:
                return {
                    "response": "What is your credit score category? (Excellent/Good/Fair/Poor)",
                    "conversation_complete": False,
                    "assessment_result": None,
                }
            elif "credit" in user_message.lower() or "good" in user_message.lower():
                return {
                    "response": "What is the value of the property you want to purchase?",
                    "conversation_complete": False,
                    "assessment_result": None,
                }
            elif "property" in user_message.lower() or "400000" in user_message:
                return {
                    "response": "How much down payment do you have saved?",
                    "conversation_complete": False,
                    "assessment_result": None,
                }
            elif "down payment" in user_message.lower() or "85000" in user_message:
                return {
                    "response": "Thank you! Here's your assessment:",
                    "conversation_complete": True,
                    "assessment_result": {
                        "user_inputs": {
                            "annual_income": 80000,
                            "monthly_debt": 1500,
                            "credit_score_category": "Good",
                            "property_value": 400000,
                            "down_payment": 85000,
                        },
                        "calculated_metrics": {"dti_ratio": 0.225, "ltv_ratio": 0.7875},
                        "assessment": {
                            "outcome": "Approved",
                            "notes": "User meets all preliminary criteria for a standard mortgage.",
                        },
                    },
                }
            else:
                # Default greeting response
                return {
                    "response": "Hello! I'm here to assist you with your mortgage assessment. Could you please share your total gross annual income with me in dollars?",
                    "conversation_complete": False,
                    "assessment_result": None,
                }

        mock_service.process_message.side_effect = create_fast_response
        mock_service.reset_conversation.return_value = None

        mock_get_service.return_value = mock_service
        yield mock_get_service


@pytest.fixture(autouse=True)
def mock_all_langchain_calls():
    """Mock all LangChain calls to prevent any real API calls."""
    with patch("langchain_openai.ChatOpenAI") as mock_chat_openai:
        # Mock ChatOpenAI
        mock_llm = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "Mocked response from LangChain OpenAI"
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm

        yield


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key", "DEBUG": "false"}):
        yield
