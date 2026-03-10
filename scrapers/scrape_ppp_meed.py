"""
Scraper for MEED Projects, Zawya Projects Monitor, and Gulf business news.

Sources:
1. MEED Projects: https://www.meed.com/projects
   - Tracks $3.7T+ of projects across GCC
   - May be paywalled; scrape publicly accessible content
2. Zawya Projects Monitor: https://www.zawya.com/en/projects
   - Free public project tracker for MENA region
   - Project cards with name, country, sector, value, stage
3. Gulf Business: https://gulfbusiness.com
   - Public news articles about mega-projects in GCC

Focus: GCC mega-projects (Saudi, UAE, Qatar, Kuwait, Bahrain, Oman)
with extension to broader MENA.
"""

import json
import logging
import re
import time
from typing import Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config import (
    HEADERS,
    MENA_COUNTRIES,
    MENA_COUNTRIES_AR,
    MENA_COUNTRIES_FR,
)
from base_scraper import (
    classify_sector,
    classify_ppp_contract,
    generate_ppp_id,
    parse_date,
    parse_amount,
    save_ppp_projects,
)

logger = logging.getLogger("ppp_meed")

# ---------------------------------------------------------------------------
# URL constants
# ---------------------------------------------------------------------------
MEED_BASE = "https://www.meed.com"
MEED_PROJECTS_URL = "https://www.meed.com/projects"

ZAWYA_BASE = "https://www.zawya.com"
ZAWYA_PROJECTS_URL = "https://www.zawya.com/en/projects"
ZAWYA_API_BASE = "https://www.zawya.com/api"

GULF_BIZ_BASE = "https://gulfbusiness.com"

# GCC country codes (primary focus)
GCC_CODES = {"SA", "AE", "QA", "KW", "BH", "OM"}

# Broader MENA for Zawya
MENA_CODES = set(MENA_COUNTRIES.keys())

# Country name patterns for extraction from text
COUNTRY_PATTERNS = {}
for code, name in MENA_COUNTRIES.items():
    COUNTRY_PATTERNS[name.lower()] = code
# Additional aliases
COUNTRY_PATTERNS.update({
    "saudi": "SA", "saudi arabia": "SA", "ksa": "SA", "kingdom": "SA",
    "uae": "AE", "emirates": "AE", "dubai": "AE", "abu dhabi": "AE",
    "sharjah": "AE", "ajman": "AE", "ras al khaimah": "AE",
    "qatar": "QA", "doha": "QA",
    "kuwait": "KW",
    "bahrain": "BH", "manama": "BH",
    "oman": "OM", "muscat": "OM",
    "egypt": "EG", "cairo": "EG",
    "morocco": "MA", "casablanca": "MA", "rabat": "MA",
    "jordan": "JO", "amman": "JO",
    "iraq": "IQ", "baghdad": "IQ",
    "tunisia": "TN",
    "algeria": "DZ",
    "libya": "LY",
    "lebanon": "LB", "beirut": "LB",
    "yemen": "YE",
    "sudan": "SD",
    "palestine": "PS",
    "neom": "SA", "riyadh": "SA", "jeddah": "SA",
    "lusail": "QA",
})

# Stage patterns for project tracker data
STAGE_PATTERNS = {
    "design": "feasibility",
    "study": "feasibility",
    "concept": "identification",
    "planning": "planning",
    "tender": "tender",
    "bid": "tender",
    "pre-qualification": "tender",
    "shortlisted": "shortlisted",
    "awarded": "awarded",
    "award": "awarded",
    "under construction": "construction",
    "construction": "construction",
    "execution": "construction",
    "building": "construction",
    "operational": "operational",
    "completed": "operational",
    "on hold": "planning",
    "cancelled": "cancelled",
    "suspended": "cancelled",
}


def _detect_country(text: str) -> Optional[str]:
    """Detect MENA country from text content."""
    if not text:
        return None
    lower = text.lower()
    for pattern, code in sorted(COUNTRY_PATTERNS.items(), key=lambda x: -len(x[0])):
        if pattern in lower:
            return code
    return None


