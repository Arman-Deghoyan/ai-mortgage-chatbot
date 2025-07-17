from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class CreditScoreCategory(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"


class AssessmentOutcome(str, Enum):
    APPROVED = "Approved"
    PRE_QUALIFIED = "Pre-qualified with Conditions"
    NEEDS_REVIEW = "Needs Manual Review"


class UserInputs(BaseModel):
    annual_income: Optional[float] = None
    monthly_debt: Optional[float] = None
    credit_score_category: Optional[CreditScoreCategory] = None
    property_value: Optional[float] = None
    down_payment: Optional[float] = None

    def is_complete(self) -> bool:
        return all(
            [
                self.annual_income is not None,
                self.monthly_debt is not None,
                self.credit_score_category is not None,
                self.property_value is not None,
                self.down_payment is not None,
            ]
        )


class CalculatedMetrics(BaseModel):
    dti_ratio: float = Field(..., description="Debt-to-Income ratio")
    ltv_ratio: float = Field(..., description="Loan-to-Value ratio")


class Assessment(BaseModel):
    outcome: AssessmentOutcome
    notes: str


class MortgageAssessmentResult(BaseModel):
    user_inputs: UserInputs
    calculated_metrics: CalculatedMetrics
    assessment: Assessment


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender (user or assistant)")
    content: str = Field(..., description="Content of the message")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message")
    conversation_id: Optional[str] = Field(
        default=None,
        description="Conversation ID for persistence (optional for new conversations)",
    )
    conversation_history: List[ChatMessage] = Field(
        default_factory=list,
        description="Previous conversation history (deprecated, kept for compatibility)",
    )


class ChatResponse(BaseModel):
    response: str = Field(..., description="Chatbot's response")
    conversation_id: str = Field(..., description="Conversation ID for tracking")
    conversation_complete: bool = Field(
        default=False, description="Whether the conversation is complete"
    )
    assessment_result: Optional[MortgageAssessmentResult] = Field(
        default=None, description="Final assessment if conversation is complete"
    )


class ConversationState(BaseModel):
    user_inputs: UserInputs = Field(default_factory=UserInputs)
    current_step: str = Field(
        default="greeting", description="Current step in the conversation flow"
    )
    conversation_history: List[ChatMessage] = Field(default_factory=list)
    is_complete: bool = Field(default=False)


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
