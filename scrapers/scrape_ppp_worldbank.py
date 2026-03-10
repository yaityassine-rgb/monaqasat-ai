"""
Scraper for World Bank PPI (Private Participation in Infrastructure) Database.
Source: https://ppi.worldbank.org/

Strategy:
1. Primary: World Bank PPI API via bulk CSV download endpoint
2. Secondary: World Bank Data API v2 for infrastructure indicators
3. Tertiary: IATI Datastore for WB-funded PPP projects

Covers MENA countries, focusing on projects from 2015 onwards.
Data includes: project name, country, sector, type, financial closure,
total investment, private investment, debt, equity.
"""

import csv
import io
import json
import logging
import re
import time
from datetime import datetime
from typing import Optional

import requests

from config import (
    HEADERS,
    MENA_COUNTRIES,
    MENA_COUNTRIES_AR,
    MENA_COUNTRIES_FR,
    PPP_DIR,
)
from base_scraper import (
    classify_sector,
    classify_ppp_contract,
    generate_ppp_id,
    parse_date,
    parse_amount,
    save_ppp_projects,
)

logger = logging.getLogger("ppp_worldbank")

# ---------------------------------------------------------------------------
# PPI Database endpoints
# ---------------------------------------------------------------------------
PPI_CSV_URL = "https://ppi.worldbank.org/en/ppi/generate-csv"
PPI_API_URL = "https://ppi.worldbank.org/api/v1/ppi"
PPI_SEARCH_URL = "https://ppi.worldbank.org/en/ppi"

# World Bank Data API
WB_DATA_API = "https://api.worldbank.org/v2"

# IATI Datastore (WB org)
IATI_API = "https://datastore.codeforiati.org/api/1/access/activity.json"
WB_IATI_ORG = "XM-DAC-44000"

# ---------------------------------------------------------------------------
# PPI sector mapping
# ---------------------------------------------------------------------------
PPI_SECTOR_MAP = {
    "energy": "energy",
    "electricity": "energy",
    "natural gas": "energy",
    "transport": "transport",
    "airports": "transport",
    "ports": "transport",
    "railways": "transport",
    "roads": "transport",
    "telecom": "telecom",
    "telecoms": "telecom",
    "water and sewerage": "water",
    "water": "water",
    "ict": "telecom",
    "municipal solid waste": "water",
    "treatment plant": "water",
}

# PPI stage mapping from status strings
PPI_STAGE_MAP = {
    "active": "operational",
    "concluded": "operational",
    "under construction": "construction",
    "construction": "construction",
    "cancelled": "cancelled",
    "distressed": "operational",
    "merged": "operational",
}

# ---------------------------------------------------------------------------
# Country code mapping (World Bank uses ISO3 in some APIs)
# ---------------------------------------------------------------------------
ISO2_TO_ISO3 = {
    "MA": "MAR", "SA": "SAU", "AE": "ARE", "EG": "EGY", "KW": "KWT",
    "QA": "QAT", "BH": "BHR", "OM": "OMN", "JO": "JOR", "TN": "TUN",
    "DZ": "DZA", "LY": "LBY", "IQ": "IRQ", "LB": "LBN", "PS": "PSE",
    "SD": "SDN", "YE": "YEM", "MR": "MRT",
}

ISO3_TO_ISO2 = {v: k for k, v in ISO2_TO_ISO3.items()}

# World Bank country names may differ slightly
WB_NAME_TO_CODE = {}
for code, name in MENA_COUNTRIES.items():
    WB_NAME_TO_CODE[name.lower()] = code
    WB_NAME_TO_CODE[name.lower().replace(" ", "")] = code
# Add aliases
WB_NAME_TO_CODE["united arab emirates"] = "AE"
WB_NAME_TO_CODE["uae"] = "AE"
WB_NAME_TO_CODE["west bank and gaza"] = "PS"
WB_NAME_TO_CODE["west bank"] = "PS"
WB_NAME_TO_CODE["palestinian territories"] = "PS"
WB_NAME_TO_CODE["syrian arab republic"] = "SY"


