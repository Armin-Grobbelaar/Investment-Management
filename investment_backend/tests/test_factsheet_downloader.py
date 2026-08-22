"""
Tests for factsheet_downloader.py — slug generation, file paths,
factsheet download/store and view (DB read-back).
"""

import os
import tempfile
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

import modules.factsheet_downloader as fd

class TestSlugify:
    def test_basic(self):
        assert fd._slugify("Allan Gray Equity Fund") == "allan-gray-equity-fund"

    def test_strips_special_chars(self):
        assert fd._slugify("M&G Equity Fund (A)") == "m-g-equity-fund-a"

    def test_double_spaces_and_punct(self):
        assert fd._slugify("  Satrix   S&P 500! ") == "satrix-s-p-500"

class TestGetFactsheetPath:
    def test_path_structure(self, tmp_path):
        with patch.object(fd, "FACTSHEETS_DIR", str(tmp_path)):
            path = fd.get_factsheet_path(61, 2026, 8)
            assert path == os.path.join(str(tmp_path), "61", "2026_08_MDD.pdf")
            assert os.path.isdir(os.path.dirname(path))

class TestGetFactsheetsForInvestment:
    @patch("modules.database.get_db_connection")
    def test_returns_rows(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        mock_cursor.description = [
            ("id",), ("factsheet_date",), ("factsheet_year",), ("factsheet_month",), ("factsheet_type",),
            ("source_url",), ("file_path",), ("file_name",), ("file_size_bytes",),
            ("downloaded_at",),
        ]
        mock_cursor.fetchall.return_value = [
            (1, date(2026, 8, 1), 2026, 8, "MDD", "https://example.com/x.pdf", "/tmp/f.pdf",
             "f.pdf", 1024, date(2026, 8, 1)),
        ]

        result = fd.get_factsheets_for_investment(61, "Investments")
        assert len(result) == 1
        assert result[0]["factsheet_year"] == 2026
        assert result[0]["factsheet_month"] == 8
        assert result[0]["file_name"] == "f.pdf"

    @patch("modules.database.get_db_connection")
    def test_year_month_filter_in_query(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)
        mock_cursor.description = [("id",)]
        mock_cursor.fetchall.return_value = []

        fd.get_factsheets_for_investment(61, "Investments", year=2025, month=3)
        sql = mock_cursor.execute.call_args.args[0].lower()
        assert "factsheet_year" in sql and "factsheet_month" in sql

class TestDownloadFactsheet:
    @patch("modules.database.get_db_connection")
    def test_skips_when_already_downloaded(self, mock_get_db, tmp_path):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [(1,)]
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        with patch.object(fd, "FACTSHEETS_DIR", str(tmp_path)):
            fp = fd.get_factsheet_path(61, date.today().year, date.today().month, "MDD")
            with open(fp, "wb") as f:
                f.write(b"%PDF dummy")
            result = fd.download_factsheet(61, "Allan Gray Equity Fund Class A",
                                           "Allan Gray", "Investments")

        assert result["success"] is True
        assert result["error"] == "Already downloaded this month"

    @patch("modules.database.get_db_connection")
    def test_url_not_found(self, mock_get_db, tmp_path):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [None, None]
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        with patch.object(fd, "FACTSHEETS_DIR", str(tmp_path)):
            result = fd.download_factsheet(61, "Unknown Fund", "Unknown Inst", "Investments")

        assert result["success"] is False
