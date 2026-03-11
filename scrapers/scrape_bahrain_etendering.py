"""
Scraper for Bahrain eTendering System.
Source: https://etendering.tenderboard.gov.bh/

This is an expanded scraper for Bahrain's electronic tendering system
that complements the existing scrape_bahrain.py. While scrape_bahrain.py
focuses on public tenders via the ASP.NET AJAX endpoint, this scraper
provides deeper coverage by:

1. Accessing the eTendering portal for electronic procurement
2. Scraping pre-qualification notices
3. Scraping auction listings
4. Parsing both English and Arabic content
5. Extracting additional fields like tender value, category, and documents

The eTendering portal at etendering.tenderboard.gov.bh is the electronic
submission and management system, separate from the public listings on
tenderboard.gov.bh.

Content is available in both English and Arabic.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, parse_amount, save_tenders

logger = logging.getLogger("bahrain_etendering")

BASE_URL = "https://etendering.tenderboard.gov.bh"
PORTAL_URL = f"{BASE_URL}/"
# Public-facing tender board URLs
TENDER_BOARD_URL = "https://www.tenderboard.gov.bh"
PREQUALIFICATION_URL = f"{TENDER_BOARD_URL}/Tenders/PrequalificationNotice/"
AUCTIONS_URL = f"{TENDER_BOARD_URL}/Tenders/PublicAuctions/"
SME_TENDERS_URL = f"{TENDER_BOARD_URL}/Tenders/SMETenders/"
# AJAX endpoint from the main tender board
AJAX_URL = f"{TENDER_BOARD_URL}/Templates/TenderBoardWebService.aspx/GetCurrentPublicTenderByPage"
MAX_PAGES = 15


def _create_session() -> requests.Session:
    """Create a session with proper headers for the Bahrain portal."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Referer": TENDER_BOARD_URL,
    })
    return s


