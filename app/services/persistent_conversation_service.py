"""Database-persistent conversation service using linear state machine approach"""

from typing import Any

from langchain_openai import ChatOpenAI

from app.models.mortgage import CreditScoreCategory
from app.services.database_service import DatabaseService
from app.services.mortgage_service import MortgageCalculationService
from app.utils.logger import LoggerMixin


class PersistentConversationService(LoggerMixin):
    """Database-persistent conversation service using step-by-step linear flow"""

    def __init__(self, openai_api_key: str, db_service: DatabaseService):
        self.llm = ChatOpenAI(api_key=openai_api_key, model="gpt-3.5-turbo")
        self.db = db_service

    def start_new_conversation(self, user_id: str | None = None) -> str:
        """Start a new conversation and return conversation ID"""
        conversation = self.db.create_conversation(user_id=user_id)
        return conversation.id

    def process_message(
        self,
        user_message: str,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        """Process user message with database persistence"""
        try:
            # Create new conversation if none provided
            if not conversation_id:
                conversation_id = self.start_new_conversation()

            # Save user message to database
            self.db.add_message(conversation_id, "user", user_message)

            # Determine what step we're on based on completed data, not just message count
            step_number = self._determine_conversation_step(conversation_id)

            self.logger.info(f"Processing step {step_number}: {user_message}")

            # Process based on step using match-case
            match step_number:
                case 1:
                    response_data = self._handle_greeting(user_message, conversation_id)
                case 2:
                    response_data = self._handle_confirmation(
                        user_message, conversation_id
                    )
                case 3:
                    response_data = self._handle_income(user_message, conversation_id)
                case 4:
                    response_data = self._handle_debt(user_message, conversation_id)
                case 5:
                    response_data = self._handle_credit(user_message, conversation_id)
                case 6:
                    response_data = self._handle_property(user_message, conversation_id)
                case 7:
                    response_data = self._handle_down_payment(
                        user_message, conversation_id
                    )
                case _:  # Default case
                    response_data = {
                        "response": "Assessment completed. Would you like to start over?",
                        "conversation_complete": True,
                        "assessment_result": None,
                    }

            # Save assistant response to database
            self.db.add_message(conversation_id, "assistant", response_data["response"])

            # Mark conversation as completed if finished
            if response_data.get("conversation_complete"):
                self.db.complete_conversation(conversation_id)
            else:
                # Update conversation step in database only if conversation continues
                self.db.update_conversation_step(conversation_id, step_number)

            # Add conversation_id to response
            response_data["conversation_id"] = conversation_id
            return response_data

        except Exception as e:
            self.logger.error("Error processing message", error=str(e))
            error_response = {
                "response": "I'm sorry, I encountered an error. Please try again.",
                "conversation_complete": False,
                "assessment_result": None,
                "conversation_id": conversation_id or "error",
            }

            # Try to save error response to database
            try:
                if conversation_id:
                    self.db.add_message(
                        conversation_id, "assistant", error_response["response"]
                    )
            except Exception:
                pass  # Don't fail if we can't save error message

            return error_response

    def _determine_conversation_step(self, conversation_id: str) -> int:
        """Determine conversation step based on completed data, not just message count"""
        try:
            # Check conversation status first - if completed, don't advance steps
            conversation = self.db.get_conversation(conversation_id)
            if conversation and conversation.status == "completed":
                # Return a step that indicates conversation is done
                return 8  # Assessment complete/conversation ended

            # Get conversation messages to understand flow
            messages = self.db.get_conversation_messages(conversation_id)
            user_messages = [msg for msg in messages if msg.role == "user"]
            assistant_messages = [msg for msg in messages if msg.role == "assistant"]

            # If no messages yet, we're at step 1 (greeting)
            if not user_messages:
                return 1

            # If only one user message, we're processing the initial greeting
            if len(user_messages) == 1:
                return 1

            # If we have 2 user messages, we're processing the confirmation response
            if len(user_messages) == 2:
                return 2

            # For 2+ messages, need to check if user proceeded or declined
            # Look at the last assistant message to understand the flow
            assistant_messages = [msg for msg in messages if msg.role == "assistant"]
            if assistant_messages:
                last_response = assistant_messages[-1].content.lower()
                # If the last response was a decline message, we're done
                if (
                    "feel free to come back" in last_response
                    or "have a great day" in last_response
                ):
                    return 8  # Conversation ended

            # Get user inputs to see what data we have
            user_inputs = self.db.get_user_inputs(conversation_id)

            # For 3+ messages, check completed data to determine where we are
            if not user_inputs:
                # User confirmed but no data saved yet, need income
                return 3

            # Check what data we have completed using match-case pattern
            missing_field = None
            if user_inputs.annual_income is None:
                missing_field = "income"
            elif user_inputs.monthly_debt is None:
                missing_field = "debt"
            elif user_inputs.credit_score_category is None:
                missing_field = "credit"
            elif user_inputs.property_value is None:
                missing_field = "property"
            elif user_inputs.down_payment is None:
                missing_field = "down_payment"
            else:
                missing_field = "complete"

            match missing_field:
                case "income":
                    return 3  # Need income
                case "debt":
                    return 4  # Need debt
                case "credit":
                    return 5  # Need credit score
                case "property":
                    return 6  # Need property value
                case "down_payment":
                    return 7  # Need down payment
                case _:  # complete
                    return 8  # Assessment complete

        except Exception as e:
            self.logger.error("Error determining conversation step", error=str(e))
            # Fallback to message count if determination fails
            messages = self.db.get_conversation_messages(conversation_id)
            user_messages = [msg for msg in messages if msg.role == "user"]
            return len(user_messages)

    def _handle_greeting(
        self, user_message: str, conversation_id: str
    ) -> dict[str, Any]:
        """Handle initial greeting"""
        response = "Hello! Welcome to the Mortgage Advisor chatbot. I'm here to assist you with a preliminary mortgage eligibility assessment. Would you like to begin the assessment process today? Just let me know when you're ready to get started!"

        return {
            "response": response,
            "conversation_complete": False,
            "assessment_result": None,
        }

    def _handle_confirmation(
        self, user_message: str, conversation_id: str
    ) -> dict[str, Any]:
        """Handle confirmation and ask for income"""
        try:
            confirmation_prompt = f"""
Analyze the user's message and determine if they are expressing consent or agreement to proceed.

User message: "{user_message}"

Instructions:
- If the user says yes, agrees, or wants to continue, respond with exactly: "PROCEED"
- If the user says no, declines, or wants to stop, respond with exactly: "DECLINE"
- If the message is unclear, respond with exactly: "UNCLEAR"

Response:"""

            response = self.llm.invoke(confirmation_prompt).content.strip()

            # Determine response type for cleaner switch-case
            response_type = None
            if "PROCEED" in response.upper():
                response_type = "proceed"
            elif "DECLINE" in response.upper():
                response_type = "decline"
            else:
                response_type = "unclear"

            match response_type:
                case "proceed":
                    return {
                        "response": "Great! Let's get started with your mortgage assessment. First, I'll need to know your annual income. Please tell me your total yearly income before taxes.",
                        "conversation_complete": False,
                        "assessment_result": None,
                    }
                case "decline":
                    return {
                        "response": "No problem! Feel free to come back anytime when you're ready to explore your mortgage options. Have a great day!",
                        "conversation_complete": True,
                        "assessment_result": None,
                    }
                case _:  # unclear or any other case
                    return {
                        "response": "I want to make sure I understand correctly. Are you interested in getting a mortgage eligibility assessment today? Please let me know with a simple yes or no.",
                        "conversation_complete": False,
                        "assessment_result": None,
                    }

        except Exception as e:
            self.logger.error("Error in confirmation handling", error=str(e))
            return {
                "response": "Great! Let's get started with your mortgage assessment. First, I'll need to know your annual income. Please tell me your total yearly income before taxes.",
                "conversation_complete": False,
                "assessment_result": None,
            }

    def _handle_income(self, user_message: str, conversation_id: str) -> dict[str, Any]:
        """Handle income input and ask for debt"""
        try:
            income_prompt = f"""
Extract the annual income amount from the user's message. The user is providing their yearly income before taxes.

User message: "{user_message}"

Instructions:
- Extract the numeric value representing annual income
- Convert to a float (e.g., "50k" -> 50000.0, "75,000" -> 75000.0)
- If you find a valid income, respond with just the number
- If no valid income found, respond with "INVALID"

Response:"""

            response = self.llm.invoke(income_prompt).content.strip()

            try:
                annual_income = float(response.replace(",", ""))
                if annual_income > 0:
                    # Save to database
                    self.db.update_user_input_field(
                        conversation_id, "annual_income", annual_income
                    )

                    return {
                        "response": f"Thank you! I've recorded your annual income as ${annual_income:,.0f}. Next, I need to understand your monthly debt obligations. Please tell me your total monthly debt payments (credit cards, student loans, car payments, etc.).",
                        "conversation_complete": False,
                        "assessment_result": None,
                    }
                else:
                    raise ValueError("Income must be positive")
            except (ValueError, TypeError):
                return {
                    "response": "I need a valid annual income amount. Please provide your yearly income before taxes as a number (for example: 75000 or 75k).",
                    "conversation_complete": False,
                    "assessment_result": None,
                }

        except Exception as e:
            self.logger.error("Error in income handling", error=str(e))
            return {
                "response": "I need a valid annual income amount. Please provide your yearly income before taxes as a number (for example: 75000 or 75k).",
                "conversation_complete": False,
                "assessment_result": None,
            }

    def _handle_debt(self, user_message: str, conversation_id: str) -> dict[str, Any]:
        """Handle debt input and ask for credit score"""
        try:
            debt_prompt = f"""
Extract the monthly debt amount from the user's message. This includes credit cards, loans, car payments, etc.

User message: "{user_message}"

Instructions:
- Extract the numeric value representing monthly debt payments
- Convert to a float (e.g., "1500" -> 1500.0, "1.5k" -> 1500.0)
- If you find a valid debt amount, respond with just the number
- If user explicitly says they have "no debt", "zero debt", or "0", respond with "0"
- If user says "I don't know", "not sure", "unclear", or provides non-numeric responses, respond with "INVALID"
- If no valid amount found, respond with "INVALID"

Response:"""

            response = self.llm.invoke(debt_prompt).content.strip()

            try:
                monthly_debt = float(response.replace(",", ""))
                if monthly_debt >= 0:
                    # Save to database
                    self.db.update_user_input_field(
                        conversation_id, "monthly_debt", monthly_debt
                    )

                    return {
                        "response": f"Got it! I've recorded your monthly debt as ${monthly_debt:,.0f}. Now, what's your credit score range? Please choose from: Excellent (750+), Good (700-749), Fair (650-699), or Poor (below 650).",
                        "conversation_complete": False,
                        "assessment_result": None,
                    }
                else:
                    raise ValueError("Debt cannot be negative")
            except (ValueError, TypeError):
                return {
                    "response": "Please provide a valid monthly debt amount as a number (for example: 1500 or 0 if you have no debt).",
                    "conversation_complete": False,
                    "assessment_result": None,
                }

        except Exception as e:
            self.logger.error("Error in debt handling", error=str(e))
            return {
                "response": "Please provide a valid monthly debt amount as a number (for example: 1500 or 0 if you have no debt).",
                "conversation_complete": False,
                "assessment_result": None,
            }

    def _handle_credit(self, user_message: str, conversation_id: str) -> dict[str, Any]:
        """Handle credit score and ask for property value"""
        try:
            credit_prompt = f"""
Determine the credit score category from the user's message.

User message: "{user_message}"

Instructions:
- Match to one of these categories: "Excellent", "Good", "Fair", "Poor"
- Look for keywords like "excellent", "good", "fair", "poor" or score ranges
- Excellent: 750+, Good: 700-749, Fair: 650-699, Poor: below 650
- Respond with exactly one of: "Excellent", "Good", "Fair", "Poor"
- If unclear, respond with "INVALID"

Response:"""

            response = self.llm.invoke(credit_prompt).content.strip()

            try:
                credit_category = CreditScoreCategory(response)
                # Save to database
                self.db.update_user_input_field(
                    conversation_id, "credit_score_category", credit_category
                )

                return {
                    "response": f"Perfect! I've noted your credit score as {credit_category.value}. Now, what's the value of the property you're looking to purchase?",
                    "conversation_complete": False,
                    "assessment_result": None,
                }
            except ValueError:
                return {
                    "response": "Please specify your credit score range: Excellent (750+), Good (700-749), Fair (650-699), or Poor (below 650).",
                    "conversation_complete": False,
                    "assessment_result": None,
                }

        except Exception as e:
            self.logger.error("Error in credit handling", error=str(e))
            return {
                "response": "Please specify your credit score range: Excellent (750+), Good (700-749), Fair (650-699), or Poor (below 650).",
                "conversation_complete": False,
                "assessment_result": None,
            }

    def _handle_property(
        self, user_message: str, conversation_id: str
    ) -> dict[str, Any]:
        """Handle property value and ask for down payment"""
        try:
            property_prompt = f"""
Extract the property value from the user's message.

User message: "{user_message}"

Instructions:
- Extract the numeric value representing property/home value
- Convert to a float (e.g., "300k" -> 300000.0, "450,000" -> 450000.0)
- If you find a valid property value, respond with just the number
- If no valid value found, respond with "INVALID"

Response:"""

            response = self.llm.invoke(property_prompt).content.strip()

            try:
                property_value = float(response.replace(",", ""))
                if property_value > 0:
                    # Save to database
                    self.db.update_user_input_field(
                        conversation_id, "property_value", property_value
                    )

                    return {
                        "response": f"Excellent! I've recorded the property value as ${property_value:,.0f}. Finally, how much are you planning to put down as a down payment?",
                        "conversation_complete": False,
                        "assessment_result": None,
                    }
                else:
                    raise ValueError("Property value must be positive")
            except (ValueError, TypeError):
                return {
                    "response": "Please provide a valid property value as a number (for example: 300000 or 300k).",
                    "conversation_complete": False,
                    "assessment_result": None,
                }

        except Exception as e:
            self.logger.error("Error in property handling", error=str(e))
            return {
                "response": "Please provide a valid property value as a number (for example: 300000 or 300k).",
                "conversation_complete": False,
                "assessment_result": None,
            }

    def _handle_down_payment(
        self, user_message: str, conversation_id: str
    ) -> dict[str, Any]:
        """Handle down payment and provide assessment"""
        try:
            down_payment_prompt = f"""
Extract the down payment amount from the user's message.

User message: "{user_message}"

Instructions:
- Extract the numeric value representing down payment
- Convert to a float (e.g., "50k" -> 50000.0, "60,000" -> 60000.0)
- If you find a valid down payment, respond with just the number
- If no valid amount found, respond with "INVALID"

Response:"""

            response = self.llm.invoke(down_payment_prompt).content.strip()

            try:
                down_payment = float(response.replace(",", ""))
                if down_payment >= 0:
                    # Save to database
                    self.db.update_user_input_field(
                        conversation_id, "down_payment", down_payment
                    )

                    # Get all user inputs from database
                    user_inputs = self.db.get_user_inputs(conversation_id)

                    if user_inputs and user_inputs.is_complete():
                        # Calculate assessment
                        result = MortgageCalculationService.perform_complete_assessment(
                            user_inputs
                        )

                        # Format the result nicely
                        formatted_result = self._format_assessment_result(result)

                        return {
                            "response": formatted_result,
                            "conversation_complete": True,
                            "assessment_result": result,
                        }
                    else:
                        return {
                            "response": "I'm missing some information. Let me start over to collect all needed details.",
                            "conversation_complete": False,
                            "assessment_result": None,
                        }
                else:
                    raise ValueError("Down payment cannot be negative")
            except (ValueError, TypeError):
                return {
                    "response": "Please provide a valid down payment amount as a number (for example: 50000 or 50k).",
                    "conversation_complete": False,
                    "assessment_result": None,
                }

        except Exception as e:
            self.logger.error("Error in down payment handling", error=str(e))
            return {
                "response": "Please provide a valid down payment amount as a number (for example: 50000 or 50k).",
                "conversation_complete": False,
                "assessment_result": None,
            }

    def _format_assessment_result(self, result) -> str:
        """Format the assessment result for display"""
        # Simple completion message - detailed results shown in UI component
        return "✅ Your mortgage assessment is complete! Please see the detailed results below."

    def get_conversation_history(self, conversation_id: str) -> list[dict[str, Any]]:
        """Get conversation history from database"""
        return self.db.get_conversation_history_for_service(conversation_id)

    def continue_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        """Check if a conversation exists and can be continued"""
        conversation = self.db.get_conversation(conversation_id)
        if conversation and conversation.status == "in_progress":
            messages = self.db.get_conversation_history_for_service(conversation_id)
            return {
                "conversation_exists": True,
                "current_step": conversation.current_step,
                "message_count": len(messages),
                "last_message": messages[-1] if messages else None,
            }
        return None
