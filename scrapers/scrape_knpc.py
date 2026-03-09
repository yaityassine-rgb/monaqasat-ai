"""
Scraper for Kuwait Oil Sector (K-Tendering) - KNPC and KPC.
Source: https://ktendering.com.kw

JAGGAER-based platform. The public running tenders page lists PDF links to
running tender reports. The "Current Opportunities" page at
/esop/guest/go/public/opportunity/current requires authentication (401).

We scrape the running tenders HTML page which has links to JSP-generated
tender reports, and attempt the public opportunity listing.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("knpc")

BASE_URL = "https://ktendering.com.kw"
KNPC_RUNNING_URL = f"{BASE_URL}/esop/kuw-kpc-host/public/ktendering/web/KNPC_running_tenders.html"
IPC_TENDERS_URL = f"{BASE_URL}/esop/kuw-kpc-host/public/report/runningTenders.jsp?ipc=1"
HPC_TENDERS_URL = f"{BASE_URL}/esop/kuw-kpc-host/public/report/runningTenders.jsp?ipc=0"
CURRENT_OPP_URL = f"{BASE_URL}/esop/guest/go/public/opportunity/current"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def _scrape_running_tenders_jsp(url: str, label: str) -> list[dict]:
    """Scrape the JSP running tenders report page."""
    tenders: list[dict] = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)

        if resp.status_code != 200:
            logger.warning(f"KNPC {label}: HTTP {resp.status_code}")
            return tenders

        content_type = resp.headers.get("Content-Type", "")

        # If it returns a PDF, we can't parse it here
        if "pdf" in content_type.lower():
            logger.info(f"KNPC {label}: Returns PDF content, cannot parse directly")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # The JSP page may render as HTML table with tender data
        tables = soup.select("table")
        for table in tables:
            rows = table.select("tr")
            header_found = False
            header_map: dict[str, int] = {}

            for row in rows:
                cells = row.select("td, th")
                if not cells:
                    continue

                texts = [c.get_text(strip=True) for c in cells]

                # Detect header row
                if not header_found:
                    header_text = " ".join(texts).lower()
                    if any(kw in header_text for kw in
                           ["tender", "description", "closing", "subject", "bid"]):
                        header_found = True
                        for i, t in enumerate(texts):
                            header_map[t.lower()] = i
                        continue

                if not header_found or len(texts) < 3:
                    continue

                # Extract fields based on header position or heuristics
                title = ""
                ref = ""
                deadline = ""
                pub_date = ""

                for i, t in enumerate(texts):
                    if not t:
                        continue
                    # Reference number (usually short, alphanumeric)
                    if re.match(r'^[A-Z0-9\-/]{4,25}$', t) and not ref:
                        ref = t
                    # Date detection
                    elif parse_date(t):
                        if not pub_date:
                            pub_date = parse_date(t)
                        else:
                            deadline = parse_date(t)
                    # Longer text is likely the title/description
                    elif len(t) > len(title):
                        title = t

                if not title or len(title) < 5:
                    continue

                if not ref:
                    ref = title[:60]

                tender = {
                    "id": generate_id("knpc", ref, ""),
                    "source": "KNPC K-Tendering",
                    "sourceRef": ref,
                    "sourceLanguage": "en",
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": "Kuwait National Petroleum Company (KNPC)",
                        "ar": "شركة البترول الوطنية الكويتية",
                        "fr": "Kuwait National Petroleum Company (KNPC)",
                    },
                    "country": "Kuwait",
                    "countryCode": "KW",
                    "sector": classify_sector(title + " oil gas petroleum energy"),
                    "budget": 0,
                    "currency": "KWD",
                    "deadline": deadline or "",
                    "publishDate": pub_date or "",
                    "status": "open",
                    "description": {
                        "en": " | ".join(texts)[:500],
                        "ar": " | ".join(texts)[:500],
                        "fr": " | ".join(texts)[:500],
                    },
                    "requirements": [],
                    "matchScore": 0,
                    "sourceUrl": url,
                }
                tenders.append(tender)

    except Exception as e:
        logger.error(f"KNPC {label} scraper error: {e}")

    return tenders


def _scrape_current_opportunities() -> list[dict]:
    """Try to access the JAGGAER current opportunities page."""
    tenders: list[dict] = []

    try:
        resp = requests.get(CURRENT_OPP_URL, headers=HEADERS, timeout=30,
                            allow_redirects=True)

        if resp.status_code == 401:
            logger.info("KNPC current opportunities: Requires authentication (401)")
            return tenders

        if resp.status_code != 200:
            logger.warning(f"KNPC current opportunities: HTTP {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # JAGGAER lists opportunities in table or card format
        rows = soup.select("tr, .opportunity-row, .opp-item, [class*='opportunity']")

        for row in rows:
            title_el = row.select_one("a, .title, td:nth-child(2)")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            link_el = row.select_one("a[href]")
            href = ""
            if link_el:
                href = link_el.get("href", "")
                if href and not href.startswith("http"):
                    href = BASE_URL + href

            row_text = row.get_text(" ", strip=True)
            ref_match = re.search(r'([A-Z0-9]{2,}-[A-Z0-9\-]+)', row_text)
            ref = ref_match.group(1) if ref_match else title[:60]

            tender = {
                "id": generate_id("knpc", ref, ""),
                "source": "KNPC K-Tendering",
                "sourceRef": ref,
                "sourceLanguage": "en",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "Kuwait Petroleum Corporation (KPC)",
                    "ar": "مؤسسة البترول الكويتية",
                    "fr": "Kuwait Petroleum Corporation (KPC)",
                },
                "country": "Kuwait",
                "countryCode": "KW",
                "sector": classify_sector(title + " oil gas petroleum energy"),
                "budget": 0,
                "currency": "KWD",
                "deadline": "",
                "publishDate": "",
                "status": "open",
                "description": {
                    "en": row_text[:500],
                    "ar": row_text[:500],
                    "fr": row_text[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": href or CURRENT_OPP_URL,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"KNPC current opportunities error: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape Kuwait oil sector tenders from K-Tendering."""
    ipc_tenders = _scrape_running_tenders_jsp(IPC_TENDERS_URL, "IPC")
    time.sleep(2)
    hpc_tenders = _scrape_running_tenders_jsp(HPC_TENDERS_URL, "HPC")
    time.sleep(2)
    opp_tenders = _scrape_current_opportunities()

    # Merge and deduplicate
    seen: set[str] = set()
    all_tenders: list[dict] = []
    for t in ipc_tenders + hpc_tenders + opp_tenders:
        key = t["sourceRef"]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    logger.info(f"KNPC total: {len(all_tenders)} tenders "
                f"(IPC: {len(ipc_tenders)}, HPC: {len(hpc_tenders)}, "
                f"opportunities: {len(opp_tenders)})")

    if not all_tenders:
        logger.warning("KNPC: No tenders found. The K-Tendering portal "
                        "running tenders pages return PDF reports or require "
                        "authentication. The public KNPC running tenders page "
                        "provides links to PDF-based tender lists.")

    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "knpc")
    print(f"Scraped {len(results)} tenders from KNPC K-Tendering")
