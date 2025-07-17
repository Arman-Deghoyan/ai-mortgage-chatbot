# Configuration
from typing import Any, Dict

import requests
import streamlit as st

from app.config import settings

# Use configured API base URL
API_BASE_URL = settings.api_base_url

# Page configuration
st.set_page_config(
    page_title=settings.app_name,
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        text-align: center;
        color: #2E86AB;
        font-size: 2.5rem;
        margin-bottom: 2rem;
    }

    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        max-width: 80%;
    }

    .user-message {
        background-color: #E3F2FD;
        margin-left: auto;
        text-align: right;
    }

    .bot-message {
        background-color: #F1F8E9;
        margin-right: auto;
    }

    .assessment-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .metric-card {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        color: #333;
    }

    .approved {
        border-left: 5px solid #4CAF50;
    }

    .pre-qualified {
        border-left: 5px solid #FF9800;
    }

    .needs-review {
        border-left: 5px solid #F44336;
    }
</style>
""",
    unsafe_allow_html=True,
)


def initialize_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_complete" not in st.session_state:
        st.session_state.conversation_complete = False
    if "assessment_result" not in st.session_state:
        st.session_state.assessment_result = None
    if "api_connected" not in st.session_state:
        st.session_state.api_connected = False


def check_api_health() -> bool:
    """Check if the API is healthy"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200 and response.json().get("status") == "ok"
    except requests.exceptions.RequestException:
        return False