def _resolve_country_code(country_str: str) -> Optional[str]:
    """Resolve a country name/code to ISO2 for MENA countries."""
    if not country_str:
        return None
    s = country_str.strip()
    # Direct ISO2
    if s.upper() in MENA_COUNTRIES:
        return s.upper()
    # Direct ISO3
    if s.upper() in ISO3_TO_ISO2:
        return ISO3_TO_ISO2[s.upper()]
    # Name match
    return WB_NAME_TO_CODE.get(s.lower())


def _map_ppi_sector(raw: str) -> str:
    """Map PPI sector string to our sector taxonomy."""
    if not raw:
        return "construction"
    lower = raw.lower().strip()
    for key, sector in PPI_SECTOR_MAP.items():
        if key in lower:
            return sector
    return classify_sector(raw)


def _map_ppi_stage(raw: str) -> str:
    """Map PPI status to our pipeline stage."""
    if not raw:
        return "operational"
    lower = raw.lower().strip()
    for key, stage in PPI_STAGE_MAP.items():
        if key in lower:
            return stage
    return "operational"


def _build_ppp_record(
    source_ref: str,
    name: str,
    country_code: str,
    sector: str,
    subsector: str = "",
    stage: str = "operational",
    contract_type: str = "concession",
    investment_value: float = 0,
    debt_value: float = 0,
    equity_value: float = 0,
    currency: str = "USD",
    government_entity: str = "",
    sponsors: list = None,
    lenders: list = None,
    description: str = "",
    financial_close_date: str = None,
    contract_duration_years: int = None,
    source_url: str = "",
    metadata: dict = None,
) -> dict:
    """Build a standardized PPP project record."""
    country_name = MENA_COUNTRIES.get(country_code, "")
    country_ar = MENA_COUNTRIES_AR.get(country_code, "")
    country_fr = MENA_COUNTRIES_FR.get(country_code, "")

    return {
        "id": generate_ppp_id("ppi_database", source_ref),
        "name": name,
        "name_ar": "",
        "name_fr": "",
        "source": "ppi_database",
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
        "debt_value": debt_value,
        "equity_value": equity_value,
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
        "contract_duration_years": contract_duration_years,
        "tender_deadline": None,
        "award_date": None,
        "tags": _build_tags(sector, investment_value, name),
        "metadata": metadata or {},
    }


def _build_tags(sector: str, value: float, name: str) -> list[str]:
    """Generate tags based on project attributes."""
    tags = []
    if sector:
        tags.append(sector)
    if value >= 1_000_000_000:
        tags.append("mega_project")
    if value >= 500_000_000:
        tags.append("large_project")
    name_lower = name.lower()
    for keyword in ["solar", "wind", "renewable", "green", "hydrogen"]:
        if keyword in name_lower:
            tags.append("green_energy")
            break
    for keyword in ["desalination", "water treatment", "wastewater"]:
        if keyword in name_lower:
            tags.append("water_infrastructure")
            break
    return list(set(tags))


# =========================================================================
# Strategy 1: PPI Database API / CSV download
# =========================================================================

def _scrape_ppi_api() -> list[dict]:
    """
    Try the PPI Database API.
    The PPI database may expose a JSON API or a CSV download endpoint.
    """
    projects = []

    # Try the PPI JSON API first
    for iso2, country_name in MENA_COUNTRIES.items():
        iso3 = ISO2_TO_ISO3.get(iso2)
        if not iso3:
            continue

        try:
            # Attempt PPI API with country filter
            url = f"{PPI_API_URL}"
            params = {
                "country": iso3,
                "format": "json",
                "year_from": 2015,
            }
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("results", data.get("data", []))
                if isinstance(items, list):
                    for item in items:
                        proj = _parse_ppi_json(item, iso2)
                        if proj:
                            projects.append(proj)
                    logger.info(f"PPI API {iso2}: {len(items)} records")
            else:
                logger.debug(f"PPI API {iso2}: HTTP {resp.status_code}")

        except requests.exceptions.JSONDecodeError:
            logger.debug(f"PPI API {iso2}: non-JSON response, trying CSV")
            # Try CSV endpoint
            csv_projects = _try_ppi_csv(iso2, iso3)
            projects.extend(csv_projects)
        except Exception as e:
            logger.debug(f"PPI API {iso2}: {e}")

        time.sleep(0.5)

    return projects


