"""
Grant scraper for Islamic Development Bank (IsDB).
Source: https://www.isdb.org/projects

Scrapes the IsDB projects page for MENA-region grant opportunities.
IsDB covers all OIC member states, including all MENA countries.
Uses requests + BeautifulSoup to parse project listings.

Also tries the IsDB API endpoint for structured project data.
"""

import re
import requests
import logging
import time
from bs4 import BeautifulSoup
from config import (
    HEADERS, MENA_COUNTRIES, MENA_COUNTRIES_AR, MENA_COUNTRIES_FR,
)
from base_scraper import (
    generate_grant_id, classify_sector, classify_grant_type,
    parse_date, parse_amount, save_grants,
)

logger = logging.getLogger("grants_isdb")

ISDB_BASE = "https://www.isdb.org"

# Primary scraping targets
ISDB_PROJECTS_URL = "https://www.isdb.org/projects"
ISDB_PROJECT_LIST_URLS = [
    "https://www.isdb.org/projects",
    "https://www.isdb.org/projects?page=1",
    "https://www.isdb.org/projects?page=2",
    "https://www.isdb.org/projects?page=3",
    "https://www.isdb.org/projects?page=4",
    "https://www.isdb.org/projects?page=5",
    "https://www.isdb.org/projects?page=6",
    "https://www.isdb.org/projects?page=7",
    "https://www.isdb.org/projects?page=8",
    "https://www.isdb.org/projects?page=9",
    "https://www.isdb.org/projects?page=10",
]

# Browser-like headers for IsDB (they may block scrapers)
ISDB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8,fr;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.isdb.org/",
}

# Reverse lookup: country name → ISO code
_NAME_TO_CODE: dict[str, str] = {v.lower(): k for k, v in MENA_COUNTRIES.items()}
_NAME_TO_CODE.update({
    "united arab emirates": "AE",
    "uae": "AE",
    "kingdom of saudi arabia": "SA",
    "ksa": "SA",
    "state of palestine": "PS",
    "palestine, state of": "PS",
    "republic of iraq": "IQ",
    "arab republic of egypt": "EG",
    "hashemite kingdom of jordan": "JO",
    "republic of tunisia": "TN",
    "people's democratic republic of algeria": "DZ",
    "sultanate of oman": "OM",
    "state of kuwait": "KW",
    "kingdom of bahrain": "BH",
    "state of qatar": "QA",
    "republic of sudan": "SD",
    "republic of yemen": "YE",
    "kingdom of morocco": "MA",
    "islamic republic of mauritania": "MR",
})


def _detect_country(text: str) -> tuple[str, str]:
    """Detect MENA country from text. Returns (code, name) or ("", "")."""
    text_lower = text.lower()
    for name, code in _NAME_TO_CODE.items():
        if name in text_lower:
            return code, MENA_COUNTRIES.get(code, "")
    return "", ""


def _clean_amount(text: str) -> float:
    """Parse monetary amounts from IsDB display text."""
    if not text:
        return 0.0
    # Remove currency symbols and labels
    cleaned = re.sub(r"[A-Za-z$€£¥]", "", text)
    cleaned = cleaned.replace(",", "").replace(" ", "").strip()
    # Handle million/billion suffixes
    if "million" in text.lower() or "m" in text.lower():
        try:
            return float(re.sub(r"[^\d.]", "", cleaned)) * 1_000_000
        except ValueError:
            pass
    if "billion" in text.lower() or "b" in text.lower():
        try:
            return float(re.sub(r"[^\d.]", "", cleaned)) * 1_000_000_000
        except ValueError:
            pass
    return parse_amount(cleaned)


