"""
Grant scraper for UN-Habitat and additional UN agencies.
Sources:
  - UNGM extended agency search: https://www.ungm.org/Public/Notice/Search
  - UN-Habitat procurement: https://procurement.unhabitat.org/
  - IATI Datastore (UN-Habitat org): XM-DAC-41120

This scraper focuses on UN agencies NOT fully covered by the existing
scrape_grants_ungm.py scraper, with emphasis on:
  - UN-Habitat (human settlements, urban development)
  - UNDP (development projects)
  - UNICEF (children's programs)
  - WHO (health)
  - WFP (food programs)
  - UNOPS (project services)
  - ESCWA (Economic and Social Commission for Western Asia)
  - UNRWA (Palestine refugees)
  - FAO (agriculture)

Uses IATI Datastore to get structured project data with budgets and
multilingual titles not available through UNGM HTML scraping.

Currency: USD
"""

import requests
import logging
import time
from config import (
    HEADERS, MENA_COUNTRIES, MENA_COUNTRIES_AR, MENA_COUNTRIES_FR,
)
from base_scraper import (
    generate_grant_id, classify_sector, classify_grant_type,
    parse_date, parse_amount, save_grants,
)

logger = logging.getLogger("grants_un_habitat")

IATI_API = "https://datastore.codeforiati.org/api/1/access/activity.json"

# UN agency IATI organisation identifiers
UN_AGENCY_ORGS = {
    "XM-DAC-41120": {
        "name": "UN-Habitat",
        "name_ar": "\u0645\u0648\u0626\u0644 \u0627\u0644\u0623\u0645\u0645 \u0627\u0644\u0645\u062a\u062d\u062f\u0629 \u0644\u0644\u0645\u0633\u062a\u0648\u0637\u0646\u0627\u062a \u0627\u0644\u0628\u0634\u0631\u064a\u0629",
        "name_fr": "ONU-Habitat",
        "short": "UNHABITAT",
    },
    "XM-DAC-41114": {
        "name": "UNICEF",
        "name_ar": "\u0627\u0644\u064a\u0648\u0646\u064a\u0633\u0641",
        "name_fr": "UNICEF",
        "short": "UNICEF",
    },
    "XM-DAC-41140": {
        "name": "WFP",
        "name_ar": "\u0628\u0631\u0646\u0627\u0645\u062c \u0627\u0644\u0623\u063a\u0630\u064a\u0629 \u0627\u0644\u0639\u0627\u0644\u0645\u064a",
        "name_fr": "PAM",
        "short": "WFP",
    },
    "XM-DAC-41122": {
        "name": "UNOPS",
        "name_ar": "\u0645\u0643\u062a\u0628 \u0627\u0644\u0623\u0645\u0645 \u0627\u0644\u0645\u062a\u062d\u062f\u0629 \u0644\u062e\u062f\u0645\u0627\u062a \u0627\u0644\u0645\u0634\u0627\u0631\u064a\u0639",
        "name_fr": "UNOPS",
        "short": "UNOPS",
    },
    "XM-DAC-41301": {
        "name": "FAO",
        "name_ar": "\u0645\u0646\u0638\u0645\u0629 \u0627\u0644\u0623\u063a\u0630\u064a\u0629 \u0648\u0627\u0644\u0632\u0631\u0627\u0639\u0629",
        "name_fr": "FAO",
        "short": "FAO",
    },
    "XM-DAC-41119": {
        "name": "UNDP",
        "name_ar": "\u0628\u0631\u0646\u0627\u0645\u062c \u0627\u0644\u0623\u0645\u0645 \u0627\u0644\u0645\u062a\u062d\u062f\u0629 \u0627\u0644\u0625\u0646\u0645\u0627\u0626\u064a",
        "name_fr": "PNUD",
        "short": "UNDP",
    },
    "XM-DAC-41302": {
        "name": "WHO",
        "name_ar": "\u0645\u0646\u0638\u0645\u0629 \u0627\u0644\u0635\u062d\u0629 \u0627\u0644\u0639\u0627\u0644\u0645\u064a\u0629",
        "name_fr": "OMS",
        "short": "WHO",
    },
    "XM-DAC-41130": {
        "name": "UNRWA",
        "name_ar": "\u0648\u0643\u0627\u0644\u0629 \u0627\u0644\u0623\u0648\u0646\u0631\u0648\u0627",
        "name_fr": "UNRWA",
        "short": "UNRWA",
    },
    "XM-DAC-41126": {
        "name": "ESCWA",
        "name_ar": "\u0627\u0644\u0625\u0633\u0643\u0648\u0627",
        "name_fr": "CESAO",
        "short": "ESCWA",
    },
    "XM-DAC-41116": {
        "name": "UNFPA",
        "name_ar": "\u0635\u0646\u062f\u0648\u0642 \u0627\u0644\u0623\u0645\u0645 \u0627\u0644\u0645\u062a\u062d\u062f\u0629 \u0644\u0644\u0633\u0643\u0627\u0646",
        "name_fr": "FNUAP",
        "short": "UNFPA",
    },
    "XM-DAC-41304": {
        "name": "UNESCO",
        "name_ar": "\u0627\u0644\u064a\u0648\u0646\u0633\u0643\u0648",
        "name_fr": "UNESCO",
        "short": "UNESCO",
    },
}

