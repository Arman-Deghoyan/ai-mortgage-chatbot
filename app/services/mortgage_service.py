from app.models.mortgage import (
    Assessment,
    AssessmentOutcome,
    CalculatedMetrics,
    CreditScoreCategory,
    MortgageAssessmentResult,
    UserInputs,
)
from app.utils.logger import LoggerMixin, get_logger


class MortgageCalculationService(LoggerMixin):
    """Service to handle mortgage calculations and eligibility assessments"""

    @classmethod
    def calculate_dti_ratio(cls, annual_income: float, monthly_debt: float) -> float:
        """Calculate Debt-to-Income ratio"""
        logger = get_logger(__name__)

        if annual_income <= 0:
            logger.warning(
                "Invalid annual income for DTI calculation", annual_income=annual_income
            )
            return float("inf")

        monthly_income = annual_income / 12
        dti_ratio = monthly_debt / monthly_income

        logger.info(
            "DTI ratio calculated",
            annual_income=annual_income,
            monthly_debt=monthly_debt,
            monthly_income=monthly_income,
            dti_ratio=dti_ratio,
        )

        return dti_ratio

    @classmethod
    def calculate_ltv_ratio(cls, property_value: float, down_payment: float) -> float:
        """Calculate Loan-to-Value ratio"""
        logger = get_logger(__name__)

        if property_value <= 0:
            logger.warning(
                "Invalid property value for LTV calculation",
                property_value=property_value,
            )
            return float("inf")

        loan_amount = property_value - down_payment
        ltv_ratio = loan_amount / property_value

        logger.info(
            "LTV ratio calculated",
            property_value=property_value,
            down_payment=down_payment,
            loan_amount=loan_amount,
            ltv_ratio=ltv_ratio,
        )

        return ltv_ratio

    @staticmethod
    def assess_eligibility(
        user_inputs: UserInputs, calculated_metrics: CalculatedMetrics
    ) -> Assessment:
        """Assess mortgage eligibility based on predefined rules"""
        dti_ratio = calculated_metrics.dti_ratio
        ltv_ratio = calculated_metrics.ltv_ratio
        credit_score = user_inputs.credit_score_category

        # Rule 1: Approved
        if (
            dti_ratio < 0.43
            and ltv_ratio < 0.80
            and credit_score
            in [CreditScoreCategory.GOOD, CreditScoreCategory.EXCELLENT]
        ):
            return Assessment(
                outcome=AssessmentOutcome.APPROVED,
                notes="User meets all preliminary criteria for a standard mortgage.",
            )

        # Rule 2: Pre-qualified with Conditions
        elif dti_ratio < 0.43 and 0.80 <= ltv_ratio <= 0.95:
            return Assessment(
                outcome=AssessmentOutcome.PRE_QUALIFIED,
                notes="User pre-qualifies but will need PMI due to high LTV ratio.",
            )

        # Rule 3: Needs Manual Review
        else:
            reasons = []
            if dti_ratio >= 0.43:
                reasons.append("DTI ratio is above 43%")
            if credit_score in [CreditScoreCategory.FAIR, CreditScoreCategory.POOR]:
                reasons.append("Credit score needs improvement")
            if ltv_ratio > 0.95:
                reasons.append("Down payment is insufficient")

            notes = f"Manual review required. Issues: {', '.join(reasons)}."
            return Assessment(outcome=AssessmentOutcome.NEEDS_REVIEW, notes=notes)

    @classmethod
    def perform_complete_assessment(
        cls, user_inputs: UserInputs
    ) -> MortgageAssessmentResult:
        """Perform complete mortgage assessment"""
        logger = get_logger(__name__)

        # Validate inputs
        if user_inputs.annual_income is None or user_inputs.monthly_debt is None:
            logger.error("Missing required income data for assessment")
            raise ValueError("Annual income and monthly debt are required")

        if user_inputs.property_value is None or user_inputs.down_payment is None:
            logger.error("Missing required property data for assessment")
            raise ValueError("Property value and down payment are required")

        # Calculate metrics
        dti_ratio = cls.calculate_dti_ratio(
            user_inputs.annual_income, user_inputs.monthly_debt
        )
        ltv_ratio = cls.calculate_ltv_ratio(
            user_inputs.property_value, user_inputs.down_payment
        )

        calculated_metrics = CalculatedMetrics(dti_ratio=dti_ratio, ltv_ratio=ltv_ratio)

        # Assess eligibility
        assessment = cls.assess_eligibility(user_inputs, calculated_metrics)

        logger.info(
            "Complete mortgage assessment performed",
            user_id="default",  # In real app, this would be user-specific
            dti_ratio=dti_ratio,
            ltv_ratio=ltv_ratio,
            credit_score=(
                user_inputs.credit_score_category.value
                if user_inputs.credit_score_category
                else None
            ),
            assessment_outcome=assessment.outcome.value,
        )

        return MortgageAssessmentResult(
            user_inputs=user_inputs,
            calculated_metrics=calculated_metrics,
            assessment=assessment,
        )