def _scrape_projects_page(url: str, session: requests.Session) -> list[dict]:
    """Scrape a single IsDB projects page and return raw project dicts."""
    raw_projects: list[dict] = []

    try:
        resp = session.get(url, headers=ISDB_HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"IsDB {url}: HTTP {resp.status_code}")
            return raw_projects

        soup = BeautifulSoup(resp.text, "lxml")

        # Strategy 1: Look for project cards (typical Drupal view)
        card_selectors = [
            ".views-row",
            ".node--type-project",
            ".project-card",
            ".view-projects .views-row",
            "article.node--type-project",
            ".view-content > div",
            ".card",
            ".project-item",
        ]

        for selector in card_selectors:
            cards = soup.select(selector)
            if not cards or len(cards) < 2:
                continue

            logger.info(f"IsDB: {len(cards)} items with '{selector}' on {url}")

            for card in cards:
                project: dict = {}

                # Title
                title_el = card.select_one(
                    "h2 a, h3 a, h4 a, .title a, "
                    ".field--name-title a, .card-title a, "
                    "a.project-title"
                )
                if not title_el:
                    title_el = card.select_one("h2, h3, h4, .title, .card-title")
                if not title_el:
                    continue
                project["title"] = title_el.get_text(strip=True)
                if len(project["title"]) < 10:
                    continue

                # Link
                a_tag = card.select_one("a[href]")
                if a_tag:
                    href = a_tag.get("href", "")
                    if href and not href.startswith("http"):
                        href = f"{ISDB_BASE}{href}"
                    project["url"] = href
                else:
                    project["url"] = ""

                # Country
                country_el = card.select_one(
                    ".field--name-field-country, .country, "
                    ".field-country, .location, "
                    "[class*='country']"
                )
                if country_el:
                    project["country_text"] = country_el.get_text(strip=True)
                else:
                    project["country_text"] = card.get_text()

                # Sector
                sector_el = card.select_one(
                    ".field--name-field-sector, .sector, "
                    ".field-sector, [class*='sector']"
                )
                project["sector_text"] = (
                    sector_el.get_text(strip=True) if sector_el else ""
                )

                # Amount
                amount_el = card.select_one(
                    ".field--name-field-approval-amount, "
                    ".field--name-field-amount, .amount, "
                    ".field-amount, [class*='amount'], "
                    "[class*='budget']"
                )
                project["amount_text"] = (
                    amount_el.get_text(strip=True) if amount_el else ""
                )

                # Status
                status_el = card.select_one(
                    ".field--name-field-status, .status, "
                    ".field-status, [class*='status']"
                )
                project["status_text"] = (
                    status_el.get_text(strip=True) if status_el else ""
                )

                # Date
                date_el = card.select_one(
                    ".date, time, .field--name-field-date, "
                    ".field--name-field-approval-date, .datetime, "
                    "[class*='date']"
                )
                project["date_text"] = (
                    date_el.get_text(strip=True) if date_el else ""
                )

                # Description snippet
                desc_el = card.select_one(
                    ".field--name-body, .description, "
                    ".summary, .teaser, p"
                )
                project["description"] = (
                    desc_el.get_text(strip=True)[:500] if desc_el else ""
                )

                raw_projects.append(project)

            if raw_projects:
                break  # Found working selector

        # Strategy 2: Table-based layout
        if not raw_projects:
            tables = soup.select("table")
            for table in tables:
                rows = table.select("tbody tr, tr")
                if len(rows) < 2:
                    continue

                logger.info(f"IsDB: {len(rows)} table rows on {url}")

                for row in rows:
                    cells = row.select("td")
                    if len(cells) < 2:
                        continue

                    title_text = cells[0].get_text(strip=True)
                    if len(title_text) < 10:
                        continue

                    a_tag = cells[0].select_one("a[href]")
                    href = ""
                    if a_tag:
                        href = a_tag.get("href", "")
                        if href and not href.startswith("http"):
                            href = f"{ISDB_BASE}{href}"

                    project = {
                        "title": title_text,
                        "url": href,
                        "country_text": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                        "sector_text": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                        "amount_text": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                        "status_text": cells[4].get_text(strip=True) if len(cells) > 4 else "",
                        "date_text": cells[5].get_text(strip=True) if len(cells) > 5 else "",
                        "description": "",
                    }
                    raw_projects.append(project)

                if raw_projects:
                    break

    except Exception as e:
        logger.error(f"IsDB scrape error on {url}: {e}")

    return raw_projects


def _scrape_project_detail(url: str, session: requests.Session) -> dict:
    """Scrape additional details from an individual IsDB project page."""
    details: dict = {}
    if not url:
        return details

    try:
        resp = session.get(url, headers=ISDB_HEADERS, timeout=20)
        if resp.status_code != 200:
            return details

        soup = BeautifulSoup(resp.text, "lxml")

        # Description
        desc_el = soup.select_one(
            ".field--name-body, .project-description, "
            ".field--name-field-description, article .content p"
        )
        if desc_el:
            details["description"] = desc_el.get_text(strip=True)[:2000]

        # Amount
        amount_el = soup.select_one(
            ".field--name-field-approval-amount, "
            ".field--name-field-total-amount, "
            "[class*='amount']"
        )
        if amount_el:
            details["amount_text"] = amount_el.get_text(strip=True)

        # Country
        country_el = soup.select_one(
            ".field--name-field-country, [class*='country']"
        )
        if country_el:
            details["country_text"] = country_el.get_text(strip=True)

        # Sector
        sector_el = soup.select_one(
            ".field--name-field-sector, [class*='sector']"
        )
        if sector_el:
            details["sector_text"] = sector_el.get_text(strip=True)

        # Dates
        for cls in [
            ".field--name-field-approval-date",
            ".field--name-field-start-date",
            ".field--name-field-end-date",
        ]:
            el = soup.select_one(cls)
            if el:
                label = cls.replace(".field--name-field-", "").replace("-", "_")
                details[label] = el.get_text(strip=True)

    except Exception as e:
        logger.debug(f"IsDB detail scrape error {url}: {e}")

    return details