# IATI activity status codes
STATUS_MAP = {
    "1": "open",
    "2": "open",
    "3": "open",
    "4": "closed",
    "5": "closed",
}


def _get_narrative(field, lang: str = "en") -> str:
    """Extract narrative text from IATI title/description field."""
    if isinstance(field, list):
        narratives = field
    elif isinstance(field, dict):
        narratives = field.get("narrative", [])
    else:
        return ""

    if isinstance(narratives, dict):
        narratives = [narratives]

    for n in narratives:
        if isinstance(n, dict):
            n_lang = n.get("xml:lang", "") or n.get("lang", "")
            if n_lang.startswith(lang):
                return (n.get("text", "") or "").strip()

    for n in narratives:
        if isinstance(n, dict) and n.get("text"):
            return n["text"].strip()

    return ""


def _parse_budget(budget_data) -> tuple[float, str]:
    """Parse total budget from IATI budget field."""
    if not budget_data:
        return 0.0, "USD"

    budgets = budget_data if isinstance(budget_data, list) else [budget_data]

    total = 0.0
    currency = "USD"

    for b in budgets:
        val = b.get("value", {})
        if isinstance(val, dict):
            try:
                amount = float(val.get("text", "0") or "0")
            except (ValueError, TypeError):
                amount = 0.0
            cur = val.get("currency", "USD") or "USD"
            total += amount
            currency = cur
        elif isinstance(val, (int, float)):
            total += float(val)

    return total, currency


def _parse_transaction_total(transactions) -> float:
    """Sum commitment transactions as an alternative budget source."""
    if not transactions:
        return 0.0

    if isinstance(transactions, dict):
        transactions = [transactions]

    total = 0.0
    for txn in transactions:
        txn_type = txn.get("transaction-type", {})
        if isinstance(txn_type, dict):
            type_code = txn_type.get("code", "")
        else:
            type_code = str(txn_type)

        if type_code == "2":  # Commitment
            val = txn.get("value", {})
            if isinstance(val, dict):
                try:
                    amount = float(val.get("text", "0") or "0")
                except (ValueError, TypeError):
                    amount = 0.0
                total += amount

    return total


def _extract_dates(act: dict) -> tuple[str, str, str, str]:
    """Extract dates from IATI activity."""
    dates = act.get("activity-date", [])
    if isinstance(dates, dict):
        dates = [dates]

    planned_start = ""
    actual_start = ""
    planned_end = ""
    actual_end = ""

    for d in dates:
        if not isinstance(d, dict):
            continue
        dtype = str(d.get("type", ""))
        iso = d.get("iso-date", "")
        if dtype == "1":
            planned_start = iso
        elif dtype == "2":
            actual_start = iso
        elif dtype == "3":
            planned_end = iso
        elif dtype == "4":
            actual_end = iso

    return planned_start, actual_start, planned_end, actual_end