def _try_ppi_csv(iso2: str, iso3: str) -> list[dict]:
    """Try downloading PPI data as CSV."""
    projects = []
    try:
        params = {
            "country": iso3,
            "year_from": 2015,
            "format": "csv",
        }
        resp = requests.get(PPI_CSV_URL, params=params, headers=HEADERS, timeout=60)
        if resp.status_code == 200 and "text/csv" in resp.headers.get("Content-Type", ""):
            reader = csv.DictReader(io.StringIO(resp.text))
            for row in reader:
                proj = _parse_ppi_csv_row(row, iso2)
                if proj:
                    projects.append(proj)
            logger.info(f"PPI CSV {iso2}: {len(projects)} records")
        else:
            logger.debug(f"PPI CSV {iso2}: HTTP {resp.status_code}")
    except Exception as e:
        logger.debug(f"PPI CSV {iso2}: {e}")

    return projects


def _parse_ppi_json(item: dict, country_code: str) -> Optional[dict]:
    """Parse a PPI API JSON record into our PPP format."""
    name = item.get("project_name") or item.get("name") or item.get("title", "")
    if not name:
        return None

    ref = str(item.get("ppi_id") or item.get("id") or item.get("project_id") or name[:80])
    sector_raw = item.get("sector") or item.get("primary_sector") or ""
    subsector = item.get("subsector") or item.get("sub_sector") or ""
    ppi_type = item.get("type") or item.get("ppi_type") or ""
    status = item.get("status") or ""

    total_inv = parse_amount(item.get("total_investment") or item.get("investment") or 0)
    debt = parse_amount(item.get("debt") or 0)
    equity = parse_amount(item.get("equity") or 0)

    # If total is in millions in the PPI database
    if total_inv > 0 and total_inv < 100000:
        total_inv *= 1_000_000
    if debt > 0 and debt < 100000:
        debt *= 1_000_000
    if equity > 0 and equity < 100000:
        equity *= 1_000_000

    fc_year = item.get("financial_closure_year") or item.get("financial_close") or ""
    fc_date = parse_date(str(fc_year)) if fc_year else None

    gov_entity = item.get("government_granting_authority") or item.get("awarding_authority") or ""
    sponsors_raw = item.get("sponsors") or item.get("private_sponsors") or ""
    sponsors = [s.strip() for s in str(sponsors_raw).split(",") if s.strip()] if sponsors_raw else []

    contract_text = f"{ppi_type} {name} {item.get('description', '')}"
    contract_type = classify_ppp_contract(contract_text)

    desc = item.get("description") or f"PPI Database: {name} in {MENA_COUNTRIES.get(country_code, '')}. Sector: {sector_raw}. Total investment: ${total_inv:,.0f}."

    return _build_ppp_record(
        source_ref=ref,
        name=name,
        country_code=country_code,
        sector=_map_ppi_sector(sector_raw),
        subsector=subsector.lower().replace(" ", "_") if subsector else "",
        stage=_map_ppi_stage(status),
        contract_type=contract_type,
        investment_value=total_inv,
        debt_value=debt,
        equity_value=equity,
        government_entity=gov_entity,
        sponsors=sponsors,
        description=desc,
        financial_close_date=fc_date,
        source_url=f"https://ppi.worldbank.org/en/snapshots/project/{ref}",
        metadata={
            "ppi_type": ppi_type,
            "financial_closure_year": str(fc_year),
            "raw_sector": sector_raw,
        },
    )