def scrape() -> list[dict]:
    """Scrape IsDB projects for MENA grant opportunities."""
    logger.info("Starting IsDB grants scraper...")

    session = requests.Session()
    grants: list[dict] = []
    seen_titles: set[str] = set()

    # Phase 1: Scrape all project list pages
    all_raw: list[dict] = []
    for url in ISDB_PROJECT_LIST_URLS:
        raw = _scrape_projects_page(url, session)
        all_raw.extend(raw)
        logger.info(f"IsDB page {url}: {len(raw)} raw projects")
        if not raw:
            break  # No more pages
        time.sleep(1.0)

    logger.info(f"IsDB: {len(all_raw)} total raw projects from list pages")

    # Phase 2: Process each raw project
    for raw in all_raw:
        title = raw.get("title", "")
        if not title or title in seen_titles:
            continue

        # Detect country
        country_text = raw.get("country_text", "")
        country_code, country_name = _detect_country(
            country_text + " " + title
        )

        if not country_code:
            # Skip non-MENA projects
            continue

        seen_titles.add(title)

        # Optionally fetch detail page for richer data
        detail_url = raw.get("url", "")
        details: dict = {}
        if detail_url and len(grants) < 200:
            # Rate-limit detail page scraping
            details = _scrape_project_detail(detail_url, session)
            time.sleep(0.5)

        # Merge data
        description = (
            details.get("description", "")
            or raw.get("description", "")
            or title
        )

        amount_text = details.get("amount_text", "") or raw.get("amount_text", "")
        funding_amount = _clean_amount(amount_text)

        sector_text = (
            details.get("sector_text", "")
            or raw.get("sector_text", "")
            or ""
        )

        combined_text = f"{title} {description} {sector_text}"
        sector = classify_sector(combined_text)
        grant_type = classify_grant_type(combined_text)

        # Multiple sectors
        sectors = [sector]
        if sector_text:
            alt_sector = classify_sector(sector_text)
            if alt_sector != sector:
                sectors.append(alt_sector)

        # Status
        status_text = raw.get("status_text", "").lower()
        if "closed" in status_text or "completed" in status_text:
            status = "closed"
        elif "cancelled" in status_text:
            status = "closed"
        else:
            status = "open"

        # Date
        date_text = raw.get("date_text", "")
        approval_date = parse_date(date_text) or ""

        # Reference from URL
        ref = ""
        if detail_url:
            # Extract project ID from URL like /projects/detail/123
            match = re.search(r"/projects?/(?:detail/)?(\d+)", detail_url)
            if match:
                ref = match.group(1)
            else:
                # Use URL path as ref
                ref = detail_url.rstrip("/").split("/")[-1]
        if not ref:
            ref = title[:80]

        grant = {
            "id": generate_grant_id("isdb", ref),
            "title": title,
            "title_ar": "",
            "title_fr": "",
            "source": "isdb",
            "source_ref": ref,
            "source_url": detail_url or ISDB_PROJECTS_URL,
            "funding_organization": "Islamic Development Bank",
            "funding_organization_ar": "البنك الإسلامي للتنمية",
            "funding_organization_fr": "Banque islamique de développement",
            "funding_amount": funding_amount,
            "funding_amount_max": 0,
            "currency": "USD",
            "grant_type": grant_type,
            "country": country_name,
            "country_code": country_code,
            "region": "MENA",
            "sector": sector,
            "sectors": sectors,
            "eligibility_criteria": "OIC member state project",
            "eligibility_countries": [country_code],
            "description": description[:2000],
            "description_ar": "",
            "description_fr": "",
            "application_deadline": "",
            "publish_date": approval_date,
            "status": status,
            "contact_info": "",
            "documents_url": detail_url or "",
            "tags": ["OIC", "IsDB"],
            "metadata": {
                "sector_text": sector_text,
                "amount_text": amount_text,
                "status_text": raw.get("status_text", ""),
            },
        }
        grants.append(grant)

    logger.info(f"IsDB total: {len(grants)} MENA grants")
    return grants


if __name__ == "__main__":
    results = scrape()
    save_grants(results, "isdb")
    print(f"Scraped {len(results)} grants from IsDB")