def _extract_sectors(act: dict) -> tuple[str, list[str]]:
    """Extract primary sector and all sectors from IATI activity."""
    sectors_raw = act.get("sector", [])
    if isinstance(sectors_raw, dict):
        sectors_raw = [sectors_raw]

    sector_texts: list[str] = []
    for s in sectors_raw:
        if not isinstance(s, dict):
            continue
        text = _get_narrative(s, "en")
        if text:
            sector_texts.append(text)

    classified = []
    for text in sector_texts:
        c = classify_sector(text)
        if c not in classified:
            classified.append(c)

    primary = classified[0] if classified else "it"
    return primary, classified if classified else [primary]


def _extract_participating_orgs(act: dict) -> list[str]:
    """Extract participating organisations from IATI activity."""
    orgs_raw = act.get("participating-org", [])
    if isinstance(orgs_raw, dict):
        orgs_raw = [orgs_raw]

    orgs = []
    for org in orgs_raw:
        if not isinstance(org, dict):
            continue
        name = _get_narrative(org, "en")
        if not name:
            name = org.get("ref", "")
        if name and name not in orgs:
            orgs.append(name)

    return orgs


def _scrape_agency_iati(org_id: str, agency_info: dict) -> list[dict]:
    """Scrape a single UN agency from IATI Datastore for MENA countries."""
    grants: list[dict] = []
    seen_ids: set[str] = set()

    agency_name = agency_info["name"]
    agency_name_ar = agency_info["name_ar"]
    agency_name_fr = agency_info["name_fr"]
    agency_short = agency_info["short"]

    for country_code, country_name in MENA_COUNTRIES.items():
        offset = 0
        page_size = 50
        country_count = 0

        while True:
            try:
                params = {
                    "reporting-org": org_id,
                    "recipient-country": country_code,
                    "limit": page_size,
                    "offset": offset,
                }

                resp = requests.get(IATI_API, params=params, timeout=30)
                if resp.status_code != 200:
                    break

                data = resp.json()
                total_count = data.get("total-count", 0)
                activities = data.get("iati-activities", [])

                if not activities:
                    break

                for entry in activities:
                    act = entry.get("iati-activity", entry)

                    iati_id = act.get("iati-identifier", "")
                    if not iati_id or iati_id in seen_ids:
                        continue

                    # Title in multiple languages
                    title_en = _get_narrative(act.get("title", {}), "en")
                    title_fr = _get_narrative(act.get("title", {}), "fr")
                    title_ar = _get_narrative(act.get("title", {}), "ar")

                    if not title_en and not title_fr:
                        continue
                    if not title_en:
                        title_en = title_fr

                    # Status
                    status_field = act.get("activity-status", {})
                    if isinstance(status_field, dict):
                        status_code = status_field.get("code", "2")
                    else:
                        status_code = str(status_field)
                    status = STATUS_MAP.get(str(status_code), "open")

                    if status == "closed":
                        continue

                    seen_ids.add(iati_id)

                    # Description
                    desc_data = act.get("description", {})
                    if isinstance(desc_data, list):
                        desc_en = _get_narrative(desc_data[0], "en") if desc_data else ""
                        desc_fr = _get_narrative(desc_data[0], "fr") if desc_data else ""
                        desc_ar = _get_narrative(desc_data[0], "ar") if desc_data else ""
                    else:
                        desc_en = _get_narrative(desc_data, "en")
                        desc_fr = _get_narrative(desc_data, "fr")
                        desc_ar = _get_narrative(desc_data, "ar")

                    # Budget
                    budget, currency = _parse_budget(act.get("budget"))
                    if budget == 0:
                        budget = _parse_transaction_total(act.get("transaction"))
                        if budget > 0:
                            currency = "USD"

                    # Dates
                    planned_start, actual_start, planned_end, actual_end = (
                        _extract_dates(act)
                    )
                    publish_date = actual_start or planned_start or ""
                    deadline = planned_end or actual_end or ""

                    # Skip ancient projects — only include 2020+
                    all_dates = [planned_start, actual_start, planned_end, actual_end]
                    most_recent_year = 0
                    for d in all_dates:
                        if d and len(d) >= 4:
                            try:
                                most_recent_year = max(most_recent_year, int(d[:4]))
                            except ValueError:
                                pass
                    if most_recent_year > 0 and most_recent_year < 2020:
                        continue

                    # Sectors
                    primary_sector, sectors_list = _extract_sectors(act)

                    # If no sector from IATI, try from title
                    if primary_sector == "it":
                        title_sector = classify_sector(f"{title_en} {desc_en}")
                        if title_sector != "it":
                            primary_sector = title_sector
                            sectors_list = [title_sector]

                    # Grant type
                    combined_text = f"{title_en} {desc_en}"
                    grant_type = classify_grant_type(combined_text)

                    # Participating organisations
                    participating_orgs = _extract_participating_orgs(act)

                    # Tags
                    tags: list[str] = ["UN", agency_short]
                    if budget > 5_000_000:
                        tags.append("large_project")

                    # Source URL
                    source_url = ""
                    if agency_short == "UNDP":
                        source_url = f"https://open.undp.org/projects/{iati_id}"
                    elif agency_short == "UNICEF":
                        source_url = f"https://www.unicef.org/supply/procurement/"
                    elif agency_short == "UNHABITAT":
                        source_url = f"https://open.unhabitat.org/projects/{iati_id}"
                    elif agency_short == "WHO":
                        source_url = f"https://www.who.int/activities/"
                    elif agency_short == "UNRWA":
                        source_url = f"https://www.unrwa.org/what-we-do"
                    else:
                        source_url = f"https://d-portal.org/q.html?aid={iati_id}"

                    grant = {
                        "id": generate_grant_id(f"un_{agency_short.lower()}", iati_id),
                        "title": title_en,
                        "title_ar": title_ar or "",
                        "title_fr": title_fr or "",
                        "source": f"un_{agency_short.lower()}",
                        "source_ref": iati_id,
                        "source_url": source_url,
                        "funding_organization": agency_name,
                        "funding_organization_ar": agency_name_ar,
                        "funding_organization_fr": agency_name_fr,
                        "funding_amount": round(budget, 2),
                        "funding_amount_max": 0,
                        "currency": currency,
                        "grant_type": grant_type,
                        "country": country_name,
                        "country_code": country_code,
                        "region": "MENA",
                        "sector": primary_sector,
                        "sectors": sectors_list,
                        "eligibility_criteria": "",
                        "eligibility_countries": [country_code],
                        "description": (desc_en or title_en)[:2000],
                        "description_ar": (desc_ar or "")[:2000],
                        "description_fr": (desc_fr or title_fr)[:2000],
                        "application_deadline": parse_date(deadline) or "",
                        "publish_date": parse_date(publish_date) or "",
                        "status": status,
                        "contact_info": "; ".join(participating_orgs[:3]),
                        "documents_url": "",
                        "tags": tags[:10],
                        "metadata": {
                            "iati_id": iati_id,
                            "agency": agency_short,
                            "activity_status_code": str(status_code),
                            "planned_start": planned_start,
                            "actual_start": actual_start,
                            "planned_end": planned_end,
                            "actual_end": actual_end,
                            "participating_orgs": participating_orgs,
                        },
                    }
                    grants.append(grant)
                    country_count += 1

                offset += page_size
                if offset >= total_count or offset >= 2000:
                    break

                time.sleep(0.3)

            except Exception as e:
                logger.error(f"IATI {agency_short} {country_code}: {e}")
                break

        if country_count > 0:
            logger.info(
                f"{agency_short} {country_code} ({country_name}): "
                f"{country_count} active projects"
            )

    logger.info(f"{agency_name}: {len(grants)} total MENA projects")
    return grants