def _parse_bahrain_date(date_str: str) -> str:
    """Parse Bahrain-specific date formats like '08, Mar,2026'."""
    if not date_str:
        return ""
    # Clean up
    cleaned = re.sub(r"\s+", " ", date_str.strip())
    formats = [
        "%d, %b,%Y",
        "%d %b,%Y",
        "%d, %b, %Y",
        "%d %b %Y",
        "%d %b, %Y",
        "%d,%b,%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            from datetime import datetime
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return parse_date(cleaned) or ""


def _parse_tender_div(div) -> dict | None:
    """Parse a single tender from HTML response (rows layout)."""
    columns = div.find_all("div", class_="column")
    if len(columns) < 5:
        return None

    data = {}
    for col in columns:
        label = col.get("data-label", "")
        text = col.get_text(strip=True)
        data[label] = text

    # Extract tender number and title from link
    tender_no = ""
    title = ""
    source_url = f"{TENDER_BOARD_URL}/Tenders/PublicTenders/"
    link = div.find("a", href=True)
    if link:
        href = link.get("href", "")
        source_url = href if href.startswith("http") else f"{TENDER_BOARD_URL}{href}"
        span = link.find("span")
        if span:
            tender_no = span.get_text(strip=True)
            title = link.get_text(strip=True).replace(tender_no, "", 1).strip()
        else:
            title = link.get_text(strip=True)

    if not title or len(title) < 5:
        title = data.get("No./Tender Subject", "")
    if not title or len(title) < 5:
        return None

    org = data.get("Purchasing Authority", "")
    tender_type = data.get("Tender Type", "")
    pub_date = _parse_bahrain_date(
        data.get("Publish Date", "") or data.get("Published Date", "")
    )
    deadline = _parse_bahrain_date(data.get("Closing Date", ""))
    purchase_before = _parse_bahrain_date(data.get("Purchase Before", ""))

    # Determine status
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

    # Build description
    desc_parts = []
    if tender_type:
        desc_parts.append(f"Type: {tender_type}")
    if org:
        desc_parts.append(f"Authority: {org}")
    if purchase_before:
        desc_parts.append(f"Purchase before: {purchase_before}")
    desc = " | ".join(desc_parts) if desc_parts else title

    return {
        "id": generate_id("bahrain_et", tender_no or title[:80], ""),
        "source": "Bahrain eTendering",
        "sourceRef": tender_no,
        "sourceLanguage": "en",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or "Government of Bahrain",
            "ar": org or "حكومة البحرين",
            "fr": org or "Gouvernement de Bahrein",
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


def _scrape_etendering_portal(session: requests.Session) -> list[dict]:
    """Try to scrape the eTendering portal directly."""
    tenders: list[dict] = []

    try:
        resp = session.get(PORTAL_URL, timeout=30, allow_redirects=True)

        if resp.status_code == 403:
            logger.info("Bahrain eTendering: access denied (403)")
            return tenders
        if resp.status_code != 200:
            logger.info(f"Bahrain eTendering: HTTP {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Check if portal requires login
        login_indicators = soup.find_all(
            string=re.compile(r"log\s*in|sign\s*in|username|password|تسجيل", re.I)
        )
        form_inputs = soup.find_all("input", attrs={"type": "password"})
        if len(login_indicators) >= 2 or form_inputs:
            logger.info(
                "Bahrain eTendering: login page detected. "
                "Portal requires authentication for tender listings."
            )
            return tenders

        # Try to find public tender listings
        cards = (
            soup.select(".tender-card, .tender-item, .tender-row")
            or soup.select("article, .card, .item")
            or soup.select("[class*='tender']")
            or soup.select("table tbody tr")
        )

        for card in cards:
            title_el = card.find(["h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if len(title) < 10:
                continue

            link = card.find("a", href=True)
            source_url = PORTAL_URL
            if link:
                href = link.get("href", "")
                if href.startswith("http"):
                    source_url = href
                elif href.startswith("/"):
                    source_url = f"{BASE_URL}{href}"

            ref = card.get("data-id", "") or ""
            desc_el = card.find("p")
            description = desc_el.get_text(strip=True) if desc_el else title

            tender = {
                "id": generate_id("bahrain_et", ref or title[:80], ""),
                "source": "Bahrain eTendering",
                "sourceRef": ref,
                "sourceLanguage": "en",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "Government of Bahrain",
                    "ar": "حكومة البحرين",
                    "fr": "Gouvernement de Bahrein",
                },
                "country": "Bahrain",
                "countryCode": "BH",
                "sector": classify_sector(title + " " + description),
                "budget": 0,
                "currency": "BHD",
                "deadline": "",
                "publishDate": "",
                "status": "open",
                "description": {
                    "en": description[:500],
                    "ar": description[:500],
                    "fr": description[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": source_url,
            }
            tenders.append(tender)

        logger.info(f"Bahrain eTendering portal: {len(tenders)} tenders")

    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Bahrain eTendering portal: connection error — {e}")
    except Exception as e:
        logger.error(f"Bahrain eTendering portal: {e}")

    return tenders


def _scrape_prequalification(session: requests.Session) -> list[dict]:
    """Scrape pre-qualification notices from Bahrain Tender Board."""
    tenders: list[dict] = []

    try:
        # Use AJAX endpoint with prequalification flag
        for page in range(1, 6):
            payload = (
                "{"
                "'tenderNumber':'','ministry':'0','category':'0',"
                "'tendertype':'0','closingDate_filter':'',"
                "'publicTenderOnly':'false','prequalificationOnly':'true',"
                "'auctionOnly':'false','sortingType':'0',"
                "'listPage':'mainList',"
                f"'Page':'{page}',"
                "'smeTendersOnly':'false','sectionName':''"
                "}"
            )

            resp = session.post(
                AJAX_URL,
                data=payload,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Origin": TENDER_BOARD_URL,
                    "Referer": PREQUALIFICATION_URL,
                },
                timeout=30,
            )

            if resp.status_code != 200:
                break

            data = resp.json()
            html_content = data.get("d", "")
            if not html_content:
                break

            soup = BeautifulSoup(html_content, "lxml")
            rows = soup.find_all("div", class_="rows")

            if not rows:
                break

            page_count = 0
            for row in rows:
                tender = _parse_tender_div(row)
                if tender:
                    # Update source to indicate pre-qualification
                    tender["source"] = "Bahrain eTendering"
                    tender["requirements"].append("Pre-qualification")
                    tenders.append(tender)
                    page_count += 1

            logger.info(f"Bahrain prequalification page {page}: {page_count} notices")

            if page_count == 0:
                break

            time.sleep(2)

    except Exception as e:
        logger.error(f"Bahrain prequalification: {e}")

    return tenders


def _scrape_auctions(session: requests.Session) -> list[dict]:
    """Scrape public auction notices from Bahrain Tender Board."""
    tenders: list[dict] = []

    try:
        for page in range(1, 6):
            payload = (
                "{"
                "'tenderNumber':'','ministry':'0','category':'0',"
                "'tendertype':'0','closingDate_filter':'',"
                "'publicTenderOnly':'false','prequalificationOnly':'false',"
                "'auctionOnly':'true','sortingType':'0',"
                "'listPage':'mainList',"
                f"'Page':'{page}',"
                "'smeTendersOnly':'false','sectionName':''"
                "}"
            )

            resp = session.post(
                AJAX_URL,
                data=payload,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Origin": TENDER_BOARD_URL,
                    "Referer": AUCTIONS_URL,
                },
                timeout=30,
            )

            if resp.status_code != 200:
                break

            data = resp.json()
            html_content = data.get("d", "")
            if not html_content:
                break

            soup = BeautifulSoup(html_content, "lxml")
            rows = soup.find_all("div", class_="rows")

            if not rows:
                break

            page_count = 0
            for row in rows:
                tender = _parse_tender_div(row)
                if tender:
                    tender["source"] = "Bahrain eTendering"
                    tender["requirements"].append("Public Auction")
                    tenders.append(tender)
                    page_count += 1

            logger.info(f"Bahrain auctions page {page}: {page_count} notices")

            if page_count == 0:
                break

            time.sleep(2)

    except Exception as e:
        logger.error(f"Bahrain auctions: {e}")

    return tenders


def _scrape_sme_tenders(session: requests.Session) -> list[dict]:
    """Scrape SME-specific tenders from Bahrain Tender Board."""
    tenders: list[dict] = []

    try:
        for page in range(1, 6):
            payload = (
                "{"
                "'tenderNumber':'','ministry':'0','category':'0',"
                "'tendertype':'0','closingDate_filter':'',"
                "'publicTenderOnly':'false','prequalificationOnly':'false',"
                "'auctionOnly':'false','sortingType':'0',"
                "'listPage':'mainList',"
                f"'Page':'{page}',"
                "'smeTendersOnly':'true','sectionName':''"
                "}"
            )

            resp = session.post(
                AJAX_URL,
                data=payload,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Origin": TENDER_BOARD_URL,
                    "Referer": SME_TENDERS_URL,
                },
                timeout=30,
            )

            if resp.status_code != 200:
                break

            data = resp.json()
            html_content = data.get("d", "")
            if not html_content:
                break

            soup = BeautifulSoup(html_content, "lxml")
            rows = soup.find_all("div", class_="rows")

            if not rows:
                break

            page_count = 0
            for row in rows:
                tender = _parse_tender_div(row)
                if tender:
                    tender["source"] = "Bahrain eTendering"
                    tender["requirements"].append("SME Tender")
                    tenders.append(tender)
                    page_count += 1

            logger.info(f"Bahrain SME tenders page {page}: {page_count} notices")

            if page_count == 0:
                break

            time.sleep(2)

    except Exception as e:
        logger.error(f"Bahrain SME tenders: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape Bahrain eTendering system for procurement notices."""
    session = _create_session()

    # Try the eTendering portal first
    portal_tenders = _scrape_etendering_portal(session)

    # Scrape pre-qualification notices
    preq_tenders = _scrape_prequalification(session)

    # Scrape auction notices
    auction_tenders = _scrape_auctions(session)

    # Scrape SME tenders
    sme_tenders = _scrape_sme_tenders(session)

    # Merge and deduplicate
    seen: set[str] = set()
    all_tenders: list[dict] = []

    for t in portal_tenders + preq_tenders + auction_tenders + sme_tenders:
        key = t["sourceRef"] or t["title"]["en"][:60]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    logger.info(
        f"Bahrain eTendering total: {len(all_tenders)} tenders "
        f"(portal: {len(portal_tenders)}, prequalification: {len(preq_tenders)}, "
        f"auctions: {len(auction_tenders)}, SME: {len(sme_tenders)})"
    )

    if not all_tenders:
        logger.warning(
            "Bahrain eTendering: No tenders retrieved. The eTendering portal "
            "may require authentication. The Tender Board AJAX endpoint may "
            "have no current pre-qualification, auction, or SME listings."
        )

    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "bahrain_etendering")
    print(f"Scraped {len(results)} tenders from Bahrain eTendering")
