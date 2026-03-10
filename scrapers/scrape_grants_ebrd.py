"""
Grant scraper for European Bank for Reconstruction and Development (EBRD).
Sources:
  - ECEPP portal: https://ecepp.ebrd.com/delta/noticeSearchResults.html
  - Main procurement: https://www.ebrd.com/work-with-us/procurement/notices.html
  - Technical cooperation: https://www.ebrd.com/work-with-us/procurement.html

EBRD MENA coverage: Egypt, Jordan, Lebanon, Morocco, Tunisia, West Bank/Gaza.
Focuses on grant/technical cooperation opportunities (not just procurement).
"""

import re
import requests
import logging
import time
from bs4 import BeautifulSoup
from config import (
    MENA_COUNTRIES, MENA_COUNTRIES_AR, MENA_COUNTRIES_FR,
)
from base_scraper import (
    generate_grant_id, classify_sector, classify_grant_type,
    parse_date, parse_amount, save_grants,
)

logger = logging.getLogger("grants_ebrd")

# ECEPP (EBRD Client E-Procurement Portal)
ECEPP_SEARCH_URL = (
    "https://ecepp.ebrd.com/delta/noticeSearchResults.html"
    "?locale=en"
    "&form_fields[keyword]="
    "&form_fields[noticeType]="
    "&form_fields[status]="
)
ECEPP_NOTICE_BASE = "https://ecepp.ebrd.com/delta/"

# Main EBRD procurement pages
EBRD_PROCUREMENT_URL = "https://www.ebrd.com/work-with-us/procurement.html"
EBRD_NOTICES_URL = "https://www.ebrd.com/work-with-us/procurement/notices.html"

# Browser headers
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

# EBRD MENA countries
EBRD_MENA: dict[str, tuple[str, str]] = {
    "egypt": ("Egypt", "EG"),
    "jordan": ("Jordan", "JO"),
    "lebanon": ("Lebanon", "LB"),
    "morocco": ("Morocco", "MA"),
    "tunisia": ("Tunisia", "TN"),
    "west bank": ("Palestine", "PS"),
    "gaza": ("Palestine", "PS"),
    "palestine": ("Palestine", "PS"),
}

# Grant/TC-related keywords in EBRD notices
GRANT_KEYWORDS = [
    "grant", "technical cooperation", "technical assistance",
    "capacity building", "advisory", "TC project",
    "donor-funded", "donor funded", "SSF",
    "small business support", "investment grant",
    "green economy", "GEFF", "climate",
    "women in business", "know-how",
]

# EBRD notice types that indicate grants/TC
GRANT_NOTICE_TYPES = [
    "technical cooperation",
    "consultancy",
    "advisory services",
    "individual consultant",
    "grant",
    "call for expressions of interest",
]


def _detect_country(text: str) -> tuple[str, str]:
    """Detect EBRD MENA country from text."""
    text_lower = text.lower()
    for keyword, (name, code) in EBRD_MENA.items():
        if keyword in text_lower:
            return code, name
    return "", ""