def _parse_ppi_csv_row(row: dict, default_country: str) -> Optional[dict]:
    """Parse a PPI CSV row into our PPP format."""
    # CSV column names vary; try common variants
    name = (
        row.get("Project Name")
        or row.get("project_name")
        or row.get("Project name")
        or row.get("Name")
        or ""
    ).strip()
    if not name:
        return None

    ref = (
        row.get("PPI ID")
        or row.get("ppi_id")
        or row.get("Project ID")
        or row.get("project_id")
        or name[:80]
    )

    # Country resolution
    country_raw = row.get("Country") or row.get("country") or ""
    country_code = _resolve_country_code(country_raw) or default_country
    if country_code not in MENA_COUNTRIES:
        return None

    sector_raw = row.get("Sector") or row.get("sector") or row.get("Primary Sector") or ""
    subsector_raw = row.get("Subsector") or row.get("Sub-sector") or row.get("subsector") or ""
    ppi_type = row.get("Type") or row.get("PPI Type") or row.get("type") or ""
    status = row.get("Status") or row.get("status") or ""

    total_inv = parse_amount(row.get("Total Investment") or row.get("total_investment") or 0)
    debt = parse_amount(row.get("Debt") or row.get("debt") or 0)
    equity = parse_amount(row.get("Equity") or row.get("equity") or 0)

    # PPI reports values in millions USD
    if total_inv > 0 and total_inv < 500000:
        total_inv *= 1_000_000
    if debt > 0 and debt < 500000:
        debt *= 1_000_000
    if equity > 0 and equity < 500000:
        equity *= 1_000_000

    fc_year = row.get("Financial Closure Year") or row.get("Financial Closure") or ""
    fc_date = parse_date(str(fc_year)) if fc_year else None

    gov_entity = row.get("Government Granting Authority") or row.get("Awarding Authority") or ""
    sponsors_raw = row.get("Sponsors") or row.get("Private Sponsors") or ""
    sponsors = [s.strip() for s in str(sponsors_raw).split(";") if s.strip()] if sponsors_raw else []

    contract_text = f"{ppi_type} {name} {subsector_raw}"
    contract_type = classify_ppp_contract(contract_text)

    return _build_ppp_record(
        source_ref=str(ref),
        name=name,
        country_code=country_code,
        sector=_map_ppi_sector(sector_raw),
        subsector=subsector_raw.lower().replace(" ", "_") if subsector_raw else "",
        stage=_map_ppi_stage(status),
        contract_type=contract_type,
        investment_value=total_inv,
        debt_value=debt,
        equity_value=equity,
        government_entity=gov_entity,
        sponsors=sponsors,
        description=f"World Bank PPI: {name}. Country: {MENA_COUNTRIES.get(country_code, '')}. Sector: {sector_raw}. Type: {ppi_type}. Investment: ${total_inv:,.0f}.",
        financial_close_date=fc_date,
        source_url=f"https://ppi.worldbank.org/en/snapshots/project/{ref}",
        metadata={
            "ppi_type": ppi_type,
            "financial_closure_year": str(fc_year),
            "raw_sector": sector_raw,
            "raw_subsector": subsector_raw,
        },
    )


# =========================================================================
# Strategy 2: World Bank Data API v2 — infrastructure indicators
# =========================================================================

