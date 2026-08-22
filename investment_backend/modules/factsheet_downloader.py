"""
factsheet_downloader.py
========================
Downloads MDD/factsheet PDFs for investments from asset manager websites.

Strategy chain (tried in order until one succeeds):
  1. Direct URL patterns (verified, per-manager)
  2. Fund-page scraping: visit the manager's actual fund page and find PDF links
  3. DuckDuckGo HTML search restricted to the manager's own domain
  4. Generic domain guess + common path patterns
  5. Broad web search fallback (no site: restriction)
  6. Playwright for JS-heavy pages (slowest, last resort)

All PDFs are validated (must start with %PDF and be >5 KB).
Successful URL patterns are cached in the DB for future runs.
"""
import os
import re
import time
import urllib.parse
import requests
import logging
from datetime import date, datetime
from typing import Optional, List, Tuple

logger = logging.getLogger("factsheet_downloader")

FACTSHEETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "factsheets"
)

# ---------------------------------------------------------------------------
# Known SA / global asset manager configurations
# domain:   used for DuckDuckGo site: search restriction
# fund_page_template: URL template for the fund's own product page
#           supports: {slug}, {ticker}
# direct_patterns: verified direct-download URL patterns (tried first, fastest)
# ---------------------------------------------------------------------------
MANAGER_CONFIGS = {
    "allan gray": {
        "domain": "allangray.co.za",
        "fund_page_template": "https://www.allangray.co.za/funds/{slug}/",
        "alt_fund_pages": [
            "https://www.allangray.co.za/individual/investing/prices-and-factsheets/",
            "https://www.allangray.co.za/funds/",
        ],
        "direct_patterns": [
            "https://www.allangray.co.za/globalassets/documents/fund-documents/{ticker}-mdd.pdf",
            "https://www.allangray.co.za/globalassets/documents/fund-documents/{slug}-mdd.pdf",
            "https://www.allangray.co.za/globalassets/documents/fund-documents/{ticker}-fact-sheet.pdf",
            "https://www.allangray.co.za/globalassets/documents/fund-documents/{slug}-fact-sheet.pdf",
        ],
    },
    "coronation": {
        "domain": "coronation.com",
        "fund_page_template": "https://www.coronation.com/en-za/personal/funds/{slug}/",
        "alt_fund_pages": [
            "https://www.coronation.com/en-za/personal/funds/",
        ],
        "direct_patterns": [
            "https://cdn.coronation.com/assets/documents/{ticker}-mdd.pdf",
            "https://cdn.coronation.com/assets/documents/{slug}-mdd.pdf",
            "https://www.coronation.com/assets/documents/{slug}-mdd.pdf",
        ],
    },
    "satrix": {
        "domain": "satrix.co.za",
        "fund_page_template": "https://satrix.co.za/products/product-details?id={slug}",
        "alt_fund_pages": [
            "https://satrix.co.za/api/products/search/filter",
            "https://satrix.co.za/products",
        ],
        "direct_patterns": [
            "https://satrix.co.za/fund/mdd/{ticker}",
            "https://satrix.co.za/fund/mdd/{slug}",
            "https://satrix.co.za/assets/Uploads/Documents/Factsheets/{ticker}-MDD.pdf",
            "https://satrix.co.za/assets/Uploads/Documents/Factsheets/satrix-{slug}-mdd.pdf",
            "https://www.satrix.co.za/assets/media/documents/satrix-{ticker}-mdd.pdf",
            "https://www.satrix.co.za/assets/media/documents/satrix-{slug}-mdd.pdf",
        ],
    },
    "sygnia": {
        "domain": "sygnia.co.za",
        "fund_page_template": "https://www.sygnia.co.za/funds/{slug}/",
        "alt_fund_pages": [
            "https://www.sygnia.co.za/fund-centre/",
            "https://www.sygnia.co.za/etfs/",
        ],
        "direct_patterns": [
            "https://www.sygnia.co.za/assets/documents/{slug}-mdd.pdf",
            "https://www.sygnia.co.za/assets/documents/{ticker}-mdd.pdf",
            "https://www.sygnia.co.za/fund-fact-sheets/",
        ],
    },
    "ninety one": {
        "domain": "ninetyone.com",
        "fund_page_template": "https://za.ninetyone.com/south-africa/our-capabilities/funds/{slug}",
        "alt_fund_pages": [
            "https://za.ninetyone.com/south-africa/our-capabilities/funds/",
        ],
        "direct_patterns": [
            "https://ninetyone.com/-/media/documents/factsheets/{slug}-mdd-en-za.pdf",
            "https://ninetyone.com/-/media/documents/factsheets/{ticker}-mdd-en-za.pdf",
            "https://za.ninetyone.com/-/media/documents/factsheets/{slug}-mdd.pdf",
        ],
    },
    "psg": {
        "domain": "psg.co.za",
        "fund_page_template": "https://www.psg.co.za/wealth-management/psg-funds/{slug}/",
        "alt_fund_pages": [
            "https://www.psg.co.za/wealth-management/psg-funds/",
        ],
        "direct_patterns": [
            "https://www.psg.co.za/globalassets/documents/{slug}-mdd.pdf",
            "https://www.psgam.co.za/globalassets/documents/{slug}-mdd.pdf",
        ],
    },
    "old mutual": {
        "domain": "oldmutual.co.za",
        "fund_page_template": "https://www.oldmutual.co.za/investments/funds/{slug}/",
        "alt_fund_pages": [
            "https://www.oldmutual.co.za/investments/funds/",
        ],
        "direct_patterns": [
            "https://www.oldmutual.co.za/globalassets/documents/fund-documents/{slug}-mdd.pdf",
        ],
    },
    "sanlam": {
        "domain": "sanlam.co.za",
        "fund_page_template": "https://www.sanlam.co.za/investments/unit-trusts/{slug}/",
        "alt_fund_pages": [],
        "direct_patterns": [
            "https://www.sanlam.co.za/documents/fund-factsheets/{slug}-mdd.pdf",
        ],
    },
    "foord": {
        "domain": "foord.co.za",
        "fund_page_template": "https://www.foord.co.za/funds/{slug}/",
        "alt_fund_pages": [
            "https://www.foord.co.za/funds/",
        ],
        "direct_patterns": [
            "https://www.foord.co.za/assets/documents/{slug}-mdd.pdf",
            "https://www.foord.co.za/assets/documents/{ticker}-mdd.pdf",
        ],
    },
    "absa": {
        "domain": "absainvestments.co.za",
        "fund_page_template": "https://www.absainvestments.co.za/funds/{slug}/",
        "alt_fund_pages": [],
        "direct_patterns": [
            "https://www.absainvestments.co.za/globalassets/documents/{slug}-mdd.pdf",
        ],
    },
    "investec": {
        "domain": "investec.com",
        "fund_page_template": "https://www.investec.com/en_za/banking/our-products/asset-management/{slug}.html",
        "alt_fund_pages": [],
        "direct_patterns": [],
    },
    "momentum": {
        "domain": "momentum.co.za",
        "fund_page_template": "https://www.momentum.co.za/investments/unit-trusts/{slug}/",
        "alt_fund_pages": [],
        "direct_patterns": [
            "https://www.momentum.co.za/documents/fund-factsheets/{slug}-mdd.pdf",
        ],
    },
    "blackrock": {
        "domain": "blackrock.com",
        "fund_page_template": "https://www.blackrock.com/za/individual/products/{ticker}/",
        "alt_fund_pages": [],
        "direct_patterns": [
            "https://www.blackrock.com/za/literature/fact-sheet/{ticker}-fund-fact-sheet-za.pdf",
            "https://www.blackrock.com/us/individual/literature/fact-sheet/{ticker}-fund-fact-sheet-va.pdf",
        ],
    },
    "ishares": {
        "domain": "blackrock.com",
        "fund_page_template": "https://www.ishares.com/us/products/{ticker}/",
        "alt_fund_pages": [],
        "direct_patterns": [
            "https://www.blackrock.com/us/individual/literature/fact-sheet/{ticker}-fund-fact-sheet-va.pdf",
        ],
    },
    "vanguard": {
        "domain": "vanguard.co.za",
        "fund_page_template": "https://www.vanguard.co.za/professional/products/etf/{ticker}/",
        "alt_fund_pages": [],
        "direct_patterns": [
            "https://advisors.vanguard.com/pub/Pdf/factsheet/{ticker}.pdf",
            "https://www.vanguard.co.uk/professional/api/funddetail/factsheet/{ticker}",
        ],
    },
    "fidelity": {
        "domain": "fidelity.co.za",
        "fund_page_template": "https://www.fidelity.co.za/funds/{slug}/",
        "alt_fund_pages": [],
        "direct_patterns": [],
    },
    "alexander forbes": {
        "domain": "alexanderforbes.co.za",
        "fund_page_template": "https://www.alexanderforbes.co.za/products/{slug}/",
        "alt_fund_pages": [],
        "direct_patterns": [],
    },
    "10x": {
        "domain": "10x.co.za",
        "fund_page_template": "https://www.10x.co.za/funds/{slug}/",
        "alt_fund_pages": ["https://www.10x.co.za/funds/"],
        "direct_patterns": [
            "https://www.10x.co.za/assets/documents/{slug}-mdd.pdf",
        ],
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower()
    for char in [" ", "/", "\\", "_", ",", ".", "&", "(", ")", "!", "?",
                  "'", '"', "+", "%", "#", "@", "*", "$", ":", ";", "="]:
        text = text.replace(char, "-")
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-")


def _make_browser_headers() -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-ZA,en;q=0.9",
    }


def _is_valid_pdf(content: bytes) -> bool:
    """Check if bytes look like a real PDF (must start with %PDF and be > 5 KB)."""
    return len(content) > 5_000 and content[:4] == b"%PDF"


def _try_url(url: str, timeout: int = 20) -> Optional[bytes]:
    """
    Download a URL and return content if it is a valid PDF, else None.
    """
    headers = _make_browser_headers()
    try:
        r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if r.status_code == 200 and _is_valid_pdf(r.content):
            return r.content
    except requests.exceptions.SSLError:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, verify=False)
            if r.status_code == 200 and _is_valid_pdf(r.content):
                return r.content
        except Exception:
            pass
    except requests.RequestException as e:
        logger.debug(f"_try_url request error for {url}: {e}")
    return None


