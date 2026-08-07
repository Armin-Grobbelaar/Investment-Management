from datetime import datetime
from .database import DEFAULT_DB

def generate_investment_pdf_report(database_name=DEFAULT_DB, output_file=None):
    """
    Generate comprehensive investment PDF report with charts.
    
    This function creates a detailed PDF report including:
    - Unit price charts for each investment and portfolio
    - Investment metrics charts over time
    - Predictions for unit prices and metrics
    - Professional formatting and layout
    
    Args:
        database_name: Database name (default: DEFAULT_DB)
        output_file: Output PDF file path (default: auto-generated with timestamp)
    
    Returns:
        Path to the generated PDF file
    """
    try:
        # We import here to avoid circular dependencies if enhanced_pdf_report imports back
        # Also, enhanced_pdf_report is in the parent directory currently
        import sys
        import os
        
        # Add parent directory to path if not present
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            
        from enhanced_pdf_report import generate_investment_report
        
        if output_file is None:
            output_file = f"investment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return generate_investment_report(database_name, output_file)
        
    except ImportError as e:
        print(f"Error: enhanced_pdf_report module not found: {e}")
        raise
    except Exception as e:
        print(f"Error generating PDF report: {e}")
        import traceback
        traceback.print_exc()
        raise
