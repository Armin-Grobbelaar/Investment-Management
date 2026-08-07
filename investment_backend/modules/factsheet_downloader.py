import os
import urllib.parse
import requests
import logging
from datetime import date, datetime
from typing import Optional
from playwright.sync_api import sync_playwright
from .database import get_db_connection

logger = logging.getLogger("factsheet_downloader")
logging.basicConfig(level=logging.INFO)

FACTSHEETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "factsheets")

ASSET_MANAGER_MDD_URLS = {
    "allan gray": "https://www.allangray.co.za/globalassets/documents/fund-documents/{fund_slug}-mdd.pdf",
    "coronation": "https://www.coronation.com/globalassets/documents/fund-documents/{fund_slug}-mdd.pdf",
    "ninety one": "https://ninetyone.com/-/media/documents/factsheets/{fund_slug}-mdd-en-za.pdf",
    "satrix": "https://satrix.co.za/documents/factsheet/{fund_slug}-mdd.pdf"
}

def get_factsheet_path(investment_id: int, year: int, month: int, factsheet_type: str = "MDD") -> str:
    """Get absolute file path to store factsheet PDF."""
    dir_path = os.path.join(FACTSHEETS_DIR, str(investment_id))
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, f"{year}_{month:02d}_{factsheet_type}.pdf")

def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower()
    # Replace separators and special characters with dashes
    for char in [" ", "/", "\\", "_", ",", ".", "&", "(", ")", "!", "?",
                 "'", '"', "+", "%", "#", "@", "*", "$", ":", ";", "="]:
        text = text.replace(char, "-")
    # Remove consecutive dashes
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-")

def search_pdf_via_google(query: str, headless: bool = True) -> Optional[str]:
    """Search for a PDF URL using DuckDuckGo Lite with Playwright, falling back to Google on failure."""
    logger.info(f"Searching PDF via search query: {query}")
    from .playwright_helper import chromium_path
    chromium = chromium_path()
    if chromium is None:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless, executable_path=chromium)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            pdf_urls = []
            
            # Try DuckDuckGo Lite first (less JS, less CAPTCHAs)
            try:
                search_url = f"https://lite.duckduckgo.com/lite/"
                page.goto(search_url, timeout=30000)
                page.fill("input[name='q']", query)
                page.click("input[type='submit']")
                page.wait_for_load_state("networkidle", timeout=10000)
                
                links = page.query_selector_all("a")
                for link in links:
                    href = link.get_attribute("href")
                    if href and href.startswith("http"):
                        # DDG Lite redirect
                        if "uddg=" in href:
                            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            if 'uddg' in parsed:
                                href = parsed['uddg'][0]
                        
                        if href.lower().endswith(".pdf") or "mdd" in href.lower() or "factsheet" in href.lower():
                            pdf_urls.append(href)
            except Exception as e:
                logger.warning(f"DuckDuckGo search failed: {e}")
            
            # Fallback to Google if no URLs found
            if not pdf_urls:
                try:
                    search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                    page.goto(search_url, timeout=30000)
                    page.wait_for_load_state("networkidle", timeout=10000)
                    
                    links = page.query_selector_all("a")
                    for link in links:
                        href = link.get_attribute("href")
                        if href and href.startswith("http"):
                            if href.lower().endswith(".pdf") or "mdd" in href.lower() or "factsheet" in href.lower():
                                pdf_urls.append(href)
                except Exception as e:
                    logger.warning(f"Google search failed: {e}")
            
            browser.close()
            
            if pdf_urls:
                # Return the first actual PDF URL found
                for url in pdf_urls:
                    if url.lower().endswith(".pdf"):
                        return url
                return pdf_urls[0]
    except Exception as e:
        logger.error(f"Search completely failed: {e}")
    return None

