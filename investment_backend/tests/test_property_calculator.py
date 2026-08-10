"""
Tests for property_calculator.py financial calculations.

Covers the amortisation (PMT / outstanding balance), SA transfer duty
brackets, CGT on disposal, and the projection IRR/rethIRR logic.

Transfer duty bracket values cross-checked against SARS rates:
- 2024/25: sars.gov.za/tax-rates/transfer-duty/ (historical)
- 2025/26: effective 1 April 2025; unchanged for 2026/27 per SARS
  "2027 (With effect from 1 April 2026) – No changes from last year."
  Source: https://www.sars.gov.za/tax-rates/transfer-duty/

CGT exclusions updated to Budget 2026 values (effective 2 March 2026):
- Annual exclusion: R50 000 (was R40 000)
- Primary residence: R3 000 000 (was R2 000 000)
  Source: https://www.sars.gov.za/tax-rates/income-tax/capital-gains-tax-cgt/
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
    """SA transfer duty brackets 2025/26 (effective 1 April 2025).

    SARS source: https://www.sars.gov.za/tax-rates/transfer-duty/
    Unchanged for 2026/27 per SARS ("2027 – No changes from last year").
    """

    def test_zero_duty_below_threshold(self):
        # R1 000 000 and R1 210 000 both fall in the 0% band (up to R1 210 000)
        assert calculate_sa_transfer_duty(1_000_000) == 0.0
        assert calculate_sa_transfer_duty(1_210_000) == 0.0

    def test_three_percent_band(self):
        # R1 450 000: 0 + 3% of (1 450 000 − 1 210 000) = 7 200
        assert calculate_sa_transfer_duty(1_450_000) == pytest.approx(7_200.0)

    def test_six_percent_band_base(self):
        # R2 000 000: 13 614 + 6% of (2 000 000 − 1 663 800) = 13 614 + 20 172 = 33 786
        assert calculate_sa_transfer_duty(2_000_000) == pytest.approx(33_786.0)

    def test_eight_percent_band(self):
        # R2 400 000: 53 544 + 8% of (2 400 000 − 2 329 300) = 53 544 + 5 656 = 59 200
        assert calculate_sa_transfer_duty(2_400_000) == pytest.approx(59_200.0)

    def test_eleven_percent_band(self):
        # R8 000 000: 106 784 + 11% of (8 000 000 − 2 994 800) = 106 784 + 550 572 = 657 356
        assert calculate_sa_transfer_duty(8_000_000) == pytest.approx(657_356.0)

    def test_top_band(self):
        # R15 000 000: 1 241 456 + 13% of (15 000 000 − 13 310 000) = 1 241 456 + 219 700 = 1 461 156
        assert calculate_sa_transfer_duty(15_000_000) == pytest.approx(1_461_156.0)

    def test_exact_boundary_uses_next_band(self):
        # Price exactly at R1 210 000 is the zero-band upper bound (inclusive)
        assert calculate_sa_transfer_duty(1_210_000) == 0.0
        # Just above goes into the 3% band: 3% of R1 ≈ R0.03
        assert calculate_sa_transfer_duty(1_210_001) == pytest.approx(0.03)


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

    def test_primary_residence_exclusion_reduces_gain(self):
        # Gain 3m. Without primary residence: 3m - 40k = 2.96m taxable base.
        # With the R2m primary-residence exclusion: 3m - 2m - 40k = 960k.
        without = calculate_cgt(proceeds=5_000_000, base_cost=2_000_000,
                                inclusion_rate=0.40, marginal_tax_rate=0.45,
                                annual_exclusion=40_000)
        with_res = calculate_cgt(proceeds=5_000_000, base_cost=2_000_000,
                                 inclusion_rate=0.40, marginal_tax_rate=0.45,
                                 annual_exclusion=40_000,
                                 primary_residence_exclusion=2_000_000)
        assert without["net_gain"] == pytest.approx(2_960_000)
        assert with_res["net_gain"] == pytest.approx(960_000)
        assert with_res["cgt_payable"] == pytest.approx(0.4 * 0.45 * 960_000)
        assert with_res["primary_residence_exclusion"] == pytest.approx(2_000_000)
        # Exclusion is opt-in: the default must NOT apply it
        assert without["primary_residence_exclusion"] == 0.0

    def test_primary_residence_exclusion_never_negative(self):
        # Primary-residence exclusion larger than the gain -> no CGT
        r = calculate_cgt(proceeds=1_500_000, base_cost=1_000_000,
                          inclusion_rate=0.40, marginal_tax_rate=0.45,
                          annual_exclusion=40_000,
                          primary_residence_exclusion=2_000_000)
        assert r["net_gain"] == 0.0
        assert r["cgt_payable"] == 0.0


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

    def test_primary_residence_reduces_cgt_in_projection(self):
        """Tickbox flows through: the R3M primary-residence exclusion (Budget
        2026) must cut the year-20 CGT by inclusion_rate * marginal_rate * 3m."""
        normal = run_property_projection(**self._full_inputs())
        primary = run_property_projection(**self._full_inputs(is_primary_residence=True))
        assert normal["cgt_20yr"] > 0
        assert primary["cgt_20yr"] < normal["cgt_20yr"]
        assert normal["cgt_20yr"] - primary["cgt_20yr"] == pytest.approx(0.40 * 0.45 * 3_000_000, abs=1.0)
        # Lower CGT -> higher net sale proceeds -> higher IRR
        assert primary["irr_20yr"] > normal["irr_20yr"]