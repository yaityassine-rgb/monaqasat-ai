"""
Scraper for Oman Tender Board (etendering.tenderboard.gov.om).
Source: https://etendering.tenderboard.gov.om/product/publicDash

Oman's official government tender board. The public dashboard shows
new/open tenders in an HTML table. POSTing with viewFlag=NewTenders
returns the tender listing. Detail pages use getNit(tenderId) pattern
which resolves to /product/nitParameterView?mode=public&tenderNo={id}&PublicUrl=1.
Content is primarily in Arabic.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("oman")

BASE_URL = "https://etendering.tenderboard.gov.om"
DASHBOARD_URL = f"{BASE_URL}/product/publicDash"
DETAIL_URL_TEMPLATE = f"{BASE_URL}/product/nitParameterView?mode=public&tenderNo={{tid}}&PublicUrl=1"


def _create_session() -> requests.Session:
    """Create a session with proper headers."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ar,en;q=0.9",
    })
    return s


def _parse_oman_dates(date_cell_text: str) -> tuple[str, str]:
    """Parse Oman date cell which contains both sales end date and bid closing date.

    Format: 'Sales EndDate:DD-MM-YYYY-Bid Closing Date:DD-MM-YYYY'
    """
    sales_end = ""
    bid_closing = ""

    # Extract Sales EndDate
    match = re.search(r"Sales\s*EndDate[:\s]*(\d{2}-\d{2}-\d{4})", date_cell_text)
    if match:
        sales_end = parse_date(match.group(1)) or ""

    # Extract Bid Closing Date
    match = re.search(r"Bid\s*Closing\s*Date[:\s]*(\d{2}-\d{2}-\d{4})", date_cell_text)
    if match:
        bid_closing = parse_date(match.group(1)) or ""

    return sales_end, bid_closing


def _extract_tender_id(row) -> str:
    """Extract the tender ID from the row's action column (getNit('id') onclick)."""
    for a in row.find_all("a", onclick=True):
        onclick = a.get("onclick", "")
        match = re.search(r"getNit\(['\"]?(\d+)['\"]?\)", onclick)
        if match:
            return match.group(1)
    return ""


def _parse_tender_row(row) -> dict | None:
    """Parse a single tender row from the Oman public dashboard table.

    Table headers:
    [0] Serial No.
    [1] Tender Number
    [2] Tender Name
    [3] Entity/Government Unit
    [4] Procurement Category [Grade]
    [5] Tender Type [Company Type]
    [6] Date (Sales End + Bid Closing)
    [7] Tender Fee
    [8] Bank Guarantee (%/value)
    [9] Action
    """
    cells = row.find_all("td")
    if len(cells) < 7:
        return None

    texts = [c.get_text(strip=True) for c in cells]

    serial = texts[0] if len(texts) > 0 else ""
    tender_no = texts[1] if len(texts) > 1 else ""
    name = texts[2] if len(texts) > 2 else ""
    org = texts[3] if len(texts) > 3 else ""
    category = texts[4] if len(texts) > 4 else ""
    tender_type_raw = texts[5] if len(texts) > 5 else ""
    date_text = texts[6] if len(texts) > 6 else ""
    fee_text = texts[7] if len(texts) > 7 else ""

    if not name or len(name) < 5:
        return None

    # Parse the tender type (remove company type info)
    tender_type = tender_type_raw.split("[")[0].strip() if tender_type_raw else ""

    # Parse dates
    sales_end, bid_closing = _parse_oman_dates(date_text)

    # Parse fee
    fee = 0.0
    try:
        fee_clean = re.sub(r"[^\d.]", "", fee_text)
        if fee_clean:
            fee = float(fee_clean)
    except ValueError:
        pass

    # Extract tender ID for detail URL
    tender_id = _extract_tender_id(row)
    if tender_id:
        source_url = DETAIL_URL_TEMPLATE.format(tid=tender_id)
    else:
        source_url = DASHBOARD_URL

    # Clean the name (may end with ".....")
    name_clean = re.sub(r"\.{3,}", "", name).strip()

    # Build description
    desc_parts = []
    if tender_type:
        desc_parts.append(tender_type)
    if category:
        # Clean category (remove grade info in brackets)
        cat_clean = category.split("[")[0].strip()
        desc_parts.append(cat_clean)
    if org:
        desc_parts.append(org)
    desc = " | ".join(desc_parts) if desc_parts else name_clean

    return {
        "id": generate_id("oman", tender_no or name_clean[:80], ""),
        "source": "Oman Tender Board",
        "sourceRef": tender_no,
        "sourceLanguage": "ar",
        "title": {"en": name_clean, "ar": name_clean, "fr": name_clean},
        "organization": {
            "en": org or "Government of Oman",
            "ar": org or "حكومة سلطنة عمان",
            "fr": org or "Gouvernement d'Oman",
        },
        "country": "Oman",
        "countryCode": "OM",
        "sector": classify_sector(name_clean + " " + category),
        "budget": fee,
        "currency": "OMR",
        "deadline": bid_closing,
        "publishDate": sales_end,
        "status": "open",
        "description": {"en": desc, "ar": desc, "fr": desc},
        "requirements": [tender_type] if tender_type else [],
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def scrape() -> list[dict]:
    """Scrape Oman Tender Board for public procurement notices."""
    tenders: list[dict] = []
    seen: set[str] = set()
    session = _create_session()

    # First, get the public dashboard (GET) to establish session
    try:
        resp = session.get(DASHBOARD_URL, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"Oman dashboard GET: HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"Oman dashboard GET: {e}")

    time.sleep(2)

    # POST to get new tenders listing
    view_flags = ["NewTenders", "InProcessTenders"]

    for view_flag in view_flags:
        try:
            resp = session.post(
                DASHBOARD_URL,
                data={
                    "viewFlag": view_flag,
                    "securityFlag": "1",
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": DASHBOARD_URL,
                },
                timeout=30,
            )

            if resp.status_code != 200:
                logger.warning(f"Oman {view_flag}: HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Find the tender table (class="display" with 8+ column headers)
            tables = soup.find_all("table")
            tender_table = None
            for t in tables:
                headers = t.find_all("th")
                if len(headers) >= 7:
                    header_text = " ".join(h.get_text(strip=True) for h in headers)
                    if "رقم المناقصة" in header_text or "إسم المناقصة" in header_text:
                        tender_table = t
                        break

            if not tender_table:
                logger.info(f"Oman {view_flag}: no tender table found")
                continue

            rows = tender_table.find_all("tr")
            page_count = 0

            for row in rows[1:]:  # Skip header row
                tender = _parse_tender_row(row)
                if not tender:
                    continue
                key = tender["sourceRef"] or tender["title"]["ar"][:60]
                if key in seen:
                    continue
                seen.add(key)
                tenders.append(tender)
                page_count += 1

            logger.info(f"Oman {view_flag}: {page_count} tenders (total: {len(tenders)})")
            time.sleep(2)

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Oman {view_flag}: connection error — {e}")
        except Exception as e:
            logger.error(f"Oman {view_flag}: {e}")

    logger.info(f"Oman total: {len(tenders)} tenders")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "oman")
    print(f"Scraped {len(results)} tenders from Oman Tender Board")
