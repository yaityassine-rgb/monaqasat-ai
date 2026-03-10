"""
Scraper for national PPP portals across MENA countries.

Sources:
1. Saudi NCP (National Center for Privatization): https://www.ncp.gov.sa/en
2. UAE Ministry of Finance PPP: https://www.mof.gov.ae
3. Egypt PPP Central Unit: https://www.pppu.gov.eg/
4. Morocco PPP / Ministry of Finance: https://ppp.finances.gov.ma / https://www.finances.gov.ma
5. Jordan PPP Unit: various government portals
6. Additional: Oman, Qatar, Bahrain, Kuwait PPP portals

Each portal is scraped for project listings, cards, and tables containing:
name, sector, stage, value, government entity.
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

logger = logging.getLogger("ppp_national")

# ---------------------------------------------------------------------------
# Portal configurations per country
# ---------------------------------------------------------------------------
PORTALS = {
    "SA": {
        "name": "Saudi NCP",
        "name_ar": "المركز الوطني للتخصيص",
        "entity": "National Center for Privatization & PPP",
        "entity_ar": "المركز الوطني للتخصيص",
        "entity_fr": "Centre national de privatisation",
        "urls": [
            "https://www.ncp.gov.sa/en/Pages/default.aspx",
            "https://www.ncp.gov.sa/en/Pages/Projects.aspx",
            "https://www.ncp.gov.sa/en/Pages/Sectors.aspx",
            "https://www.ncp.gov.sa/en/Mediacenter/Pages/news.aspx",
            "https://ncp.gov.sa/en/Pages/Projects.aspx",
        ],
        "api_urls": [
            "https://www.ncp.gov.sa/_api/web/lists",
            "https://www.ncp.gov.sa/en/_api/web/lists/GetByTitle('Projects')/items",
        ],
    },
    "AE": {
        "name": "UAE Ministry of Finance PPP",
        "name_ar": "وزارة المالية - الشراكة بين القطاعين",
        "entity": "Ministry of Finance - PPP Unit",
        "entity_ar": "وزارة المالية",
        "entity_fr": "Ministere des Finances - PPP",
        "urls": [
            "https://www.mof.gov.ae/en/strategicPartnership/Pages/default.aspx",
            "https://www.mof.gov.ae/en/About/Pages/ppp.aspx",
            "https://www.mof.gov.ae/en/StrategicPartnerships/Pages/PublicPrivatePartnership.aspx",
            "https://www.mof.gov.ae/en/resourcesAndBudget/Pages/ppp.aspx",
        ],
        "api_urls": [],
    },
    "EG": {
        "name": "Egypt PPP Central Unit",
        "name_ar": "الوحدة المركزية للشراكة مع القطاع الخاص",
        "entity": "PPP Central Unit - Ministry of Finance",
        "entity_ar": "الوحدة المركزية للشراكة",
        "entity_fr": "Unite centrale PPP - Ministere des Finances",
        "urls": [
            "https://www.pppu.gov.eg/",
            "https://www.pppu.gov.eg/Projects",
            "https://www.pppu.gov.eg/en/projects",
            "https://www.pppu.gov.eg/en/projects/awarded",
            "https://www.pppu.gov.eg/en/projects/pipeline",
            "https://pppu.gov.eg/en/awarded-projects",
        ],
        "api_urls": [
            "https://www.pppu.gov.eg/api/projects",
            "https://www.pppu.gov.eg/api/v1/projects",
        ],
    },
    "MA": {
        "name": "Morocco PPP",
        "name_ar": "الشراكة بين القطاعين العام والخاص - المغرب",
        "entity": "Ministry of Economy and Finance - PPP Unit",
        "entity_ar": "وزارة الاقتصاد والمالية",
        "entity_fr": "Ministere de l'Economie et des Finances - Unite PPP",
        "urls": [
            "https://ppp.finances.gov.ma/",
            "https://ppp.finances.gov.ma/projets",
            "https://ppp.finances.gov.ma/en/projects",
            "https://www.finances.gov.ma/fr/Pages/ppp.aspx",
            "https://ppp.finances.gov.ma/fr/projets",
        ],
        "api_urls": [
            "https://ppp.finances.gov.ma/api/projects",
        ],
    },
    "JO": {
        "name": "Jordan PPP",
        "name_ar": "وحدة الشراكة بين القطاعين - الأردن",
        "entity": "Executive Privatization Commission",
        "entity_ar": "هيئة الخصخصة التنفيذية",
        "entity_fr": "Commission de privatisation",
        "urls": [
            "https://www.mop.gov.jo/",
            "https://www.mop.gov.jo/en/page/public-private-partnership",
            "https://www.epc.jo/en/pages/projects",
            "http://www.epc.jo/",
        ],
        "api_urls": [],
    },
    "OM": {
        "name": "Oman PPP",
        "name_ar": "وحدة الشراكة - عُمان",
        "entity": "Ministry of Finance - Privatization Unit",
        "entity_ar": "وزارة المالية - وحدة التخصيص",
        "entity_fr": "Ministere des Finances - Unite de privatisation",
        "urls": [
            "https://www.mof.gov.om/",
            "https://www.mof.gov.om/en/PPP",
            "https://invest.gov.om/",
        ],
        "api_urls": [],
    },
    "QA": {
        "name": "Qatar PPP",
        "name_ar": "الشراكة بين القطاعين - قطر",
        "entity": "Ministry of Finance - PPP Department",
        "entity_ar": "وزارة المالية - إدارة الشراكة",
        "entity_fr": "Ministere des Finances - Departement PPP",
        "urls": [
            "https://www.mof.gov.qa/en/Pages/default.aspx",
            "https://www.ashghal.gov.qa/en/Pages/default.aspx",
        ],
        "api_urls": [],
    },
    "KW": {
        "name": "Kuwait PPP",
        "name_ar": "هيئة مشروعات الشراكة - الكويت",
        "entity": "Kuwait Authority for Partnership Projects (KAPP)",
        "entity_ar": "هيئة مشروعات الشراكة بين القطاعين العام والخاص",
        "entity_fr": "Autorite des projets de partenariat du Koweit",
        "urls": [
            "https://www.kapp.gov.kw/",
            "https://www.kapp.gov.kw/en/Projects",
            "https://kapp.gov.kw/en/projects",
            "https://www.kapp.gov.kw/en/Pages/Projects.aspx",
        ],
        "api_urls": [],
    },
    "BH": {
        "name": "Bahrain PPP",
        "name_ar": "الشراكة بين القطاعين - البحرين",
        "entity": "Ministry of Finance and National Economy",
        "entity_ar": "وزارة المالية والاقتصاد الوطني",
        "entity_fr": "Ministere des Finances et de l'Economie nationale",
        "urls": [
            "https://www.mofne.gov.bh/",
            "https://www.bahrain.bh/en/business/ppp",
        ],
        "api_urls": [],
    },
    "TN": {
        "name": "Tunisia PPP",
        "name_ar": "الشراكة بين القطاعين - تونس",
        "entity": "Instance Generale des Partenariats Public-Prive",
        "entity_ar": "الهيئة العامة للشراكة",
        "entity_fr": "Instance Generale des PPP",
        "urls": [
            "https://www.igppp.tn/",
            "https://www.igppp.tn/fr/projets",
            "https://www.igppp.tn/en/projects",
        ],
        "api_urls": [],
    },
    "DZ": {
        "name": "Algeria PPP",
        "name_ar": "الشراكة - الجزائر",
        "entity": "Ministry of Finance",
        "entity_ar": "وزارة المالية",
        "entity_fr": "Ministere des Finances",
        "urls": [
            "https://www.mf.gov.dz/",
        ],
        "api_urls": [],
    },
}

# Stage mapping
STAGE_MAP = {
    "pipeline": "identification",
    "identification": "identification",
    "planning": "planning",
    "preparation": "feasibility",
    "feasibility": "feasibility",
    "study": "feasibility",
    "pre-qualification": "tender",
    "procurement": "tender",
    "tender": "tender",
    "tendering": "tender",
    "rfp": "tender",
    "rfq": "tender",
    "eoi": "tender",
    "shortlisted": "shortlisted",
    "shortlist": "shortlisted",
    "evaluation": "shortlisted",
    "awarded": "awarded",
    "award": "awarded",
    "signed": "awarded",
    "financial close": "awarded",
    "construction": "construction",
    "under construction": "construction",
    "execution": "construction",
    "implementation": "construction",
    "operational": "operational",
    "completed": "operational",
    "active": "operational",
    "cancelled": "cancelled",
    "suspended": "cancelled",
    "on hold": "planning",
    # Arabic stages
    "قيد التنفيذ": "construction",
    "مرحلة الطرح": "tender",
    "مرحلة الدراسة": "feasibility",
    "تم الترسية": "awarded",
    "تشغيلي": "operational",
    "ملغى": "cancelled",
    # French stages
    "en cours": "construction",
    "appel d'offres": "tender",
    "etude": "feasibility",
    "attribue": "awarded",
    "operationnel": "operational",
    "annule": "cancelled",
}


def _map_stage(raw: str) -> str:
    """Map raw stage text to our taxonomy."""
    if not raw:
        return "planning"
    lower = raw.lower().strip()
    for key, stage in STAGE_MAP.items():
        if key in lower:
            return stage
    return "planning"


def _extract_value(text: str) -> float:
    """Extract monetary value from text in various formats and currencies."""
    if not text:
        return 0

    # SAR/AED/EGP/MAD/JOD patterns
    currency_patterns = [
        (r'(?:SAR|sar)\s*([\d,.]+)\s*(?:billion|bn|b)', 1_000_000_000, 3.75),
        (r'(?:SAR|sar)\s*([\d,.]+)\s*(?:million|mn|m)', 1_000_000, 3.75),
        (r'(?:AED|aed)\s*([\d,.]+)\s*(?:billion|bn|b)', 1_000_000_000, 3.67),
        (r'(?:AED|aed)\s*([\d,.]+)\s*(?:million|mn|m)', 1_000_000, 3.67),
        (r'(?:EGP|egp|LE|le|E\.?P\.?)\s*([\d,.]+)\s*(?:billion|bn|b)', 1_000_000_000, 50.0),
        (r'(?:EGP|egp|LE|le|E\.?P\.?)\s*([\d,.]+)\s*(?:million|mn|m)', 1_000_000, 50.0),
        (r'(?:MAD|mad|DH|dh)\s*([\d,.]+)\s*(?:billion|bn|milliard)', 1_000_000_000, 10.0),
        (r'(?:MAD|mad|DH|dh)\s*([\d,.]+)\s*(?:million|mn|m)', 1_000_000, 10.0),
        (r'(?:JOD|jod|JD|jd)\s*([\d,.]+)\s*(?:billion|bn|b)', 1_000_000_000, 0.71),
        (r'(?:JOD|jod|JD|jd)\s*([\d,.]+)\s*(?:million|mn|m)', 1_000_000, 0.71),
        (r'(?:KWD|kwd|KD|kd)\s*([\d,.]+)\s*(?:billion|bn|b)', 1_000_000_000, 0.31),
        (r'(?:KWD|kwd|KD|kd)\s*([\d,.]+)\s*(?:million|mn|m)', 1_000_000, 0.31),
        (r'(?:QAR|qar|QR|qr)\s*([\d,.]+)\s*(?:billion|bn|b)', 1_000_000_000, 3.64),
        (r'(?:QAR|qar|QR|qr)\s*([\d,.]+)\s*(?:million|mn|m)', 1_000_000, 3.64),
        # USD patterns
        (r'\$\s*([\d,.]+)\s*(?:billion|bn|b)', 1_000_000_000, 1.0),
        (r'\$\s*([\d,.]+)\s*(?:million|mn|m)', 1_000_000, 1.0),
        (r'\$\s*([\d,.]+)\s*(?:trillion|tn|t)', 1_000_000_000_000, 1.0),
        (r'(?:USD|usd)\s*([\d,.]+)\s*(?:billion|bn|b)', 1_000_000_000, 1.0),
        (r'(?:USD|usd)\s*([\d,.]+)\s*(?:million|mn|m)', 1_000_000, 1.0),
        # Arabic number patterns
        (r'([\d,.]+)\s*(?:مليار)', 1_000_000_000, 1.0),
        (r'([\d,.]+)\s*(?:مليون)', 1_000_000, 1.0),
        # French number patterns
        (r'([\d,.]+)\s*(?:milliard)', 1_000_000_000, 1.0),
        (r'([\d,.]+)\s*(?:millions?)', 1_000_000, 1.0),
    ]

    for pattern, multiplier, fx_rate in currency_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                amount = float(match.group(1).replace(",", ""))
                return (amount * multiplier) / fx_rate  # Convert to USD
            except (ValueError, ZeroDivisionError):
                continue

    # Plain dollar amount
    match = re.search(r'\$\s*([\d,.]+)', text)
    if match:
        return parse_amount(match.group(1))

    return 0


def _build_ppp_record(
    source: str,
    source_ref: str,
    name: str,
    country_code: str,
    portal_config: dict,
    sector: str = "construction",
    subsector: str = "",
    stage: str = "planning",
    contract_type: str = "concession",
    investment_value: float = 0,
    currency: str = "USD",
    sponsors: list = None,
    description: str = "",
    description_ar: str = "",
    description_fr: str = "",
    source_url: str = "",
    tender_deadline: str = None,
    metadata: dict = None,
) -> dict:
    """Build a standardized PPP project record with portal-specific data."""
    country_name = MENA_COUNTRIES.get(country_code, "")

    tags = [sector] if sector else []
    if investment_value >= 1_000_000_000:
        tags.append("mega_project")
    if investment_value >= 500_000_000:
        tags.append("large_project")
    tags.append("national_ppp_portal")

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
        "government_entity": portal_config.get("entity", ""),
        "government_entity_ar": portal_config.get("entity_ar", ""),
        "government_entity_fr": portal_config.get("entity_fr", ""),
        "sponsors": sponsors or [],
        "lenders": [],
        "advisors": [],
        "description": description,
        "description_ar": description_ar,
        "description_fr": description_fr,
        "financial_close_date": None,
        "contract_duration_years": None,
        "tender_deadline": tender_deadline,
        "award_date": None,
        "tags": list(set(tags)),
        "metadata": metadata or {},
    }


# =========================================================================
# Generic portal scraper — works for all portals
# =========================================================================

def _scrape_portal_api(country_code: str, portal: dict) -> list[dict]:
    """Try API endpoints for a portal."""
    projects = []

    for api_url in portal.get("api_urls", []):
        try:
            # Try with JSON accept header
            headers = {**HEADERS, "Accept": "application/json"}
            resp = requests.get(api_url, headers=headers, timeout=20)
            if resp.status_code != 200:
                continue

            data = resp.json()

            # Handle different response shapes
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Try common wrapper keys
                for key in ["value", "d", "results", "data", "projects", "items", "Records"]:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
                if not items and "d" in data and isinstance(data["d"], dict):
                    items = data["d"].get("results", [])

            for item in items:
                if not isinstance(item, dict):
                    continue

                name = (
                    item.get("Title") or item.get("Name") or item.get("ProjectName")
                    or item.get("name") or item.get("title") or item.get("project_name")
                    or ""
                ).strip()
                if not name or len(name) < 5:
                    continue

                ref = str(item.get("Id") or item.get("id") or item.get("ID") or name[:80])
                sector_raw = item.get("Sector") or item.get("sector") or item.get("Category") or ""
                stage_raw = item.get("Status") or item.get("status") or item.get("Stage") or item.get("stage") or ""
                value = parse_amount(
                    item.get("Value") or item.get("Investment") or item.get("Cost")
                    or item.get("value") or item.get("investment") or item.get("cost") or 0
                )
                desc = item.get("Description") or item.get("description") or item.get("Summary") or ""

                projects.append(_build_ppp_record(
                    source=f"ppp_{country_code.lower()}",
                    source_ref=f"{country_code.lower()}-api-{ref}",
                    name=name,
                    country_code=country_code,
                    portal_config=portal,
                    sector=classify_sector(f"{name} {sector_raw} {desc}"),
                    stage=_map_stage(stage_raw),
                    contract_type=classify_ppp_contract(f"{name} {desc}"),
                    investment_value=value,
                    description=desc[:500] if desc else f"{portal['name']}: {name}",
                    source_url=api_url,
                    metadata={"raw_sector": sector_raw, "raw_stage": stage_raw, "data_source": "api"},
                ))

            if items:
                logger.info(f"{portal['name']} API: {len(items)} projects from {api_url}")
                return projects

        except requests.exceptions.JSONDecodeError:
            continue
        except Exception as e:
            logger.debug(f"{portal['name']} API {api_url}: {e}")

    return projects


def _scrape_portal_pages(country_code: str, portal: dict) -> list[dict]:
    """Scrape HTML pages for a portal."""
    projects = []
    seen_names: set[str] = set()

    for url in portal.get("urls", []):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
            if resp.status_code != 200:
                logger.debug(f"{portal['name']} {url}: HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Parse project cards/items
            page_projects = _extract_projects_from_page(soup, country_code, portal, url)
            for p in page_projects:
                name_key = re.sub(r'[^a-z0-9]', '', p["name"].lower())
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    projects.append(p)

            # Parse tables
            table_projects = _extract_projects_from_tables(soup, country_code, portal, url)
            for p in table_projects:
                name_key = re.sub(r'[^a-z0-9]', '', p["name"].lower())
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    projects.append(p)

            # Look for embedded JSON data
            json_projects = _extract_projects_from_scripts(soup, country_code, portal, url)
            for p in json_projects:
                name_key = re.sub(r'[^a-z0-9]', '', p["name"].lower())
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    projects.append(p)

            time.sleep(0.6)

        except Exception as e:
            logger.debug(f"{portal['name']} {url}: {e}")

    return projects


def _extract_projects_from_page(
    soup: BeautifulSoup, country_code: str, portal: dict, page_url: str
) -> list[dict]:
    """Extract project entries from page HTML elements."""
    projects = []

    # Broad selector set for different portal designs
    selectors = [
        ".project-card", ".project-item", ".project",
        ".card", ".item", ".list-item",
        "article", ".article",
        ".sector-card", ".sector-item",
        ".views-row", ".node",
        "[class*='project']", "[class*='Project']",
        ".col-md-4", ".col-md-6", ".col-lg-4",  # Common grid items
        ".ms-webpartzone .ms-webpart",  # SharePoint
        ".accordion-item", ".panel",
    ]

    for selector in selectors:
        cards = soup.select(selector)
        if not cards:
            continue

        for card in cards:
            # Title
            title_el = card.select_one(
                "h1, h2, h3, h4, h5, "
                ".title, .name, .project-name, .card-title, "
                "a.title, a[class*='title']"
            )
            if not title_el:
                continue
            name = title_el.get_text(strip=True)
            if not name or len(name) < 5:
                continue
            # Skip navigation/footer items
            if any(skip in name.lower() for skip in ["home", "about", "contact", "login", "menu", "copyright"]):
                continue

            # Link
            link = ""
            if title_el.name == "a":
                link = title_el.get("href", "")
            else:
                link_el = card.select_one("a")
                if link_el:
                    link = link_el.get("href", "")
            if link and not link.startswith("http"):
                # Reconstruct base URL
                from urllib.parse import urljoin
                link = urljoin(page_url, link)

            # Description
            desc_el = card.select_one("p, .description, .summary, .body, .content, .text")
            desc = desc_el.get_text(strip=True)[:500] if desc_el else ""

            # Value
            value_el = card.select_one(
                ".value, .cost, .amount, .investment, .budget, "
                "[class*='value'], [class*='cost'], [class*='amount']"
            )
            value_text = value_el.get_text(strip=True) if value_el else ""
            value = _extract_value(value_text) or _extract_value(card.get_text())

            # Sector
            sector_el = card.select_one(".sector, .category, .tag, [class*='sector']")
            sector_text = sector_el.get_text(strip=True) if sector_el else ""

            # Stage/Status
            status_el = card.select_one(
                ".status, .stage, .phase, .badge, "
                "[class*='status'], [class*='stage']"
            )
            stage_text = status_el.get_text(strip=True) if status_el else ""

            ref = f"{country_code.lower()}-page-{re.sub(r'[^a-z0-9]', '', name.lower())[:30]}"

            projects.append(_build_ppp_record(
                source=f"ppp_{country_code.lower()}",
                source_ref=ref,
                name=name,
                country_code=country_code,
                portal_config=portal,
                sector=classify_sector(f"{name} {sector_text} {desc}"),
                stage=_map_stage(stage_text),
                contract_type=classify_ppp_contract(f"{name} {desc}"),
                investment_value=value,
                description=desc or f"{portal['name']}: {name}",
                source_url=link or page_url,
                metadata={"raw_sector": sector_text, "raw_stage": stage_text, "data_source": "html_card"},
            ))

        if projects:
            break  # Found results with this selector

    return projects


def _extract_projects_from_tables(
    soup: BeautifulSoup, country_code: str, portal: dict, page_url: str
) -> list[dict]:
    """Extract project entries from HTML tables."""
    projects = []

    for table in soup.select("table"):
        rows = table.select("tr")
        if len(rows) < 2:
            continue

        # Parse header
        header_row = rows[0]
        headers_list = [
            th.get_text(strip=True).lower()
            for th in header_row.select("th, td")
        ]

        if not headers_list:
            continue

        # Identify column indices
        name_idx = None
        sector_idx = None
        stage_idx = None
        value_idx = None

        for i, h in enumerate(headers_list):
            h_lower = h.lower()
            if any(kw in h_lower for kw in ["project", "name", "title", "المشروع", "اسم", "projet"]):
                name_idx = i
            elif any(kw in h_lower for kw in ["sector", "category", "القطاع", "secteur"]):
                sector_idx = i
            elif any(kw in h_lower for kw in ["status", "stage", "phase", "الحالة", "المرحلة", "statut"]):
                stage_idx = i
            elif any(kw in h_lower for kw in ["value", "cost", "investment", "budget", "amount",
                                                "القيمة", "التكلفة", "valeur", "cout"]):
                value_idx = i

        if name_idx is None:
            # Default: first column is name
            name_idx = 0

        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.select("td")]
            if len(cells) <= name_idx:
                continue

            name = cells[name_idx]
            if not name or len(name) < 5:
                continue

            sector_text = cells[sector_idx] if sector_idx is not None and sector_idx < len(cells) else ""
            stage_text = cells[stage_idx] if stage_idx is not None and stage_idx < len(cells) else ""
            value_text = cells[value_idx] if value_idx is not None and value_idx < len(cells) else ""
            value = _extract_value(value_text) or parse_amount(value_text)

            ref = f"{country_code.lower()}-tbl-{re.sub(r'[^a-z0-9]', '', name.lower())[:30]}"

            projects.append(_build_ppp_record(
                source=f"ppp_{country_code.lower()}",
                source_ref=ref,
                name=name,
                country_code=country_code,
                portal_config=portal,
                sector=classify_sector(f"{name} {sector_text}"),
                stage=_map_stage(stage_text),
                contract_type=classify_ppp_contract(name),
                investment_value=value,
                description=f"{portal['name']}: {name}. Sector: {sector_text}. Stage: {stage_text}.",
                source_url=page_url,
                metadata={
                    "raw_sector": sector_text,
                    "raw_stage": stage_text,
                    "raw_value": value_text,
                    "data_source": "html_table",
                },
            ))

    return projects


def _extract_projects_from_scripts(
    soup: BeautifulSoup, country_code: str, portal: dict, page_url: str
) -> list[dict]:
    """Extract project data from embedded JavaScript/JSON in page."""
    projects = []

    for script in soup.select("script"):
        text = script.string or ""
        if not text or len(text) < 100:
            continue

        # Look for JSON arrays/objects with project data
        # Pattern: var projects = [...] or window.__data = {...}
        patterns = [
            r'(?:projects|data|items|records)\s*[:=]\s*(\[.*?\])\s*[;,\n]',
            r'(?:JSON\.parse|parse)\s*\(\s*[\'"](\[.*?\])[\'"]\s*\)',
        ]

        for pat in patterns:
            matches = re.findall(pat, text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    items = json.loads(match)
                    if not isinstance(items, list):
                        continue

                    for item in items:
                        if not isinstance(item, dict):
                            continue

                        name = (
                            item.get("title") or item.get("name") or item.get("Title")
                            or item.get("Name") or item.get("project_name") or ""
                        ).strip()
                        if not name or len(name) < 5:
                            continue

                        ref_raw = str(item.get("id") or item.get("Id") or name[:80])
                        sector_raw = item.get("sector") or item.get("Sector") or item.get("category") or ""
                        stage_raw = item.get("status") or item.get("Status") or item.get("stage") or ""
                        value = parse_amount(
                            item.get("value") or item.get("Value") or item.get("investment")
                            or item.get("cost") or 0
                        )
                        desc = item.get("description") or item.get("Description") or ""

                        ref = f"{country_code.lower()}-js-{re.sub(r'[^a-z0-9]', '', name.lower())[:30]}"

                        projects.append(_build_ppp_record(
                            source=f"ppp_{country_code.lower()}",
                            source_ref=ref,
                            name=name,
                            country_code=country_code,
                            portal_config=portal,
                            sector=classify_sector(f"{name} {sector_raw} {desc}"),
                            stage=_map_stage(stage_raw),
                            contract_type=classify_ppp_contract(f"{name} {desc}"),
                            investment_value=value,
                            description=desc[:500] if desc else f"{portal['name']}: {name}",
                            source_url=page_url,
                            metadata={"data_source": "js_embedded"},
                        ))

                except (json.JSONDecodeError, TypeError):
                    continue

    return projects


# =========================================================================
# Country-specific scrapers for portals with known structures
# =========================================================================

def _scrape_saudi_ncp() -> list[dict]:
    """
    Specialized scraper for Saudi NCP portal.
    NCP lists sectors with PPP projects: health, education, transport, etc.
    """
    projects = []
    portal = PORTALS["SA"]

    # Known NCP PPP sectors and projects (these are well-documented)
    ncp_sectors = [
        {
            "url": "https://www.ncp.gov.sa/en/Pages/HealthSector.aspx",
            "sector": "healthcare",
            "label": "Health Sector PPP",
        },
        {
            "url": "https://www.ncp.gov.sa/en/Pages/EducationSector.aspx",
            "sector": "education",
            "label": "Education Sector PPP",
        },
        {
            "url": "https://www.ncp.gov.sa/en/Pages/TransportSector.aspx",
            "sector": "transport",
            "label": "Transport Sector PPP",
        },
        {
            "url": "https://www.ncp.gov.sa/en/Pages/EnvironmentSector.aspx",
            "sector": "water",
            "label": "Environment & Water Sector PPP",
        },
        {
            "url": "https://www.ncp.gov.sa/en/Pages/MunicipalitiesSector.aspx",
            "sector": "real_estate",
            "label": "Municipalities Sector PPP",
        },
        {
            "url": "https://www.ncp.gov.sa/en/Pages/EnergySector.aspx",
            "sector": "energy",
            "label": "Energy Sector PPP",
        },
    ]

    for sector_info in ncp_sectors:
        try:
            resp = requests.get(sector_info["url"], headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract project information from the sector page
            content = soup.select_one("#content, .content, .main-content, #ctl00_PlaceHolderMain")
            if not content:
                content = soup

            # Find project names/descriptions in the content
            text = content.get_text(" ", strip=True)

            # Extract project-like sections
            for heading in content.select("h2, h3, h4, strong, b"):
                heading_text = heading.get_text(strip=True)
                if len(heading_text) < 10 or len(heading_text) > 200:
                    continue
                # Must look like a project name
                if any(kw in heading_text.lower() for kw in [
                    "project", "program", "initiative", "phase",
                    "مشروع", "برنامج", "مبادرة", "مرحلة",
                ]):
                    # Get description from following siblings
                    desc = ""
                    for sibling in heading.find_next_siblings():
                        if sibling.name in ("h2", "h3", "h4"):
                            break
                        desc += sibling.get_text(strip=True) + " "
                        if len(desc) > 500:
                            break

                    value = _extract_value(desc) or _extract_value(heading_text)

                    ref = f"ncp-{sector_info['sector']}-{re.sub(r'[^a-z0-9]', '', heading_text.lower())[:30]}"
                    projects.append(_build_ppp_record(
                        source="ppp_sa",
                        source_ref=ref,
                        name=heading_text,
                        country_code="SA",
                        portal_config=portal,
                        sector=sector_info["sector"],
                        stage="planning",
                        contract_type=classify_ppp_contract(f"{heading_text} {desc}"),
                        investment_value=value,
                        description=desc[:500].strip() if desc else f"Saudi NCP {sector_info['label']}: {heading_text}",
                        source_url=sector_info["url"],
                        metadata={"ncp_sector": sector_info["label"]},
                    ))

            time.sleep(0.5)

        except Exception as e:
            logger.debug(f"NCP sector {sector_info['label']}: {e}")

    return projects


def _scrape_egypt_pppu() -> list[dict]:
    """
    Specialized scraper for Egypt PPP Central Unit.
    PPPU has structured project listings with categories:
    awarded, pipeline, under preparation.
    """
    projects = []
    portal = PORTALS["EG"]

    categories = [
        ("awarded", "awarded"),
        ("pipeline", "identification"),
        ("under-preparation", "feasibility"),
        ("pre-qualification", "tender"),
    ]

    for category, default_stage in categories:
        urls = [
            f"https://www.pppu.gov.eg/en/projects/{category}",
            f"https://pppu.gov.eg/en/{category}-projects",
            f"https://www.pppu.gov.eg/{category}",
        ]

        for url in urls:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=20)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")

                for card in soup.select(
                    ".project, .card, article, .list-item, "
                    ".project-item, [class*='project'], .row .col"
                ):
                    title_el = card.select_one("h2, h3, h4, .title, a")
                    if not title_el:
                        continue
                    name = title_el.get_text(strip=True)
                    if not name or len(name) < 5:
                        continue

                    link = ""
                    if title_el.name == "a":
                        link = title_el.get("href", "")
                    else:
                        a_el = card.select_one("a")
                        if a_el:
                            link = a_el.get("href", "")
                    if link and not link.startswith("http"):
                        link = f"https://www.pppu.gov.eg{link}"

                    desc_el = card.select_one("p, .description, .summary")
                    desc = desc_el.get_text(strip=True)[:500] if desc_el else ""

                    value = _extract_value(card.get_text())

                    sector_el = card.select_one(".sector, .category")
                    sector_text = sector_el.get_text(strip=True) if sector_el else ""

                    stage_el = card.select_one(".status, .stage")
                    stage_text = stage_el.get_text(strip=True) if stage_el else ""
                    stage = _map_stage(stage_text) if stage_text else default_stage

                    ref = f"eg-pppu-{category}-{re.sub(r'[^a-z0-9]', '', name.lower())[:30]}"

                    projects.append(_build_ppp_record(
                        source="ppp_eg",
                        source_ref=ref,
                        name=name,
                        country_code="EG",
                        portal_config=portal,
                        sector=classify_sector(f"{name} {sector_text} {desc}"),
                        stage=stage,
                        contract_type=classify_ppp_contract(f"{name} {desc}"),
                        investment_value=value,
                        description=desc or f"Egypt PPPU ({category}): {name}",
                        source_url=link or url,
                        metadata={"pppu_category": category},
                    ))

                if projects:
                    break  # Got data from this URL

                time.sleep(0.5)

            except Exception as e:
                logger.debug(f"Egypt PPPU {category} {url}: {e}")

    return projects


def _scrape_morocco_ppp() -> list[dict]:
    """
    Specialized scraper for Morocco PPP portal.
    Morocco has an active PPP program with French/Arabic content.
    """
    projects = []
    portal = PORTALS["MA"]

    ppp_urls = [
        "https://ppp.finances.gov.ma/",
        "https://ppp.finances.gov.ma/projets",
        "https://ppp.finances.gov.ma/fr/projets",
        "https://ppp.finances.gov.ma/en/projects",
        "https://www.finances.gov.ma/fr/Pages/ppp.aspx",
    ]

    for url in ppp_urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Parse project listings
            for card in soup.select(
                ".project, .projet, article, .card, .item, "
                "[class*='projet'], [class*='project'], .list-item"
            ):
                title_el = card.select_one("h2, h3, h4, .title, .titre, a")
                if not title_el:
                    continue
                name = title_el.get_text(strip=True)
                if not name or len(name) < 5:
                    continue

                link = ""
                if title_el.name == "a":
                    link = title_el.get("href", "")
                if link and not link.startswith("http"):
                    from urllib.parse import urljoin
                    link = urljoin(url, link)

                desc_el = card.select_one("p, .description, .resume")
                desc = desc_el.get_text(strip=True)[:500] if desc_el else ""

                value = _extract_value(card.get_text())
                sector = classify_sector(f"{name} {desc}")

                ref = f"ma-ppp-{re.sub(r'[^a-z0-9]', '', name.lower())[:30]}"

                projects.append(_build_ppp_record(
                    source="ppp_ma",
                    source_ref=ref,
                    name=name,
                    country_code="MA",
                    portal_config=portal,
                    sector=sector,
                    stage="planning",
                    contract_type=classify_ppp_contract(f"{name} {desc}"),
                    investment_value=value,
                    description=desc or f"Morocco PPP: {name}",
                    description_fr=desc if any(c in desc for c in "aeioueaiou") else "",
                    source_url=link or url,
                    metadata={"data_source": "morocco_ppp_portal"},
                ))

            # Also parse any tables
            table_projects = _extract_projects_from_tables(soup, "MA", portal, url)
            projects.extend(table_projects)

            time.sleep(0.5)

        except Exception as e:
            logger.debug(f"Morocco PPP {url}: {e}")

    return projects


def _scrape_kuwait_kapp() -> list[dict]:
    """
    Specialized scraper for Kuwait KAPP (Authority for Partnership Projects).
    KAPP has a structured project pipeline.
    """
    projects = []
    portal = PORTALS["KW"]

    kapp_urls = [
        "https://www.kapp.gov.kw/en/Projects",
        "https://kapp.gov.kw/en/projects",
        "https://www.kapp.gov.kw/en/Pages/Projects.aspx",
        "https://www.kapp.gov.kw/",
    ]

    for url in kapp_urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # KAPP typically shows project cards with sector, status, value
            for card in soup.select(
                ".project, .card, article, .item, [class*='project'], "
                ".col-md-4, .col-md-6, .panel"
            ):
                title_el = card.select_one("h2, h3, h4, .title, .name, a")
                if not title_el:
                    continue
                name = title_el.get_text(strip=True)
                if not name or len(name) < 5:
                    continue

                desc_el = card.select_one("p, .description, .summary")
                desc = desc_el.get_text(strip=True)[:500] if desc_el else ""

                value = _extract_value(card.get_text())
                stage_el = card.select_one(".status, .stage, .badge")
                stage_text = stage_el.get_text(strip=True) if stage_el else ""

                ref = f"kw-kapp-{re.sub(r'[^a-z0-9]', '', name.lower())[:30]}"

                projects.append(_build_ppp_record(
                    source="ppp_kw",
                    source_ref=ref,
                    name=name,
                    country_code="KW",
                    portal_config=portal,
                    sector=classify_sector(f"{name} {desc}"),
                    stage=_map_stage(stage_text),
                    contract_type=classify_ppp_contract(f"{name} {desc}"),
                    investment_value=value,
                    description=desc or f"Kuwait KAPP: {name}",
                    source_url=url,
                    metadata={"data_source": "kapp_portal"},
                ))

            if projects:
                break

            time.sleep(0.5)

        except Exception as e:
            logger.debug(f"Kuwait KAPP {url}: {e}")

    return projects


# =========================================================================
# Deduplication
# =========================================================================

def _deduplicate(projects: list[dict]) -> list[dict]:
    """Remove duplicates by source_ref and normalized name."""
    seen_refs: set[str] = set()
    seen_keys: set[str] = set()
    unique = []

    for p in projects:
        ref = p.get("source_ref", "")
        if ref and ref in seen_refs:
            continue

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
    Scrape national PPP portals across MENA countries.

    Strategy per country:
    1. Try portal API endpoints
    2. Scrape portal HTML pages
    3. Run country-specific specialized scrapers
    """
    all_projects: list[dict] = []

    # Phase 1: Country-specific specialized scrapers
    logger.info("=== Phase 1: Country-specific scrapers ===")

    logger.info("--- Saudi NCP ---")
    sa_projects = _scrape_saudi_ncp()
    logger.info(f"Saudi NCP: {len(sa_projects)} projects")
    all_projects.extend(sa_projects)

    logger.info("--- Egypt PPPU ---")
    eg_projects = _scrape_egypt_pppu()
    logger.info(f"Egypt PPPU: {len(eg_projects)} projects")
    all_projects.extend(eg_projects)

    logger.info("--- Morocco PPP ---")
    ma_projects = _scrape_morocco_ppp()
    logger.info(f"Morocco PPP: {len(ma_projects)} projects")
    all_projects.extend(ma_projects)

    logger.info("--- Kuwait KAPP ---")
    kw_projects = _scrape_kuwait_kapp()
    logger.info(f"Kuwait KAPP: {len(kw_projects)} projects")
    all_projects.extend(kw_projects)

    # Phase 2: Generic scraper for all portals (catches remaining countries)
    logger.info("=== Phase 2: Generic portal scraping ===")

    # Skip countries already handled with specialized scrapers
    specialized = {"SA", "EG", "MA", "KW"}

    for country_code, portal in PORTALS.items():
        if country_code in specialized:
            continue

        logger.info(f"--- {portal['name']} ({country_code}) ---")

        # Try API first
        api_projects = _scrape_portal_api(country_code, portal)
        if api_projects:
            all_projects.extend(api_projects)
            logger.info(f"{portal['name']} API: {len(api_projects)} projects")
            continue

        # Fall back to page scraping
        page_projects = _scrape_portal_pages(country_code, portal)
        all_projects.extend(page_projects)
        logger.info(f"{portal['name']} pages: {len(page_projects)} projects")

    # Deduplicate
    unique = _deduplicate(all_projects)
    logger.info(f"National PPP portals total: {len(unique)} unique projects (from {len(all_projects)} raw)")

    return unique


if __name__ == "__main__":
    results = scrape()
    save_ppp_projects(results, "national_ppp")
    print(f"Scraped {len(results)} PPP projects from national MENA portals")
