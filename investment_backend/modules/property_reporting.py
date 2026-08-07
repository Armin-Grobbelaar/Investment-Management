import os
import uuid
import numpy as np
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

def generate_property_pdf_report(payload: dict, output_file: str = None) -> str:
    """
    Generates a PDF report for Property Analysis.
    payload contains:
    - inputs (dict)
    - result (dict)
    - monte_carlo (dict)
    - sensitivity (dict)
    """
    if not output_file:
        output_file = f"/tmp/property_report_{uuid.uuid4().hex[:8]}.pdf"
        
    inputs = payload.get("inputs", {})
    result = payload.get("result", {})
    monte_carlo = payload.get("monte_carlo", {})
    sensitivity = payload.get("sensitivity", {})
    
    doc = SimpleDocTemplate(
        output_file,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2980b9'),
        spaceBefore=12,
        spaceAfter=6
    )
    normal_style = styles['Normal']
    
    elements = []
    
    # --- Title Page ---
    property_name = inputs.get("property_name", "Property Investment")
    elements.append(Paragraph(f"{property_name} Analysis Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
    elements.append(Spacer(1, 0.5 * inch))
    
    # --- Executive Summary ---
    elements.append(Paragraph("Executive Summary", h2_style))
    
    def format_curr(val):
        if val is None: return "N/A"
        return f"R {val:,.2f}"
        
    def format_pct(val):
        if val is None: return "N/A"
        return f"{val:.2f}%"

    summary_data = [
        ["Metric", "Value"],
        ["Purchase Price", format_curr(inputs.get("purchase_price"))],
        ["Total Acquisition Cost", format_curr(result.get("total_acquisition_cost"))],
        ["Initial Outflow", format_curr(result.get("initial_outflow"))],
        ["Bond Amount", format_curr(result.get("bond_amount"))],
        ["Monthly Bond Repayment", format_curr(result.get("bond_monthly_repayment"))],
        ["First Year Gross Yield", format_pct(result.get("first_year_gross_yield"))],
        ["First Year Net Yield", format_pct(result.get("first_year_net_yield"))],
        ["10-Year Nominal IRR", format_pct(result.get("irr_10yr"))],
        ["10-Year Real IRR", format_pct(result.get("real_irr_10yr"))]
    ]
    
    t_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('GRID', (0,0), (-1,-1), 1, colors.white),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
    ])
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(t_style)
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5 * inch))
    
    # --- Input Parameters ---
    elements.append(Paragraph("Key Parameters", h2_style))
    params_data = [
        ["Parameter", "Value", "Parameter", "Value"],
        ["Deposit Amount", format_curr(inputs.get("deposit_amount")), "Bond Interest Rate", format_pct(inputs.get("bond_interest_rate"))],
        ["Bond Term (Years)", str(inputs.get("bond_term_years")), "Monthly Rent", format_curr(inputs.get("monthly_rental_income"))],
        ["Rental Growth p.a.", format_pct(inputs.get("rental_growth_rate_pa", 0)*100), "Prop Growth p.a.", format_pct(inputs.get("property_growth_rate_pa", 0)*100)],
        ["Vacancy Rate", format_pct(inputs.get("vacancy_rate_pct")), "Inflation Rate", format_pct(inputs.get("inflation_rate", 0)*100)],
        ["Monthly Levies", format_curr(inputs.get("monthly_levy")), "Monthly Rates", format_curr(inputs.get("monthly_rates"))]
    ]
    
    p_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ])
    params_table = Table(params_data, colWidths=[1.8*inch, 1.2*inch, 1.8*inch, 1.2*inch])
    params_table.setStyle(p_style)
    elements.append(params_table)
    
    elements.append(PageBreak())
    
    # --- Cash Flow Projection ---
    elements.append(Paragraph("10-Year Projections", h2_style))
    
    monthly_proj = result.get("monthly_projection", [])
    if monthly_proj:
        proj_data = [["Year", "Rent", "Expenses", "Bond", "Net Cash Flow", "Prop Value", "Equity"]]
        for i, row in enumerate(monthly_proj):
            if i >= 10: break
            proj_data.append([
                str(row.get("year")),
                format_curr(row.get("monthly_rental")),
                format_curr(row.get("monthly_expenses")),
                format_curr(row.get("monthly_bond")),
                format_curr(row.get("annual_net_cash_flow")),
                format_curr(row.get("property_value")),
                format_curr(row.get("equity"))
            ])
            
        proj_table = Table(proj_data)
        proj_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ]))
        elements.append(proj_table)
        elements.append(Spacer(1, 0.5 * inch))

    # --- Monte Carlo Summary ---
    elements.append(Paragraph("Monte Carlo Analysis (20 Yrs)", h2_style))
    if monte_carlo:
        percentiles = monte_carlo.get("percentiles_irr", {})
        mc_data = [
            ["Metric", "Nominal IRR", "Real IRR"],
            ["Median (50th %)", format_pct(percentiles.get("p50")), "N/A"],
            ["5th Percentile (Worst Case)", format_pct(percentiles.get("p5")), "N/A"],
            ["95th Percentile (Best Case)", format_pct(percentiles.get("p95")), "N/A"],
            ["Prob of Positive IRR", f"{monte_carlo.get('prob_positive_irr', 0):.2f}%", ""],
            ["Prob Beats Inflation", f"{monte_carlo.get('prob_irr_beats_inflation', 0):.2f}%", ""]
        ]
        mc_table = Table(mc_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
        mc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8e44ad')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ]))
        elements.append(mc_table)

    doc.build(elements)
    return output_file