def _map_stage(raw: str) -> str:
    """Map raw stage text to our taxonomy."""
    if not raw:
        return "planning"
    lower = raw.lower().strip()
    for pattern, stage in STAGE_PATTERNS.items():
        if pattern in lower:
            return stage
    return "planning"


def _extract_value_from_text(text: str) -> float:
    """Extract monetary value from text like '$5.2 billion' or 'SAR 2.5bn'."""
    if not text:
        return 0

    patterns = [
        # $5.2 billion / $5.2bn / $5.2B
        r'[\$US]{1,3}\s*([\d,.]+)\s*(billion|bn|b)\b',
        r'[\$US]{1,3}\s*([\d,.]+)\s*(million|mn|m)\b',
        r'[\$US]{1,3}\s*([\d,.]+)\s*(trillion|tn|t)\b',
        # 5.2 billion dollars
        r'([\d,.]+)\s*(billion|bn)\s*(?:dollars?|usd)',
        r'([\d,.]+)\s*(million|mn)\s*(?:dollars?|usd)',
        # SAR/AED/QAR values
        r'(?:SAR|AED|QAR|KWD|BHD|OMR)\s*([\d,.]+)\s*(billion|bn|b)\b',
        r'(?:SAR|AED|QAR|KWD|BHD|OMR)\s*([\d,.]+)\s*(million|mn|m)\b',
        # Plain dollar amounts
        r'\$([\d,.]+)\s*(billion|bn|b|million|mn|m|trillion|tn|t)\b',
    ]

    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            amount_str = groups[0].replace(",", "")
            unit = groups[1].lower() if len(groups) > 1 else ""

            try:
                amount = float(amount_str)
            except ValueError:
                continue

            if unit in ("billion", "bn", "b"):
                return amount * 1_000_000_000
            elif unit in ("million", "mn", "m"):
                return amount * 1_000_000
            elif unit in ("trillion", "tn", "t"):
                return amount * 1_000_000_000_000
            return amount

    # Try plain number extraction as last resort
    match = re.search(r'\$([\d,.]+)', text)
    if match:
        return parse_amount(match.group(1))

    return 0


def _build_ppp_record(
    source: str,
    source_ref: str,
    name: str,
    country_code: str,
    sector: str = "construction",
    subsector: str = "",
    stage: str = "planning",
    contract_type: str = "concession",
    investment_value: float = 0,
    currency: str = "USD",
    government_entity: str = "",
    sponsors: list = None,
    description: str = "",
    source_url: str = "",
    metadata: dict = None,
) -> dict:
    """Build a standardized PPP project record."""
    country_name = MENA_COUNTRIES.get(country_code, "")

    tags = [sector] if sector else []
    if investment_value >= 1_000_000_000:
        tags.append("mega_project")
    if investment_value >= 500_000_000:
        tags.append("large_project")
    name_lower = name.lower()
    for kw in ["neom", "the line", "oxagon", "trojena", "lusail", "expo", "world cup"]:
        if kw in name_lower:
            tags.append("flagship_project")
            break

    return {
        "id": generate_ppp_id(source, source_ref),
        "name": name,
        "name_ar": "",
        "name_fr": "",
        "source": source,
        "source_ref": source_ref,
        "source_url": source_url,
        "country": country_name,
        "country_code": country_code,
        "region": "MENA",
        "sector": sector,
        "subsector": subsector,
        "stage": stage,
        "contract_type": contract_type,
        "investment_value": investment_value,
        "debt_value": 0,
        "equity_value": 0,
        "currency": currency,
        "government_entity": government_entity,
        "government_entity_ar": "",
        "government_entity_fr": "",
        "sponsors": sponsors or [],
        "lenders": [],
        "advisors": [],
        "description": description,
        "description_ar": "",
        "description_fr": "",
        "financial_close_date": None,
        "contract_duration_years": None,
        "tender_deadline": None,
        "award_date": None,
        "tags": list(set(tags)),
        "metadata": metadata or {},
    }


