import json
from .database import get_db_connection

def get_portfolio_metrics_data_api(database_name: str, dimension_type: str = "portfolio", dimension_value: str = "All") -> dict:
    """
    Returns time-series portfolio metrics formatted for the ViewInvestmentMetrics dashboard.
    """
    try:
        with get_db_connection(database_name) as (conn, cursor):
            query = """
                SELECT 
                    metrics_date,
                    total_contributions,
                    total_current_value,
                    total_return_amount,
                    total_return_pct,
                    total_fees,
                    total_dividends,
                    total_tax,
                    investment_count
                FROM portfolio_metrics
                WHERE dimension_type = %s AND dimension_value = %s
                ORDER BY metrics_date ASC
            """
            
            cursor.execute(query, (dimension_type, dimension_value))
            rows = cursor.fetchall()
            
            if not rows:
                return {
                    "portfolio_performance_return": [],
                    "rolling_returns": {"one_year": [], "three_year": [], "five_year": []},
                    "risk_metrics": {"volatility": [], "sharpe_ratio": [], "max_drawdown": []},
                    "contribution_vs_growth": [],
                    "drawdown_analysis": [],
                    "dividend_yield": [],
                    "fee_analysis": [],
                    "tax_analysis": [],
                    "cagr_trend": [],
                    "irr_trend": [],
                    "key_metrics": [],
                    "conclusion": "No data found for this filter.",
                    "filter_type": dimension_type,
                    "data_points": 0
                }
            
            # Arrays for charts
            contrib_vs_growth = []
            fee_analysis = []
            tax_analysis = []
            cagr_trend = []
            irr_trend = []
            portfolio_performance_return = []
            
            for idx, row in enumerate(rows):
                date_str = row[0].strftime("%Y-%m")
                contrib = float(row[1] or 0)
                current_val = float(row[2] or 0)
                ret_amt = float(row[3] or 0)
                ret_pct = float(row[4] or 0)
                fees = float(row[5] or 0)
                tax = float(row[7] or 0)
                
                contrib_vs_growth.append({
                    "period": date_str,
                    "contributions": contrib,
                    "growth": current_val - contrib,
                    "index": idx
                })
                
                fee_analysis.append({
                    "period": date_str,
                    "fee_ratio": (fees / current_val * 100) if current_val > 0 else 0,
                    "total_fees": fees,
                    "index": idx
                })
                
                tax_analysis.append({
                    "period": date_str,
                    "tax_ratio": (tax / current_val * 100) if current_val > 0 else 0,
                    "total_tax": tax,
                    "index": idx
                })
                
                cagr_trend.append({
                    "period": date_str,
                    "value": ret_pct, # Approximation for now
                    "index": idx
                })
                
                portfolio_performance_return.append({
                    "period": date_str,
                    "value": ret_pct,
                    "index": idx
                })
            
            # Key metrics
            latest = rows[-1]
            contrib = float(latest[1] or 0)
            current_val = float(latest[2] or 0)
            ret_amt = float(latest[3] or 0)
            
            key_metrics = [
                {"title": "Total Value", "value": f"R{current_val:,.2f}", "trend": "up", "change": ""},
                {"title": "Contributions", "value": f"R{contrib:,.2f}", "trend": "neutral", "change": ""},
                {"title": "Net Growth", "value": f"R{ret_amt:,.2f}", "trend": "up" if ret_amt > 0 else "down", "change": ""},
                {"title": "Active Investments", "value": str(latest[8]), "trend": "neutral", "change": ""}
            ]
            
            conclusion = f"Aggregated {dimension_type} '{dimension_value}': Total Value R{current_val:,.2f}, Total Contributions R{contrib:,.2f}, Growth R{ret_amt:,.2f}."
            
            return {
                "portfolio_performance_return": portfolio_performance_return,
                "rolling_returns": {"one_year": [], "three_year": [], "five_year": []},
                "risk_metrics": {"volatility": [], "sharpe_ratio": [], "max_drawdown": []},
                "contribution_vs_growth": contrib_vs_growth,
                "drawdown_analysis": [],
                "dividend_yield": [],
                "fee_analysis": fee_analysis,
                "tax_analysis": tax_analysis,
                "cagr_trend": cagr_trend,
                "irr_trend": cagr_trend,
                "key_metrics": key_metrics,
                "conclusion": conclusion,
                "filter_type": dimension_type,
                "data_points": len(rows)
            }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Exception(f"Database error: {str(e)}")