def _scrape_un_habitat_procurement() -> list[dict]:
    """Scrape UN-Habitat procurement portal directly."""
    grants: list[dict] = []
    seen_refs: set[str] = set()

    # Country name -> code
    _name_to_code: dict[str, str] = {v.lower(): k for k, v in MENA_COUNTRIES.items()}
    _name_to_code.update({
        "united arab emirates": "AE",
        "uae": "AE",
        "palestine": "PS",
        "state of palestine": "PS",
    })

    procurement_url = "https://procurement.unhabitat.org"

    browser_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        resp = requests.get(
            procurement_url,
            headers=browser_headers,
            timeout=30,
        )
        if resp.status_code != 200:
            logger.warning(f"UN-Habitat procurement HTTP {resp.status_code}")
            return grants

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")

        # Look for procurement notices
        notices = (
            soup.select(".procurement-notice")
            or soup.select(".notice-item")
            or soup.select("article")
            or soup.select("[class*='tender']")
            or soup.select("[class*='procurement']")
            or soup.select(".views-row")
            or soup.select("table tr")
        )

        for notice in notices:
            title_el = (
                notice.select_one("h3")
                or notice.select_one("h2")
                or notice.select_one("h4")
                or notice.select_one(".title")
                or notice.select_one("a")
            )
            title = title_el.get_text(strip=True) if title_el else ""
            if not title or len(title) < 10:
                continue

            # Get link
            link = notice.select_one("a")
            href = link.get("href", "") if link else ""

            notice_text = notice.get_text(strip=True)

            # Detect MENA country
            country_code = ""
            country_name = ""
            for name, code in _name_to_code.items():
                if name in notice_text.lower():
                    country_code = code
                    country_name = MENA_COUNTRIES.get(code, "")
                    break

            if not country_code:
                continue

            ref = href.split("/")[-1] if href else title[:50]
            if ref in seen_refs:
                continue
            seen_refs.add(ref)

            desc_el = notice.select_one("p") or notice.select_one(".description")
            description = desc_el.get_text(strip=True) if desc_el else title

            source_url = href
            if href and not href.startswith("http"):
                source_url = f"{procurement_url}{href}"

            sector = classify_sector(f"{title} {description}")
            grant_type = classify_grant_type(f"{title} {description}")

            grant = {
                "id": generate_grant_id("un_habitat_proc", ref),
                "title": title,
                "title_ar": "",
                "title_fr": "",
                "source": "un_unhabitat",
                "source_ref": ref,
                "source_url": source_url,
                "funding_organization": "UN-Habitat",
                "funding_organization_ar": "\u0645\u0648\u0626\u0644 \u0627\u0644\u0623\u0645\u0645 \u0627\u0644\u0645\u062a\u062d\u062f\u0629 \u0644\u0644\u0645\u0633\u062a\u0648\u0637\u0646\u0627\u062a \u0627\u0644\u0628\u0634\u0631\u064a\u0629",
                "funding_organization_fr": "ONU-Habitat",
                "funding_amount": 0,
                "funding_amount_max": 0,
                "currency": "USD",
                "grant_type": grant_type,
                "country": country_name,
                "country_code": country_code,
                "region": "MENA",
                "sector": sector,
                "sectors": [sector],
                "eligibility_criteria": "UN-Habitat procurement",
                "eligibility_countries": [country_code],
                "description": (description or title)[:2000],
                "description_ar": "",
                "description_fr": "",
                "application_deadline": "",
                "publish_date": "",
                "status": "open",
                "contact_info": "UN-Habitat Procurement",
                "documents_url": source_url,
                "tags": ["UN", "UNHABITAT", "procurement"],
                "metadata": {},
            }
            grants.append(grant)

    except Exception as e:
        logger.error(f"UN-Habitat procurement: {e}")

    logger.info(f"UN-Habitat procurement: {len(grants)} notices")
    return grants