def _is_grant_related(text: str) -> bool:
    """Check if text indicates a grant/TC opportunity."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in GRANT_KEYWORDS)


def _parse_ecepp_date(date_str: str) -> str:
    """Parse ECEPP date format like '09/03/2026 09:29UK Time'."""
    if not date_str or date_str.strip() == "N/A":
        return ""
    match = re.match(r"(\d{2}/\d{2}/\d{4})", date_str.strip())
    if match:
        parsed = parse_date(match.group(1))
        if parsed:
            return parsed
    return ""


def _scrape_ecepp() -> list[dict]:
    """Scrape ECEPP portal for grant/TC notices in MENA."""
    grants: list[dict] = []

    try:
        resp = requests.get(ECEPP_SEARCH_URL, headers=BROWSER_HEADERS, timeout=60)
        if resp.status_code != 200:
            logger.warning(f"ECEPP: HTTP {resp.status_code}")
            return grants

        soup = BeautifulSoup(resp.text, "lxml")
        table = soup.select_one("table.basic-table")
        if not table:
            logger.warning("ECEPP: Could not find basic-table element")
            return grants

        rows = table.select("tr")
        if len(rows) < 2:
            logger.warning("ECEPP: Table has no data rows")
            return grants

        logger.info(f"ECEPP: {len(rows) - 1} total notices, filtering for MENA grants...")

        for row in rows[1:]:
            cells = row.select("td")
            if len(cells) < 6:
                continue

            # Full row text
            full_text = " ".join(c.get_text(strip=True) for c in cells)
            full_lower = full_text.lower()

            # Must be MENA
            country_code, country_name = _detect_country(full_text)
            if not country_code:
                continue

            # Extract cells
            title_cell = cells[0]
            notice_type = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            procurement_title = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            published_raw = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            closing_raw = cells[4].get_text(strip=True) if len(cells) > 4 else ""
            current_state = cells[5].get_text(strip=True) if len(cells) > 5 else ""

            title_text = title_cell.get_text(strip=True)
            if not title_text or len(title_text) < 5:
                continue

            # Check if grant/TC related
            combined = f"{title_text} {notice_type} {procurement_title}"
            is_grant = _is_grant_related(combined)
            is_grant_type = any(
                gt in notice_type.lower() for gt in GRANT_NOTICE_TYPES
            )

            if not is_grant and not is_grant_type:
                continue

            # Link
            link_el = title_cell.select_one("a[href]")
            href = ""
            if link_el:
                href = link_el.get("href", "")
                if href and not href.startswith("http"):
                    href = ECEPP_NOTICE_BASE + href

            # Dates
            pub_date = _parse_ecepp_date(published_raw)
            deadline = _parse_ecepp_date(closing_raw)

            # Source reference
            source_ref = ""
            if href:
                ref_match = re.search(r"displayNoticeId=(\d+)", href)
                if ref_match:
                    source_ref = f"ECEPP-{ref_match.group(1)}"
            if not source_ref:
                source_ref = title_text[:60]

            # Status
            status = "open"
            state_lower = current_state.lower()
            if "closed" in state_lower or "awarded" in state_lower:
                status = "closed"

            # Classify
            sector = classify_sector(combined)
            grant_type = classify_grant_type(combined)

            # Description
            desc_parts = []
            if procurement_title and procurement_title != "N/A":
                desc_parts.append(f"Project: {procurement_title}")
            if notice_type:
                desc_parts.append(f"Type: {notice_type}")
            if current_state:
                desc_parts.append(f"State: {current_state}")
            description = ". ".join(desc_parts) if desc_parts else title_text

            grant = {
                "id": generate_grant_id("ebrd_ecepp", source_ref),
                "title": title_text,
                "title_ar": "",
                "title_fr": "",
                "source": "ebrd",
                "source_ref": source_ref,
                "source_url": href or ECEPP_SEARCH_URL,
                "funding_organization": "European Bank for Reconstruction and Development",
                "funding_organization_ar": "البنك الأوروبي لإعادة الإعمار والتنمية",
                "funding_organization_fr": "Banque européenne pour la reconstruction et le développement",
                "funding_amount": 0,
                "funding_amount_max": 0,
                "currency": "EUR",
                "grant_type": grant_type,
                "country": country_name,
                "country_code": country_code,
                "region": "MENA",
                "sector": sector,
                "sectors": [sector],
                "eligibility_criteria": notice_type or "",
                "eligibility_countries": [country_code],
                "description": description[:2000],
                "description_ar": "",
                "description_fr": "",
                "application_deadline": deadline,
                "publish_date": pub_date,
                "status": status,
                "contact_info": "",
                "documents_url": href or "",
                "tags": ["EBRD", "ECEPP", notice_type] if notice_type else ["EBRD", "ECEPP"],
                "metadata": {
                    "notice_type": notice_type,
                    "procurement_title": procurement_title,
                    "current_state": current_state,
                    "source_portal": "ECEPP",
                },
            }
            grants.append(grant)

    except Exception as e:
        logger.error(f"ECEPP scraper error: {e}")

    return grants


def _scrape_ebrd_main_page(url: str) -> list[dict]:
    """Scrape the main EBRD procurement/notices page for grant opportunities."""
    grants: list[dict] = []

    try:
        resp = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"EBRD main page {url}: HTTP {resp.status_code}")
            return grants

        soup = BeautifulSoup(resp.text, "lxml")

        # Strategy 1: Look for procurement listings
        item_selectors = [
            ".procurement-item",
            ".notice-item",
            ".listing-item",
            ".content-listing li",
            "article",
            ".views-row",
            ".view-content > div",
            "table.data-table tbody tr",
            ".card",
        ]

        for selector in item_selectors:
            items = soup.select(selector)
            if not items or len(items) < 2:
                continue

            logger.info(f"EBRD main: {len(items)} items with '{selector}' on {url}")

            for item in items:
                # Title
                title_el = item.select_one(
                    "h2 a, h3 a, h4 a, a.title, "
                    ".title, .notice-title, td:first-child a"
                )
                if not title_el:
                    title_el = item.select_one("h2, h3, h4")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                if len(title) < 10:
                    continue

                full_text = item.get_text()

                # Must be MENA
                country_code, country_name = _detect_country(full_text + " " + title)
                if not country_code:
                    continue

                # Must be grant/TC related
                if not _is_grant_related(full_text):
                    continue

                # Link
                a_tag = item.select_one("a[href]")
                href = ""
                if a_tag:
                    href = a_tag.get("href", "")
                    if href and not href.startswith("http"):
                        href = f"https://www.ebrd.com{href}"

                # Date
                date_el = item.select_one(
                    ".date, time, .datetime, [class*='date']"
                )
                pub_date = ""
                if date_el:
                    pub_date = parse_date(date_el.get_text(strip=True)) or ""

                # Deadline
                deadline_el = item.select_one(
                    ".deadline, [class*='deadline'], [class*='closing']"
                )
                deadline = ""
                if deadline_el:
                    deadline = parse_date(deadline_el.get_text(strip=True)) or ""

                # Classify
                combined = f"{title} {full_text[:300]}"
                sector = classify_sector(combined)
                grant_type = classify_grant_type(combined)

                ref = title[:80]
                if href:
                    path = href.rstrip("/").split("/")[-1]
                    if path:
                        ref = path

                grant = {
                    "id": generate_grant_id("ebrd_main", ref),
                    "title": title,
                    "title_ar": "",
                    "title_fr": "",
                    "source": "ebrd",
                    "source_ref": ref,
                    "source_url": href or url,
                    "funding_organization": "European Bank for Reconstruction and Development",
                    "funding_organization_ar": "البنك الأوروبي لإعادة الإعمار والتنمية",
                    "funding_organization_fr": "Banque européenne pour la reconstruction et le développement",
                    "funding_amount": 0,
                    "funding_amount_max": 0,
                    "currency": "EUR",
                    "grant_type": grant_type,
                    "country": country_name,
                    "country_code": country_code,
                    "region": "MENA",
                    "sector": sector,
                    "sectors": [sector],
                    "eligibility_criteria": "",
                    "eligibility_countries": [country_code],
                    "description": title,
                    "description_ar": "",
                    "description_fr": "",
                    "application_deadline": deadline,
                    "publish_date": pub_date,
                    "status": "open",
                    "contact_info": "",
                    "documents_url": href or "",
                    "tags": ["EBRD", "technical_cooperation"],
                    "metadata": {
                        "source_portal": "ebrd_main",
                    },
                }
                grants.append(grant)

            if grants:
                break  # Found working selector

    except Exception as e:
        logger.error(f"EBRD main page error on {url}: {e}")

    return grants


def _scrape_ebrd_tc_projects() -> list[dict]:
    """Scrape EBRD technical cooperation projects page."""
    grants: list[dict] = []

    tc_urls = [
        "https://www.ebrd.com/work-with-us/procurement.html",
        "https://www.ebrd.com/work-with-us/procurement/notices.html",
    ]

    for url in tc_urls:
        try:
            resp = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.warning(f"EBRD TC page {url}: HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Find all links that mention MENA countries + grant/TC
            all_links = soup.select("a[href]")

            for link in all_links:
                text = link.get_text(strip=True)
                href = link.get("href", "")

                if len(text) < 15:
                    continue

                # Check for MENA country
                country_code, country_name = _detect_country(text)
                if not country_code:
                    continue

                # Check for grant/TC keywords
                if not _is_grant_related(text):
                    continue

                if href and not href.startswith("http"):
                    href = f"https://www.ebrd.com{href}"

                ref = text[:80]
                sector = classify_sector(text)
                grant_type = classify_grant_type(text)

                grant = {
                    "id": generate_grant_id("ebrd_tc", ref),
                    "title": text,
                    "title_ar": "",
                    "title_fr": "",
                    "source": "ebrd",
                    "source_ref": ref,
                    "source_url": href or url,
                    "funding_organization": "European Bank for Reconstruction and Development",
                    "funding_organization_ar": "البنك الأوروبي لإعادة الإعمار والتنمية",
                    "funding_organization_fr": "Banque européenne pour la reconstruction et le développement",
                    "funding_amount": 0,
                    "funding_amount_max": 0,
                    "currency": "EUR",
                    "grant_type": grant_type,
                    "country": country_name,
                    "country_code": country_code,
                    "region": "MENA",
                    "sector": sector,
                    "sectors": [sector],
                    "eligibility_criteria": "",
                    "eligibility_countries": [country_code],
                    "description": text,
                    "description_ar": "",
                    "description_fr": "",
                    "application_deadline": "",
                    "publish_date": "",
                    "status": "open",
                    "contact_info": "",
                    "documents_url": href or "",
                    "tags": ["EBRD", "technical_cooperation"],
                    "metadata": {
                        "source_portal": "ebrd_tc",
                    },
                }
                grants.append(grant)

        except Exception as e:
            logger.error(f"EBRD TC page error on {url}: {e}")

        time.sleep(1.0)

    return grants


def scrape() -> list[dict]:
    """Scrape EBRD for MENA grant/technical cooperation opportunities."""
    logger.info("Starting EBRD grants scraper...")

    all_grants: list[dict] = []
    seen_refs: set[str] = set()

    # Phase 1: ECEPP portal (primary source)
    ecepp_grants = _scrape_ecepp()
    for g in ecepp_grants:
        if g["source_ref"] not in seen_refs:
            seen_refs.add(g["source_ref"])
            all_grants.append(g)
    logger.info(f"Phase 1 — ECEPP: {len(ecepp_grants)} grant notices")

    time.sleep(1.0)

    # Phase 2: Main procurement pages
    for url in [EBRD_PROCUREMENT_URL, EBRD_NOTICES_URL]:
        main_grants = _scrape_ebrd_main_page(url)
        new_count = 0
        for g in main_grants:
            if g["source_ref"] not in seen_refs:
                seen_refs.add(g["source_ref"])
                all_grants.append(g)
                new_count += 1
        logger.info(f"Phase 2 — {url}: {new_count} new grants")
        time.sleep(1.0)

    # Phase 3: Technical cooperation projects
    tc_grants = _scrape_ebrd_tc_projects()
    new_tc = 0
    for g in tc_grants:
        if g["source_ref"] not in seen_refs:
            seen_refs.add(g["source_ref"])
            all_grants.append(g)
            new_tc += 1
    logger.info(f"Phase 3 — TC projects: {new_tc} new grants")

    logger.info(f"EBRD total grants: {len(all_grants)}")

    if not all_grants:
        logger.warning(
            "EBRD: No MENA grant/TC notices found. "
            "Site structure may have changed."
        )

    return all_grants


if __name__ == "__main__":
    results = scrape()
    save_grants(results, "ebrd")
    print(f"Scraped {len(results)} grants from EBRD")
