"""
Scraper for Bahrain Tender Board.
Source: https://www.tenderboard.gov.bh/Tenders/PublicTenders/

Bahrain's official government tender board. Uses an ASP.NET AJAX endpoint
that returns HTML fragments containing tender listings.
Content is in English.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("bahrain")

BASE_URL = "https://www.tenderboard.gov.bh"
AJAX_URL = f"{BASE_URL}/Templates/TenderBoardWebService.aspx/GetCurrentPublicTenderByPage"
PUBLIC_TENDERS_URL = f"{BASE_URL}/Tenders/PublicTenders/"
MAX_PAGES = 20


def _create_session() -> requests.Session:
    """Create a session with proper headers for ASP.NET."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Referer": PUBLIC_TENDERS_URL,
        "Origin": BASE_URL,
        "X-Requested-With": "XMLHttpRequest",
    })
    return s


def _parse_bahrain_date(date_str: str) -> str:
    """Parse Bahrain-specific date formats like '08, Mar,2026'."""
    if not date_str:
        return ""
    # Clean up the date string
    cleaned = re.sub(r"\s+", " ", date_str.strip())
    # Try formats: "08, Mar,2026", "29 Mar,2026", "08 Mar 2026"
    formats = [
        "%d, %b,%Y",
        "%d %b,%Y",
        "%d, %b, %Y",
        "%d %b %Y",
        "%d %b, %Y",
        "%d,%b,%Y",
    ]
    for fmt in formats:
        try:
            from datetime import datetime
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Fallback to generic parser
    return parse_date(cleaned) or ""


def _parse_tender_div(div) -> dict | None:
    """Parse a single tender from the AJAX HTML response."""
    columns = div.find_all("div", class_="column")
    if len(columns) < 5:
        return None

    # Column mapping based on data-label attributes:
    # [0] index, [1] No./Tender Subject, [2] Tender Type, [3] Purchasing Authority,
    # [4] Published Date, [5] Purchase Before, [6] Closing Date
    data = {}
    for col in columns:
        label = col.get("data-label", "")
        text = col.get_text(strip=True)
        data[label] = text

    # Extract tender number and title from the link
    tender_no = ""
    title = ""
    source_url = PUBLIC_TENDERS_URL
    link = div.find("a", href=True)
    if link:
        href = link.get("href", "")
        source_url = href if href.startswith("http") else f"{BASE_URL}{href}"
        # The link contains a span with the reference and text with the title
        span = link.find("span")
        if span:
            tender_no = span.get_text(strip=True)
            # Title is the text after the span
            title = link.get_text(strip=True).replace(tender_no, "", 1).strip()
        else:
            title = link.get_text(strip=True)

    if not title or len(title) < 5:
        title = data.get("No./Tender Subject", "")
    if not title or len(title) < 5:
        return None

    org = data.get("Purchasing Authority", "")
    tender_type = data.get("Tender Type", "")
    pub_date = _parse_bahrain_date(data.get("Publish Date", "") or data.get("Published Date", ""))
    deadline = _parse_bahrain_date(data.get("Closing Date", ""))
    purchase_before = _parse_bahrain_date(data.get("Purchase Before", ""))

    # Determine status from closing date tooltip (days remaining)
    status = "open"
    closing_col = None
    for col in columns:
        if col.get("data-label") == "Closing Date":
            closing_col = col
            break
    if closing_col:
        tooltip = closing_col.find("span", attrs={"data-toggle": "tooltip"})
        if tooltip:
            tooltip_text = tooltip.get("title", "")
            day_match = re.search(r"(\d+)\s*day", tooltip_text)
            if day_match:
                days_remaining = int(day_match.group(1))
                if days_remaining <= 7:
                    status = "closing-soon"

    desc_parts = []
    if tender_type:
        desc_parts.append(f"Type: {tender_type}")
    if org:
        desc_parts.append(f"Authority: {org}")
    if purchase_before:
        desc_parts.append(f"Purchase before: {purchase_before}")
    desc = " | ".join(desc_parts) if desc_parts else title

    return {
        "id": generate_id("bahrain", tender_no or title[:80], ""),
        "source": "Bahrain Tender Board",
        "sourceRef": tender_no,
        "sourceLanguage": "en",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or "Government of Bahrain",
            "ar": org or "حكومة البحرين",
            "fr": org or "Gouvernement de Bahreïn",
        },
        "country": "Bahrain",
        "countryCode": "BH",
        "sector": classify_sector(title + " " + tender_type),
        "budget": 0,
        "currency": "BHD",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": status,
        "description": {"en": desc, "ar": desc, "fr": desc},
        "requirements": [tender_type] if tender_type else [],
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def scrape() -> list[dict]:
    """Scrape Bahrain Tender Board for public procurement notices."""
    tenders: list[dict] = []
    seen: set[str] = set()
    session = _create_session()

    for page in range(1, MAX_PAGES + 1):
        try:
            payload = (
                "{"
                "'tenderNumber':'','ministry':'0','category':'0',"
                "'tendertype':'0','closingDate_filter':'',"
                "'publicTenderOnly':'true','prequalificationOnly':'false',"
                "'auctionOnly':'false','sortingType':'0',"
                "'listPage':'mainList',"
                f"'Page':'{page}',"
                "'smeTendersOnly':'false','sectionName':''"
                "}"
            )

            resp = session.post(
                AJAX_URL,
                data=payload,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=30,
            )

            if resp.status_code != 200:
                logger.warning(f"Bahrain page {page}: HTTP {resp.status_code}")
                break

            data = resp.json()
            html_content = data.get("d", "")
            if not html_content:
                logger.info(f"Bahrain page {page}: empty response")
                break

            soup = BeautifulSoup(html_content, "lxml")
            rows = soup.find_all("div", class_="rows")

            if not rows:
                logger.info(f"Bahrain page {page}: no tender rows found")
                break

            page_count = 0
            for row in rows:
                tender = _parse_tender_div(row)
                if not tender:
                    continue
                key = tender["sourceRef"] or tender["title"]["en"][:60]
                if key in seen:
                    continue
                seen.add(key)
                tenders.append(tender)
                page_count += 1

            logger.info(f"Bahrain page {page}: {page_count} tenders (total: {len(tenders)})")

            if page_count == 0:
                break

            time.sleep(2)

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Bahrain page {page}: connection error — {e}")
            break
        except Exception as e:
            logger.error(f"Bahrain page {page}: {e}")
            break

    logger.info(f"Bahrain total: {len(tenders)} tenders")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "bahrain")
    print(f"Scraped {len(results)} tenders from Bahrain Tender Board")