# =========================================================================
# Strategy 1: Zawya Projects Monitor (primary — publicly accessible)
# =========================================================================

def _scrape_zawya_projects() -> list[dict]:
    """
    Scrape Zawya Projects Monitor for MENA project listings.
    Zawya provides publicly accessible project tracking data.
    """
    projects = []

    # Try the Zawya API first
    api_projects = _scrape_zawya_api()
    if api_projects:
        projects.extend(api_projects)

    # Then scrape the public project pages
    page_projects = _scrape_zawya_pages()
    projects.extend(page_projects)

    return projects


def _scrape_zawya_api() -> list[dict]:
    """Try Zawya internal API for project data."""
    projects = []

    api_endpoints = [
        f"{ZAWYA_API_BASE}/projects/list",
        f"{ZAWYA_API_BASE}/v1/projects",
        f"{ZAWYA_BASE}/en/projects/api/list",
    ]

    for endpoint in api_endpoints:
        for page in range(1, 6):  # Up to 5 pages
            try:
                params = {
                    "page": page,
                    "pageSize": 50,
                    "region": "mena",
                    "sort": "value",
                    "order": "desc",
                }
                resp = requests.get(endpoint, params=params, headers=HEADERS, timeout=20)
                if resp.status_code != 200:
                    break

                data = resp.json()
                items = data if isinstance(data, list) else data.get("data", data.get("projects", data.get("results", [])))

                if not isinstance(items, list) or not items:
                    break

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    name = item.get("name") or item.get("title") or item.get("project_name") or ""
                    if not name:
                        continue

                    country_raw = item.get("country") or item.get("location") or ""
                    country_code = _detect_country(country_raw) or _detect_country(name)
                    if not country_code or country_code not in MENA_COUNTRIES:
                        continue

                    value = parse_amount(item.get("value") or item.get("cost") or item.get("investment") or 0)
                    sector_raw = item.get("sector") or item.get("category") or ""
                    stage_raw = item.get("status") or item.get("stage") or ""
                    desc = item.get("description") or item.get("summary") or ""

                    ref = str(item.get("id") or item.get("project_id") or name[:80])

                    projects.append(_build_ppp_record(
                        source="zawya_projects",
                        source_ref=f"zawya-{ref}",
                        name=name,
                        country_code=country_code,
                        sector=classify_sector(f"{name} {sector_raw} {desc}"),
                        stage=_map_stage(stage_raw),
                        contract_type=classify_ppp_contract(f"{name} {desc}"),
                        investment_value=value,
                        description=desc[:500] if desc else f"Zawya Projects: {name}. Value: ${value:,.0f}.",
                        source_url=f"{ZAWYA_BASE}/en/projects/{ref}" if ref.isdigit() else "",
                        metadata={
                            "raw_sector": sector_raw,
                            "raw_stage": stage_raw,
                            "raw_country": country_raw,
                        },
                    ))

                time.sleep(0.3)

            except requests.exceptions.JSONDecodeError:
                break  # Not a JSON API
            except Exception as e:
                logger.debug(f"Zawya API {endpoint} page {page}: {e}")
                break

        if projects:
            logger.info(f"Zawya API: {len(projects)} projects from {endpoint}")
            break  # Successful endpoint found

    return projects