def get_factsheet_path(investment_id: int, year: int, month: int,
                       factsheet_type: str = "MDD") -> str:
    """Get absolute file path to store factsheet PDF."""
    dir_path = os.path.join(FACTSHEETS_DIR, str(investment_id))
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, f"{year}_{month:02d}_{factsheet_type}.pdf")


# ---------------------------------------------------------------------------
# HTML scraping helpers
# ---------------------------------------------------------------------------

def _get_page_html(url: str, timeout: int = 20) -> Optional[str]:
    """Fetch a web page's HTML, returning None on failure."""
    try:
        r = requests.get(url, headers=_make_browser_headers(), timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        logger.debug(f"_get_page_html failed for {url}: {e}")
    return None


def _extract_pdf_links(html: str, base_url: str,
                        keywords: List[str] = None) -> List[str]:
    """
    Extract all PDF links from HTML.  If `keywords` is provided, prefer links
    containing those keywords; also include all other PDF links as fallback.
    Returns a deduplicated, ordered list: keyword-matched first, then others.
    """
    keywords = keywords or ["mdd", "minimum-disclosure", "minimum_disclosure",
                             "fact-sheet", "factsheet", "fund-fact"]
    parsed_base = urllib.parse.urlparse(base_url)
    base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

    # Find all href and src attributes that contain .pdf
    raw_hrefs = re.findall(
        r'(?:href|src)=["\']([^"\']*\.pdf[^"\']*)["\']',
        html, re.IGNORECASE
    )
    # Also catch JavaScript-embedded URLs like window.open("...pdf")
    raw_hrefs += re.findall(r'["\'](https?://[^"\']+\.pdf[^"\']*)["\']', html, re.IGNORECASE)

    def make_absolute(href: str) -> str:
        if href.startswith("http"):
            return href
        if href.startswith("//"):
            return parsed_base.scheme + ":" + href
        if href.startswith("/"):
            return base_origin + href
        return base_origin + "/" + href

    seen = set()
    keyword_matches = []
    other_pdfs = []

    for raw in raw_hrefs:
        raw = raw.strip()
        abs_url = make_absolute(raw)
        if abs_url in seen:
            continue
        seen.add(abs_url)
        lower = abs_url.lower()
        if any(kw in lower for kw in keywords):
            keyword_matches.append(abs_url)
        else:
            other_pdfs.append(abs_url)

    return keyword_matches + other_pdfs


def _scrape_page_for_mdd(page_url: str,
                          keywords: List[str] = None) -> Optional[str]:
    """
    Visit a page and find the first PDF link that looks like an MDD/factsheet.
    Returns the absolute URL of the PDF (not the content).
    """
    html = _get_page_html(page_url)
    if not html:
        return None
    links = _extract_pdf_links(html, page_url, keywords)
    if links:
        return links[0]
    return None


# ---------------------------------------------------------------------------
# DuckDuckGo HTML search (no API key needed)
# ---------------------------------------------------------------------------

def _duckduckgo_search(query: str, max_results: int = 10) -> List[str]:
    """
    Search DuckDuckGo via their HTML endpoint and extract result URLs.
    Returns a list of result URLs.
    """
    try:
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        headers = {
            **_make_browser_headers(),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        r = requests.post(url, data=params, headers=headers, timeout=20)
        if r.status_code != 200:
            return []
        html = r.text
        # DuckDuckGo HTML results contain result URLs in uddg= query params
        # or directly in href attributes of result links
        urls = []

        # Pattern 1: uddg= encoded URLs (DDG redirect links)
        for match in re.finditer(r'href="//duckduckgo\.com/l/\?[^"]*uddg=([^"&]+)', html):
            try:
                decoded = urllib.parse.unquote(match.group(1))
                if decoded.startswith("http"):
                    urls.append(decoded)
            except Exception:
                pass

        # Pattern 2: direct result hrefs
        for match in re.finditer(r'class="result__url"[^>]*>([^<]+)<', html):
            href = match.group(1).strip()
            if href and not href.startswith("http"):
                href = "https://" + href
            if href.startswith("http"):
                urls.append(href)

        # Pattern 3: result__a links
        for match in re.finditer(r'class="result__a"[^>]*href="([^"]+)"', html):
            href = match.group(1)
            if href.startswith("http"):
                urls.append(href)

        return list(dict.fromkeys(urls))[:max_results]  # dedup, preserve order
    except Exception as e:
        logger.debug(f"DuckDuckGo search failed: {e}")
    return []


def _search_for_mdd_url(institution_name: str, investment_name: str,
                          ticker: str, manager_domain: str = None) -> Optional[str]:
    """
    Use DuckDuckGo to find the MDD PDF URL.

    Strategy:
    1. Search with site: restriction to manager's own domain (gets latest from source)
    2. If no PDF found, broaden to remove site: restriction
    """
    kw_suffix = "MDD filetype:pdf"

    queries = []
    if manager_domain:
        # Prefer results from the manager's own website (most current)
        queries.append(f'"{investment_name}" {kw_suffix} site:{manager_domain}')
        queries.append(f'"{institution_name}" "{investment_name}" MDD site:{manager_domain}')
        queries.append(f'{ticker} MDD factsheet site:{manager_domain}')
    # Broader fallback queries
    queries.append(f'"{institution_name}" "{investment_name}" MDD filetype:pdf')
    queries.append(f'{institution_name} {investment_name} "minimum disclosure document" filetype:pdf')
    queries.append(f'{ticker} MDD factsheet "minimum disclosure" filetype:pdf')

    for query in queries:
        logger.info(f"DuckDuckGo search: {query}")
        results = _duckduckgo_search(query)
        for url in results:
            lower = url.lower()
            if lower.endswith(".pdf") or "mdd" in lower or "factsheet" in lower or "minimum-disclosure" in lower:
                # If manager_domain is provided, ensure domain matches or fund slug is present in URL
                slug_clean = _slugify(investment_name).replace("-", "")
                inst_clean = _slugify(institution_name).replace("-", "")
                url_clean = lower.replace("-", "").replace("_", "")
                
                # Check for relevancy to avoid downloading wrong fund's PDF
                if manager_domain and manager_domain.lower().lstrip("www.") not in lower:
                    if inst_clean not in url_clean and slug_clean[:6] not in url_clean:
                        logger.warning(f"Skipping PDF URL {url} — domain/slug mismatch for {investment_name}")
                        continue

                # Verify the URL actually returns a valid PDF
                content = _try_url(url)
                if content:
                    logger.info(f"DuckDuckGo found valid PDF: {url}")
                    return url
        time.sleep(1)  # Rate limiting

    return None


# ---------------------------------------------------------------------------
# Per-manager page scrapers (visit fund product page, find PDF)
# ---------------------------------------------------------------------------

def _find_manager_config(inst_lower: str) -> Optional[dict]:
    """Find matching manager config by substring match, longest match first."""
    # Sort by key length descending to prefer more specific matches
    for key in sorted(MANAGER_CONFIGS.keys(), key=len, reverse=True):
        if key in inst_lower:
            return MANAGER_CONFIGS[key]
    return None


def _try_direct_patterns(config: dict, slug: str, ticker: str) -> Optional[Tuple[str, bytes]]:
    """Try all direct URL patterns from the manager config."""
    for pattern in config.get("direct_patterns", []):
        url = pattern.format(slug=slug, ticker=ticker, fund_slug=slug)
        logger.debug(f"Trying direct pattern: {url}")
        content = _try_url(url)
        if content:
            logger.info(f"Direct pattern succeeded: {url}")
            return url, content
    return None


def _try_fund_page_scrape(config: dict, slug: str, ticker: str,
                           investment_name: str) -> Optional[Tuple[str, bytes]]:
    """Scrape the manager's fund page to find and download the MDD PDF."""
    keywords = ["mdd", "minimum-disclosure", "minimum_disclosure",
                "fact-sheet", "factsheet", "fund-fact"]

    pages_to_try = []

    # Primary fund page (with slug or ticker substitution)
    template = config.get("fund_page_template", "")
    if template:
        pages_to_try.append(template.format(slug=slug, ticker=ticker))
        # Try ticker as slug too
        if ticker != slug:
            pages_to_try.append(template.format(slug=ticker, ticker=slug))

    # Alt pages (usually listing pages)
    pages_to_try.extend(config.get("alt_fund_pages", []))

    for page_url in pages_to_try:
        logger.info(f"Scraping fund page: {page_url}")
        html = _get_page_html(page_url)
        if not html:
            continue

        pdf_links = _extract_pdf_links(html, page_url, keywords)

        # Score each link: prefer links that mention the fund name or ticker
        name_words = [w.lower() for w in investment_name.split() if len(w) > 2]
        scored = []
        for link in pdf_links:
            lower = link.lower()
            score = 0
            if any(kw in lower for kw in ["mdd", "minimum-disclosure"]):
                score += 10
            if ticker.lower() in lower:
                score += 5
            if any(w in lower for w in name_words):
                score += 3
            if any(kw in lower for kw in ["factsheet", "fact-sheet"]):
                score += 2
            scored.append((score, link))

        # Try from highest score down
        for _, link in sorted(scored, reverse=True):
            content = _try_url(link)
            if content:
                logger.info(f"Fund page scrape found PDF: {link}")
                return link, content

    return None


def _try_playwright_scrape(page_url: str, keywords: List[str] = None) -> Optional[str]:
    """Last-resort: use Playwright for JS-rendered pages."""
    keywords = keywords or ["mdd", "factsheet", "fact sheet", "fund fact", "minimum disclosure"]
    try:
        from .playwright_helper import chromium_path
        chromium = chromium_path()
        if chromium is None:
            return None
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=chromium)
            context = browser.new_context(user_agent=_make_browser_headers()["User-Agent"])
            page = context.new_page()
            try:
                page.goto(page_url, timeout=30_000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                links = page.evaluate(
                    "() => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)"
                )
                for href in links:
                    hl = href.lower()
                    if href.endswith(".pdf") or any(kw in hl for kw in keywords):
                        if href.endswith(".pdf"):
                            return href
                for href in links:
                    if href.lower().endswith(".pdf"):
                        return href
            except Exception as e:
                logger.warning(f"Playwright scrape of {page_url} failed: {e}")
            finally:
                browser.close()
    except Exception as e:
        logger.debug(f"Playwright not available: {e}")
    return None


# ---------------------------------------------------------------------------
# Generic domain guess (for unknown managers)
# ---------------------------------------------------------------------------

def _guess_manager_domain(inst_lower: str) -> List[str]:
    """
    Guess the asset manager's website domain from their name.
    Returns a list of domain candidates (without scheme).
    """
    # Strip common suffixes
    stop_words = {
        "fund", "funds", "asset", "investment", "investments", "management",
        "manager", "managers", "wealth", "south", "africa", "financial",
        "services", "limited", "pty", "trust", "collective", "schemes",
        "unit", "trusts", "global", "international", "sa", "the", "and"
    }
    words = [
        w for w in inst_lower.replace("-", " ").split()
        if len(w) > 2 and w not in stop_words
    ]
    if not words:
        return []

    brand = words[0]
    domains = []
    # South African and global TLDs
    for tld in [".co.za", ".com", ".co.uk"]:
        domains.append(f"www.{brand}{tld}")
        domains.append(f"{brand}{tld}")
    return domains


def _try_generic_domain(inst_lower: str, slug: str, ticker: str) -> Optional[Tuple[str, bytes]]:
    """Guess the manager's domain and try common MDD path patterns."""
    domains = _guess_manager_domain(inst_lower)
    if not domains:
        return None

    doc_path_patterns = [
        "/globalassets/documents/fund-documents/{s}-mdd.pdf",
        "/globalassets/documents/fund-documents/{t}-mdd.pdf",
        "/assets/documents/{s}-mdd.pdf",
        "/assets/documents/{t}-mdd.pdf",
        "/documents/factsheets/{t}-mdd.pdf",
        "/documents/{t}-mdd.pdf",
        "/factsheets/{t}-mdd.pdf",
        "/media/documents/{s}-mdd.pdf",
        "/downloads/{s}-mdd.pdf",
    ]

    for domain in domains:
        for pattern in doc_path_patterns:
            url = f"https://{domain}" + pattern.format(s=slug, t=ticker)
            content = _try_url(url)
            if content:
                logger.info(f"Generic domain pattern worked: {url}")
                return url, content

    return None


# ---------------------------------------------------------------------------
# Main download orchestrator
# ---------------------------------------------------------------------------

def download_factsheet(
    investment_id: int,
    investment_name: str,
    institution_name: str,
    database_name: str,
    factsheet_type: str = "MDD",
    investment_ticker: str = None,
) -> dict:
    """
    Download the latest factsheet/MDD for an investment.

    Returns: dict with keys: success, file_path, url, error, strategy_used
    """
    from .database import get_db_connection
    today = date.today()
    year = today.year
    month = today.month

    # ── Already downloaded this month? ──────────────────────────────────────
    try:
        with get_db_connection(database_name) as (conn, cursor):
            cursor.execute("""
                SELECT id FROM factsheets
                WHERE investment_id = %s
                  AND factsheet_year = %s
                  AND factsheet_month = %s
                  AND factsheet_type = %s
            """, (investment_id, year, month, factsheet_type))
            if cursor.fetchone():
                fp = get_factsheet_path(investment_id, year, month, factsheet_type)
                if os.path.exists(fp):
                    return {
                        "success": True, "file_path": fp, "url": None,
                        "error": "Already downloaded this month",
                        "strategy_used": "cached",
                    }
    except Exception:
        pass

    # ── Fetch ticker from DB if not provided ─────────────────────────────────
    if not investment_ticker:
        try:
            with get_db_connection(database_name) as (conn, cursor):
                cursor.execute(
                    "SELECT investment_ticker FROM investments WHERE id = %s",
                    (investment_id,)
                )
                row = cursor.fetchone()
                if row and row[0]:
                    investment_ticker = row[0]
        except Exception:
            pass

    # ── Check DB for a previously cached working URL ─────────────────────────
    try:
        with get_db_connection(database_name) as (conn, cursor):
            cursor.execute("""
                SELECT url_pattern FROM asset_manager_url_patterns
                WHERE manager_name_normalized = %s
                  AND factsheet_type = %s
                ORDER BY pattern_priority ASC
                LIMIT 5
            """, (institution_name.lower().strip(), factsheet_type))
            cached_patterns = [r[0] for r in cursor.fetchall()]
    except Exception:
        cached_patterns = []

    slug = _slugify(investment_name)
    ticker = (investment_ticker or slug).lower()
    inst_lower = institution_name.lower().strip()

    source_url: Optional[str] = None
    content: Optional[bytes] = None
    strategy_used: Optional[str] = None

    # ── Strategy 0: Cached DB URL patterns ───────────────────────────────────
    for cached_url in cached_patterns:
        url = cached_url.format(slug=slug, ticker=ticker, fund_slug=slug)
        c = _try_url(url)
        if c:
            source_url, content, strategy_used = url, c, "cached-db-pattern"
            break

    # ── Strategy 1: Direct verified URL patterns (per-manager) ───────────────
    if not source_url:
        config = _find_manager_config(inst_lower)
        if config:
            logger.info(f"Strategy 1: direct patterns for '{inst_lower}'")
            result = _try_direct_patterns(config, slug, ticker)
            if result:
                source_url, content = result
                strategy_used = "direct-pattern"

    # ── Strategy 2: Fund page scraping ───────────────────────────────────────
    if not source_url:
        config = _find_manager_config(inst_lower)
        if config:
            logger.info(f"Strategy 2: fund page scraping for '{inst_lower}'")
            result = _try_fund_page_scrape(config, slug, ticker, investment_name)
            if result:
                source_url, content = result
                strategy_used = "fund-page-scrape"

    # ── Strategy 3: DuckDuckGo search (site: restricted to manager domain) ───
    if not source_url:
        config = _find_manager_config(inst_lower)
        manager_domain = config["domain"] if config else None

        # Also try guessed domain
        if not manager_domain:
            guessed = _guess_manager_domain(inst_lower)
            manager_domain = guessed[0].lstrip("www.") if guessed else None

        logger.info(f"Strategy 3: DuckDuckGo search (domain={manager_domain})")
        url = _search_for_mdd_url(institution_name, investment_name, ticker, manager_domain)
        if url:
            c = _try_url(url)
            if c:
                source_url, content, strategy_used = url, c, "duckduckgo-search"

    # ── Strategy 4: Generic domain + common paths ────────────────────────────
    if not source_url:
        logger.info("Strategy 4: generic domain guess")
        result = _try_generic_domain(inst_lower, slug, ticker)
        if result:
            source_url, content = result
            strategy_used = "generic-domain"

    # ── Strategy 5: Playwright scraping ─────────────────────────────────────
    if not source_url:
        config = _find_manager_config(inst_lower)
        if config:
            template = config.get("fund_page_template", "")
            if template:
                fund_page = template.format(slug=slug, ticker=ticker)
                logger.info(f"Strategy 5: Playwright for {fund_page}")
                pdf_url = _try_playwright_scrape(fund_page)
                if pdf_url:
                    c = _try_url(pdf_url)
                    if c:
                        source_url, content, strategy_used = pdf_url, c, "playwright"

    # ── Strategy 6: Broad web search (no site: restriction) ─────────────────
    if not source_url:
        logger.info("Strategy 6: broad DuckDuckGo search")
        url = _search_for_mdd_url(institution_name, investment_name, ticker, None)
        if url:
            c = _try_url(url)
            if c:
                source_url, content, strategy_used = url, c, "broad-web-search"

    # ── All strategies exhausted ─────────────────────────────────────────────
    if not source_url or not content:
        logger.warning(
            f"All strategies exhausted for {investment_name} ({institution_name})"
        )
        return {
            "success": False,
            "file_path": None,
            "url": None,
            "error": (
                f"Could not find a valid MDD/factsheet PDF for '{investment_name}' "
                f"from '{institution_name}'. Tried: direct URL patterns, fund page "
                f"scraping, DuckDuckGo search (site:{_guess_manager_domain(inst_lower)[0] if _guess_manager_domain(inst_lower) else 'unknown'}), "
                f"generic domain guessing, and broad web search."
            ),
            "strategy_used": None,
        }

    logger.info(
        f"Found {factsheet_type} for {investment_name} via '{strategy_used}': {source_url}"
    )

    # ── Save PDF to disk ─────────────────────────────────────────────────────
    file_path = get_factsheet_path(investment_id, year, month, factsheet_type)
    try:
        with open(file_path, "wb") as f:
            f.write(content)
        file_name = os.path.basename(file_path)
        file_size = len(content)

        # Persist factsheet metadata to DB
        try:
            with get_db_connection(database_name) as (conn, cursor):
                cursor.execute("""
                    INSERT INTO factsheets (
                        investment_id, factsheet_date, factsheet_type,
                        factsheet_year, factsheet_month,
                        source_url, file_path, file_name,
                        file_size_bytes, downloaded_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT ON CONSTRAINT
                        factsheets_investment_id_factsheet_year_factsheet_month_fac_key
                    DO UPDATE SET
                        source_url = EXCLUDED.source_url,
                        file_size_bytes = EXCLUDED.file_size_bytes,
                        downloaded_at = EXCLUDED.downloaded_at
                """, (
                    investment_id, today, factsheet_type, year, month,
                    source_url, file_path, file_name, file_size, datetime.now()
                ))
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to save factsheet metadata to DB: {e}")

        # Cache the working URL pattern for future use
        try:
            with get_db_connection(database_name) as (conn, cursor):
                manager_norm = inst_lower
                cursor.execute("""
                    INSERT INTO asset_manager_url_patterns
                        (manager_name, manager_name_normalized, factsheet_type,
                         url_pattern, pattern_priority)
                    VALUES (%s, %s, %s, %s, 1)
                    ON CONFLICT DO NOTHING
                """, (institution_name, manager_norm, factsheet_type, source_url))
                conn.commit()
        except Exception:
            pass

        return {
            "success": True,
            "file_path": file_path,
            "url": source_url,
            "error": None,
            "strategy_used": strategy_used,
        }
    except Exception as e:
        logger.error(f"Failed to save factsheet: {e}")
        return {
            "success": False, "file_path": None, "url": source_url,
            "error": str(e), "strategy_used": strategy_used,
        }


# ---------------------------------------------------------------------------
# Batch helpers
# ---------------------------------------------------------------------------

def get_factsheets_for_investment(
    investment_id: int,
    database_name: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> list:
    """Get metadata for all factsheets belonging to an investment."""
    from .database import get_db_connection
    with get_db_connection(database_name) as (conn, cursor):
        query = (
            "SELECT id, factsheet_date, factsheet_type, factsheet_year, "
            "factsheet_month, file_name, file_size_bytes, downloaded_at "
            "FROM factsheets WHERE investment_id = %s"
        )
        params: list = [investment_id]
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
        for r in results:
            if r.get("factsheet_date"):
                r["factsheet_date"] = r["factsheet_date"].isoformat()
            if r.get("downloaded_at"):
                r["downloaded_at"] = r["downloaded_at"].isoformat()
        return results


def run_monthly_factsheet_downloader(database_name: str = "Investments"):
    """Downloads factsheets for all active investments. Called monthly."""
    logger.info("Starting monthly factsheet downloader batch...")
    from .database import get_db_connection
    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute("""
            SELECT id, investment_name, institution_name, investment_ticker
            FROM investments
            WHERE investment_status = 'Active'
        """)
        investments = cursor.fetchall()

    success_count = 0
    for inv_id, name, inst, ticker in investments:
        try:
            res = download_factsheet(inv_id, name, inst, database_name, investment_ticker=ticker)
            if res["success"]:
                success_count += 1
        except Exception as e:
            logger.error(f"Error downloading factsheet for {name}: {e}")

    logger.info(
        f"Finished factsheet downloads: {success_count}/{len(investments)} succeeded."
    )
    return {"total": len(investments), "success": success_count}


# ---------------------------------------------------------------------------
# URL preview (find URL without downloading)
# ---------------------------------------------------------------------------

def preview_factsheet_url(
    investment_name: str,
    institution_name: str,
    investment_ticker: str = None,
    database_name: str = None,
) -> dict:
    """
    Find the most likely MDD URL without downloading/saving.
    Useful for letting the user confirm the URL before a full download.
    """
    slug = _slugify(investment_name)
    ticker = (investment_ticker or slug).lower()
    inst_lower = institution_name.lower().strip()

    config = _find_manager_config(inst_lower)

    # Try direct patterns first (fast)
    if config:
        for pattern in config.get("direct_patterns", []):
            url = pattern.format(slug=slug, ticker=ticker, fund_slug=slug)
            c = _try_url(url)
            if c:
                return {"found": True, "url": url, "method": "direct-pattern"}

    # Try fund page scrape
    if config:
        template = config.get("fund_page_template", "")
        if template:
            pdf_url = _scrape_page_for_mdd(
                template.format(slug=slug, ticker=ticker)
            )
            if pdf_url:
                return {"found": True, "url": pdf_url, "method": "fund-page-scrape"}

    # DuckDuckGo search
    manager_domain = config["domain"] if config else None
    if not manager_domain:
        guessed = _guess_manager_domain(inst_lower)
        manager_domain = guessed[0].lstrip("www.") if guessed else None

    url = _search_for_mdd_url(institution_name, investment_name, ticker, manager_domain)
    if url:
        return {"found": True, "url": url, "method": "web-search"}

    return {
        "found": False,
        "url": None,
        "method": None,
        "message": f"Could not locate MDD URL for '{investment_name}' from '{institution_name}'",
    }


def download_factsheet_from_url(
    investment_id: int,
    custom_url: str,
    database_name: str = "Investments",
    year: Optional[int] = None,
    month: Optional[int] = None,
    factsheet_type: str = "MDD",
) -> dict:
    """
    Download a factsheet PDF directly from a specified URL and save to DB.
    Allows users to fetch past/historical MDDs or specify exact direct links.
    """
    from .database import get_db_connection
    today = date.today()
    target_year = year or today.year
    target_month = month or today.month

    content = _try_url(custom_url)
    if not content:
        return {
            "success": False,
            "file_path": None,
            "url": custom_url,
            "error": "Failed to download a valid PDF from the specified URL.",
            "strategy_used": "custom-url",
        }

    file_path = get_factsheet_path(investment_id, target_year, target_month, factsheet_type)
    try:
        with open(file_path, "wb") as f:
            f.write(content)
        file_name = os.path.basename(file_path)
        file_size = len(content)

        with get_db_connection(database_name) as (conn, cursor):
            cursor.execute("""
                INSERT INTO factsheets (
                    investment_id, factsheet_date, factsheet_type,
                    factsheet_year, factsheet_month,
                    source_url, file_path, file_name,
                    file_size_bytes, downloaded_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT ON CONSTRAINT
                    factsheets_investment_id_factsheet_year_factsheet_month_fac_key
                DO UPDATE SET
                    source_url = EXCLUDED.source_url,
                    file_size_bytes = EXCLUDED.file_size_bytes,
                    downloaded_at = EXCLUDED.downloaded_at
            """, (
                investment_id, today, factsheet_type, target_year, target_month,
                custom_url, file_path, file_name, file_size, datetime.now()
            ))
            conn.commit()

        return {
            "success": True,
            "file_path": file_path,
            "url": custom_url,
            "error": None,
            "strategy_used": "custom-url",
        }
    except Exception as e:
        return {
            "success": False,
            "file_path": None,
            "url": custom_url,
            "error": str(e),
            "strategy_used": "custom-url",
        }