def _scrape_wb_data_api() -> list[dict]:
    """
    Query WB Data API for PPI indicators.
    Indicator codes:
      IE.PPI.TRAN.CD — PPI in transport (current USD)
      IE.PPI.ENGY.CD — PPI in energy (current USD)
      IE.PPI.WATS.CD — PPI in water & sanitation (current USD)
      IE.PPI.TELE.CD — PPI in telecom (current USD)
    These are aggregate country-level indicators, not project-level.
    We use them to generate summary records when the PPI project API is down.
    """
    projects = []

    indicators = {
        "IE.PPI.TRAN.CD": ("transport", "PPI in Transport"),
        "IE.PPI.ENGY.CD": ("energy", "PPI in Energy"),
        "IE.PPI.WATS.CD": ("water", "PPI in Water & Sanitation"),
        "IE.PPI.TELE.CD": ("telecom", "PPI in Telecom"),
    }

    iso3_codes = ";".join(ISO2_TO_ISO3.get(c, c) for c in MENA_COUNTRIES)

    for indicator_code, (sector, label) in indicators.items():
        try:
            url = f"{WB_DATA_API}/country/{iso3_codes}/indicator/{indicator_code}"
            params = {
                "format": "json",
                "date": "2015:2026",
                "per_page": 500,
            }
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.debug(f"WB Data API {indicator_code}: HTTP {resp.status_code}")
                continue

            data = resp.json()
            if not isinstance(data, list) or len(data) < 2:
                continue

            records = data[1]
            if not isinstance(records, list):
                continue

            # Group by country, take most recent non-null value
            country_latest: dict[str, dict] = {}
            for rec in records:
                if not rec.get("value"):
                    continue
                iso3 = rec.get("countryiso3code") or rec.get("country", {}).get("id", "")
                iso2 = ISO3_TO_ISO2.get(iso3)
                if not iso2:
                    continue
                year = int(rec.get("date", "0"))
                if iso2 not in country_latest or year > country_latest[iso2]["year"]:
                    country_latest[iso2] = {
                        "year": year,
                        "value": float(rec["value"]),
                        "country_name": rec.get("country", {}).get("value", MENA_COUNTRIES.get(iso2, "")),
                    }

            for iso2, info in country_latest.items():
                ref = f"wb-ppi-{indicator_code}-{iso2}-{info['year']}"
                name = f"{label} - {info['country_name']} ({info['year']})"
                projects.append(_build_ppp_record(
                    source_ref=ref,
                    name=name,
                    country_code=iso2,
                    sector=sector,
                    stage="operational",
                    contract_type="concession",
                    investment_value=info["value"],
                    description=f"World Bank aggregate PPI indicator: {label} for {info['country_name']}. Year: {info['year']}. Total private participation: ${info['value']:,.0f}.",
                    source_url=f"https://data.worldbank.org/indicator/{indicator_code}?locations={ISO2_TO_ISO3.get(iso2, iso2)}",
                    metadata={
                        "indicator": indicator_code,
                        "year": info["year"],
                        "data_type": "aggregate_indicator",
                    },
                ))

            logger.info(f"WB Data API {indicator_code}: {len(country_latest)} country records")
            time.sleep(0.3)

        except Exception as e:
            logger.error(f"WB Data API {indicator_code}: {e}")

    return projects


# =========================================================================
# Strategy 3: World Bank IATI activities tagged as PPP / infrastructure
# =========================================================================

PPP_KEYWORDS = [
    "public-private partnership", "ppp", "private participation",
    "concession", "build-operate-transfer", "BOT", "BOO", "BOOT",
    "privatization", "divestiture", "infrastructure investment",
]


