"""
Scraper for Oman eTendering Portal (expanded).
Source: https://etendering.tenderboard.gov.om/product/publicDash

This is an expanded scraper for Oman's official government tender board
that complements the existing scrape_oman.py. While scrape_oman.py focuses
on the basic NewTenders and InProcessTenders views, this scraper provides
deeper coverage by:

1. Scraping additional tender categories (completed, awarded)
2. Parsing detail pages for richer tender information
3. Extracting organization details, categories, and bank guarantees
4. Following pagination within each view
5. Extracting Arabic and English content where available

Content is primarily in Arabic with some English fields.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, parse_amount, save_tenders

logger = logging.getLogger("oman_etendering")

BASE_URL = "https://etendering.tenderboard.gov.om"
DASHBOARD_URL = f"{BASE_URL}/product/publicDash"
DETAIL_URL_TEMPLATE = (
    f"{BASE_URL}/product/nitParameterView?mode=public&tenderNo={{tid}}&PublicUrl=1"
)
# Additional endpoints
SEARCH_URL = f"{BASE_URL}/product/search"
CATEGORY_URL = f"{BASE_URL}/product/publicDash"

# All view flags to scrape
VIEW_FLAGS = [
    "NewTenders",
    "InProcessTenders",
    "ClosedTenders",
    "AwardedTenders",
    "PrequalificationTenders",
]

MAX_PAGES_PER_VIEW = 5


def _create_session() -> requests.Session:
    """Create a session with proper headers for the Oman portal."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ar,en;q=0.9",
        "Referer": DASHBOARD_URL,
    })
    return s


def _parse_oman_dates(date_cell_text: str) -> tuple[str, str]:
    """Parse Oman date cell which may contain both sales end and bid closing dates.

    Common formats:
    - 'Sales EndDate:DD-MM-YYYY-Bid Closing Date:DD-MM-YYYY'
    - 'DD-MM-YYYY' (single date)
    - 'DD/MM/YYYY'
    """
    sales_end = ""
    bid_closing = ""

    if not date_cell_text:
        return sales_end, bid_closing

    # Extract Sales EndDate
    match = re.search(r"Sales\s*EndDate[:\s]*(\d{2}[-/]\d{2}[-/]\d{4})", date_cell_text)
    if match:
        sales_end = parse_date(match.group(1)) or ""

    # Extract Bid Closing Date
    match = re.search(r"Bid\s*Closing\s*Date[:\s]*(\d{2}[-/]\d{2}[-/]\d{4})", date_cell_text)
    if match:
        bid_closing = parse_date(match.group(1)) or ""

    # If no structured format, try to find any dates
    if not sales_end and not bid_closing:
        dates = re.findall(r"(\d{2}[-/]\d{2}[-/]\d{4})", date_cell_text)
        if len(dates) >= 2:
            sales_end = parse_date(dates[0]) or ""
            bid_closing = parse_date(dates[1]) or ""
        elif len(dates) == 1:
            bid_closing = parse_date(dates[0]) or ""

    return sales_end, bid_closing


def _extract_tender_id(row) -> str:
    """Extract the tender ID from the row's action column."""
    # Look for getNit('id') or similar onclick patterns
    for a in row.find_all("a", onclick=True):
        onclick = a.get("onclick", "")
        match = re.search(r"getNit\(['\"]?(\d+)['\"]?\)", onclick)
        if match:
            return match.group(1)
    # Try data attributes
    tender_id = row.get("data-id", "") or row.get("data-tender-id", "")
    if tender_id:
        return tender_id
    # Try hidden inputs
    hidden = row.find("input", attrs={"type": "hidden"})
    if hidden:
        return hidden.get("value", "")
    return ""


