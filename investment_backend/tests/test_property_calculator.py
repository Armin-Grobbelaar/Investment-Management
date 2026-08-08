"""
Tests for property_calculator.py financial calculations.

Covers the amortisation (PMT / outstanding balance), SA transfer duty
brackets, CGT on disposal, and the projection IRR/rethIRR logic.
Bracket values cross-checked against SARS rates (unchanged 1 April 2026).
"""

import numpy as np
import pytest

from modules.property_calculator import (
    calculate_pmt,
    calculate_remaining_bond,
    calculate_sa_transfer_duty,
    calculate_cgt,
    run_property_projection,
)


class TestCalculatePmt:
    def test_zero_principal(self):
        assert calculate_pmt(0, 10.0, 20) == 0.0

    def test_zero_rate_amortises_equally(self):
        # No interest: payment = principal / n
        assert calculate_pmt(1200000, 0, 20) == pytest.approx(5000.0)

    def test_zero_term(self):
        assert calculate_pmt(100000, 8.0, 0) == 0.0

    def test_positive_rate(self):
        # R1.2m @ 11.75% over 20 years -> ~R13,023.xx/month (standard annuity)
        pmt = calculate_pmt(1200000, 11.75, 20)
        assert pmt == pytest.approx(13022.0, abs=20.0)


class TestCalculateRemainingBond:
    def test_after_full_term_is_zero(self):
        assert calculate_remaining_bond(1200000, 11.75, 20, 240) == 0.0

    def test_after_zero_months_is_principal(self):
        assert calculate_remaining_bond(1200000, 11.75, 20, 0) == 1200000.0

    def test_after_one_payment_less_than_principal(self):
        rem = calculate_remaining_bond(1200000, 11.75, 20, 1)
        assert 0 < rem < 1200000.0

    def test_monotonic_decrease(self):
        prev = calculate_remaining_bond(1200000, 11.75, 20, 12)
        cur = calculate_remaining_bond(1200000, 11.75, 20, 24)
        assert cur < prev

    def test_zero_rate_straight_line(self):
        # Check the no-interest path: principal - (principal/n)*months
        rem = calculate_remaining_bond(1200000, 0, 20, 60)
        assert rem == pytest.approx(1200000 - (1200000 / 240) * 60)


class TestTransferDuty:
    """SA transfer duty brackets (2024/25..2026/27 — unchanged since 1 Apr 2025)."""

    def test_zero_duty_below_threshold(self):
        assert calculate_sa_transfer_duty(1_000_000) == 0.0
        assert calculate_sa_transfer_duty(1_100_000) == 0.0

    def test_three_percent_band(self):
        # 1.3m: 0 + 3% of (1.3m - 1.1m) = 6,000
        assert calculate_sa_transfer_duty(1_300_000) == pytest.approx(6000.0)

    def test_six_percent_band_base(self):
        # 1.7m: 12,375 + 6% of (1.7m - 1,512,500) = 12,375 + 11,250 = 23,625
        assert calculate_sa_transfer_duty(1_700_000) == pytest.approx(23625.0)

    def test_eight_percent_band(self):
        # 2.4m: 48,675 + 8% of (2.4m - 2,117,500) = 48,675 + 22,600 = 71,275
        assert calculate_sa_transfer_duty(2_400_000) == pytest.approx(71275.0)

    def test_top_band(self):
        # 15m: 1,128,600 + 13% of (15m - 12.1m) = 1,128,600 + 377,000 = 1,505,600
        assert calculate_sa_transfer_duty(15_000_000) == pytest.approx(1505600.0)

    def test_exact_boundary_uses_next_band(self):
        # Price exactly at 1,100,000 is the zero band upper bound (inclusive)
        assert calculate_sa_transfer_duty(1_100_000) == 0.0
        # Just above goes into the 3% band
        assert calculate_sa_transfer_duty(1_100_001) == pytest.approx(0.03)


class TestCgt:
    def test_no_tax_below_base_cost(self):
        r = calculate_cgt(proceeds=1_000_000, base_cost=1_200_000,
                          annual_exclusion=40_000)
        assert r["cgt_payable"] == 0.0
        assert r["net_gain"] == 0.0

    def test_annual_exclusion_applies(self):
        # Gain of 60k - 40k exclusion = 20k taxable; 40% incl; 45% marginal
        r = calculate_cgt(proceeds=1_060_000, base_cost=1_000_000,
                          inclusion_rate=0.40, marginal_tax_rate=0.45,
                          annual_exclusion=40_000)
        assert r["net_gain"] == pytest.approx(20_000)
        assert r["taxable_gain"] == pytest.approx(8_000)
        assert r["cgt_payable"] == pytest.approx(3_600)


class TestRunPropertyProjection:
    def _full_inputs(self, **overrides):
        """Return a complete set of projection inputs with sane defaults."""
        base = dict(
            purchase_price=1_500_000,
            transfer_costs=25_000,
            transfer_duty=-1,              # auto-compute
            bond_registration_costs=15_000,
            other_acquisition_costs=0,
            deposit_amount=150_000,
            bond_interest_rate=11.75,
            bond_term_years=20,
            monthly_levy=1_500, monthly_rates=800, monthly_insurance=400,
            monthly_maintenance_reserve=500, monthly_management_fee_pct=8,
            monthly_other_costs=0, monthly_rental_income=12_000,
            rental_growth_rate_pa=5.0, vacancy_rate_pct=5.0,
            property_growth_rate_pa=7.0, inflation_rate=5.0,
            projection_years=20,
        )
        base.update(overrides)
        return base

    def test_irr_reaches_sale_value(self):
        """A sale in year N should produce a positive nominal IRR for a property
        that grows faster than all-in costs."""
        res = run_property_projection(**self._full_inputs())
        # transfer duty was auto-computed using the landed brackets
        assert res["transfer_duty"] > 0
        assert res["bond_amount"] == pytest.approx(1_350_000.0)
        # 20-year IRR must be positive given 7% growth
        assert res["irr_20yr"] > 0
        # Real IRR below nominal IRR once inflation > 0
        assert res["real_irr_20yr"] < res["irr_20yr"]

    def test_irr_negative_with_flat_property_growth(self):
        """Flat property values and high costs should give a non-positive IRR."""
        res = run_property_projection(**self._full_inputs(
            property_growth_rate_pa=0.0,
            rental_growth_rate_pa=0.0,
            vacancy_rate_pct=0.0,
            inflation_rate=0.0,
        ))
        assert res["irr_10yr"] <= 0

    def test_first_year_yields(self):
        res = run_property_projection(**self._full_inputs(
            purchase_price=1_000_000,
            monthly_rental_income=10_000,
            deposit_amount=100_000,
            transfer_costs=0,
            bond_registration_costs=0,
            monthly_levy=0, monthly_rates=0, monthly_insurance=0,
            monthly_maintenance_reserve=0, monthly_management_fee_pct=0,
            monthly_other_costs=0,
        ))
        assert res["first_year_gross_yield"] == pytest.approx(12.0)  # 120k / 1m