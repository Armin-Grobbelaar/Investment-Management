#!/usr/bin/env python3
"""
Enhanced Investment PDF Report Generator

Generates comprehensive PDF reports with:
- Unit price charts for each investment and portfolio
- Investment metrics charts over time
- Predictions for unit prices and metrics
- Professional formatting and layout

Usage:
    from enhanced_pdf_report import generate_investment_report
    generate_investment_report(database_name, output_file)
"""

import os
import sys
from datetime import datetime, timedelta
from io import BytesIO
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, Frame, PageTemplate
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfgen import canvas as pdf_canvas

# Import from investment_database_functions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from investment_database_functions import (
    get_db_connection,
    get_investment_summary,
    DEFAULT_DB,
    CURRENCY_SYMBOLS
)


class InvestmentPDFReport:
    """Enhanced PDF report generator for investments."""
    
    def __init__(self, database_name=DEFAULT_DB):
        self.database_name = database_name
        self.temp_chart_files = []
        
        # Setup styles
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a4d2e'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2d6a4f'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        self.subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#40916c'),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
    
    def create_chart(self, data, title, xlabel, ylabel, filename, chart_type='line'):
        """Create a matplotlib chart and save to file."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if chart_type == 'line':
            for column in data.columns:
                if column != 'date':
                    ax.plot(data['date'], data[column], label=column, linewidth=2, marker='o', markersize=4)
        elif chart_type == 'bar':
            data.plot(kind='bar', ax=ax)
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel(xlabel, fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='best', framealpha=0.9)
        
        # Format x-axis for dates
        if 'date' in data.columns:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
        
        self.temp_chart_files.append(filename)
        return filename
    
    def get_unit_price_data(self, investment_id):
        """Get unit price history for an investment."""
        with get_db_connection(self.database_name) as (conn, cursor):
            cursor.execute("""
                SELECT unit_price_date, unit_price
                FROM v_investment_prices
                WHERE investment_id = %s
                ORDER BY unit_price_date
            """, (investment_id,))
            
            data = cursor.fetchall()
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data, columns=['date', 'unit_price'])
            df['date'] = pd.to_datetime(df['date'])
            return df
    
    def get_metrics_data(self, investment_id):
        """Get investment metrics history."""
        with get_db_connection(self.database_name) as (conn, cursor):
            cursor.execute("""
                SELECT 
                    metrics_date,
                    local_cagr,
                    local_irr,
                    local_total_return,
                    local_total_fee_ratio,
                    local_dividend_yield
                FROM investment_metrics
                WHERE investment_id = %s
                ORDER BY metrics_date
            """, (investment_id,))
            
            data = cursor.fetchall()
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data, columns=[
                'date', 'CAGR', 'IRR', 'Total Return', 'Fee Ratio', 'Dividend Yield'
            ])
            df['date'] = pd.to_datetime(df['date'])
            return df
    
    def get_predictions_data(self, investment_id):
        """Get prediction data for an investment."""
        with get_db_connection(self.database_name) as (conn, cursor):
            cursor.execute("""
                SELECT 
                    prediction_date,
                    model_name,
                    prediction_data
                FROM predictions
                WHERE scope = 'investment'
                AND prediction_data->>'investment_id' = %s
                ORDER BY prediction_date DESC
                LIMIT 1
            """, (str(investment_id),))
            
            result = cursor.fetchone()
            if not result:
                return pd.DataFrame()
            
            # Parse JSON prediction data
            import json
            pred_data = json.loads(result[2]) if isinstance(result[2], str) else result[2]
            
            # Extract predictions
            predictions = pred_data.get('predictions', {})
            if not predictions:
                return pd.DataFrame()
            
            # Convert to DataFrame
            dates = []
            values = []
            for date_str, value in predictions.items():
                dates.append(pd.to_datetime(date_str))
                values.append(value)
            
            df = pd.DataFrame({'date': dates, 'predicted_price': values})
            return df.sort_values('date')
    
    def create_investment_summary_table(self):
        """Create summary table of all investments."""
        summary_df = get_investment_summary(self.database_name)
        
        if summary_df.empty:
            return None
        
        # Prepare data for table
        table_data = [['Investment', 'Ticker', 'Value', 'Units', 'Status']]
        
        for _, row in summary_df.iterrows():
            table_data.append([
                row['investment_name'][:30],
                row['investment_ticker'],
                f"{row['unit_currency']} {row['investment_value']:,.2f}",
                f"{row['number_of_units_held']:.4f}",
                row['investment_status']
            ])
        
        # Create table with styling
        table = Table(table_data, colWidths=[2.5*inch, 1*inch, 1.5*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d6a4f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        return table
    
    def generate_investment_page(self, investment_id, investment_name, investment_ticker):
        """Generate content for a single investment."""
        elements = []
        
        # Investment title
        elements.append(Paragraph(f"{investment_name} ({investment_ticker})", self.heading_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # 1. Unit Price Chart
        price_data = self.get_unit_price_data(investment_id)
        if not price_data.empty:
            chart_file = f"/tmp/inv_{investment_id}_prices.png"
            self.create_chart(
                price_data,
                f"Unit Price History - {investment_name}",
                "Date",
                "Unit Price",
                chart_file
            )
            img = Image(chart_file, width=6*inch, height=3.6*inch)
            elements.append(img)
            elements.append(Spacer(1, 0.3*inch))
        else:
            elements.append(Paragraph("No price data available", self.styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
        # 2. Metrics Chart
        metrics_data = self.get_metrics_data(investment_id)
        if not metrics_data.empty:
            chart_file = f"/tmp/inv_{investment_id}_metrics.png"
            # Select key metrics for chart
            metrics_subset = metrics_data[['date', 'CAGR', 'IRR', 'Total Return']].copy()
            # Convert to percentage
            for col in ['CAGR', 'IRR', 'Total Return']:
                metrics_subset[col] = metrics_subset[col] * 100
            
            self.create_chart(
                metrics_subset,
                f"Key Metrics Over Time - {investment_name}",
                "Date",
                "Percentage (%)",
                chart_file
            )
            img = Image(chart_file, width=6*inch, height=3.6*inch)
            elements.append(img)
            elements.append(Spacer(1, 0.3*inch))
        else:
            elements.append(Paragraph("No metrics data available", self.styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
        # 3. Predictions Chart
        predictions_data = self.get_predictions_data(investment_id)
        if not predictions_data.empty:
            # Combine historical and predicted prices
            price_data_recent = price_data.tail(30).copy() if not price_data.empty else pd.DataFrame()
            
            if not price_data_recent.empty:
                price_data_recent = price_data_recent.rename(columns={'unit_price': 'historical_price'})
                
                # Merge with predictions
                chart_data = pd.DataFrame({'date': price_data_recent['date'], 'Historical': price_data_recent['historical_price']})
                pred_chart_data = pd.DataFrame({'date': predictions_data['date'], 'Predicted': predictions_data['predicted_price']})
                
                # Combine
                combined = pd.concat([chart_data, pred_chart_data], ignore_index=True).sort_values('date')
                
                chart_file = f"/tmp/inv_{investment_id}_predictions.png"
                self.create_chart(
                    combined,
                    f"Price Predictions (Auto-ARIMA included) - {investment_name}",
                    "Date",
                    "Unit Price",
                    chart_file
                )
                img = Image(chart_file, width=6*inch, height=3.6*inch)
                elements.append(img)
                elements.append(Spacer(1, 0.3*inch))
        else:
            elements.append(Paragraph("No prediction data available", self.styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
        elements.append(PageBreak())
        return elements
    
    def generate_portfolio_page(self, portfolio_id):
        """Generate portfolio-specific charts."""
        elements = []
        
        elements.append(Paragraph("Portfolio Overview", self.heading_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Portfolio unit price history
        price_data = self.get_unit_price_data(portfolio_id)
        if not price_data.empty:
            chart_file = "/tmp/portfolio_prices.png"
            self.create_chart(
                price_data,
                "Total Portfolio Value Over Time",
                "Date",
                "Portfolio Value (ZAR)",
                chart_file
            )
            img = Image(chart_file, width=6*inch, height=3.6*inch)
            elements.append(img)
            elements.append(Spacer(1, 0.3*inch))
        
        # Portfolio metrics
        metrics_data = self.get_metrics_data(portfolio_id)
        if not metrics_data.empty:
            chart_file = "/tmp/portfolio_metrics.png"
            metrics_subset = metrics_data[['date', 'CAGR', 'IRR', 'Total Return']].copy()
            for col in ['CAGR', 'IRR', 'Total Return']:
                metrics_subset[col] = metrics_subset[col] * 100
            
            self.create_chart(
                metrics_subset,
                "Portfolio Performance Metrics",
                "Date",
                "Percentage (%)",
                chart_file
            )
            img = Image(chart_file, width=6*inch, height=3.6*inch)
            elements.append(img)
            elements.append(Spacer(1, 0.3*inch))
        
        # Portfolio predictions
        predictions_data = self.get_predictions_data(portfolio_id)
        if not predictions_data.empty and not price_data.empty:
            price_data_recent = price_data.tail(30).copy()
            price_data_recent = price_data_recent.rename(columns={'unit_price': 'historical_value'})
            
            chart_data = pd.DataFrame({'date': price_data_recent['date'], 'Historical': price_data_recent['historical_value']})
            pred_chart_data = pd.DataFrame({'date': predictions_data['date'], 'Predicted': predictions_data['predicted_price']})
            
            combined = pd.concat([chart_data, pred_chart_data], ignore_index=True).sort_values('date')
            
            chart_file = "/tmp/portfolio_predictions.png"
            self.create_chart(
                combined,
                "Portfolio Value Predictions",
                "Date",
                "Portfolio Value (ZAR)",
                chart_file
            )
            img = Image(chart_file, width=6*inch, height=3.6*inch)
            elements.append(img)
            elements.append(Spacer(1, 0.3*inch))
        
        elements.append(PageBreak())
        return elements
    
    def generate_report(self, output_file):
        """Generate the complete PDF report."""
        print(f"Generating investment report: {output_file}")
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_file,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )
        
        elements = []
        
        # Title Page
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph("Investment Portfolio Report", self.title_style))
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles['Normal']
        ))
        elements.append(PageBreak())
        
        # Summary Table
        elements.append(Paragraph("Investment Summary", self.heading_style))
        elements.append(Spacer(1, 0.2*inch))
        
        summary_table = self.create_investment_summary_table()
        if summary_table:
            elements.append(summary_table)
        elements.append(PageBreak())
        
        # Get all investments
        with get_db_connection(self.database_name) as (conn, cursor):
            cursor.execute("""
                SELECT id, investment_name, investment_ticker
                FROM investments
                ORDER BY 
                    CASE WHEN investment_ticker = 'PORTFOLIO' THEN 0 ELSE 1 END,
                    id
            """)
            investments = cursor.fetchall()
        
        # Generate pages for each investment
        for inv_id, inv_name, inv_ticker in investments:
            if inv_ticker == 'PORTFOLIO':
                # Special handling for portfolio
                portfolio_elements = self.generate_portfolio_page(inv_id)
                elements.extend(portfolio_elements)
            else:
                # Regular investment
                inv_elements = self.generate_investment_page(inv_id, inv_name, inv_ticker)
                elements.extend(inv_elements)
        
        # Prediction vs Actual Comparison Page
        elements.append(PageBreak())
        elements.append(Paragraph("Prediction Accuracy Analysis", self.heading_style))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("Comparison of past predictions against actual performance to evaluate model accuracy.", self.styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))

        # Fetch accuracy data (simplified logic to fetch from DB)
        try:
             # This assumes we have a function or query to get this. 
             # For now, we will add a placeholder or simple chart if data exists in prediction_accuracy table.
             # In a real scenario, you'd fetch using a module function.
             with get_db_connection(self.database_name) as (conn, cursor):
                cursor.execute("""
                    SELECT 
                        pa.actual_date, 
                        pa.predicted_value, 
                        pa.actual_value,
                        p.model_name
                    FROM prediction_accuracy pa
                    JOIN predictions p ON pa.prediction_id = p.id
                    WHERE pa.created_at > NOW() - INTERVAL '90 days'
                    ORDER BY pa.actual_date ASC
                    LIMIT 100
                """)
                acc_data = cursor.fetchall()
                
                if acc_data:
                    df_acc = pd.DataFrame(acc_data, columns=['date', 'Predicted', 'Actual', 'Model'])
                    # Plot comparison for the first available model found (simplified for report)
                    model_name = df_acc['Model'].iloc[0]
                    df_plot = df_acc[df_acc['Model'] == model_name]
                    
                    if not df_plot.empty:
                        chart_file = "/tmp/prediction_accuracy_comparison.png"
                        
                        # Prepare data for existing chart function
                        plot_data = pd.DataFrame({
                            'date': pd.to_datetime(df_plot['date']),
                            'Predicted': df_plot['Predicted'].astype(float),
                            'Actual': df_plot['Actual'].astype(float)
                        })
                        
                        self.create_chart(
                            plot_data,
                            f"Prediction vs Actual ({model_name})",
                            "Date",
                            "Value",
                            chart_file
                        )
                        img = Image(chart_file, width=6*inch, height=3.6*inch)
                        elements.append(img)
                        elements.append(Paragraph(f"Showing accuracy for model: {model_name}", self.styles['Italic']))
                else:
                    elements.append(Paragraph("No sufficient historical prediction accuracy data available yet to display comparison.", self.styles['Normal']))

        except Exception as e:
            print(f"Could not generate accuracy chart: {e}")
            elements.append(Paragraph("Could not retrieve accuracy data.", self.styles['Normal']))

        # Build PDF
        doc.build(elements)
        
        # Cleanup temp files
        for temp_file in self.temp_chart_files:
            try:
                os.remove(temp_file)
            except:
                pass
        
        print(f"✓ Report generated: {output_file}")
        return output_file


def generate_investment_report(database_name=DEFAULT_DB, output_file=None):
    """
    Generate comprehensive investment PDF report.
    
    Args:
        database_name: Database name
        output_file: Output PDF file path (default: auto-generated)
    
    Returns:
        Path to generated PDF file
    """
    if output_file is None:
        output_file = f"investment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    reporter = InvestmentPDFReport(database_name)
    return reporter.generate_report(output_file)


if __name__ == "__main__":
    # Test report generation
    import sys
    
    output_file = sys.argv[1] if len(sys.argv) > 1 else "investment_report.pdf"
    generate_investment_report(DEFAULT_DB, output_file)
