"""
Tests for profiledata_scraper.py — name parsing, fund selection and
ProfileData results-table price extraction.
"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from modules.profiledata_scraper import (
    parse_investment_name,
    _name_similarity,
    _select_fund,
    _extract_prices_from_page,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers to build fake Playwright pages
# ─────────────────────────────────────────────────────────────────────────────

def _mock_cell(text: str) -> MagicMock:
    cell = MagicMock()
    cell.inner_text.return_value = text
    return cell


def _mock_row(cell_texts) -> MagicMock:
    row = MagicMock()
    row.query_selector_all.return_value = [_mock_cell(t) for t in cell_texts]
    return row


def _mock_table(rows_texts) -> MagicMock:
    table = MagicMock()
    table.query_selector_all.return_value = [_mock_row(r) for r in rows_texts]
    return table


def _mock_page_with_tables(tables_rows) -> MagicMock:
    page = MagicMock()
    page.query_selector_all.return_value = [_mock_table(t) for t in tables_rows]
    return page


# ─────────────────────────────────────────────────────────────────────────────
# parse_investment_name
# ─────────────────────────────────────────────────────────────────────────────

class TestParseInvestmentName:
    def test_class_a_in_name(self):
        parsed = parse_investment_name("Allan Gray Equity Fund Class A")
        assert parsed["manager"] == "Allan Gray Unit Trust Management (RF) Pty Limited"
        assert parsed["fund"] == "Equity Fund"
        assert parsed["class"] == "A"

    def test_parenthetical_class(self):
        parsed = parse_investment_name("PSG Global Equity Feeder Fund (E) - TFSA")
        assert parsed["manager"] == "PSG Collective Investments (RF) Ltd."
        assert parsed["fund"] == "Global Equity Feeder Fund"
        assert parsed["class"] == "E"

    def test_no_class(self):
        parsed = parse_investment_name("Coronation Top 20 Fund")
        assert parsed["manager"] == "Coronation Management Company (RF) (Pty) Ltd."
        assert parsed["fund"] == "Top 20 Fund"
        assert parsed["class"] is None

    def test_psg_wealth_manager_variant(self):
        parsed = parse_investment_name("PSG Wealth Balanced Fund")
        assert parsed["manager"] == "PSG Collective Investments (RF) Ltd."

    def test_ninety_one(self):
        parsed = parse_investment_name("Ninety One Global Franchise Fund")
        assert parsed["manager"] == "Ninety One Fund Managers SA (RF) (Pty) Ltd."
        assert "Franchise" in parsed["fund"]

    def test_a_class_wording(self):
        parsed = parse_investment_name("Allan Gray A class Equity Fund")
        assert parsed["class"] == "A"

    def test_unknown_manager(self):
        parsed = parse_investment_name("My Private Fund Class B")
        assert parsed["manager"] is None
        assert parsed["fund"] == "My Private Fund"
        assert parsed["class"] == "B"


# ─────────────────────────────────────────────────────────────────────────────
# _name_similarity
# ─────────────────────────────────────────────────────────────────────────────

class TestNameSimilarity:
    def test_identical(self):
        assert _name_similarity("equity fund", "equity fund") == 1.0

    def test_subset_overlap(self):
        # 'equity' alone in the desired name vs a long option text → low score
        score = _name_similarity("equity fund", "allan gray equity fund a")
        assert 0 < score < 0.6

    def test_unrelated(self):
        assert _name_similarity("balanced", "global equity") == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# _select_fund (fund dropdown matching)
# ─────────────────────────────────────────────────────────────────────────────

class TestSelectFund:
    def _make_page(self, options: list[tuple[str, str]]):
        """options: list of (value, text) pairs"""
        page = MagicMock()
        select = MagicMock()
        page.query_selector.return_value = select  # select[name='TrustNo']
        opt_mocks = []
        for value, text in options:
            opt = MagicMock()
            opt.inner_text.return_value = text
            opt.get_attribute.return_value = value
            opt_mocks.append(opt)
        select.query_selector_all.return_value = opt_mocks
        return page, select

    def test_selects_class_a_option(self):
        options = [
            ("0244", "Allan Gray Equity Fund A"),
            ("0245", "Allan Gray Equity Fund B"),
            ("0246", "Allan Gray Equity Fund C"),
        ]
        page, select = self._make_page(options)
        result = _select_fund(page, "Equity Fund", "A")
        assert result is True
        # Should pick the A-class option
        assert select.select_option.call_args.kwargs["value"] == "0244"

    def test_selects_fund_without_class(self):
        options = [
            ("0331", "Allan Gray Balanced Fund"),
            ("0341", "Allan Gray Equity Fund"),
        ]
        page, select = self._make_page(options)
        result = _select_fund(page, "Equity Fund", None)
        assert result is True
        assert select.select_option.call_args.kwargs["value"] == "0341"

    def test_no_match_returns_false(self):
        options = [
            ("0331", "Allan Gray Balanced Fund"),
        ]
        page, select = self._make_page(options)
        result = _select_fund(page, "Satrix Global Equity Fund", None)
        assert result is False

    def test_no_select_element(self):
        page = MagicMock()
        page.query_selector.return_value = None
        assert _select_fund(page, "Equity Fund") is False


# ─────────────────────────────────────────────────────────────────────────────
# _extract_prices_from_page
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractPricesFromPage:
    SAMPLE_ROWS = [
        ["Date", "Class", "Price(cents)"],
        ["04 Aug 2026", "A", "80 543.3300"],
        ["04 Aug 2026", "C", "80 743.5900"],
        ["05 Aug 2026", "A", "80 611.4500"],
        ["05 Aug 2026", "C", "80 812.7700"],
    ]

    def test_class_specific_extraction(self):
        page = _mock_page_with_tables([self.SAMPLE_ROWS])
        prices = _extract_prices_from_page(page, "A")
        assert prices == [
            (date(2026, 8, 4), 805.4333),
            (date(2026, 8, 5), 806.1145),
        ]

    def test_no_class_averages_classes_per_date(self):
        page = _mock_page_with_tables([self.SAMPLE_ROWS])
        prices = _extract_prices_from_page(page, None)
        # 04 Aug: mean(805.4333, 807.4359) ; 05 Aug: mean(806.1145, 808.1277)
        assert len(prices) == 2
        d1, p1 = prices[0]
        assert d1 == date(2026, 8, 4)
        assert abs(p1 - ((805.4333 + 807.4359) / 2)) < 1e-6

    def test_class_letter_not_false_positive(self):
        # "Allan Gray" contains the letter 'A' — must NOT match class A row.
        rows = [
            ["Date", "Class", "Price(cents)"],
            ["04 Aug 2026", "Allan Gray Equity Fund A", "80 543.3300"],
        ]
        page = _mock_page_with_tables([rows])
        prices = _extract_prices_from_page(page, "A")
        # Long cell is not a valid class indicator → no match
        assert prices == []

    def test_ignores_header_and_bad_rows(self):
        rows = [
            ["Date", "Class", "Price(cents)"],
            ["not a date", "A", "not a price"],
            ["04 Aug 2026", "A", "80 543.3300"],
        ]
        page = _mock_page_with_tables([rows])
        prices = _extract_prices_from_page(page, "A")
        assert prices == [(date(2026, 8, 4), 805.4333)]
