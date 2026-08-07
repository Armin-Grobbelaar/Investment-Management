"""
ProfileData Scraper
===================
Scrapes historical unit prices from:
  https://funds.profiledata.co.za/aci/ASISA/HistPriceLookUp.aspx

Used as a fallback when Yahoo Finance does not have data for a fund
(typically SA unit trusts not listed on JSE).

Usage:
    prices = fetch_profiledata_prices(
        investment_name="Allan Gray Equity Fund Class A",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 10)
    )
    # Returns: [(date, float), ...]
"""

import logging
import re
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger("profiledata_scraper")

PROFILEDATA_URL = "https://funds.profiledata.co.za/aci/ASISA/HistPriceLookUp.aspx"

# ─────────────────────────────────────────────────────────────────────────────
# Name parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

# Known CIS manager name mappings (investment name fragment → dropdown label)
CIS_MANAGER_MAP = {
    "allan gray": "Allan Gray Unit Trust Management (RF) Pty Limited",
    "coronation": "Coronation Management Company (RF) (Pty) Ltd.",
    "psg": "PSG Collective Investments (RF) Ltd.",
    "psg wealth": "PSG Collective Investments (RF) Ltd.",
    "alexander forbes": "Alexander Forbes Investments Unit Trusts Limited",
    "af ": "Alexander Forbes Investments Unit Trusts Limited",
    "prescient": "Prescient Management Company Ltd. (PIM)",
    "ninety one": "Ninety One Fund Managers SA (RF) (Pty) Ltd.",
    "old mutual": "Old Mutual Unit Trust Managers (RF) (Pty) Ltd.",
    "satrix": "Satrix Managers",
    "sanlam": "Sanlam Collective Investments",
    "stanlib": "STANLIB Asset Management",
    "investec": "Ninety One Fund Managers SA (RF) (Pty) Ltd.",
    "foord": "Foord Unit Trusts Limited",
    "nedgroup": "Nedgroup Collective Investments (RF) (Pty) Ltd.",
    "discovery": "Discovery Life Collective Investments (Pty) Ltd.",
    "absa": "Absa Asset Management",
    "momentum": "Momentum Collective Investments Limited",
    "amplify": "Amplify Investment Partners",
    "perpetua": "Perpetua Investment Managers",
    "m&g": "M&G Unit Trust South Africa Ltd.",
    "mandg": "M&G Unit Trust South Africa Ltd.",
}

# Class patterns: extract class letter/number from fund name
CLASS_PATTERNS = [
    r'\bclass\s+([A-Z][0-9]?[a-z]?)\b',   # 'Class A', 'Class B2'
    r'\(([A-Z][0-9]?)\)\s*$',              # '(A)' at end
    r'\(([A-Z][0-9]?)\)\s*[-–]',           # '(E) - Voluntary' mid-name
    r'\b([A-Z][0-9]?)\s*class\b',          # 'A class'
    r'-([A-Z][0-9]?)\s*$',                 # '-A' at end
]


def parse_investment_name(investment_name: str) -> dict:
    """
    Parse an investment name into manager, fund, and class components.
    
    Examples:
        'Allan Gray Equity Fund Class A' → {'manager': 'Allan Gray', 'fund': 'Equity Fund', 'class': 'A'}
        'PSG Global Equity Feeder Fund (E)' → {'manager': 'PSG', 'fund': 'Global Equity Feeder Fund', 'class': 'E'}
        'Top 20 Fund (TFI A class)' → {'manager': 'Coronation', 'fund': 'Top 20 Fund', 'class': 'A'}
    """
    name = investment_name.strip()
    name_lower = name.lower()
    
    # 1. Detect class
    fund_class = None
    name_without_class = name
    for pattern in CLASS_PATTERNS:
        m = re.search(pattern, name, re.IGNORECASE)
        if m:
            fund_class = m.group(1).upper()
            # Remove class part from name for further parsing
            name_without_class = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()
            break
    
    # 2. Detect CIS manager
    cis_manager = None
    manager_key = None
    # Sort by length descending to match longer names first
    for key in sorted(CIS_MANAGER_MAP.keys(), key=len, reverse=True):
        if key in name_lower:
            cis_manager = CIS_MANAGER_MAP[key]
            manager_key = key
            break
    
    # 3. Extract fund name (remove manager name from the beginning)
    fund_name = name_without_class
    if manager_key:
        # Remove manager prefix case-insensitively
        fund_name = re.sub(re.escape(manager_key), '', fund_name, flags=re.IGNORECASE).strip()
        # Clean up leading/trailing punctuation
        fund_name = fund_name.lstrip('- ').rstrip('- ').strip()
    
    # Remove parenthetical class indicators from fund name
    fund_name = re.sub(r'\s*\([A-Z][0-9]?\)\s*$', '', fund_name).strip()
    fund_name = re.sub(r'\s*class\s+[A-Z][0-9]?\s*$', '', fund_name, flags=re.IGNORECASE).strip()

    # Strip common user-applied labels (NOT part of the fund name on the site)
    fund_name = re.sub(r'\s*(?:-\s*)?(Voluntary|TFSA|Tax\s*Free|RA|Retirement|Lump\s*Sum|Flexible|Monthly)\s*$',
                       '', fund_name, flags=re.IGNORECASE).strip()
    fund_name = re.sub(r'\s*\((?:TFSA|Tax\s*Free|RA|Retirement|Voluntary)\)\s*$', '',
                       fund_name, flags=re.IGNORECASE).strip()

    return {
        'manager': cis_manager,
        'manager_key': manager_key,
        'fund': fund_name if fund_name else name_without_class,
        'class': fund_class,
        'original': investment_name
    }