def download_factsheet(investment_id: int, investment_name: str, institution_name: str, database_name: str, factsheet_type: str = 'MDD') -> dict:
    """Download the latest factsheet for an investment and log it in the database."""
    today = date.today()
    year = today.year
    month = today.month
    
    # Check if we already have it
    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute("""
            SELECT id FROM factsheets 
            WHERE investment_id = %s AND factsheet_year = %s AND factsheet_month = %s AND factsheet_type = %s
        """, (investment_id, year, month, factsheet_type))
        if cursor.fetchone():
            return {"success": True, "file_path": get_factsheet_path(investment_id, year, month, factsheet_type), "url": None, "error": "Already downloaded this month"}
    
    source_url = None
    inst_lower = institution_name.lower().strip()
    
    # Check known URL patterns
    for manager, pattern in ASSET_MANAGER_MDD_URLS.items():
        if manager in inst_lower:
            slug = _slugify(investment_name)
            # Remove class suffix like '-class-a' if required for some managers, but usually the class is in the slug
            source_url = pattern.format(fund_slug=slug)
            # Quick check if URL exists using HEAD request
            try:
                if requests.head(source_url, timeout=5).status_code != 200:
                    source_url = None
                else:
                    break
            except requests.RequestException:
                source_url = None
            
    if not source_url:
        # Search query
        query = f"{institution_name} {investment_name} {factsheet_type} filetype:pdf"
        source_url = search_pdf_via_google(query)
        
    if not source_url:
        logger.warning(f"Could not find {factsheet_type} PDF URL for {investment_name}")
        return {"success": False, "file_path": None, "url": None, "error": "URL not found"}
        
    logger.info(f"Downloading {factsheet_type} from {source_url}...")
    file_path = get_factsheet_path(investment_id, year, month, factsheet_type)
    
    try:
        # Download file using requests with browser headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        r = requests.get(source_url, headers=headers, timeout=30)
        if r.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(r.content)
            file_name = os.path.basename(file_path)
            file_size = len(r.content)
            
            # Save metadata to DB
            with get_db_connection(database_name) as (conn, cursor):
                # Using DO UPDATE to avoid duplicate inserts on race conditions
                cursor.execute("""
                    INSERT INTO factsheets (
                        investment_id, factsheet_date, factsheet_type, factsheet_year, factsheet_month, 
                        source_url, file_path, file_name, file_size_bytes, downloaded_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT ON CONSTRAINT factsheets_investment_id_factsheet_year_factsheet_month_fac_key
                    DO UPDATE SET source_url = EXCLUDED.source_url, file_size_bytes = EXCLUDED.file_size_bytes, downloaded_at = EXCLUDED.downloaded_at
                """, (
                    investment_id, today, factsheet_type, year, month,
                    source_url, file_path, file_name, file_size, datetime.now()
                ))
                conn.commit()
                
            return {"success": True, "file_path": file_path, "url": source_url, "error": None}
        else:
            return {"success": False, "file_path": None, "url": source_url, "error": f"HTTP status {r.status_code}"}
    except Exception as e:
        logger.error(f"Failed to download {factsheet_type}: {e}")
        return {"success": False, "file_path": None, "url": source_url, "error": str(e)}

def get_factsheets_for_investment(investment_id: int, database_name: str, year: Optional[int] = None, month: Optional[int] = None) -> list[dict]:
    """Get metadata for all factsheets belonging to an investment."""
    with get_db_connection(database_name) as (conn, cursor):
        query = "SELECT id, factsheet_date, factsheet_type, factsheet_year, factsheet_month, file_name, file_size_bytes, downloaded_at FROM factsheets WHERE investment_id = %s"
        params = [investment_id]
        if year:
            query += " AND factsheet_year = %s"
            params.append(year)
        if month:
            query += " AND factsheet_month = %s"
            params.append(month)
            
        query += " ORDER BY factsheet_year DESC, factsheet_month DESC"
        
        cursor.execute(query, tuple(params))
        cols = [desc[0] for desc in cursor.description]
        results = [dict(zip(cols, row)) for row in cursor.fetchall()]
        
        # Convert dates to strings for JSON
        for r in results:
            if r['factsheet_date']:
                r['factsheet_date'] = r['factsheet_date'].isoformat()
            if r['downloaded_at']:
                r['downloaded_at'] = r['downloaded_at'].isoformat()
                
        return results

def run_monthly_factsheet_downloader(database_name: str = "Investments"):
    """Downloads factsheets for all active investments. Called monthly."""
    logger.info("Starting monthly factsheet downloader batch...")
    
    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute("""
            SELECT id, investment_name, institution_name 
            FROM investments 
            WHERE investment_status = 'Active'
        """)
        investments = cursor.fetchall()
        
    success_count = 0
    for inv_id, name, inst in investments:
        res = download_factsheet(inv_id, name, inst, database_name)
        if res["success"]:
            success_count += 1
            
    logger.info(f"Finished factsheet downloads. Downloaded {success_count} / {len(investments)}.")
    return {"total": len(investments), "success": success_count}