def scrape() -> list[dict]:
    """Scrape UN-Habitat and other UN agencies for MENA grants."""
    logger.info("Starting UN-Habitat / UN agencies grants scraper...")

    all_grants: list[dict] = []
    seen_refs: set[str] = set()

    # Phase 1: IATI Datastore for each UN agency
    for org_id, agency_info in UN_AGENCY_ORGS.items():
        agency_grants = _scrape_agency_iati(org_id, agency_info)

        new_count = 0
        for g in agency_grants:
            if g["source_ref"] not in seen_refs:
                seen_refs.add(g["source_ref"])
                all_grants.append(g)
                new_count += 1

        logger.info(
            f"Phase 1 -- {agency_info['short']}: {new_count} new grants "
            f"(total: {len(all_grants)})"
        )

    # Phase 2: UN-Habitat procurement portal
    habitat_proc = _scrape_un_habitat_procurement()
    for g in habitat_proc:
        if g["source_ref"] not in seen_refs:
            seen_refs.add(g["source_ref"])
            all_grants.append(g)
    logger.info(f"Phase 2 -- UN-Habitat procurement: {len(habitat_proc)} grants")

    logger.info(f"UN agencies total grants: {len(all_grants)}")
    return all_grants


if __name__ == "__main__":
    results = scrape()
    save_grants(results, "un_habitat")
    print(f"Scraped {len(results)} grants from UN agencies")