# ─────────────────────────────────────────────────────────────────────────────
# Playwright scraper
# ─────────────────────────────────────────────────────────────────────────────

def fetch_profiledata_prices(
    investment_name: str,
    start_date: date,
    end_date: date,
    headless: bool = True
) -> list[tuple[date, float]]:
    """
    Fetch historical NAV prices from ProfileData for a given fund.
    
    Instead of fetching one day at a time (which is extremely slow),
    this uses the "Get All" feature or fetches in batches of 10 days.
    
    Args:
        investment_name: Full investment name, e.g. 'Allan Gray Equity Fund Class A'
        start_date: Start of date range
        end_date: End of date range
        headless: Run browser headlessly
    
    Returns:
        List of (date, price) tuples
    """
    parsed = parse_investment_name(investment_name)
    logger.info(f"ProfileData: Parsed '{investment_name}' → {parsed}")
    
    if not parsed['manager']:
        logger.warning(f"ProfileData: Could not determine CIS manager for '{investment_name}'")
        return []
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return []
    
    from .playwright_helper import chromium_path
    chromium = chromium_path()
    if chromium is None:
        return []
    
    results = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless, executable_path=chromium)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
            )
            page = context.new_page()
            # Retry page navigation up to 3 times
            for attempt in range(1, 4):
                try:
                    page.goto(PROFILEDATA_URL, timeout=30000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                    break
                except Exception as nav_err:
                    if attempt == 3:
                        raise nav_err
                    logger.warning(f"ProfileData: page.goto attempt {attempt} failed ({nav_err}), retrying...")
                    page.wait_for_timeout(2000)
            
            # Select CIS Manager
            manager_selected = _select_cis_manager(page, parsed['manager'])
            if not manager_selected:
                logger.warning(f"ProfileData: Could not select manager '{parsed['manager']}'")
                browser.close()
                return []
            
            # Wait for fund dropdown to populate
            try:
                page.wait_for_function("document.getElementsByName('TrustNo')[0] && document.getElementsByName('TrustNo')[0].options.length > 1", timeout=10000)
            except Exception as e:
                logger.warning(f"ProfileData: wait_for_function timeout for TrustNo: {e}")
            page.wait_for_timeout(500)
            
            # Select Fund
            # Use the cleaned fund name (class + user labels stripped) so it
            # matches the dropdown option text on the ProfileData site.
            fund_match_name = parsed['fund'] if parsed['fund'] else parsed['original']
            
            fund_selected = _select_fund(page, fund_match_name, parsed['class'])
            if not fund_selected:
                logger.warning(f"ProfileData: Could not select fund '{fund_match_name}'")
                browser.close()
                return []
            
            page.wait_for_timeout(1000)
            
            # Fetch prices for every business day in the requested range.
            # The site only answers ONE date per query, so we query each day.
            results = _fetch_date_range(page, start_date, end_date, parsed['class'])
            logger.info(f"ProfileData: Fetched {len(results)} prices for {investment_name} ({start_date} – {end_date})")
            
            browser.close()
    
    except Exception as e:
        logger.error(f"ProfileData scraper error: {e}")
    
    return results


def _select_cis_manager(page, manager_name: str) -> bool:
    """Select the CIS manager from the dropdown."""
    try:
        manager_select = page.query_selector("select[name='MANCO_ID']")
        if not manager_select:
            return False
        
        options = manager_select.query_selector_all('option')
        
        # Find best matching option
        best_match = None
        best_score = 0
        manager_lower = manager_name.lower()
        
        for opt in options:
            opt_text = (opt.inner_text() or '').strip()
            opt_lower = opt_text.lower()
            score = _name_similarity(manager_lower, opt_lower)
            if score > best_score:
                best_score = score
                best_match = opt.get_attribute('value') or opt_text
        
        if best_match and best_score > 0.5:
            manager_select.select_option(value=best_match)
            logger.info(f"ProfileData: Selected manager '{best_match}' (score={best_score:.2f})")
            return True
        
        # Fallback: try partial text match
        for opt in options:
            opt_text = (opt.inner_text() or '').strip().lower()
            for word in manager_name.lower().split():
                if len(word) > 3 and word in opt_text:
                    val = opt.get_attribute('value') or opt.inner_text()
                    manager_select.select_option(value=val)
                    logger.info(f"ProfileData: Selected manager via keyword '{word}'")
                    return True
        
        return False
    except Exception as e:
        logger.error(f"_select_cis_manager error: {e}")
        return False


def _fetch_price_batch(page, start_date: date, end_date: date, fund_class: Optional[str]) -> list[tuple[date, float]]:
    """
    Fetch prices for a single date by setting PriceDate and clicking Continue.
    The ProfileData site only returns prices for ONE queried date at a time.
    Returns the class-filtered price(s) for that date.
    """
    results = []
    try:
        # Format date as e.g. "04 Aug 2026"
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        date_str_za = f"{start_date.day:02d} {months[start_date.month - 1]} {start_date.year}"
        
        # Set date value via JS because input is readonly
        page.evaluate(f"document.querySelector(\"input[name='PriceDate']\").value = '{date_str_za}'")
        
        # Click the lookup/submit button
        page.evaluate("document.querySelector(\"input[name='Submit']\").click()")
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(500)
        
        # Extract prices from result table
        prices = _extract_prices_from_page(page, fund_class)
        
        # Filter to our date range
        for d, p in prices:
            if start_date <= d <= end_date:
                results.append((d, p))
        
        # Navigate back so the form is available for the next query
        page.go_back()
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(500)
        
    except Exception as e:
        logger.warning(f"_fetch_price_batch({start_date}): {e}")
        # Attempt recovery by going back if we're on the results page
        try:
            page.go_back()
            page.wait_for_timeout(500)
        except Exception:
            pass
    return results


def _fetch_date_range(page, start_date: date, end_date: date,
                      fund_class: Optional[str]) -> list[tuple[date, float]]:
    """
    Fetch prices for every business day in [start_date, end_date].
    Queries one date at a time with a respectful delay between requests.
    """
    import time
    import random

    results: list[tuple[date, float]] = []
    current = start_date
    while current <= end_date:
        # Skip weekends (Saturday=5, Sunday=6)
        if current.weekday() < 5:
            batch = _fetch_price_batch(page, current, end_date, fund_class)
            results.extend(batch)
        current += timedelta(days=1)
        # Respectful delay to avoid overloading the site
        time.sleep(random.uniform(0.8, 1.5))
    return results


def _extract_prices_from_page(page, fund_class: Optional[str]) -> list[tuple[date, float]]:
    """
    Extract all NAV prices from the results table.
    If fund_class is specified, find the matching row.
    Otherwise, return the mean of all class prices.
    """
    prices = []
    try:
        # Look for tables with price data
        tables = page.query_selector_all('table')
        
        for table in tables:
            rows = table.query_selector_all('tr')
            for row in rows:
                cells = row.query_selector_all('td, th')
                if len(cells) < 2:
                    continue
                
                row_texts = [c.inner_text().strip() for c in cells]
                
                # Try to find date and price in the row
                price_val = None
                date_val = None
                
                for text in row_texts:
                    # Try to parse as date (DD Mon YYYY or YYYY-MM-DD)
                    date_match = re.match(r'(\d{2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})', text, re.IGNORECASE)
                    if date_match:
                        months_map = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
                        date_val = date(int(date_match.group(3)), months_map[date_match.group(2).lower()], int(date_match.group(1)))
                        continue
                    
                    # Try to parse as price
                    try:
                        cleaned = text.replace(',', '').replace('R', '').replace('r', '').replace(' ', '').replace('\xa0', '').strip()
                        val = float(cleaned)
                        if 0.01 < val < 1000000:  # Reasonable NAV range
                            # The site reports "Price(cents)" — convert to Rands.
                            price_val = val / 100.0
                    except ValueError:
                        continue
                
                if date_val and price_val:
                    # ── Class matching ──────────────────────────────────────
                    if fund_class:
                        class_upper = fund_class.upper()
                        # Match ONLY in cells that are short (1-4 chars) and
                        # look like a class indicator, to avoid false positives
                        # like "A" matching inside "Allan".
                        matched = False
                        for t in row_texts:
                            t_stripped = t.strip()
                            if len(t_stripped) <= 4 and class_upper == t_stripped.upper():
                                matched = True
                                break
                        if matched:
                            prices.append((date_val, price_val))
                    else:
                        prices.append((date_val, price_val))
        
        # If we have multiple classes and no specific class was requested, average them
        if not fund_class and prices:
            # Group by date and average
            from collections import defaultdict
            by_date = defaultdict(list)
            for d, p in prices:
                by_date[d].append(p)
            prices = [(d, sum(ps)/len(ps)) for d, ps in sorted(by_date.items())]
        
        return prices
    
    except Exception as e:
        logger.warning(f"_extract_prices_from_page error: {e}")
        return []


def _name_similarity(a: str, b: str) -> float:
    """Simple word-overlap similarity between two strings."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    # Remove common stop words
    stop = {'the', 'a', 'an', 'of', 'and', 'or', 'in', 'for', 'to', 'fund', 'class'}
    words_a -= stop
    words_b -= stop
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _select_fund(page, fund_name: str, fund_class: Optional[str] = None) -> bool:
    """
    Select the fund from the dropdown.

    ``fund_name`` is the cleaned fund name (manager + class stripped).
    ``fund_class`` (if provided) is the share-class letter, which is used to
    disambiguate between e.g. "Equity Fund A" and "Equity Fund B".
    """
    try:
        fund_select = page.query_selector("select[name='TrustNo']")
        if not fund_select:
            return False

        options = fund_select.query_selector_all('option')

        STOP = {'the', 'a', 'an', 'of', 'and', 'or', 'in', 'for', 'to', 'fund', 'class',
                'funds', 'unit', 'trust'}
        name_words = {w for w in re.findall(r'[a-z0-9]+', fund_name.lower()) if w not in STOP}
        if not name_words:
            return False

        best_match = None
        best_score = -1.0
        class_upper = (fund_class or "").upper()

        for opt in options:
            opt_text = (opt.inner_text() or '').strip()
            if not opt_text:
                continue
            opt_words = {w for w in re.findall(r'[a-z0-9]+', opt_text.lower()) if w not in STOP}
            if not opt_words:
                continue

            # coverage: fraction of desired name present in the option
            coverage = len(name_words & opt_words) / len(name_words)
            # precision: fraction of option that is the desired name
            precision = len(name_words & opt_words) / len(opt_words)
            # SequenceMatcher for ordering/similarity of the raw strings
            try:
                from difflib import SequenceMatcher
                sm = SequenceMatcher(None, fund_name.lower(), opt_text.lower()).ratio()
            except Exception:
                sm = 0.0

            score = 0.55 * coverage + 0.20 * precision + 0.15 * sm
            # Boost options that carry the requested class letter
            if class_upper and re.search(r'[\(\s\-]?' + re.escape(class_upper) + r'[\)\s,.]?$', opt_text, re.IGNORECASE):
                score += 0.15

            if score > best_score:
                best_score = score
                best_match = opt.get_attribute('value') or opt_text

        # Lower threshold for clear coverage (a fund whose name appears fully)
        threshold = 0.35 if class_upper else 0.45
        if best_match and best_score >= threshold:
            fund_select.select_option(value=best_match)
            logger.info(f"ProfileData: Selected fund '{best_match}' (score={best_score:.2f})")
            return True

        logger.info(f"ProfileData: Fund match failed for '{fund_name}' — best score {best_score:.2f}")
        return False
    except Exception as e:
        logger.error(f"_select_fund error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Integration with price_scraper batch system
# ─────────────────────────────────────────────────────────────────────────────

def backfill_profiledata_prices(
    investment_id: int,
    investment_name: str,
    database_name: str,
    batch_days: int = 10
) -> int:
    """
    Fetch and store up to `batch_days` historical prices for an investment
    using ProfileData scraper. Performs backwards backfill starting from today.
    
    Returns number of prices stored.
    """
    from datetime import datetime, date
    from .database import get_db_connection
    
    try:
        with get_db_connection(database_name) as (conn, cursor):
            # Get existing price dates
            cursor.execute(
                "SELECT unit_price_date FROM unit_prices WHERE investment_id = %s",
                (investment_id,)
            )
            existing_dates = {row[0] for row in cursor.fetchall()}
            
            # Get earliest investment date (inception)
            cursor.execute("""
                SELECT LEAST(MIN(t.transaction_date), i.initial_investment_date)
                FROM investments i
                LEFT JOIN transactions t ON t.investment_id = i.id
                WHERE i.id = %s
                GROUP BY i.initial_investment_date
            """, (investment_id,))
            row = cursor.fetchone()
            inception_dt = row[0] if row and row[0] else (date.today() - timedelta(days=365))
            
            # Get backfill cursor from source meta
            cursor.execute(
                "SELECT backfill_cursor, backfill_complete FROM investment_source_meta WHERE investment_id = %s",
                (investment_id,)
            )
            meta_row = cursor.fetchone()
            
            backfill_complete = False
            if meta_row and meta_row[1]:  # backfill_complete = True
                # Fully backfilled: only fetch today
                start_dt = date.today()
                end_dt = date.today()
                backfill_complete = True
            else:
                # Still backfilling
                if meta_row and meta_row[0]:  # backfill_cursor exists
                    end_dt = meta_row[0] - timedelta(days=1)
                else:
                    end_dt = date.today()
                
                start_dt = end_dt - timedelta(days=batch_days)
                if start_dt <= inception_dt:
                    start_dt = inception_dt
                    backfill_complete = True
            
            if start_dt > end_dt:
                backfill_complete = True
                start_dt = date.today()
                end_dt = date.today()
        
        # Fetch prices
        prices = []
        if start_dt <= end_dt:
            logger.info(f"ProfileData backfill for '{investment_name}': fetching {start_dt} to {end_dt} (backwards cursor)...")
            prices = fetch_profiledata_prices(investment_name, start_dt, end_dt)
        
        if not prices:
            logger.warning(f"ProfileData: No prices for '{investment_name}' ({start_dt} – {end_dt})")
            if not backfill_complete:
                with get_db_connection(database_name) as (conn, cursor):
                    new_cursor = start_dt
                    cursor.execute("""
                        INSERT INTO investment_source_meta (investment_id, source, backfill_cursor, backfill_complete, last_fetched)
                        VALUES (%s, 'profiledata', %s, %s, NOW())
                        ON CONFLICT (investment_id)
                        DO UPDATE SET
                            backfill_cursor = EXCLUDED.backfill_cursor,
                            backfill_complete = EXCLUDED.backfill_complete,
                            last_fetched = NOW()
                    """, (investment_id, new_cursor, False))
                    conn.commit()
            return 0
        
        # Store prices
        stored = 0
        with get_db_connection(database_name) as (conn, cursor):
            for price_date, price in prices:
                if price_date not in existing_dates:
                    cursor.execute("""
                        INSERT INTO unit_prices (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change)
                        VALUES (%s, %s, %s, 0.0, 0.0)
                        ON CONFLICT (investment_id, unit_price_date)
                        DO UPDATE SET unit_price = EXCLUDED.unit_price
                    """, (investment_id, price_date, price))
                    stored += 1
            
            # Update backfill cursor
            new_cursor = start_dt
            cursor.execute("""
                INSERT INTO investment_source_meta (investment_id, source, backfill_cursor, backfill_complete, last_fetched)
                VALUES (%s, 'profiledata', %s, %s, NOW())
                ON CONFLICT (investment_id)
                DO UPDATE SET
                    backfill_cursor = EXCLUDED.backfill_cursor,
                    backfill_complete = EXCLUDED.backfill_complete,
                    last_fetched = NOW()
            """, (investment_id, new_cursor, backfill_complete))
            
            # Update current unit price to the latest price fetched
            if prices:
                latest_price = prices[-1][1]
                cursor.execute(
                    "UPDATE investments SET unit_price = %s WHERE id = %s",
                    (latest_price, investment_id)
                )
            
            conn.commit()
        
        logger.info(f"ProfileData: Stored {stored} prices for '{investment_name}'")
        return stored
    
    except Exception as e:
        logger.error(f"ProfileData backfill error for '{investment_name}': {e}")
        return 0