def _scrape_wb_iati_ppp() -> list[dict]:
    """
    Scrape WB IATI activities that mention PPP-related keywords.
    This catches individual WB-funded PPP projects.
    """
    projects = []

    for iso2, country_name in MENA_COUNTRIES.items():
        try:
            params = {
                "reporting-org": WB_IATI_ORG,
                "recipient-country": iso2,
                "limit": 100,
                "offset": 0,
            }
            resp = requests.get(IATI_API, params=params, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                continue

            data = resp.json()
            activities = data.get("iati-activities", [])

            for entry in activities:
                act = entry.get("iati-activity", entry)

                # Extract title
                title_field = act.get("title", {})
                narratives = title_field.get("narrative", []) if isinstance(title_field, dict) else []
                if isinstance(narratives, dict):
                    narratives = [narratives]
                title = ""
                for n in narratives:
                    if isinstance(n, dict):
                        title = n.get("text", "")
                        if title:
                            break
                if not title:
                    continue

                # Extract description
                desc_field = act.get("description", {})
                if isinstance(desc_field, list):
                    desc_field = desc_field[0] if desc_field else {}
                desc_narratives = desc_field.get("narrative", []) if isinstance(desc_field, dict) else []
                if isinstance(desc_narratives, dict):
                    desc_narratives = [desc_narratives]
                desc = ""
                for n in desc_narratives:
                    if isinstance(n, dict):
                        desc = n.get("text", "")
                        if desc:
                            break

                # Check if PPP-related
                combined = f"{title} {desc}".lower()
                is_ppp = any(kw in combined for kw in PPP_KEYWORDS)
                if not is_ppp:
                    continue

                # Budget
                budget_data = act.get("budget", [])
                if isinstance(budget_data, dict):
                    budget_data = [budget_data]
                total_budget = 0
                for b in budget_data:
                    val = b.get("value", {})
                    if isinstance(val, dict):
                        try:
                            total_budget += float(val.get("text", "0"))
                        except (ValueError, TypeError):
                            pass

                # Dates
                dates = act.get("activity-date", [])
                if isinstance(dates, dict):
                    dates = [dates]
                start_date = None
                end_date = None
                for d in dates:
                    dtype = str(d.get("type", ""))
                    iso = d.get("iso-date", "")
                    if dtype in ("1", "2"):
                        start_date = iso
                    elif dtype in ("3", "4"):
                        end_date = iso

                iati_id = act.get("iati-identifier", "")
                contract_type = classify_ppp_contract(combined)
                sector = classify_sector(combined)

                projects.append(_build_ppp_record(
                    source_ref=iati_id or title[:80],
                    name=title,
                    country_code=iso2,
                    sector=sector,
                    stage="operational" if end_date else "construction",
                    contract_type=contract_type,
                    investment_value=total_budget,
                    description=desc[:500] if desc else f"World Bank PPP project: {title}",
                    financial_close_date=parse_date(start_date) if start_date else None,
                    source_url=f"https://projects.worldbank.org/en/projects-operations/project-detail/{iati_id.split('-')[-1]}" if iati_id else "",
                    metadata={
                        "iati_id": iati_id,
                        "data_source": "iati_datastore",
                    },
                ))

            logger.info(f"WB IATI {iso2}: {len([p for p in projects if p['country_code'] == iso2])} PPP activities")
            time.sleep(0.3)

        except Exception as e:
            logger.debug(f"WB IATI {iso2}: {e}")

    return projects


# =========================================================================
# Strategy 4: World Bank Projects API — PPP-tagged projects
# =========================================================================

WB_PROJECTS_API = "https://search.worldbank.org/api/v2/projects"


def _scrape_wb_projects_ppp() -> list[dict]:
    """
    Search WB Projects API for PPP/infrastructure projects in MENA.
    Filters on theme codes and keywords.
    """
    projects = []

    for iso2 in MENA_COUNTRIES:
        offset = 0
        page_size = 100
        fetched_for_country = 0

        while offset < 500:
            try:
                params = {
                    "format": "json",
                    "countrycode_exact": iso2,
                    "rows": page_size,
                    "os": offset,
                    "qterm": "public private partnership OR PPP OR concession OR BOT OR privatization",
                    "fl": "id,project_name,boardapprovaldate,closingdate,totalamt,countryname,sector1,theme1,lendinginstr,status,url,borrower",
                }
                resp = requests.get(WB_PROJECTS_API, params=params, headers=HEADERS, timeout=30)
                if resp.status_code != 200:
                    break

                data = resp.json()
                total = int(data.get("total", 0))
                proj_dict = data.get("projects", {})

                if isinstance(proj_dict, dict):
                    proj_list = [v for v in proj_dict.values() if isinstance(v, dict)]
                else:
                    break

                if not proj_list:
                    break

                for proj in proj_list:
                    name = proj.get("project_name", "")
                    if not name:
                        continue

                    project_id = proj.get("id", "")
                    sector_raw = proj.get("sector1", "")
                    theme_raw = proj.get("theme1", "")
                    amount = parse_amount(proj.get("totalamt", 0))
                    borrower = proj.get("borrower", "")
                    approval = proj.get("boardapprovaldate", "")
                    proj_url = proj.get("url", "")
                    status = proj.get("status", "Active")

                    # Determine stage
                    if status == "Active":
                        stage = "construction"
                    elif status == "Closed":
                        stage = "operational"
                    else:
                        stage = "planning"

                    combined = f"{name} {sector_raw} {theme_raw}".lower()
                    contract_type = classify_ppp_contract(combined)
                    sector = classify_sector(combined)

                    projects.append(_build_ppp_record(
                        source_ref=project_id or name[:80],
                        name=name,
                        country_code=iso2,
                        sector=sector,
                        stage=stage,
                        contract_type=contract_type,
                        investment_value=amount,
                        government_entity=borrower,
                        description=f"World Bank Project: {name}. Sector: {sector_raw}. Theme: {theme_raw}. Commitment: ${amount:,.0f}.",
                        financial_close_date=parse_date(str(approval)) if approval else None,
                        source_url=proj_url,
                        metadata={
                            "wb_project_id": project_id,
                            "lending_instrument": proj.get("lendinginstr", ""),
                            "wb_status": status,
                        },
                    ))
                    fetched_for_country += 1

                offset += page_size
                if offset >= total:
                    break
                time.sleep(0.3)

            except Exception as e:
                logger.error(f"WB Projects PPP {iso2}: {e}")
                break

        if fetched_for_country:
            logger.info(f"WB Projects PPP {iso2}: {fetched_for_country} projects")

    return projects


# =========================================================================
# Deduplication
# =========================================================================

def _deduplicate(projects: list[dict]) -> list[dict]:
    """Remove duplicate projects by source_ref or similar name+country."""
    seen_refs: set[str] = set()
    seen_keys: set[str] = set()
    unique = []

    for p in projects:
        ref = p.get("source_ref", "")
        if ref and ref in seen_refs:
            continue

        # Fuzzy dedup by normalized name + country
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
    Scrape World Bank PPI Database and related APIs for MENA PPP projects.

    Tries multiple strategies in order:
    1. PPI Database API / CSV
    2. WB Projects API (PPP-tagged)
    3. WB IATI Datastore (PPP keywords)
    4. WB Data API (aggregate PPI indicators as fallback)
    """
    all_projects: list[dict] = []

    # Strategy 1: PPI Database
    logger.info("--- Strategy 1: PPI Database API ---")
    ppi_projects = _scrape_ppi_api()
    logger.info(f"PPI Database: {len(ppi_projects)} projects")
    all_projects.extend(ppi_projects)

    # Strategy 2: WB Projects API — PPP tagged
    logger.info("--- Strategy 2: WB Projects API (PPP) ---")
    wb_projects = _scrape_wb_projects_ppp()
    logger.info(f"WB Projects PPP: {len(wb_projects)} projects")
    all_projects.extend(wb_projects)

    # Strategy 3: IATI Datastore — WB PPP activities
    logger.info("--- Strategy 3: WB IATI Datastore ---")
    iati_projects = _scrape_wb_iati_ppp()
    logger.info(f"WB IATI PPP: {len(iati_projects)} projects")
    all_projects.extend(iati_projects)

    # Strategy 4: WB Data API aggregate indicators (fallback context)
    if len(all_projects) < 20:
        logger.info("--- Strategy 4: WB Data API indicators (fallback) ---")
        indicator_projects = _scrape_wb_data_api()
        logger.info(f"WB Data API: {len(indicator_projects)} indicator records")
        all_projects.extend(indicator_projects)

    # Deduplicate
    unique = _deduplicate(all_projects)
    logger.info(f"World Bank PPP total: {len(unique)} unique projects (from {len(all_projects)} raw)")

    return unique


if __name__ == "__main__":
    results = scrape()
    save_ppp_projects(results, "ppi_database")
    print(f"Scraped {len(results)} PPP projects from World Bank PPI Database")