def send_message(message: str) -> Dict[str, Any]:
    """Send a message to the chatbot API"""
    try:
        # Get conversation ID from session state
        conversation_id = st.session_state.get("conversation_id", None)

        # Build conversation history from session state (for compatibility)
        conversation_history = []
        for msg in st.session_state.messages:
            conversation_history.append(
                {"role": msg["role"], "content": msg["content"]}
            )

        payload = {"message": message, "conversation_history": conversation_history}

        # Add conversation_id if we have one
        if conversation_id:
            payload["conversation_id"] = conversation_id

        response = requests.post(
            f"{API_BASE_URL}/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()

        # Store conversation_id in session state
        if "conversation_id" in result:
            st.session_state.conversation_id = result["conversation_id"]

        return result
    except requests.exceptions.RequestException as e:
        st.error(f"Error communicating with API: {str(e)}")
        return {}


def reset_conversation():
    """Start a new conversation"""
    try:
        response = requests.post(f"{API_BASE_URL}/conversation/reset", timeout=5)
        result = response.json() if response.status_code == 200 else {}

        # Clear session state
        st.session_state.messages = []
        st.session_state.conversation_complete = False
        st.session_state.assessment_result = None

        # Start new conversation if API provides conversation_id
        if "conversation_id" in result:
            st.session_state.conversation_id = result["conversation_id"]
        else:
            # Clear old conversation_id to start fresh
            if "conversation_id" in st.session_state:
                del st.session_state.conversation_id

        st.success("New conversation started successfully!")
        st.rerun()
    except requests.exceptions.RequestException as e:
        st.error(f"Error starting new conversation: {str(e)}")


def display_message(role: str, content: str):
    """Display a chat message"""
    if role == "user":
        st.markdown(
            f'<div class="chat-message user-message">👤 **You:** {content}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="chat-message bot-message">🤖 **AI Advisor:** {content}</div>',
            unsafe_allow_html=True,
        )


def display_assessment_result(assessment: Dict[str, Any]):
    """Display the mortgage assessment result"""
    st.markdown('<div class="assessment-card">', unsafe_allow_html=True)
    st.markdown("### 📋 Mortgage Assessment Result")

    # Create three columns for better layout
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 💰 Financial Information")
        user_inputs = assessment["user_inputs"]
        st.write(f"**Annual Income:** ${user_inputs['annual_income']:,.0f}")
        st.write(f"**Monthly Debt:** ${user_inputs['monthly_debt']:,.0f}")
        st.write(f"**Credit Score:** {user_inputs['credit_score_category']}")
        st.write(f"**Property Value:** ${user_inputs['property_value']:,.0f}")
        st.write(f"**Down Payment:** ${user_inputs['down_payment']:,.0f}")

    with col2:
        st.markdown("#### 📊 Calculated Metrics")
        metrics = assessment["calculated_metrics"]
        dti_percentage = metrics["dti_ratio"] * 100
        ltv_percentage = metrics["ltv_ratio"] * 100

        st.metric(
            label="Debt-to-Income Ratio",
            value=f"{dti_percentage:.1f}%",
            delta=f"{'✅ Good' if dti_percentage < 43 else '❌ High'}",
        )
        st.metric(
            label="Loan-to-Value Ratio",
            value=f"{ltv_percentage:.1f}%",
            delta=f"{'✅ Good' if ltv_percentage < 80 else '⚠️ High' if ltv_percentage <= 95 else '❌ Too High'}",
        )

    with col3:
        st.markdown("#### 🎯 Assessment Result")
        outcome = assessment["assessment"]["outcome"]
        notes = assessment["assessment"]["notes"]

        # Style based on outcome
        if outcome == "Approved":
            st.success(f"✅ **{outcome}**")
            st.markdown(
                f'<div class="metric-card approved"><strong>Status:</strong> {notes}</div>',
                unsafe_allow_html=True,
            )
        elif outcome == "Pre-qualified with Conditions":
            st.warning(f"⚠️ **{outcome}**")
            st.markdown(
                f'<div class="metric-card pre-qualified"><strong>Status:</strong> {notes}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.error(f"❌ **{outcome}**")
            st.markdown(
                f'<div class="metric-card needs-review"><strong>Status:</strong> {notes}</div>',
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)

    # Add JSON export
    with st.expander("📄 View Raw JSON Assessment"):
        st.json(assessment)


def main():
    """Main application function"""
    initialize_session_state()

    # Header
    st.markdown(
        '<h1 class="main-header">🏠 AI Mortgage Advisor</h1>', unsafe_allow_html=True
    )
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.markdown("### 🛠️ Controls")

        # API Status
        if st.button("🔄 Check API Status"):
            st.session_state.api_connected = check_api_health()

        if st.session_state.api_connected:
            st.success("✅ API Connected")
        else:
            st.error("❌ API Disconnected")
            if st.button("🔌 Connect to API"):
                st.session_state.api_connected = check_api_health()

        st.markdown("---")

        # Reset button
        if st.button("🔄 Reset Conversation", type="secondary"):
            reset_conversation()

        st.markdown("---")

        # Information
        st.markdown("### ℹ️ About")
        st.markdown(
            """
        This AI Mortgage Advisor helps you assess your preliminary mortgage eligibility.

        **Information Required:**
        - Annual income
        - Monthly debt payments
        - Credit score category
        - Property value
        - Down payment amount

        **Assessment Criteria:**
        - **Approved**: DTI < 43%, LTV < 80%, Good+ credit
        - **Pre-qualified**: DTI < 43%, LTV 80-95%
        - **Manual Review**: DTI ≥ 43% or Fair/Poor credit
        """
        )

    # Main content area
    main_container = st.container()

    with main_container:
        # Check API connection on load
        if not st.session_state.api_connected:
            st.session_state.api_connected = check_api_health()

        if not st.session_state.api_connected:
            st.error(
                "🚨 Cannot connect to the API. Please make sure the FastAPI server is running on http://localhost:8000"
            )
            st.info(
                "Start the server with: `uvicorn app.main:app --host 0.0.0.0 --port 8000`"
            )
            return

        # Display conversation history
        chat_container = st.container()
        with chat_container:
            if not st.session_state.messages:
                st.info(
                    "👋 Welcome! Click the button below to start your mortgage eligibility assessment."
                )

            for message in st.session_state.messages:
                display_message(message["role"], message["content"])

        # Display assessment result if conversation is complete
        if (
            st.session_state.conversation_complete
            and st.session_state.assessment_result
        ):
            display_assessment_result(st.session_state.assessment_result)

        # Input section
        input_container = st.container()
        with input_container:
            st.markdown("---")

            # Start conversation button
            if not st.session_state.messages:
                if st.button("🚀 Start Mortgage Assessment", type="primary"):
                    with st.spinner("Starting conversation..."):
                        response = send_message("Hello")
                        if response:
                            st.session_state.messages.append(
                                {"role": "user", "content": "Hello"}
                            )
                            st.session_state.messages.append(
                                {"role": "assistant", "content": response["response"]}
                            )
                            st.rerun()

            # Chat input
            elif not st.session_state.conversation_complete:
                col1, col2 = st.columns([4, 1])

                with col1:
                    user_input = st.text_input(
                        "Your message:",
                        key="user_input",
                        placeholder="Type your response here...",
                    )

                with col2:
                    send_button = st.button("Send", type="primary")

                if send_button and user_input:
                    with st.spinner("Processing..."):
                        response = send_message(user_input)
                        if response:
                            st.session_state.messages.append(
                                {"role": "user", "content": user_input}
                            )
                            st.session_state.messages.append(
                                {"role": "assistant", "content": response["response"]}
                            )

                            if response.get("conversation_complete", False):
                                st.session_state.conversation_complete = True
                                st.session_state.assessment_result = response.get(
                                    "assessment_result"
                                )

                            st.rerun()

            # Conversation complete
            else:
                st.success("✅ Assessment Complete!")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Start New Assessment", type="primary"):
                        reset_conversation()
                with col2:
                    if st.button("📧 Contact Advisor", type="secondary"):
                        st.info(
                            "Contact our human advisors for detailed mortgage consultation!"
                        )


if __name__ == "__main__":
    main()
