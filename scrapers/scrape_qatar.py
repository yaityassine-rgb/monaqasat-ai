"""
Scraper for Qatar Government Monaqasat Portal.
Source: https://monaqasat.mof.gov.qa/TendersOnlineServices/AvailableMinistriesTenders/1

Qatar's official government procurement portal. Content is primarily in Arabic.
The site uses a card-based layout within table rows (not traditional <td> cells).

Each card contains:
  - Reference number (e.g., 1221/2026)
  - Title with link to detail page
  - Publish date (تاريخ الطرح)
  - Sector type (نوع القطاع المطلوب)
  - Bond amount in QAR (التأمين المؤقت)
  - Organization (الجهة)
  - Closing date (تاريخ الإغلاق)
  - PDF document link
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger("qatar")

BASE_URL = "https://monaqasat.mof.gov.qa"
LISTING_URL = f"{BASE_URL}/TendersOnlineServices/AvailableMinistriesTenders"
MAX_PAGES = 10

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ar,en;q=0.9",
    "Referer": BASE_URL,
}


def _get(url, **kwargs):
    """HTTP GET with TLS fingerprint impersonation if available."""
    if HAS_CURL_CFFI:
        return curl_requests.get(url, impersonate="chrome131", **kwargs)
    return requests.get(url, **kwargs)


def _parse_card(card, page_url: str) -> dict | None:
    """Parse a single tender card from the Monaqasat portal.

    The portal uses a card layout inside <tr> elements:
      <tr>
        <div class="row custom-cards">
          <div class="col-md-7">  -- ref, title, publish date, bond
          <div class="col-md-3">  -- organization, type
          <div class="col-md-2">  -- closing date, buy link, PDF
    """
    # Reference number (e.g., "1221/2026")
    ref_el = card.select_one(".col-header .card-label")
    ref = ref_el.get_text(strip=True) if ref_el else ""

    # Title and detail link
    title_el = card.select_one(".col-header .card-title a")
    if not title_el:
        return None
    title = title_el.get_text(strip=True)
    if not title or len(title) < 5:
        return None

    # Detail page URL
    href = title_el.get("href", "")
    detail_url = f"{BASE_URL}{href}" if href and not href.startswith("http") else href

    # Extract fields from cards-row elements
    pub_date = ""
    deadline = ""
    bond = 0
    org = ""
    tender_type = ""
    sector_type = ""

    for cards_row in card.select(".cards-row"):
        label_el = cards_row.select_one(".card-label")
        value_el = cards_row.select_one(".card-title")
        if not label_el or not value_el:
            continue

        label = label_el.get_text(strip=True)
        value = value_el.get_text(strip=True)

        if "تاريخ الطرح" in label:  # Publish date
            pub_date = parse_date(value) or ""
        elif "القطاع" in label:  # Sector type
            sector_type = value
        elif "التأمين" in label:  # Bond amount
            amount_str = re.sub(r'[^\d.]', '', value)
            try:
                bond = int(float(amount_str))
            except (ValueError, TypeError):
                pass
        elif "النوع" in label:  # Type
            tender_type = value

    # Organization from second column
    org_cols = card.select(".cards-col")
    if len(org_cols) >= 2:
        org_el = org_cols[1].select_one(".col-header .card-title")
        if org_el:
            org = org_el.get_text(strip=True)

    # Closing date from circle-container
    circle = card.select_one(".circle-container")
    if circle:
        close_labels = circle.select(".card-label span")
        for i, span in enumerate(close_labels):
            if "الإغلاق" in span.get_text():  # تاريخ الإغلاق = Closing date
                # Next span should be the date
                if i + 1 < len(close_labels):
                    deadline = parse_date(close_labels[i + 1].get_text(strip=True)) or ""

    # Source URL: prefer the buy/purchase link, fall back to detail page
    source_url = detail_url or page_url
    buy_link = card.select_one(".circle-container a.btn[href]")
    if buy_link:
        buy_href = buy_link.get("href", "")
        if buy_href:
            source_url = f"{BASE_URL}{buy_href}" if not buy_href.startswith("http") else buy_href

    return {
        "id": generate_id("qatar", ref or title[:80], ""),
        "source": "Qatar Monaqasat",
        "sourceRef": ref,
        "sourceLanguage": "ar",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or "Government of Qatar",
            "ar": org or "حكومة قطر",
            "fr": org or "Gouvernement du Qatar",
        },
        "country": "Qatar",
        "countryCode": "QA",
        "sector": classify_sector(title + " " + sector_type),
        "budget": bond,
        "currency": "QAR",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": "open",
        "description": {"en": title, "ar": title, "fr": title},
        "requirements": [],
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def _scrape_page(soup, page_url: str, seen: set) -> list[dict]:
    """Parse all tender cards from a page's BeautifulSoup."""
    tenders = []
    rows = soup.select("table tbody tr")

    for row in rows:
        tender = _parse_card(row, page_url)
        if not tender:
            continue
        key = tender["sourceRef"] or tender["title"]["ar"][:60]
        if key in seen:
            continue
        seen.add(key)
        tenders.append(tender)

    return tenders