def _parse_tender_row(row, view_flag: str) -> dict | None:
    """Parse a single tender row from the Oman public dashboard table.

    Table columns (Arabic headers):
    [0] م (Serial No.)
    [1] رقم المناقصة (Tender Number)
    [2] إسم المناقصة (Tender Name)
    [3] الجهة الحكومية (Government Entity)
    [4] تصنيف المشتريات (Procurement Category) [Grade]
    [5] نوع المناقصة (Tender Type) [Company Type]
    [6] التاريخ (Date - Sales End + Bid Closing)
    [7] رسم المناقصة (Tender Fee)
    [8] ضمان العطاء (Bank Guarantee)
    [9] إجراء (Action)
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
    guarantee_text = texts[8] if len(texts) > 8 else ""

    if not name or len(name) < 3:
        return None

    # Parse tender type (remove company type info in brackets)
    tender_type = tender_type_raw.split("[")[0].strip() if tender_type_raw else ""

    # Parse category (remove grade info in brackets)
    category_clean = category.split("[")[0].strip() if category else ""

    # Parse dates
    sales_end, bid_closing = _parse_oman_dates(date_text)

    # Parse fee
    fee = 0.0
    if fee_text:
        fee = parse_amount(fee_text)

    # Parse bank guarantee
    guarantee = ""
    if guarantee_text:
        guarantee = guarantee_text.strip()

    # Extract tender ID for detail URL
    tender_id = _extract_tender_id(row)
    if tender_id:
        source_url = DETAIL_URL_TEMPLATE.format(tid=tender_id)
    else:
        source_url = DASHBOARD_URL

    # Clean the name (may end with "....." or have excessive whitespace)
    name_clean = re.sub(r"\.{3,}", "", name).strip()
    name_clean = re.sub(r"\s+", " ", name_clean)

    # Determine status based on view flag
    status_map = {
        "NewTenders": "open",
        "InProcessTenders": "open",
        "ClosedTenders": "closed",
        "AwardedTenders": "awarded",
        "PrequalificationTenders": "open",
    }
    status = status_map.get(view_flag, "open")

    # Build description
    desc_parts = []
    if tender_type:
        desc_parts.append(f"Type: {tender_type}")
    if category_clean:
        desc_parts.append(f"Category: {category_clean}")
    if org:
        desc_parts.append(f"Entity: {org}")
    if guarantee:
        desc_parts.append(f"Bank Guarantee: {guarantee}")
    if fee > 0:
        desc_parts.append(f"Fee: {fee} OMR")
    desc = " | ".join(desc_parts) if desc_parts else name_clean

    # Build requirements list
    requirements = []
    if tender_type:
        requirements.append(tender_type)
    if category_clean:
        requirements.append(category_clean)
    if guarantee:
        requirements.append(f"Bank Guarantee: {guarantee}")

    return {
        "id": generate_id("oman_et", tender_no or name_clean[:80], ""),
        "source": "Oman eTendering",
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
        "sector": classify_sector(name_clean + " " + category_clean),
        "budget": fee,
        "currency": "OMR",
        "deadline": bid_closing,
        "publishDate": sales_end,
        "status": status,
        "description": {"en": desc, "ar": desc, "fr": desc},
        "requirements": requirements,
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def _find_tender_table(soup: BeautifulSoup) -> list:
    """Find and return rows from the tender table in the page."""
    tables = soup.find_all("table")
    for table in tables:
        headers = table.find_all("th")
        if len(headers) >= 7:
            header_text = " ".join(h.get_text(strip=True) for h in headers)
            # Look for Arabic or English tender table headers
            if any(
                kw in header_text
                for kw in ["رقم المناقصة", "إسم المناقصة", "Tender Number", "Tender Name"]
            ):
                rows = table.find_all("tr")
                return rows[1:]  # Skip header row

    # Fallback: look for DataTable
    data_table = soup.find("table", class_=re.compile(r"dataTable|display", re.I))
    if data_table:
        rows = data_table.find_all("tr")
        return rows[1:] if rows else []

    return []


def _fetch_tender_detail(session: requests.Session, tender_id: str) -> dict:
    """Fetch additional details from a tender detail page."""
    details = {}
    try:
        url = DETAIL_URL_TEMPLATE.format(tid=tender_id)
        resp = session.get(url, timeout=20)
        if resp.status_code != 200:
            return details

        soup = BeautifulSoup(resp.text, "lxml")

        # Extract key-value pairs from the detail page
        rows = soup.find_all("tr")
        for row in rows:
            cells = row.find_all(["th", "td"])
            if len(cells) == 2:
                label = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if label and value:
                    details[label] = value

        # Try div-based key-value layout
        for div in soup.find_all("div", class_=re.compile(r"form-group|field", re.I)):
            label_el = div.find(["label", "span"], class_=re.compile(r"label|key", re.I))
            value_el = div.find(["span", "div", "p"], class_=re.compile(r"value|data", re.I))
            if label_el and value_el:
                details[label_el.get_text(strip=True)] = value_el.get_text(strip=True)

    except Exception as e:
        logger.debug(f"Detail fetch for {tender_id}: {e}")

    return details


def scrape() -> list[dict]:
    """Scrape Oman eTendering Portal for public procurement notices."""
    tenders: list[dict] = []
    seen: set[str] = set()
    session = _create_session()

    # First, GET the public dashboard to establish session cookies
    try:
        resp = session.get(DASHBOARD_URL, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"Oman eTendering dashboard GET: HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"Oman eTendering dashboard GET: {e}")

    time.sleep(2)

    # Scrape each view flag
    for view_flag in VIEW_FLAGS:
        view_tenders = 0

        for page in range(1, MAX_PAGES_PER_VIEW + 1):
            try:
                post_data = {
                    "viewFlag": view_flag,
                    "securityFlag": "1",
                }

                # Add pagination parameter if supported
                if page > 1:
                    post_data["pageNo"] = str(page)
                    post_data["page"] = str(page)

                resp = session.post(
                    DASHBOARD_URL,
                    data=post_data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Referer": DASHBOARD_URL,
                    },
                    timeout=30,
                )

                if resp.status_code != 200:
                    logger.warning(f"Oman {view_flag} page {page}: HTTP {resp.status_code}")
                    break

                soup = BeautifulSoup(resp.text, "lxml")
                rows = _find_tender_table(soup)

                if not rows:
                    if page == 1:
                        logger.info(f"Oman {view_flag}: no tender table found")
                    break

                page_count = 0
                for row in rows:
                    tender = _parse_tender_row(row, view_flag)
                    if not tender:
                        continue
                    key = tender["sourceRef"] or tender["title"]["ar"][:60]
                    if key in seen:
                        continue
                    seen.add(key)
                    tenders.append(tender)
                    page_count += 1
                    view_tenders += 1

                logger.info(
                    f"Oman {view_flag} page {page}: {page_count} tenders "
                    f"(view: {view_tenders}, total: {len(tenders)})"
                )

                if page_count == 0:
                    break

                time.sleep(2)

            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Oman {view_flag} page {page}: connection error — {e}")
                break
            except Exception as e:
                logger.error(f"Oman {view_flag} page {page}: {e}")
                break

        logger.info(f"Oman {view_flag}: {view_tenders} tenders")
        time.sleep(1)

    # Optionally enrich a sample of tenders with detail page data
    enrich_count = 0
    max_enrich = min(10, len(tenders))  # Limit to avoid too many requests
    for tender in tenders[:max_enrich]:
        if "/nitParameterView" in tender.get("sourceUrl", ""):
            tender_id_match = re.search(r"tenderNo=(\d+)", tender["sourceUrl"])
            if tender_id_match:
                details = _fetch_tender_detail(session, tender_id_match.group(1))
                if details:
                    # Update description with enriched data
                    detail_text = " | ".join(f"{k}: {v}" for k, v in list(details.items())[:5])
                    if detail_text:
                        tender["description"]["en"] = detail_text[:500]
                        tender["description"]["ar"] = detail_text[:500]
                        enrich_count += 1
                time.sleep(1)

    if enrich_count > 0:
        logger.info(f"Oman eTendering: enriched {enrich_count} tenders with detail data")

    logger.info(f"Oman eTendering total: {len(tenders)} tenders")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "oman_etendering")
    print(f"Scraped {len(results)} tenders from Oman eTendering Portal")