def _scrape_zawya_pages() -> list[dict]:
    """Scrape Zawya project listing pages."""
    projects = []

    urls = [
        f"{ZAWYA_PROJECTS_URL}",
        f"{ZAWYA_PROJECTS_URL}?page=1",
        f"{ZAWYA_PROJECTS_URL}?page=2",
        f"{ZAWYA_PROJECTS_URL}?page=3",
        f"{ZAWYA_BASE}/en/projects/gcc",
        f"{ZAWYA_BASE}/en/projects/saudi-arabia",
        f"{ZAWYA_BASE}/en/projects/uae",
        f"{ZAWYA_BASE}/en/projects/qatar",
    ]

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                logger.debug(f"Zawya page {url}: HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Parse project cards
            for card in soup.select(
                ".project-card, .project-item, .article-card, "
                ".story-card, article, .card, .list-item, "
                "[class*='project'], [class*='Project']"
            ):
                parsed = _parse_zawya_card(card, url)
                if parsed:
                    projects.append(parsed)

            # Also check for JSON-LD structured data
            for script in soup.select('script[type="application/ld+json"]'):
                try:
                    ld_data = json.loads(script.string or "")
                    if isinstance(ld_data, list):
                        for item in ld_data:
                            parsed = _parse_ld_json_project(item)
                            if parsed:
                                projects.append(parsed)
                    elif isinstance(ld_data, dict):
                        parsed = _parse_ld_json_project(ld_data)
                        if parsed:
                            projects.append(parsed)
                except (json.JSONDecodeError, TypeError):
                    pass

            # Check for embedded JS data
            for script in soup.select("script"):
                text = script.string or ""
                if "projects" in text.lower() and ("{" in text):
                    json_blocks = re.findall(r'(?:projects|data)\s*[:=]\s*(\[.*?\]);', text, re.DOTALL)
                    for block in json_blocks:
                        try:
                            items = json.loads(block)
                            if isinstance(items, list):
                                for item in items:
                                    if isinstance(item, dict):
                                        name = item.get("name") or item.get("title") or ""
                                        if name:
                                            country_code = _detect_country(
                                                item.get("country", "") + " " + name
                                            )
                                            if country_code and country_code in MENA_COUNTRIES:
                                                value = _extract_value_from_text(
                                                    str(item.get("value", "")) + " " + str(item.get("cost", ""))
                                                )
                                                ref = f"zawya-js-{re.sub(r'[^a-z0-9]', '', name.lower())[:30]}"
                                                projects.append(_build_ppp_record(
                                                    source="zawya_projects",
                                                    source_ref=ref,
                                                    name=name,
                                                    country_code=country_code,
                                                    sector=classify_sector(name),
                                                    stage=_map_stage(item.get("status", "")),
                                                    investment_value=value,
                                                    description=f"Zawya: {name}",
                                                    source_url=url,
                                                    metadata={"data_type": "js_extracted"},
                                                ))
                        except (json.JSONDecodeError, TypeError):
                            continue

            time.sleep(0.5)

        except Exception as e:
            logger.debug(f"Zawya page {url}: {e}")

    logger.info(f"Zawya pages: {len(projects)} projects")
    return projects


def _parse_zawya_card(card, page_url: str) -> Optional[dict]:
    """Parse a Zawya project card element."""
    # Title extraction
    title_el = card.select_one("h2, h3, h4, .title, a.title, .headline, .project-name")
    if not title_el:
        return None
    name = title_el.get_text(strip=True)
    if not name or len(name) < 10:
        return None

    # Link
    link = ""
    if title_el.name == "a":
        link = title_el.get("href", "")
    else:
        link_el = card.select_one("a")
        if link_el:
            link = link_el.get("href", "")
    if link and not link.startswith("http"):
        link = f"{ZAWYA_BASE}{link}"

    # Country detection
    location_el = card.select_one(".location, .country, .meta-location, [class*='location']")
    location_text = location_el.get_text(strip=True) if location_el else ""
    country_code = _detect_country(location_text) or _detect_country(name)
    if not country_code or country_code not in MENA_COUNTRIES:
        return None

    # Value extraction
    value_el = card.select_one(".value, .cost, .amount, .price, [class*='value'], [class*='cost']")
    value_text = value_el.get_text(strip=True) if value_el else ""
    value = _extract_value_from_text(value_text) or _extract_value_from_text(card.get_text())

    # Sector
    sector_el = card.select_one(".sector, .category, .tag, [class*='sector']")
    sector_text = sector_el.get_text(strip=True) if sector_el else ""

    # Status/Stage
    status_el = card.select_one(".status, .stage, .phase, [class*='status'], [class*='stage']")
    stage_text = status_el.get_text(strip=True) if status_el else ""

    # Description
    desc_el = card.select_one("p, .description, .summary, .excerpt")
    desc = desc_el.get_text(strip=True)[:500] if desc_el else ""

    ref = f"zawya-{re.sub(r'[^a-z0-9]', '', name.lower())[:40]}"

    return _build_ppp_record(
        source="zawya_projects",
        source_ref=ref,
        name=name,
        country_code=country_code,
        sector=classify_sector(f"{name} {sector_text} {desc}"),
        stage=_map_stage(stage_text),
        contract_type=classify_ppp_contract(f"{name} {desc}"),
        investment_value=value,
        description=desc or f"Zawya Projects: {name}",
        source_url=link or page_url,
        metadata={
            "raw_location": location_text,
            "raw_sector": sector_text,
            "raw_stage": stage_text,
            "raw_value": value_text,
        },
    )


def _parse_ld_json_project(data: dict) -> Optional[dict]:
    """Parse JSON-LD structured data for project info."""
    schema_type = data.get("@type", "")
    if schema_type not in ("Article", "NewsArticle", "Project", "Event", "CreativeWork", "WebPage"):
        return None

    name = data.get("headline") or data.get("name") or ""
    if not name or len(name) < 10:
        return None

    # Must be project-related
    combined = f"{name} {data.get('description', '')}".lower()
    project_keywords = ["project", "construction", "infrastructure", "billion", "million",
                        "develop", "build", "tender", "contract", "award"]
    if not any(kw in combined for kw in project_keywords):
        return None

    country_code = _detect_country(combined)
    if not country_code:
        return None

    value = _extract_value_from_text(combined)
    desc = data.get("description", "")[:500]
    url = data.get("url", "")

    ref = f"zawya-ld-{re.sub(r'[^a-z0-9]', '', name.lower())[:30]}"

    return _build_ppp_record(
        source="zawya_projects",
        source_ref=ref,
        name=name,
        country_code=country_code,
        sector=classify_sector(combined),
        stage=_map_stage(""),
        investment_value=value,
        description=desc or name,
        source_url=url,
        metadata={"data_type": "json_ld"},
    )


# =========================================================================
# Strategy 2: MEED Projects (scrape public content)
# =========================================================================

def _scrape_meed() -> list[dict]:
    """
    Scrape MEED for publicly accessible project data.
    MEED tracks $3.7T+ of projects across GCC.
    May be paywalled but headlines/summaries are often public.
    """
    projects = []

    meed_urls = [
        f"{MEED_PROJECTS_URL}",
        f"{MEED_BASE}/sectors/construction",
        f"{MEED_BASE}/sectors/energy",
        f"{MEED_BASE}/sectors/transport",
        f"{MEED_BASE}/sectors/water",
        f"{MEED_BASE}/latest",
        f"{MEED_BASE}/topic/mega-projects",
        f"{MEED_BASE}/topic/saudi-vision-2030",
        f"{MEED_BASE}/topic/qatar-2030",
    ]

    for url in meed_urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                logger.debug(f"MEED {url}: HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Parse article/project cards
            for card in soup.select(
                "article, .article-card, .project-card, .story, "
                ".card, .teaser, .list-item, [class*='article'], "
                "[class*='project'], .content-item"
            ):
                parsed = _parse_meed_card(card, url)
                if parsed:
                    projects.append(parsed)

            # Look for project data tables
            for table in soup.select("table"):
                rows = table.select("tr")
                if len(rows) < 2:
                    continue

                header_cells = [th.get_text(strip=True).lower() for th in rows[0].select("th, td")]
                for row in rows[1:]:
                    cells = [td.get_text(strip=True) for td in row.select("td")]
                    if len(cells) < 2:
                        continue

                    row_data = dict(zip(header_cells, cells))
                    name = row_data.get("project", "") or row_data.get("name", "") or cells[0]
                    if not name or len(name) < 5:
                        continue

                    country_code = _detect_country(
                        row_data.get("country", "") + " " + row_data.get("location", "") + " " + name
                    )
                    if not country_code:
                        continue

                    value_str = row_data.get("value", "") or row_data.get("cost", "") or row_data.get("budget", "")
                    value = _extract_value_from_text(value_str) or parse_amount(value_str)
                    stage_str = row_data.get("status", "") or row_data.get("stage", "")
                    sector_str = row_data.get("sector", "") or row_data.get("type", "")

                    ref = f"meed-tbl-{re.sub(r'[^a-z0-9]', '', name.lower())[:30]}"
                    projects.append(_build_ppp_record(
                        source="meed_projects",
                        source_ref=ref,
                        name=name,
                        country_code=country_code,
                        sector=classify_sector(f"{name} {sector_str}"),
                        stage=_map_stage(stage_str),
                        investment_value=value,
                        description=f"MEED Projects: {name}. Value: ${value:,.0f}." if value else f"MEED Projects: {name}.",
                        source_url=url,
                        metadata={"data_type": "meed_table"},
                    ))

            time.sleep(0.6)

        except Exception as e:
            logger.debug(f"MEED {url}: {e}")

    logger.info(f"MEED: {len(projects)} projects")
    return projects


def _parse_meed_card(card, page_url: str) -> Optional[dict]:
    """Parse a MEED article/project card."""
    title_el = card.select_one("h1, h2, h3, h4, .title, .headline, a.title")
    if not title_el:
        return None
    name = title_el.get_text(strip=True)
    if not name or len(name) < 10:
        return None

    # Link
    link = ""
    if title_el.name == "a":
        link = title_el.get("href", "")
    else:
        link_el = card.select_one("a")
        if link_el:
            link = link_el.get("href", "")
    if link and not link.startswith("http"):
        link = f"{MEED_BASE}{link}"

    # Description
    desc_el = card.select_one("p, .summary, .excerpt, .description, .teaser-text")
    desc = desc_el.get_text(strip=True)[:500] if desc_el else ""

    # Combined text for analysis
    combined = f"{name} {desc}"
    country_code = _detect_country(combined)
    if not country_code:
        return None

    # Must be project-related content
    project_keywords = ["project", "construction", "contract", "award", "tender",
                        "infrastructure", "develop", "build", "billion", "million",
                        "phase", "megaproject"]
    if not any(kw in combined.lower() for kw in project_keywords):
        return None

    value = _extract_value_from_text(combined)

    ref = f"meed-{re.sub(r'[^a-z0-9]', '', name.lower())[:40]}"

    return _build_ppp_record(
        source="meed_projects",
        source_ref=ref,
        name=name,
        country_code=country_code,
        sector=classify_sector(combined),
        stage=_map_stage(combined),
        investment_value=value,
        description=desc or name,
        source_url=link or page_url,
        metadata={"data_type": "meed_article"},
    )


# =========================================================================
# Strategy 3: Gulf Business news (mega-project coverage)
# =========================================================================

def _scrape_gulf_business() -> list[dict]:
    """
    Scrape Gulf Business for mega-project news articles.
    Public news site covering GCC business and projects.
    """
    projects = []

    urls = [
        f"{GULF_BIZ_BASE}/category/projects/",
        f"{GULF_BIZ_BASE}/category/construction/",
        f"{GULF_BIZ_BASE}/category/energy/",
        f"{GULF_BIZ_BASE}/category/real-estate/",
        f"{GULF_BIZ_BASE}/?s=mega+project",
        f"{GULF_BIZ_BASE}/?s=infrastructure+project",
        f"{GULF_BIZ_BASE}/?s=PPP+partnership",
        f"{GULF_BIZ_BASE}/?s=billion+project+contract",
    ]

    seen_names: set[str] = set()

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            for article in soup.select(
                "article, .post, .article-card, .story-card, "
                ".entry, .card, [class*='article'], [class*='post']"
            ):
                title_el = article.select_one("h2, h3, h4, .entry-title, .title, a.title")
                if not title_el:
                    continue
                name = title_el.get_text(strip=True)
                if not name or len(name) < 15:
                    continue

                # Dedup by name
                name_key = re.sub(r'[^a-z0-9]', '', name.lower())
                if name_key in seen_names:
                    continue
                seen_names.add(name_key)

                link = ""
                if title_el.name == "a":
                    link = title_el.get("href", "")
                else:
                    link_el = title_el.select_one("a") or article.select_one("a")
                    if link_el:
                        link = link_el.get("href", "")
                if link and not link.startswith("http"):
                    link = f"{GULF_BIZ_BASE}{link}"

                desc_el = article.select_one("p, .excerpt, .summary, .entry-content")
                desc = desc_el.get_text(strip=True)[:500] if desc_el else ""

                combined = f"{name} {desc}"
                country_code = _detect_country(combined)
                if not country_code:
                    continue

                # Filter for project-related content
                project_keywords = ["project", "contract", "award", "tender", "construction",
                                    "infrastructure", "develop", "build", "billion", "million"]
                if not any(kw in combined.lower() for kw in project_keywords):
                    continue

                value = _extract_value_from_text(combined)

                # Date
                date_el = article.select_one("time, .date, .published, .entry-date, [datetime]")
                pub_date = None
                if date_el:
                    pub_date = date_el.get("datetime") or date_el.get_text(strip=True)

                ref = f"gulfbiz-{name_key[:40]}"

                projects.append(_build_ppp_record(
                    source="gulf_business",
                    source_ref=ref,
                    name=name,
                    country_code=country_code,
                    sector=classify_sector(combined),
                    stage=_map_stage(combined),
                    investment_value=value,
                    description=desc or name,
                    source_url=link or url,
                    metadata={
                        "data_type": "news_article",
                        "publish_date": pub_date,
                    },
                ))

            time.sleep(0.5)

        except Exception as e:
            logger.debug(f"Gulf Business {url}: {e}")

    logger.info(f"Gulf Business: {len(projects)} projects")
    return projects


# =========================================================================
# Deduplication
# =========================================================================

def _deduplicate(projects: list[dict]) -> list[dict]:
    """Remove duplicates by source_ref and by name similarity."""
    seen_refs: set[str] = set()
    seen_keys: set[str] = set()
    unique = []

    for p in projects:
        ref = p.get("source_ref", "")
        if ref and ref in seen_refs:
            continue

        # Normalize name for fuzzy dedup
        key = re.sub(r"[^a-z0-9]", "", p.get("name", "").lower())[:50] + p.get("country_code", "")
        if key in seen_keys:
            continue

        seen_refs.add(ref)
        seen_keys.add(key)
        unique.append(p)

    return unique


# =========================================================================
# Main scrape function
# =========================================================================

def scrape() -> list[dict]:
    """
    Scrape MEED Projects, Zawya Projects Monitor, and Gulf Business
    for GCC/MENA mega-project and PPP data.

    Strategies:
    1. Zawya Projects Monitor (primary — public project tracker)
    2. MEED Projects (GCC project tracker)
    3. Gulf Business (mega-project news)
    """
    all_projects: list[dict] = []

    # Strategy 1: Zawya Projects (most likely to have public data)
    logger.info("--- Strategy 1: Zawya Projects Monitor ---")
    zawya = _scrape_zawya_projects()
    logger.info(f"Zawya total: {len(zawya)} projects")
    all_projects.extend(zawya)

    # Strategy 2: MEED Projects
    logger.info("--- Strategy 2: MEED Projects ---")
    meed = _scrape_meed()
    logger.info(f"MEED total: {len(meed)} projects")
    all_projects.extend(meed)

    # Strategy 3: Gulf Business
    logger.info("--- Strategy 3: Gulf Business ---")
    gulf = _scrape_gulf_business()
    logger.info(f"Gulf Business total: {len(gulf)} projects")
    all_projects.extend(gulf)

    # Deduplicate across all sources
    unique = _deduplicate(all_projects)
    logger.info(f"MEED/Zawya/Gulf total: {len(unique)} unique projects (from {len(all_projects)} raw)")

    return unique


if __name__ == "__main__":
    results = scrape()
    save_ppp_projects(results, "meed_projects")
    print(f"Scraped {len(results)} PPP/mega-projects from MEED, Zawya & Gulf Business")
