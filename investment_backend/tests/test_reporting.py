"""
Tests for reporting.py module.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

from modules.reporting import generate_investment_pdf_report

class TestReporting:
    """Test PDF reporting functionality."""

    def test_generate_investment_pdf_report_success(self):
        """Test generating PDF report successfully."""
        # We need to patch the sys.path modification and the import
        # The easiest way is to mock sys.modules
        mock_enhanced = MagicMock()
        mock_enhanced.generate_investment_report.return_value = "test_output.pdf"
        
        with patch.dict('sys.modules', {'enhanced_pdf_report': mock_enhanced}):
            result = generate_investment_pdf_report("test_db", "custom_output.pdf")
            
            assert result == "test_output.pdf"
            mock_enhanced.generate_investment_report.assert_called_once_with("test_db", "custom_output.pdf")

    @patch('modules.reporting.datetime')
    def test_generate_investment_pdf_report_default_filename(self, mock_datetime):
        """Test generating PDF report with default filename."""
        mock_now = MagicMock()
        mock_now.strftime.return_value = "20230101_120000"
        mock_datetime.now.return_value = mock_now
        
        mock_enhanced = MagicMock()
        mock_enhanced.generate_investment_report.return_value = "investment_report_20230101_120000.pdf"
        
        with patch.dict('sys.modules', {'enhanced_pdf_report': mock_enhanced}):
            result = generate_investment_pdf_report("test_db")
            
            assert result == "investment_report_20230101_120000.pdf"
            mock_enhanced.generate_investment_report.assert_called_once_with("test_db", "investment_report_20230101_120000.pdf")

    def test_generate_investment_pdf_report_import_error(self):
        """Test generating PDF report when module is not found."""
        # Remove the module if it exists to trigger ImportError
        import sys
        if 'enhanced_pdf_report' in sys.modules:
            del sys.modules['enhanced_pdf_report']
            
        with patch.dict('sys.modules', {'enhanced_pdf_report': None}):
            with pytest.raises(ImportError):
                generate_investment_pdf_report("test_db")