def scrape() -> list[dict]:
    """Scrape Qatar Monaqasat portal for procurement notices."""
    tenders: list[dict] = []
    seen: set[str] = set()

    for page in range(1, MAX_PAGES + 1):
        url = f"{LISTING_URL}/{page}"
        try:
            resp = _get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.warning(f"Qatar page {page}: HTTP {resp.status_code}")
                break

            soup = BeautifulSoup(resp.text, "lxml")
            page_tenders = _scrape_page(soup, url, seen)

            logger.info(f"Qatar page {page}: {len(page_tenders)} tenders (total: {len(tenders) + len(page_tenders)})")

            if not page_tenders:
                break

            tenders.extend(page_tenders)
            time.sleep(2)

        except Exception as e:
            err_str = str(e).lower()
            if "ssl" in err_str or "eof" in err_str:
                logger.warning(f"Qatar page {page}: SSL error — {e}")
            elif "timeout" in err_str or "timed out" in err_str:
                logger.warning(f"Qatar page {page}: request timed out — {e}")
            elif "connection" in err_str:
                logger.warning(f"Qatar page {page}: connection error — {e}")
            else:
                logger.error(f"Qatar page {page}: {e}")
            break

    # If HTTP scraping found nothing, try Playwright as fallback
    if not tenders and HAS_PLAYWRIGHT:
        logger.info("Qatar: HTTP scraping found nothing, trying Playwright...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                pw_page = browser.new_page()
                pw_page.set_extra_http_headers({"Accept-Language": "ar,en;q=0.9"})

                for page_num in range(1, 6):
                    url = f"{LISTING_URL}/{page_num}"
                    logger.info(f"Qatar Playwright: loading page {page_num}")
                    try:
                        pw_page.goto(url, timeout=45000, wait_until="networkidle")
                        pw_page.wait_for_timeout(3000)
                    except Exception as e:
                        logger.warning(f"Qatar Playwright page {page_num}: {e}")
                        break

                    html = pw_page.content()
                    soup = BeautifulSoup(html, "lxml")
                    page_tenders = _scrape_page(soup, url, seen)

                    logger.info(f"Qatar Playwright page {page_num}: {len(page_tenders)} tenders")
                    if not page_tenders:
                        break
                    tenders.extend(page_tenders)

                browser.close()
        except Exception as e:
            logger.error(f"Qatar Playwright error: {e}")

    if not tenders:
        logger.warning(
            "Qatar: no tenders scraped. The portal may be unreachable "
            "from outside Qatar or requires specific network access."
        )

    logger.info(f"Qatar total: {len(tenders)} tenders")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "qatar")
    print(f"Scraped {len(results)} tenders from Qatar Monaqasat")
