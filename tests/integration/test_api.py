"""Integration tests for the AI Mortgage Advisor API."""

import pytest
from httpx import AsyncClient


class TestAPIEndpoints:
    """Test cases for API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test the health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test the root endpoint."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
        assert "chat" in data["endpoints"]

    @pytest.mark.asyncio
    async def test_chat_endpoint_basic(self, client: AsyncClient):
        """Test basic chat functionality."""
        chat_request = {
            "message": "Hello, I want to check my mortgage eligibility",
            "conversation_history": [],
        }

        response = await client.post("/chat", json=chat_request)
        assert response.status_code == 200

        data = response.json()
        assert "response" in data
        assert "conversation_complete" in data
        assert isinstance(data["conversation_complete"], bool)

    @pytest.mark.asyncio
    async def test_chat_endpoint_with_history(self, client: AsyncClient):
        """Test chat with conversation history."""
        chat_request = {
            "message": "My annual income is $80,000",
            "conversation_history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "What is your annual income?"},
            ],
        }

        response = await client.post("/chat", json=chat_request)
        assert response.status_code == 200

        data = response.json()
        assert "response" in data

    @pytest.mark.asyncio
    async def test_chat_endpoint_invalid_request(self, client: AsyncClient):
        """Test chat endpoint with invalid request."""
        # Missing message field
        invalid_request = {"conversation_history": []}
        response = await client.post("/chat", json=invalid_request)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_reset_conversation_endpoint(self, client: AsyncClient):
        """Test conversation reset endpoint (now starts new conversation)."""
        response = await client.post("/conversation/reset")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "conversation_id" in data
        assert "new conversation started successfully" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_chat_conversation_flow(self, client: AsyncClient):
        """Test a complete conversation flow."""
        # Step 1: Initial greeting
        response1 = await client.post(
            "/chat", json={"message": "Hello", "conversation_history": []}
        )
        assert response1.status_code == 200

        # Step 2: Provide income
        response2 = await client.post(
            "/chat",
            json={
                "message": "My annual income is $80,000",
                "conversation_history": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": response1.json()["response"]},
                ],
            },
        )
        assert response2.status_code == 200

        # Step 3: Provide debt
        response3 = await client.post(
            "/chat",
            json={
                "message": "My monthly debt is $1,500",
                "conversation_history": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": response1.json()["response"]},
                    {"role": "user", "content": "My annual income is $80,000"},
                    {"role": "assistant", "content": response2.json()["response"]},
                ],
            },
        )
        assert response3.status_code == 200

    @pytest.mark.asyncio
    async def test_error_handling(self, client: AsyncClient):
        """Test error handling scenarios."""
        # Test with malformed JSON
        response = await client.post("/chat", content="invalid json")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_api_documentation(self, client: AsyncClient):
        """Test that API documentation is accessible."""
        response = await client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_openapi_schema(self, client: AsyncClient):
        """Test that OpenAPI schema is accessible."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        assert "/chat" in schema["paths"]
        assert "/health" in schema["paths"]


class TestChatbotLogic:
    """Test the chatbot's logical flow and responses."""

    @pytest.mark.asyncio
    async def test_greeting_response(self, client: AsyncClient):
        """Test that the chatbot responds appropriately to greetings."""
        greetings = ["Hello", "Hi there", "Good morning", "I need help with mortgage"]

        for greeting in greetings:
            response = await client.post(
                "/chat", json={"message": greeting, "conversation_history": []}
            )
            assert response.status_code == 200

            data = response.json()
            assert "response" in data
            # The response should contain mortgage-related keywords
            message_lower = data["response"].lower()
            assert any(
                keyword in message_lower
                for keyword in [
                    "mortgage",
                    "eligibility",
                    "income",
                    "help",
                    "advisor",
                    "assessment",
                ]
            )

    @pytest.mark.asyncio
    async def test_income_collection(self, client: AsyncClient):
        """Test income collection flow."""
        # First, start the conversation
        response1 = await client.post(
            "/chat",
            json={"message": "Hello", "conversation_history": []},
        )
        assert response1.status_code == 200

        data1 = response1.json()
        conversation_id = data1["conversation_id"]

        # Confirm we want to start the assessment
        response2 = await client.post(
            "/chat",
            json={
                "message": "Yes, I'd like to start the assessment",
                "conversation_id": conversation_id,
                "conversation_history": [],
            },
        )
        assert response2.status_code == 200

        # Then provide income (this should be step 3, asking for income)
        response3 = await client.post(
            "/chat",
            json={
                "message": "My annual income is $75,000",
                "conversation_id": conversation_id,
                "conversation_history": [],
            },
        )
        assert response3.status_code == 200

        data3 = response3.json()
        # Should return a debt-related question after income is provided
        message_lower = data3["response"].lower()
        # Should contain debt-related keywords
        assert any(
            keyword in message_lower for keyword in ["debt", "monthly", "payments"]
        )

    @pytest.mark.asyncio
    async def test_conversation_completion(self, client: AsyncClient):
        """Test that conversation can reach completion state."""
        # This test would require a more sophisticated mock
        # that can simulate the full conversation flow
        response = await client.post(
            "/chat",
            json={
                "message": "Complete my assessment",
                "conversation_history": [
                    {"role": "assistant", "content": "What is your annual income?"},
                    {"role": "user", "content": "$80,000"},
                    {
                        "role": "assistant",
                        "content": "What are your monthly debt payments?",
                    },
                    {"role": "user", "content": "$1,500"},
                    {
                        "role": "assistant",
                        "content": "What is your credit score category?",
                    },
                    {"role": "user", "content": "Good"},
                    {"role": "assistant", "content": "What is the property value?"},
                    {"role": "user", "content": "$400,000"},
                    {"role": "assistant", "content": "What is your down payment?"},
                    {"role": "user", "content": "$85,000"},
                ],
            },
        )
        assert response.status_code == 200

        data = response.json()
        # Should eventually complete with assessment
        if data.get("conversation_complete"):
            assert "assessment_result" in data
            assessment = data["assessment_result"]
            assert "user_inputs" in assessment
            assert "calculated_metrics" in assessment
            assert "assessment" in assessment


class TestPerformance:
    """Test API performance characteristics."""

    @pytest.mark.asyncio
    async def test_response_time(self, client: AsyncClient):
        """Test that API responses are reasonably fast."""
        import time

        start_time = time.time()
        response = await client.get("/health")
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should respond within 1 second

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client: AsyncClient):
        """Test handling of concurrent requests."""
        import asyncio

        async def make_request():
            return await client.get("/health")

        # Make 5 concurrent requests
        tasks = [make_request() for _ in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
