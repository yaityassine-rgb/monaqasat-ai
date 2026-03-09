"""
Scraper for European Bank for Reconstruction and Development (EBRD).
Source: https://ecepp.ebrd.com/delta/noticeSearchResults.html

Scrapes the ECEPP (EBRD Client E-Procurement Portal) search results page,
which is server-rendered HTML containing a table of procurement notices.
Filters for MENA-region countries relevant to monaqasat.
"""

import logging
import re
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("ebrd")

ECEPP_SEARCH_URL = (
    "https://ecepp.ebrd.com/delta/noticeSearchResults.html"
    "?locale=en"
    "&form_fields[keyword]="
    "&form_fields[noticeType]="
    "&form_fields[status]="
)

ECEPP_NOTICE_BASE = "https://ecepp.ebrd.com/delta/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# MENA countries that EBRD covers
EBRD_MENA_COUNTRIES = {
    "egypt": ("Egypt", "EG"),
    "jordan": ("Jordan", "JO"),
    "lebanon": ("Lebanon", "LB"),
    "morocco": ("Morocco", "MA"),
    "tunisia": ("Tunisia", "TN"),
    "iraq": ("Iraq", "IQ"),
    "palestine": ("Palestine", "PS"),
    "west bank": ("Palestine", "PS"),
    "gaza": ("Palestine", "PS"),
    "turkey": ("Turkey", "TR"),
    "türkiye": ("Turkey", "TR"),
    "turkiye": ("Turkey", "TR"),
}


def _detect_country(text: str) -> tuple[str, str]:
    """Detect MENA country from tender text."""
    text_lower = text.lower()
    for keyword, (name, code) in EBRD_MENA_COUNTRIES.items():
        if keyword in text_lower:
            return name, code
    return "MENA Region", "XX"


def _parse_ecepp_date(date_str: str) -> str:
    """Parse ECEPP date format like '09/03/2026 09:29UK Time' into ISO date."""
    if not date_str or date_str.strip() == "N/A":
        return ""
    # Extract date part before any time/timezone info
    match = re.match(r"(\d{2}/\d{2}/\d{4})", date_str.strip())
    if match:
        parsed = parse_date(match.group(1))
        if parsed:
            return parsed
    return ""


def _scrape_ecepp_search() -> list[dict]:
    """Scrape procurement notices from the ECEPP search results page."""
    tenders: list[dict] = []

    try:
        resp = requests.get(ECEPP_SEARCH_URL, headers=HEADERS, timeout=60)

        if resp.status_code != 200:
            logger.warning(f"ECEPP search page returned HTTP {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")
        table = soup.select_one("table.basic-table")
        if not table:
            logger.warning("ECEPP: Could not find the basic-table element")
            return tenders

        rows = table.select("tr")
        if len(rows) < 2:
            logger.warning("ECEPP: Table has no data rows")
            return tenders

        logger.info(f"ECEPP: Found {len(rows) - 1} total notices, filtering for MENA...")

        # Header row: Title | Notice Type | Procurement Exercise Title |
        #              Published | Closing Date | Current State
        # Plus hidden cols: published date, sort key, empty, metadata
        mena_keywords = set(EBRD_MENA_COUNTRIES.keys())

        for row in rows[1:]:
            cells = row.select("td")
            if len(cells) < 6:
                continue

            # Get full row text for country detection
            full_text = " ".join(c.get_text(strip=True) for c in cells)
            full_lower = full_text.lower()

            # Filter: only keep MENA-region notices
            is_mena = any(kw in full_lower for kw in mena_keywords)
            if not is_mena:
                continue

            # Extract fields from cells
            title_cell = cells[0]
            notice_type = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            procurement_title = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            published_raw = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            closing_raw = cells[4].get_text(strip=True) if len(cells) > 4 else ""
            current_state = cells[5].get_text(strip=True) if len(cells) > 5 else ""

            # Get title and link
            title_text = title_cell.get_text(strip=True)
            link_el = title_cell.select_one("a[href]")
            href = ""
            if link_el:
                href = link_el.get("href", "")
                if href and not href.startswith("http"):
                    href = ECEPP_NOTICE_BASE + href

            if not title_text or len(title_text) < 5:
                continue

            # Parse dates
            pub_date = _parse_ecepp_date(published_raw)
            deadline = _parse_ecepp_date(closing_raw)

            # Detect country from title (usually starts with "Country: ...")
            country, country_code = _detect_country(title_text + " " + full_text)

            # Extract a reference number from the notice ID in the URL
            source_ref = ""
            if href:
                ref_match = re.search(r"displayNoticeId=(\d+)", href)
                if ref_match:
                    source_ref = f"ECEPP-{ref_match.group(1)}"
            if not source_ref:
                source_ref = title_text[:60]

            # Determine status
            status = "open"
            state_lower = current_state.lower()
            if "closed" in state_lower or "awarded" in state_lower:
                status = "closed"
            elif "information" in state_lower:
                status = "open"

            # Build description from procurement title + notice type
            desc_parts = []
            if procurement_title and procurement_title != "N/A":
                desc_parts.append(f"Procurement: {procurement_title}")
            if notice_type:
                desc_parts.append(f"Type: {notice_type}")
            if current_state:
                desc_parts.append(f"State: {current_state}")
            description = ". ".join(desc_parts) if desc_parts else title_text

            tender = {
                "id": generate_id("ebrd", source_ref, ""),
                "source": "EBRD",
                "sourceRef": source_ref,
                "sourceLanguage": "en",
                "title": {"en": title_text, "ar": title_text, "fr": title_text},
                "organization": {
                    "en": "European Bank for Reconstruction and Development",
                    "ar": "البنك الأوروبي لإعادة الإعمار والتنمية",
                    "fr": "Banque européenne pour la reconstruction et le développement",
                },
                "country": country,
                "countryCode": country_code,
                "sector": classify_sector(title_text + " " + procurement_title),
                "budget": 0,
                "currency": "EUR",
                "deadline": deadline,
                "publishDate": pub_date,
                "status": status,
                "description": {
                    "en": description[:500],
                    "ar": description[:500],
                    "fr": description[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": href or ECEPP_SEARCH_URL,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"ECEPP scraper error: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape EBRD procurement notices from the ECEPP portal."""
    tenders = _scrape_ecepp_search()

    # Deduplicate by sourceRef
    seen: set[str] = set()
    unique: list[dict] = []
    for t in tenders:
        key = t["sourceRef"]
        if key not in seen:
            seen.add(key)
            unique.append(t)

    logger.info(f"EBRD total: {len(unique)} MENA-region notices from ECEPP")

    if not unique:
        logger.warning(
            "EBRD: No MENA tenders found on ECEPP. "
            "The search page may have changed its structure."
        )

    return unique


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "ebrd")
    print(f"Scraped {len(results)} notices from EBRD (ECEPP)")
