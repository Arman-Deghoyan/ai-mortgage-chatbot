import time

import pytest
import requests


@pytest.mark.integration
class TestRealConversationFlow:
    """Test the actual conversation flow using real API calls"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Wait for API to be ready"""
        time.sleep(1)

    @pytest.mark.skip(
        reason="Requires running server and uses deprecated conversation_history approach"
    )
    def test_complete_conversation_flow(self):
        """Test the complete conversation from Hello to assessment result"""
        base_url = "http://localhost:8000"
        conversation_history = []

        # Check if server is running
        try:
            requests.get(f"{base_url}/health", timeout=2)
        except requests.exceptions.ConnectionError:
            pytest.skip("API server not running at localhost:8000")

        # Step 1: Hello - Should greet and ask for confirmation
        print("\n=== Step 1: Hello ===")
        response = requests.post(
            f"{base_url}/chat",
            json={"message": "Hello", "conversation_history": conversation_history},
        )
        assert response.status_code == 200
        data = response.json()

        # Should contain greeting words and ask for confirmation
        response_text = data["response"].lower()
        assert any(word in response_text for word in ["welcome", "hello", "hi"])
        assert any(
            word in response_text for word in ["begin", "start", "ready", "assessment"]
        )
        assert "income" not in response_text  # Should NOT ask for income yet

        # Update history
        conversation_history.extend(
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": data["response"]},
            ]
        )

        # Step 2: Yes - Should ask for income
        print("=== Step 2: Yes ===")
        response = requests.post(
            f"{base_url}/chat",
            json={"message": "Yes", "conversation_history": conversation_history},
        )
        assert response.status_code == 200
        data = response.json()

        # Should ask for income
        response_text = data["response"].lower()
        assert "income" in response_text
        assert "annual" in response_text
        assert "debt" not in response_text  # Should NOT ask for debt yet

        # Update history
        conversation_history.extend(
            [
                {"role": "user", "content": "Yes"},
                {"role": "assistant", "content": data["response"]},
            ]
        )

        # Step 3: 80000 - Should ask for debt
        print("=== Step 3: 80000 (Income) ===")
        response = requests.post(
            f"{base_url}/chat",
            json={"message": "80000", "conversation_history": conversation_history},
        )
        assert response.status_code == 200
        data = response.json()

        # Should ask for debt
        response_text = data["response"].lower()
        assert "debt" in response_text
        assert "monthly" in response_text
        assert (
            "credit score" not in response_text
        )  # Should NOT ask for credit score yet

        # Update history
        conversation_history.extend(
            [
                {"role": "user", "content": "80000"},
                {"role": "assistant", "content": data["response"]},
            ]
        )

        # Step 4: 2000 - Should ask for credit score
        print("=== Step 4: 2000 (Debt) ===")
        response = requests.post(
            f"{base_url}/chat",
            json={"message": "2000", "conversation_history": conversation_history},
        )
        assert response.status_code == 200
        data = response.json()

        # Should ask for credit score
        response_text = data["response"].lower()
        assert "credit" in response_text
        assert "score" in response_text
        assert (
            "property value" not in response_text
        )  # Should NOT ask for property value yet

        # Update history
        conversation_history.extend(
            [
                {"role": "user", "content": "2000"},
                {"role": "assistant", "content": data["response"]},
            ]
        )

        # Step 5: Good - Should ask for property value
        print("=== Step 5: Good (Credit Score) ===")
        response = requests.post(
            f"{base_url}/chat",
            json={"message": "Good", "conversation_history": conversation_history},
        )
        assert response.status_code == 200
        data = response.json()

        # Should ask for property value
        response_text = data["response"].lower()
        assert "property" in response_text
        assert "value" in response_text
        assert (
            "down payment" not in response_text and "downpayment" not in response_text
        )  # Should NOT ask for down payment yet

        # Update history
        conversation_history.extend(
            [
                {"role": "user", "content": "Good"},
                {"role": "assistant", "content": data["response"]},
            ]
        )

        # Step 6: 400000 - Should ask for down payment
        print("=== Step 6: 400000 (Property Value) ===")
        response = requests.post(
            f"{base_url}/chat",
            json={"message": "400000", "conversation_history": conversation_history},
        )
        assert response.status_code == 200
        data = response.json()

        # Should ask for down payment
        response_text = data["response"].lower()
        assert "down payment" in response_text or "downpayment" in response_text

        # Update history
        conversation_history.extend(
            [
                {"role": "user", "content": "400000"},
                {"role": "assistant", "content": data["response"]},
            ]
        )

        # Step 7: 80000 - Should provide assessment
        print("=== Step 7: 80000 (Down Payment) ===")
        response = requests.post(
            f"{base_url}/chat",
            json={"message": "80000", "conversation_history": conversation_history},
        )
        assert response.status_code == 200
        data = response.json()

        # Should provide assessment result
        assert data.get("conversation_complete", False)
        assert data.get("assessment_result") is not None

        print("✅ Complete conversation flow test PASSED!")
