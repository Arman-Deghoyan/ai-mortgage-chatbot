"""Unit tests for the mortgage calculation service."""

import pytest

from app.models.mortgage import (
    Assessment,
    CalculatedMetrics,
    CreditScoreCategory,
    UserInputs,
)
from app.services.mortgage_service import MortgageCalculationService


class TestMortgageCalculationService:
    """Test cases for mortgage calculation service."""

    def test_calculate_dti_ratio(self):
        """Test DTI ratio calculation."""
        # Test case 1: Normal scenario
        annual_income = 80000
        monthly_debt = 1500
        expected_dti = 1500 / (80000 / 12)  # 0.225

        dti = MortgageCalculationService.calculate_dti_ratio(
            annual_income, monthly_debt
        )
        assert dti == pytest.approx(expected_dti, rel=1e-3)

        # Test case 2: Zero debt
        dti_zero_debt = MortgageCalculationService.calculate_dti_ratio(80000, 0)
        assert dti_zero_debt == 0.0

        # Test case 3: High debt scenario
        dti_high_debt = MortgageCalculationService.calculate_dti_ratio(50000, 2500)
        assert dti_high_debt == pytest.approx(0.6, rel=1e-3)

    def test_calculate_ltv_ratio(self):
        """Test LTV ratio calculation."""
        # Test case 1: Standard 20% down payment
        property_value = 400000
        down_payment = 80000
        expected_ltv = (400000 - 80000) / 400000  # 0.8

        ltv = MortgageCalculationService.calculate_ltv_ratio(
            property_value, down_payment
        )
        assert ltv == pytest.approx(expected_ltv, rel=1e-3)

        # Test case 2: 10% down payment
        ltv_10_percent = MortgageCalculationService.calculate_ltv_ratio(300000, 30000)
        assert ltv_10_percent == pytest.approx(0.9, rel=1e-3)

        # Test case 3: 5% down payment
        ltv_5_percent = MortgageCalculationService.calculate_ltv_ratio(200000, 10000)
        assert ltv_5_percent == pytest.approx(0.95, rel=1e-3)

    def test_assess_eligibility_approved(self):
        """Test eligibility assessment for approved scenarios."""
        # Test case 1: All criteria met
        user_inputs = UserInputs(
            annual_income=80000,
            monthly_debt=1500,
            credit_score_category=CreditScoreCategory.GOOD,
            property_value=400000,
            down_payment=85000,
        )
        calculated_metrics = CalculatedMetrics(dti_ratio=0.35, ltv_ratio=0.75)

        assessment = MortgageCalculationService.assess_eligibility(
            user_inputs, calculated_metrics
        )
        assert assessment.outcome.value == "Approved"
        assert "meets all preliminary criteria" in assessment.notes.lower()

        # Test case 2: Excellent credit
        user_inputs_excellent = UserInputs(
            annual_income=100000,
            monthly_debt=2000,
            credit_score_category=CreditScoreCategory.EXCELLENT,
            property_value=500000,
            down_payment=100000,
        )
        calculated_metrics_excellent = CalculatedMetrics(dti_ratio=0.30, ltv_ratio=0.70)

        assessment_excellent = MortgageCalculationService.assess_eligibility(
            user_inputs_excellent, calculated_metrics_excellent
        )
        assert assessment_excellent.outcome.value == "Approved"

    def test_assess_eligibility_pre_qualified(self):
        """Test eligibility assessment for pre-qualified scenarios."""
        # Test case: DTI good but LTV between 80-95%
        user_inputs = UserInputs(
            annual_income=60000,
            monthly_debt=1200,
            credit_score_category=CreditScoreCategory.GOOD,
            property_value=300000,
            down_payment=45000,
        )
        calculated_metrics = CalculatedMetrics(dti_ratio=0.35, ltv_ratio=0.85)

        assessment = MortgageCalculationService.assess_eligibility(
            user_inputs, calculated_metrics
        )
        assert assessment.outcome.value == "Pre-qualified with Conditions"
        assert "pmi" in assessment.notes.lower() or "ltv" in assessment.notes.lower()

    def test_assess_eligibility_manual_review(self):
        """Test eligibility assessment for manual review scenarios."""
        # Test case 1: High DTI
        user_inputs_high_dti = UserInputs(
            annual_income=50000,
            monthly_debt=2000,
            credit_score_category=CreditScoreCategory.GOOD,
            property_value=250000,
            down_payment=25000,
        )
        calculated_metrics_high_dti = CalculatedMetrics(dti_ratio=0.50, ltv_ratio=0.75)

        assessment_high_dti = MortgageCalculationService.assess_eligibility(
            user_inputs_high_dti, calculated_metrics_high_dti
        )
        assert assessment_high_dti.outcome.value == "Needs Manual Review"

        # Test case 2: Poor credit
        user_inputs_poor_credit = UserInputs(
            annual_income=70000,
            monthly_debt=1500,
            credit_score_category=CreditScoreCategory.POOR,
            property_value=350000,
            down_payment=70000,
        )
        calculated_metrics_poor_credit = CalculatedMetrics(
            dti_ratio=0.35, ltv_ratio=0.75
        )

        assessment_poor_credit = MortgageCalculationService.assess_eligibility(
            user_inputs_poor_credit, calculated_metrics_poor_credit
        )
        assert assessment_poor_credit.outcome.value == "Needs Manual Review"

        # Test case 3: Fair credit
        user_inputs_fair_credit = UserInputs(
            annual_income=65000,
            monthly_debt=1400,
            credit_score_category=CreditScoreCategory.FAIR,
            property_value=320000,
            down_payment=64000,
        )
        calculated_metrics_fair_credit = CalculatedMetrics(
            dti_ratio=0.35, ltv_ratio=0.75
        )

        assessment_fair_credit = MortgageCalculationService.assess_eligibility(
            user_inputs_fair_credit, calculated_metrics_fair_credit
        )
        assert assessment_fair_credit.outcome.value == "Needs Manual Review"

    def test_perform_complete_assessment(self):
        """Test complete assessment workflow."""
        user_inputs = UserInputs(
            annual_income=80000,
            monthly_debt=1500,
            credit_score_category=CreditScoreCategory.GOOD,
            property_value=400000,
            down_payment=85000,
        )

        result = MortgageCalculationService.perform_complete_assessment(user_inputs)

        # Verify structure
        assert isinstance(result.user_inputs, UserInputs)
        assert isinstance(result.calculated_metrics, CalculatedMetrics)
        assert isinstance(result.assessment, Assessment)

        # Verify calculations
        expected_dti = 1500 / (80000 / 12)  # 0.225
        expected_ltv = (400000 - 85000) / 400000  # 0.7875

        assert result.calculated_metrics.dti_ratio == pytest.approx(
            expected_dti, rel=1e-3
        )
        assert result.calculated_metrics.ltv_ratio == pytest.approx(
            expected_ltv, rel=1e-3
        )

        # Verify outcome (should be approved based on criteria)
        assert result.assessment.outcome == "Approved"

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test case 1: Zero income (returns infinity)
        dti_zero_income = MortgageCalculationService.calculate_dti_ratio(0, 1000)
        assert dti_zero_income == float("inf")

        # Test case 2: Negative income (returns infinity)
        dti_negative_income = MortgageCalculationService.calculate_dti_ratio(
            -1000, 1000
        )
        assert dti_negative_income == float("inf")

        # Test case 3: Down payment larger than property value (returns negative LTV)
        ltv_high_down = MortgageCalculationService.calculate_ltv_ratio(200000, 250000)
        assert ltv_high_down < 0

        # Test case 4: Zero property value (returns infinity)
        ltv_zero_property = MortgageCalculationService.calculate_ltv_ratio(0, 50000)
        assert ltv_zero_property == float("inf")

    def test_boundary_values(self):
        """Test boundary values for eligibility criteria."""
        # Test DTI boundary at 43%
        user_inputs_exact_dti = UserInputs(
            annual_income=60000,
            monthly_debt=2150,  # DTI = 0.43
            credit_score_category=CreditScoreCategory.GOOD,
            property_value=300000,
            down_payment=60000,
        )
        calculated_metrics_exact_dti = CalculatedMetrics(dti_ratio=0.43, ltv_ratio=0.75)

        assessment_exact_dti = MortgageCalculationService.assess_eligibility(
            user_inputs_exact_dti, calculated_metrics_exact_dti
        )
        assert assessment_exact_dti.outcome.value == "Needs Manual Review"

        # Test LTV boundary at 80%
        user_inputs_exact_ltv = UserInputs(
            annual_income=70000,
            monthly_debt=1500,
            credit_score_category=CreditScoreCategory.GOOD,
            property_value=400000,
            down_payment=80000,  # LTV = 0.80
        )
        calculated_metrics_exact_ltv = CalculatedMetrics(dti_ratio=0.35, ltv_ratio=0.80)

        assessment_exact_ltv = MortgageCalculationService.assess_eligibility(
            user_inputs_exact_ltv, calculated_metrics_exact_ltv
        )
        assert assessment_exact_ltv.outcome.value == "Pre-qualified with Conditions"

        # Test LTV boundary at 95%
        user_inputs_high_ltv = UserInputs(
            annual_income=80000,
            monthly_debt=1600,
            credit_score_category=CreditScoreCategory.GOOD,
            property_value=500000,
            down_payment=25000,  # LTV = 0.95
        )
        calculated_metrics_high_ltv = CalculatedMetrics(dti_ratio=0.35, ltv_ratio=0.95)

        assessment_high_ltv = MortgageCalculationService.assess_eligibility(
            user_inputs_high_ltv, calculated_metrics_high_ltv
        )
        assert assessment_high_ltv.outcome.value == "Pre-qualified with Conditions"
