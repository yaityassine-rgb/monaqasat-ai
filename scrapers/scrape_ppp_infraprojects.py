"""
Scraper for Global Infrastructure Hub / InfraCompass / World Bank PPP Knowledge Lab.

Sources:
1. Global Infrastructure Hub InfraCompass: https://infracompass.gihub.org/
   - Country-level infrastructure data, reform indices, investment gaps
2. World Bank PPP Knowledge Lab: https://ppp.worldbank.org/public-private-partnership/
   - PPP project pipeline, knowledge resources, country frameworks
3. Global Infrastructure Outlook: https://outlook.gihub.org/
   - Investment need forecasts by sector and country

Focuses on active/planned infrastructure projects in MENA.
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

logger = logging.getLogger("ppp_infraprojects")

# ---------------------------------------------------------------------------
# URLs and constants
# ---------------------------------------------------------------------------
INFRACOMPASS_BASE = "https://infracompass.gihub.org"
INFRACOMPASS_API = "https://infracompass.gihub.org/api"
GI_OUTLOOK_API = "https://outlook.gihub.org/api"
GI_OUTLOOK_BASE = "https://outlook.gihub.org"

PPP_KNOWLEDGE_LAB = "https://ppp.worldbank.org/public-private-partnership"
PPP_KB_API = "https://ppp.worldbank.org/api"

# ISO3 codes for MENA
ISO2_TO_ISO3 = {
    "MA": "MAR", "SA": "SAU", "AE": "ARE", "EG": "EGY", "KW": "KWT",
    "QA": "QAT", "BH": "BHR", "OM": "OMN", "JO": "JOR", "TN": "TUN",
    "DZ": "DZA", "LY": "LBY", "IQ": "IRQ", "LB": "LBN", "PS": "PSE",
    "SD": "SDN", "YE": "YEM", "MR": "MRT",
}

# InfraCompass indicator IDs (from their data model)
INFRACOMPASS_INDICATORS = {
    "infrastructure_investment": "infra_investment",
    "transport_investment": "transport_inv",
    "energy_investment": "energy_inv",
    "water_investment": "water_inv",
    "telecom_investment": "telecom_inv",
}

# Stage mapping
STAGE_MAP = {
    "pipeline": "identification",
    "planned": "planning",
    "preparation": "feasibility",
    "procurement": "tender",
    "under construction": "construction",
    "construction": "construction",
    "operational": "operational",
    "active": "operational",
    "completed": "operational",
    "cancelled": "cancelled",
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
    lenders: list = None,
    description: str = "",
    financial_close_date: str = None,
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
        "lenders": lenders or [],
        "advisors": [],
        "description": description,
        "description_ar": "",
        "description_fr": "",
        "financial_close_date": financial_close_date,
        "contract_duration_years": None,
        "tender_deadline": None,
        "award_date": None,
        "tags": list(set(tags)),
        "metadata": metadata or {},
    }


# =========================================================================
# Strategy 1: InfraCompass API — country infrastructure profiles
# =========================================================================

def _scrape_infracompass_api() -> list[dict]:
    """
    Query InfraCompass API for country-level infrastructure data.
    This provides reform scores, investment gaps, and sector breakdowns.
    """
    projects = []

    for iso2, country_name in MENA_COUNTRIES.items():
        iso3 = ISO2_TO_ISO3.get(iso2)
        if not iso3:
            continue

        # Try different API patterns
        endpoints = [
            f"{INFRACOMPASS_API}/countries/{iso3}",
            f"{INFRACOMPASS_API}/country/{iso3}",
            f"{INFRACOMPASS_API}/v1/countries/{iso3}",
            f"{INFRACOMPASS_BASE}/ind/{iso3.lower()}/data.json",
        ]

        for endpoint in endpoints:
            try:
                resp = requests.get(endpoint, headers=HEADERS, timeout=20)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                if not data:
                    continue

                # Parse country profile data
                parsed = _parse_infracompass_country(data, iso2, country_name)
                projects.extend(parsed)
                logger.info(f"InfraCompass API {iso2}: {len(parsed)} records from {endpoint}")
                break

            except requests.exceptions.JSONDecodeError:
                continue
            except Exception as e:
                logger.debug(f"InfraCompass API {iso2} {endpoint}: {e}")
                continue

        time.sleep(0.4)

    return projects


def _parse_infracompass_country(data: dict, iso2: str, country_name: str) -> list[dict]:
    """Parse InfraCompass country data into PPP records."""
    records = []

    # Extract sector investment data
    sectors_data = data.get("sectors", data.get("indicators", data.get("data", {})))
    if isinstance(sectors_data, dict):
        for sector_key, sector_data in sectors_data.items():
            if not isinstance(sector_data, dict):
                continue

            investment = 0
            if "investment" in sector_data:
                investment = parse_amount(sector_data["investment"])
            elif "value" in sector_data:
                investment = parse_amount(sector_data["value"])

            if investment <= 0:
                continue

            sector = classify_sector(sector_key)
            ref = f"infracompass-{iso2}-{sector_key}"

            records.append(_build_ppp_record(
                source="infracompass",
                source_ref=ref,
                name=f"Infrastructure Investment: {sector_key.replace('_', ' ').title()} - {country_name}",
                country_code=iso2,
                sector=sector,
                stage="planning",
                investment_value=investment,
                description=f"InfraCompass data: {sector_key.replace('_', ' ').title()} infrastructure in {country_name}. Investment: ${investment:,.0f}.",
                source_url=f"{INFRACOMPASS_BASE}/ind/{ISO2_TO_ISO3.get(iso2, '').lower()}",
                metadata={
                    "data_type": "infrastructure_profile",
                    "raw_sector": sector_key,
                    "source_dataset": "infracompass",
                },
            ))

    # Extract investment gap if available
    gap = data.get("investment_gap") or data.get("gap")
    if gap:
        gap_val = parse_amount(gap)
        if gap_val > 0:
            records.append(_build_ppp_record(
                source="infracompass",
                source_ref=f"infracompass-gap-{iso2}",
                name=f"Infrastructure Investment Gap - {country_name}",
                country_code=iso2,
                sector="construction",
                stage="identification",
                investment_value=gap_val,
                description=f"InfraCompass: {country_name} has an infrastructure investment gap of ${gap_val:,.0f}. This represents PPP opportunity.",
                source_url=f"{INFRACOMPASS_BASE}/ind/{ISO2_TO_ISO3.get(iso2, '').lower()}",
                metadata={"data_type": "investment_gap"},
            ))

    return records


# =========================================================================
# Strategy 2: InfraCompass web scraping — country pages
# =========================================================================

def _scrape_infracompass_pages() -> list[dict]:
    """
    Scrape InfraCompass country pages for MENA infrastructure data.
    Extracts key metrics, reform indicators, and investment data.
    """
    projects = []

    for iso2, country_name in MENA_COUNTRIES.items():
        iso3 = ISO2_TO_ISO3.get(iso2, "").lower()
        if not iso3:
            continue

        urls = [
            f"{INFRACOMPASS_BASE}/ind/{iso3}",
            f"{INFRACOMPASS_BASE}/country/{iso3}",
            f"{INFRACOMPASS_BASE}/en/countries/{iso3}",
        ]

        for url in urls:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=20)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")

                # Look for data sections with investment/project information
                parsed = _parse_infracompass_page(soup, iso2, country_name, url)
                if parsed:
                    projects.extend(parsed)
                    logger.info(f"InfraCompass page {iso2}: {len(parsed)} records")
                    break

            except Exception as e:
                logger.debug(f"InfraCompass page {iso2} {url}: {e}")
                continue

        time.sleep(0.5)

    return projects


def _parse_infracompass_page(soup: BeautifulSoup, iso2: str, country_name: str, page_url: str) -> list[dict]:
    """Parse InfraCompass HTML page for infrastructure data."""
    records = []

    # Strategy: look for data cards, tables, or metric containers
    # Common patterns in infrastructure dashboards

    # Pattern 1: Look for metric cards
    for card in soup.select(".card, .metric, .indicator, .stat-card, .data-card, [class*='indicator']"):
        label_el = card.select_one(".label, .title, .metric-label, h3, h4, .card-title")
        value_el = card.select_one(".value, .number, .metric-value, .amount, .card-value")

        if not label_el or not value_el:
            continue

        label = label_el.get_text(strip=True)
        value_text = value_el.get_text(strip=True)
        value = parse_amount(value_text)

        if value <= 0 or not label:
            continue

        sector = classify_sector(label)
        ref = f"ic-page-{iso2}-{re.sub(r'[^a-z0-9]', '', label.lower())[:30]}"

        records.append(_build_ppp_record(
            source="infracompass",
            source_ref=ref,
            name=f"{label} - {country_name}",
            country_code=iso2,
            sector=sector,
            stage="planning",
            investment_value=value,
            description=f"InfraCompass: {label} for {country_name}. Value: {value_text}.",
            source_url=page_url,
            metadata={"data_type": "page_metric", "raw_label": label},
        ))

    # Pattern 2: Look for tables
    for table in soup.select("table"):
        rows = table.select("tr")
        headers_row = rows[0] if rows else None
        if not headers_row:
            continue

        headers_list = [th.get_text(strip=True).lower() for th in headers_row.select("th, td")]

        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.select("td")]
            if len(cells) < 2:
                continue

            row_data = dict(zip(headers_list, cells))
            name = row_data.get("project", "") or row_data.get("name", "") or cells[0]
            value_str = row_data.get("value", "") or row_data.get("investment", "") or row_data.get("amount", "")
            value = parse_amount(value_str) if value_str else 0

            if name and len(name) > 3:
                sector = classify_sector(name)
                ref = f"ic-tbl-{iso2}-{re.sub(r'[^a-z0-9]', '', name.lower())[:30]}"
                records.append(_build_ppp_record(
                    source="infracompass",
                    source_ref=ref,
                    name=f"{name} - {country_name}",
                    country_code=iso2,
                    sector=sector,
                    stage="planning",
                    investment_value=value,
                    description=f"InfraCompass table data: {name}.",
                    source_url=page_url,
                    metadata={"data_type": "page_table"},
                ))

    return records


# =========================================================================
# Strategy 3: Global Infrastructure Outlook API
# =========================================================================

def _scrape_gi_outlook() -> list[dict]:
    """
    Query Global Infrastructure Outlook for investment need forecasts.
    This provides forward-looking infrastructure investment data by
    sector and country, valuable for identifying PPP opportunities.
    """
    projects = []

    # Try the outlook API
    endpoints = [
        f"{GI_OUTLOOK_API}/countries",
        f"{GI_OUTLOOK_API}/v1/data",
        f"{GI_OUTLOOK_BASE}/api/data",
    ]

    country_data = None
    for endpoint in endpoints:
        try:
            resp = requests.get(endpoint, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                country_data = resp.json()
                logger.info(f"GI Outlook API responded: {endpoint}")
                break
        except Exception as e:
            logger.debug(f"GI Outlook {endpoint}: {e}")
            continue

    if not country_data:
        # Try scraping the outlook page directly
        return _scrape_gi_outlook_pages()

    # Parse API response
    if isinstance(country_data, list):
        items = country_data
    elif isinstance(country_data, dict):
        items = country_data.get("data", country_data.get("countries", []))
    else:
        return projects

    for item in items:
        if not isinstance(item, dict):
            continue

        country_code_raw = item.get("country_code") or item.get("iso3") or item.get("code", "")
        iso2 = None
        for k, v in ISO2_TO_ISO3.items():
            if v == country_code_raw.upper() or k == country_code_raw.upper():
                iso2 = k
                break

        if not iso2 or iso2 not in MENA_COUNTRIES:
            continue

        country_name = MENA_COUNTRIES[iso2]

        # Extract sector-level investment needs
        sector_fields = {
            "transport": ["transport", "transport_need", "roads", "rail", "ports", "airports"],
            "energy": ["energy", "energy_need", "electricity", "power"],
            "water": ["water", "water_need", "water_sanitation"],
            "telecom": ["telecom", "telecom_need", "telecommunications"],
        }

        for sector, field_names in sector_fields.items():
            for field in field_names:
                val = item.get(field)
                if val:
                    inv_value = parse_amount(val)
                    if inv_value > 0:
                        ref = f"gi-outlook-{iso2}-{sector}"
                        projects.append(_build_ppp_record(
                            source="gi_outlook",
                            source_ref=ref,
                            name=f"Infrastructure Need: {sector.title()} - {country_name}",
                            country_code=iso2,
                            sector=sector,
                            stage="identification",
                            investment_value=inv_value,
                            description=f"Global Infrastructure Outlook: {country_name} {sector} infrastructure investment need: ${inv_value:,.0f}.",
                            source_url=f"{GI_OUTLOOK_BASE}/countries/{ISO2_TO_ISO3.get(iso2, '').upper()}",
                            metadata={
                                "data_type": "investment_forecast",
                                "source_dataset": "global_infrastructure_outlook",
                            },
                        ))
                        break  # Use first matching field

    return projects


def _scrape_gi_outlook_pages() -> list[dict]:
    """Scrape GI Outlook country pages as fallback."""
    projects = []

    for iso2, country_name in MENA_COUNTRIES.items():
        iso3 = ISO2_TO_ISO3.get(iso2, "").upper()
        if not iso3:
            continue

        urls = [
            f"{GI_OUTLOOK_BASE}/countries/{iso3}",
            f"{GI_OUTLOOK_BASE}/country/{iso3.lower()}",
        ]

        for url in urls:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=20)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")

                # Look for embedded JSON data
                for script in soup.select("script"):
                    text = script.string or ""
                    if "investment" in text.lower() or "infrastructure" in text.lower():
                        # Try to extract JSON objects
                        json_matches = re.findall(r'\{[^{}]{50,}\}', text)
                        for match in json_matches:
                            try:
                                obj = json.loads(match)
                                if "investment" in str(obj).lower():
                                    for key, val in obj.items():
                                        if isinstance(val, (int, float)) and val > 1_000_000:
                                            sector = classify_sector(key)
                                            ref = f"gio-{iso2}-{re.sub(r'[^a-z0-9]', '', key.lower())[:20]}"
                                            projects.append(_build_ppp_record(
                                                source="gi_outlook",
                                                source_ref=ref,
                                                name=f"Investment Need: {key.replace('_', ' ').title()} - {country_name}",
                                                country_code=iso2,
                                                sector=sector,
                                                stage="identification",
                                                investment_value=val,
                                                description=f"GI Outlook: {key.replace('_', ' ')} investment need for {country_name}: ${val:,.0f}.",
                                                source_url=url,
                                                metadata={"data_type": "page_extracted"},
                                            ))
                            except (json.JSONDecodeError, ValueError):
                                continue

                break  # Successful page load

            except Exception as e:
                logger.debug(f"GI Outlook page {iso2} {url}: {e}")

        time.sleep(0.5)

    return projects


# =========================================================================
# Strategy 4: PPP Knowledge Lab — World Bank PPP portal
# =========================================================================

def _scrape_ppp_knowledge_lab() -> list[dict]:
    """
    Scrape PPP Knowledge Lab (ppp.worldbank.org) for country PPP data.
    This contains PPP frameworks, project lists, and legislative info.
    """
    projects = []

    for iso2, country_name in MENA_COUNTRIES.items():
        iso3 = ISO2_TO_ISO3.get(iso2, "").lower()
        if not iso3:
            continue

        # Try API endpoint
        api_urls = [
            f"{PPP_KB_API}/countries/{iso3}",
            f"{PPP_KB_API}/v1/country/{iso3}/projects",
            f"{PPP_KNOWLEDGE_LAB}/country/{country_name.lower().replace(' ', '-')}",
        ]

        for url in api_urls:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=20)
                if resp.status_code != 200:
                    continue

                # Check if JSON
                content_type = resp.headers.get("Content-Type", "")
                if "json" in content_type:
                    data = resp.json()
                    parsed = _parse_ppp_kb_json(data, iso2, country_name, url)
                    if parsed:
                        projects.extend(parsed)
                        logger.info(f"PPP KB API {iso2}: {len(parsed)} records")
                        break
                elif "html" in content_type:
                    parsed = _parse_ppp_kb_page(resp.text, iso2, country_name, url)
                    if parsed:
                        projects.extend(parsed)
                        logger.info(f"PPP KB page {iso2}: {len(parsed)} records")
                        break

            except Exception as e:
                logger.debug(f"PPP KB {iso2} {url}: {e}")

        time.sleep(0.4)

    return projects


def _parse_ppp_kb_json(data: dict, iso2: str, country_name: str, base_url: str) -> list[dict]:
    """Parse PPP Knowledge Lab JSON response."""
    records = []

    # Handle different response formats
    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("projects", data.get("data", data.get("results", [])))
        if not isinstance(items, list):
            items = [data]

    for item in items:
        if not isinstance(item, dict):
            continue

        name = item.get("title") or item.get("name") or item.get("project_name") or ""
        if not name or len(name) < 5:
            continue

        ref = str(item.get("id") or item.get("project_id") or name[:80])
        sector_raw = item.get("sector") or item.get("category") or ""
        stage_raw = item.get("status") or item.get("stage") or ""
        value = parse_amount(item.get("value") or item.get("investment") or item.get("cost") or 0)
        desc = item.get("description") or item.get("summary") or ""
        contract_raw = item.get("contract_type") or item.get("type") or ""

        records.append(_build_ppp_record(
            source="ppp_knowledge_lab",
            source_ref=f"ppkb-{ref}",
            name=name,
            country_code=iso2,
            sector=classify_sector(f"{name} {sector_raw} {desc}"),
            stage=_map_stage(stage_raw),
            contract_type=classify_ppp_contract(f"{contract_raw} {name} {desc}"),
            investment_value=value,
            description=desc[:500] if desc else f"PPP Knowledge Lab: {name} in {country_name}.",
            source_url=base_url,
            metadata={"raw_sector": sector_raw, "raw_stage": stage_raw},
        ))

    return records


def _parse_ppp_kb_page(html: str, iso2: str, country_name: str, page_url: str) -> list[dict]:
    """Parse PPP Knowledge Lab HTML page."""
    records = []
    soup = BeautifulSoup(html, "html.parser")

    # Look for project listings
    for item in soup.select(".project-item, .node-project, .views-row, article.project, .project-card"):
        title_el = item.select_one("h2, h3, h4, .title, .project-title a, a.title")
        if not title_el:
            continue
        name = title_el.get_text(strip=True)
        if not name or len(name) < 5:
            continue

        # Extract URL
        link = title_el.get("href") or ""
        if title_el.name != "a":
            link_el = title_el.select_one("a")
            if link_el:
                link = link_el.get("href", "")
        if link and not link.startswith("http"):
            link = f"{PPP_KNOWLEDGE_LAB}{link}"

        # Extract metadata
        desc_el = item.select_one(".description, .summary, .body, p")
        desc = desc_el.get_text(strip=True)[:500] if desc_el else ""

        sector_el = item.select_one(".sector, .field-sector, .category")
        sector_text = sector_el.get_text(strip=True) if sector_el else ""

        value_el = item.select_one(".value, .investment, .cost, .amount")
        value = parse_amount(value_el.get_text(strip=True)) if value_el else 0

        ref = f"ppkb-page-{iso2}-{re.sub(r'[^a-z0-9]', '', name.lower())[:30]}"

        records.append(_build_ppp_record(
            source="ppp_knowledge_lab",
            source_ref=ref,
            name=name,
            country_code=iso2,
            sector=classify_sector(f"{name} {sector_text} {desc}"),
            stage="planning",
            contract_type=classify_ppp_contract(f"{name} {desc}"),
            investment_value=value,
            description=desc or f"PPP Knowledge Lab: {name}",
            source_url=link or page_url,
            metadata={"data_type": "page_project"},
        ))

    # Also look for country framework data
    for section in soup.select(".country-data, .ppp-framework, .country-profile"):
        text = section.get_text(" ", strip=True)
        # Extract investment amounts
        amount_matches = re.findall(r'\$\s*([\d,.]+)\s*(million|billion|M|B)', text, re.IGNORECASE)
        for amount_str, unit in amount_matches:
            multiplier = 1_000_000 if unit.lower() in ("million", "m") else 1_000_000_000
            value = parse_amount(amount_str) * multiplier if parse_amount(amount_str) < 10000 else parse_amount(amount_str)
            if value > 0:
                ref = f"ppkb-fw-{iso2}-{len(records)}"
                records.append(_build_ppp_record(
                    source="ppp_knowledge_lab",
                    source_ref=ref,
                    name=f"PPP Framework Investment - {country_name}",
                    country_code=iso2,
                    sector="construction",
                    stage="identification",
                    investment_value=value,
                    description=f"PPP Knowledge Lab framework data for {country_name}: ${value:,.0f}.",
                    source_url=page_url,
                    metadata={"data_type": "framework_data"},
                ))

    return records


# =========================================================================
# Strategy 5: World Bank Open Data — infrastructure project search
# =========================================================================

WB_SEARCH_API = "https://search.worldbank.org/api/v2/projects"


def _scrape_wb_infra_projects() -> list[dict]:
    """
    Search World Bank projects for infrastructure/PPP in MENA.
    Broader search than PPP-specific to capture infrastructure pipeline.
    """
    projects = []

    search_terms = [
        "infrastructure investment",
        "public private partnership",
        "transport infrastructure",
        "energy infrastructure",
        "water infrastructure",
    ]

    for iso2 in MENA_COUNTRIES:
        country_projects = []

        for term in search_terms:
            try:
                params = {
                    "format": "json",
                    "countrycode_exact": iso2,
                    "rows": 50,
                    "os": 0,
                    "qterm": term,
                    "status_exact": "Active",
                    "fl": "id,project_name,boardapprovaldate,closingdate,totalamt,sector1,theme1,lendinginstr,status,url,borrower",
                }
                resp = requests.get(WB_SEARCH_API, params=params, headers=HEADERS, timeout=25)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                proj_dict = data.get("projects", {})
                if not isinstance(proj_dict, dict):
                    continue

                for key, proj in proj_dict.items():
                    if not isinstance(proj, dict):
                        continue

                    name = proj.get("project_name", "")
                    if not name:
                        continue

                    # Skip if already captured
                    if any(p["name"] == name for p in country_projects):
                        continue

                    project_id = proj.get("id", "")
                    sector_raw = proj.get("sector1", "")
                    amount = parse_amount(proj.get("totalamt", 0))
                    borrower = proj.get("borrower", "")
                    approval = proj.get("boardapprovaldate", "")
                    proj_url = proj.get("url", "")

                    country_projects.append(_build_ppp_record(
                        source="wb_infrastructure",
                        source_ref=f"wb-infra-{project_id or name[:60]}",
                        name=name,
                        country_code=iso2,
                        sector=classify_sector(f"{name} {sector_raw}"),
                        stage="construction",
                        contract_type=classify_ppp_contract(f"{name} {sector_raw}"),
                        investment_value=amount,
                        government_entity=borrower,
                        description=f"World Bank infrastructure project: {name}. Sector: {sector_raw}. Commitment: ${amount:,.0f}.",
                        financial_close_date=parse_date(str(approval)) if approval else None,
                        source_url=proj_url,
                        metadata={
                            "wb_project_id": project_id,
                            "search_term": term,
                        },
                    ))

                time.sleep(0.3)

            except Exception as e:
                logger.debug(f"WB infra search {iso2} '{term}': {e}")

        projects.extend(country_projects)
        if country_projects:
            logger.info(f"WB infra {iso2}: {len(country_projects)} projects")

    return projects


# =========================================================================
# Deduplication
# =========================================================================

def _deduplicate(projects: list[dict]) -> list[dict]:
    """Remove duplicates by source_ref and by name+country similarity."""
    seen_refs: set[str] = set()
    seen_keys: set[str] = set()
    unique = []

    for p in projects:
        ref = p.get("source_ref", "")
        if ref and ref in seen_refs:
            continue

        key = re.sub(r"[^a-z0-9]", "", p.get("name", "").lower()) + p.get("country_code", "")
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
    Scrape infrastructure project data from multiple global infrastructure sources.

    Strategies:
    1. InfraCompass API (country-level infrastructure data)
    2. InfraCompass web pages (fallback scraping)
    3. Global Infrastructure Outlook (investment forecasts)
    4. PPP Knowledge Lab (WB PPP portal)
    5. World Bank infrastructure project search
    """
    all_projects: list[dict] = []

    # Strategy 1: InfraCompass API
    logger.info("--- Strategy 1: InfraCompass API ---")
    ic_api = _scrape_infracompass_api()
    logger.info(f"InfraCompass API: {len(ic_api)} records")
    all_projects.extend(ic_api)

    # Strategy 2: InfraCompass web pages (if API yielded little)
    if len(ic_api) < 10:
        logger.info("--- Strategy 2: InfraCompass pages ---")
        ic_pages = _scrape_infracompass_pages()
        logger.info(f"InfraCompass pages: {len(ic_pages)} records")
        all_projects.extend(ic_pages)

    # Strategy 3: Global Infrastructure Outlook
    logger.info("--- Strategy 3: GI Outlook ---")
    outlook = _scrape_gi_outlook()
    logger.info(f"GI Outlook: {len(outlook)} records")
    all_projects.extend(outlook)

    # Strategy 4: PPP Knowledge Lab
    logger.info("--- Strategy 4: PPP Knowledge Lab ---")
    kb = _scrape_ppp_knowledge_lab()
    logger.info(f"PPP Knowledge Lab: {len(kb)} records")
    all_projects.extend(kb)

    # Strategy 5: WB infrastructure projects
    logger.info("--- Strategy 5: WB Infrastructure Projects ---")
    wb_infra = _scrape_wb_infra_projects()
    logger.info(f"WB Infrastructure: {len(wb_infra)} records")
    all_projects.extend(wb_infra)

    # Deduplicate
    unique = _deduplicate(all_projects)
    logger.info(f"Infrastructure projects total: {len(unique)} unique (from {len(all_projects)} raw)")

    return unique


if __name__ == "__main__":
    results = scrape()
    save_ppp_projects(results, "infra_projects")
    print(f"Scraped {len(results)} infrastructure/PPP projects from global sources")
