"""
Comparison of the same asset held in different accounts.
=========================================================
The same fund / ETF / asset can appear in several accounts (e.g. a normal
brokerage account and a tax-free savings account).  It only makes sense to
store the historical prices once (they are shared through the price master),
but the metrics differ because buys happened at different times and amounts.
This module surfaces those differences side by side.
"""
from collections import defaultdict

from .database import get_db_connection, DEFAULT_DB


def _account_entry(row: tuple) -> dict:
    """Build a per-account comparison record from a query row."""
    (
        inv_id, name, institution, currency, status, unit_price, units, inv_type,
        price_source, source, net_growth, total_return, return_multiple, cagr, irr,
        fee_ratio, tax_ratio, dividend_yield, contributions, fees, tax, dividends,
        period_days, real_irr, real_cagr, num_contributions,
    ) = row

    current_value = (unit_price or 0.0) * (units or 0.0)

    def pct(v):
        try:
            return round(float(v) * 100, 2)
        except (TypeError, ValueError):
            return None

    period_years = round(period_days / 365.0, 1) if period_days else None

    return {
        "id": inv_id,
        "name": name,
        "institution": institution,
        "currency": currency,
        "status": status,
        "investment_type": inv_type,
        "current_price": round(float(unit_price or 0.0), 4),
        "units": round(float(units or 0.0), 4),
        "current_value": round(current_value, 2),
        "total_contributions": round(float(contributions or 0.0), 2),
        "net_growth": round(float(net_growth or 0.0), 2),
        "total_return_pct": pct(total_return),
        "return_multiple": round(float(return_multiple or 0.0), 2),
        "irr_pct": pct(irr),
        "cagr_pct": pct(cagr),
        "real_irr_pct": pct(real_irr),
        "real_cagr_pct": pct(real_cagr),
        "total_fee_ratio_pct": pct(fee_ratio),
        "total_tax_ratio_pct": pct(tax_ratio),
        "dividend_yield_pct": pct(dividend_yield),
        "total_fees": round(float(fees or 0.0), 2),
        "total_tax": round(float(tax or 0.0), 2),
        "total_dividends": round(float(dividends or 0.0), 2),
        "num_contributions": num_contributions,
        "period_years": period_years,
        "price_source_id": price_source,
    }


def get_investment_comparison(database_name: str = DEFAULT_DB) -> dict:
    """
    Find assets held in more than one account and return their metrics side by
    side.

    Investments are grouped by (price source, currency, normalized asset name)
    so that account markers like "TFSA" / "Voluntary" / "RA" are ignored while
    share-class markers are kept.  Investments already linked via
    ``price_source_investment_id`` share the same ``price_source`` value.
    """
    from .price_scraper import _asset_group_key

    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute("""
            SELECT i.id, i.investment_name, i.institution_name, i.unit_currency,
                   i.investment_status, i.unit_price, i.number_of_units_held,
                   i.investment_type,
                   COALESCE(i.price_source_investment_id, i.id) AS price_source,
                   COALESCE(m.source, 'unknown') AS source,
                   im.local_net_growth, im.local_total_return, im.local_return_multiple,
                   im.local_cagr, im.local_irr, im.local_total_fee_ratio,
                   im.local_total_tax_ratio, im.local_dividend_yield,
                   im.local_total_contributions, im.local_total_fees,
                   im.local_total_tax, im.local_total_dividends,
                   im.local_investment_period, im.local_real_irr, im.local_real_cagr,
                   im.local_number_of_contributions
            FROM investments i
            LEFT JOIN investment_source_meta m ON m.investment_id = i.id
            LEFT JOIN investment_metrics im ON im.investment_id = i.id
            WHERE i.investment_type <> 'Forex'
              AND i.investment_ticker <> 'PORTFOLIO'
            ORDER BY i.id
        """)
        rows = cursor.fetchall()

    groups: dict[tuple, list] = defaultdict(list)
    for row in rows:
        key = _asset_group_key(row[1])
        if key:
            groups[(row[9], row[3], key)].append(row)

    result_groups = []
    for (source, currency, key), members in groups.items():
        if len(members) < 2:
            continue
        accounts = [_account_entry(r) for r in members]
        accounts.sort(key=lambda a: a["current_value"], reverse=True)
        total_value = sum(a["current_value"] for a in accounts)
        for a in accounts:
            a["share_pct"] = round(a["current_value"] / total_value * 100, 1) if total_value else 0.0
        result_groups.append({
            "asset": members[0][1],
            "normalized_name": key,
            "source": source,
            "currency": currency,
            "accounts": accounts,
            "total_value": round(total_value, 2),
        })

    result_groups.sort(key=lambda g: g["asset"].lower())
    return {"groups": result_groups}
