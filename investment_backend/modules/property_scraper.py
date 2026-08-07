import re
import json
import logging
from playwright.sync_api import sync_playwright

logger = logging.getLogger("property_scraper")
logging.basicConfig(level=logging.INFO)

def scrape_property_url(url: str, headless: bool = True) -> dict:
    """
    Scrape a property listing page to extract price, address, type, etc.
    Tries parsing Schema.org LD-JSON first, then falls back to DOM selectors and regex.
    """
    logger.info(f"Scraping property listing: {url}")
    result = {
        "property_url": url,
        "property_name": "",
        "property_address": "",
        "property_type": "apartment",  # default fallback
        "purchase_price": 0.0,
        "monthly_rental_income": 0.0,
    }
    
    try:
        from .playwright_helper import chromium_path
        chromium = chromium_path()
        if chromium is None:
            return result
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless, executable_path=chromium)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=10000)
            
            # Extract content
            html = page.content()
            title = page.title()
            result["property_name"] = title.split("|")[0].strip() if title else ""
            
            # 1. Check LD-JSON
            ld_json_scripts = page.query_selector_all("script[type='application/ld+json']")
            for script in ld_json_scripts:
                try:
                    data = json.loads(script.inner_text())
                    # LD-JSON can be a list or single object
                    if isinstance(data, list):
                        items = data
                    elif "@graph" in data:
                        items = data["@graph"]
                    else:
                        items = [data]
                        
                    for item in items:
                        # Look for RealEstateAgent, Product, SingleFamilyResidence, Accommodation
                        if not isinstance(item, dict):
                            continue
                            
                        # Try to find price
                        offers = item.get("offers")
                        if offers:
                            if isinstance(offers, dict):
                                price_val = offers.get("price") or offers.get("priceSpecification", {}).get("price")
                                if price_val:
                                    result["purchase_price"] = float(price_val)
                            elif isinstance(offers, list) and len(offers) > 0:
                                price_val = offers[0].get("price")
                                if price_val:
                                    result["purchase_price"] = float(price_val)
                                    
                        # Try to find address
                        address = item.get("address")
                        if address:
                            if isinstance(address, dict):
                                street = address.get("streetAddress", "")
                                locality = address.get("addressLocality", "")
                                region = address.get("addressRegion", "")
                                result["property_address"] = ", ".join(filter(None, [street, locality, region]))
                            elif isinstance(address, str):
                                result["property_address"] = address
                                
                        # Try name/description
                        if item.get("name") and not result["property_name"]:
                            result["property_name"] = item["name"]
                except Exception as ex:
                    logger.debug(f"Failed parsing ld+json script: {ex}")
                    
            # 2. Fallbacks via regex and selectors
            if result["purchase_price"] == 0.0:
                # Search for R followed by numbers (common in South Africa: e.g. R 2,500,000 or R2 500 000)
                price_matches = re.findall(r'R\s*([0-9\s,\.]+)', html)
                for pm in price_matches:
                    # Clean and parse
                    clean_pm = pm.replace(" ", "").replace(",", "").replace("\xa0", "").strip()
                    # Keep only digits and decimal dot
                    clean_pm = re.sub(r'[^\d\.]', '', clean_pm)
                    if clean_pm:
                        try:
                            val = float(clean_pm)
                            # Reasonable property price range (between R100k and R100M)
                            if 100000 <= val <= 100000000:
                                result["purchase_price"] = val
                                break
                        except ValueError:
                            pass
            
            # Extract Address from heading or common class selectors if LD-JSON failed
            if not result["property_address"]:
                addr_selectors = [".property-address", ".p24_address", "h2", "h1"]
                for sel in addr_selectors:
                    elem = page.query_selector(sel)
                    if elem:
                        txt = elem.inner_text().strip()
                        if txt and len(txt) > 5 and any(c in txt.lower() for c in ["street", "road", "ave", "drive", "way", "park", "estate", "cape", "gauteng", "natal", "johannesburg", "pretoria", "durban", "port"]):
                            result["property_address"] = txt
                            break
                            
            # Deduce Property Type
            text_lower = html.lower()
            if "apartment" in text_lower or "flat" in text_lower or "sectional title" in text_lower:
                result["property_type"] = "apartment"
            elif "house" in text_lower or "residential" in text_lower or "freestanding" in text_lower:
                result["property_type"] = "house"
            elif "commercial" in text_lower or "office" in text_lower:
                result["property_type"] = "commercial"
            else:
                result["property_type"] = "house"
                
            browser.close()
            
    except Exception as e:
        logger.error(f"Scraper encountered error: {e}")
        
    return result
