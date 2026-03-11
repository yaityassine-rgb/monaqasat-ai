"""
Grant scraper for OPEC Fund for International Development (OFID).
Sources:
  - OPEC Fund website: https://opecfund.org/
  - Operations/projects pages: https://opecfund.org/operations
  - IATI Datastore (OFID org): XM-DAC-46015

The OPEC Fund supports development in MENA and beyond, with significant
investments in Arab/OPEC member countries. Projects span infrastructure,
energy, water, health, education, agriculture and transportation.

Currency: USD
"""

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

logger = logging.getLogger("grants_opec")

# OPEC Fund endpoints
OPEC_OPERATIONS_URL = "https://opecfund.org/operations"
OPEC_PROJECTS_URL = "https://opecfund.org/operations/list"
IATI_API = "https://datastore.codeforiati.org/api/1/access/activity.json"
OFID_ORG_ID = "XM-DAC-46015"

# Country name -> code mapping
_OPEC_COUNTRY_TO_CODE: dict[str, str] = {}
for _code, _name in MENA_COUNTRIES.items():
    _OPEC_COUNTRY_TO_CODE[_name.lower()] = _code
_OPEC_COUNTRY_TO_CODE.update({
    "united arab emirates": "AE",
    "uae": "AE",
    "egypt, arab republic of": "EG",
    "arab republic of egypt": "EG",
    "morocco": "MA",
    "kingdom of morocco": "MA",
    "republic of tunisia": "TN",
    "hashemite kingdom of jordan": "JO",
    "west bank and gaza": "PS",
    "palestine": "PS",
    "state of palestine": "PS",
    "republic of iraq": "IQ",
    "republic of yemen": "YE",
    "kingdom of saudi arabia": "SA",
    "republic of sudan": "SD",
    "people's democratic republic of algeria": "DZ",
    "islamic republic of mauritania": "MR",
    "lebanese republic": "LB",
    "state of libya": "LY",
    "state of kuwait": "KW",
    "state of qatar": "QA",
    "kingdom of bahrain": "BH",
    "sultanate of oman": "OM",
})

# IATI activity status codes
STATUS_MAP = {
    "1": "open",
    "2": "open",
    "3": "open",
    "4": "closed",
    "5": "closed",
}

# Browser-like headers for website scraping
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _resolve_country(name_raw: str) -> tuple[str, str]:
    """Resolve a country name to (iso2_code, country_name).

    Returns ("", "") if not a MENA country.
    """
    if not name_raw:
        return "", ""
    key = name_raw.strip().lower()
    code = _OPEC_COUNTRY_TO_CODE.get(key, "")
    if code:
        return code, MENA_COUNTRIES[code]
    for pattern, c in _OPEC_COUNTRY_TO_CODE.items():
        if pattern in key or key in pattern:
            return c, MENA_COUNTRIES[c]
    return "", ""


def _detect_mena_country(text: str) -> tuple[str, str]:
    """Detect a MENA country mention in free text."""
    text_lower = text.lower()
    for name, code in _OPEC_COUNTRY_TO_CODE.items():
        if name in text_lower:
            return code, MENA_COUNTRIES.get(code, "")
    return "", ""


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


def _scrape_opec_website() -> list[dict]:
    """Scrape OPEC Fund operations page for MENA projects."""
    grants: list[dict] = []
    seen_refs: set[str] = set()

    # Try to scrape the operations listing
    for page_num in range(1, 20):
        try:
            params = {
                "page": page_num,
                "region": "arab",  # Filter for Arab region
            }

            resp = requests.get(
                OPEC_OPERATIONS_URL,
                params=params,
                headers=BROWSER_HEADERS,
                timeout=30,
            )
            if resp.status_code != 200:
                logger.warning(f"OPEC Fund website HTTP {resp.status_code} page {page_num}")
                break

            soup = BeautifulSoup(resp.text, "lxml")

            # Look for project cards/entries
            project_entries = (
                soup.select(".operation-card")
                or soup.select(".project-card")
                or soup.select(".card")
                or soup.select("article")
                or soup.select(".operations-list-item")
                or soup.select("[class*='project']")
                or soup.select("[class*='operation']")
            )

            if not project_entries:
                # Try to find any links to project pages
                links = soup.select("a[href*='/operations/']")
                if not links:
                    break

                for link in links:
                    href = link.get("href", "")
                    if not href or href == "/operations" or href == "/operations/":
                        continue

                    title = link.get_text(strip=True)
                    if not title or len(title) < 10:
                        continue

                    ref = href.split("/")[-1] if href else ""
                    if not ref or ref in seen_refs:
                        continue

                    # Detect MENA country
                    country_code, country_name = _detect_mena_country(title)
                    if not country_code:
                        parent_text = link.parent.get_text(strip=True) if link.parent else ""
                        country_code, country_name = _detect_mena_country(parent_text)
                    if not country_code:
                        continue

                    seen_refs.add(ref)

                    sector = classify_sector(title)
                    grant_type = classify_grant_type(title)

                    source_url = href
                    if not href.startswith("http"):
                        source_url = f"https://opecfund.org{href}"

                    grant = {
                        "id": generate_grant_id("opec_fund", ref),
                        "title": title,
                        "title_ar": "",
                        "title_fr": "",
                        "source": "opec_fund",
                        "source_ref": ref,
                        "source_url": source_url,
                        "funding_organization": "OPEC Fund for International Development",
                        "funding_organization_ar": "\u0635\u0646\u062f\u0648\u0642 \u0627\u0644\u0623\u0648\u0628\u0643 \u0644\u0644\u062a\u0646\u0645\u064a\u0629 \u0627\u0644\u062f\u0648\u0644\u064a\u0629",
                        "funding_organization_fr": "Fonds OPEP pour le d\u00e9veloppement international",
                        "funding_amount": 0,
                        "funding_amount_max": 0,
                        "currency": "USD",
                        "grant_type": grant_type,
                        "country": country_name,
                        "country_code": country_code,
                        "region": "MENA",
                        "sector": sector,
                        "sectors": [sector],
                        "eligibility_criteria": "OPEC Fund development project",
                        "eligibility_countries": [country_code],
                        "description": title,
                        "description_ar": "",
                        "description_fr": "",
                        "application_deadline": "",
                        "publish_date": "",
                        "status": "open",
                        "contact_info": "OPEC Fund for International Development",
                        "documents_url": source_url,
                        "tags": ["OPEC_Fund"],
                        "metadata": {},
                    }
                    grants.append(grant)

                continue

            for entry in project_entries:
                title_el = (
                    entry.select_one("h3")
                    or entry.select_one("h2")
                    or entry.select_one("h4")
                    or entry.select_one(".title")
                    or entry.select_one("a")
                )
                title = title_el.get_text(strip=True) if title_el else ""
                if not title or len(title) < 10:
                    continue

                # Get link
                link = entry.select_one("a")
                href = link.get("href", "") if link else ""

                # Get description
                desc_el = entry.select_one("p") or entry.select_one(".description")
                description = desc_el.get_text(strip=True) if desc_el else title

                # Extract amount if available
                amount_el = entry.select_one("[class*='amount']") or entry.select_one("[class*='value']")
                amount = 0
                if amount_el:
                    amount = parse_amount(amount_el.get_text(strip=True))

                # Detect MENA country
                entry_text = entry.get_text(strip=True)
                country_code, country_name = _detect_mena_country(entry_text)
                if not country_code:
                    country_code, country_name = _detect_mena_country(title)
                if not country_code:
                    continue

                ref = href.split("/")[-1] if href else title[:50]
                if ref in seen_refs:
                    continue
                seen_refs.add(ref)

                combined = f"{title} {description}"
                sector = classify_sector(combined)
                grant_type = classify_grant_type(combined)

                source_url = href
                if href and not href.startswith("http"):
                    source_url = f"https://opecfund.org{href}"

                grant = {
                    "id": generate_grant_id("opec_fund", ref),
                    "title": title,
                    "title_ar": "",
                    "title_fr": "",
                    "source": "opec_fund",
                    "source_ref": ref,
                    "source_url": source_url,
                    "funding_organization": "OPEC Fund for International Development",
                    "funding_organization_ar": "\u0635\u0646\u062f\u0648\u0642 \u0627\u0644\u0623\u0648\u0628\u0643 \u0644\u0644\u062a\u0646\u0645\u064a\u0629 \u0627\u0644\u062f\u0648\u0644\u064a\u0629",
                    "funding_organization_fr": "Fonds OPEP pour le d\u00e9veloppement international",
                    "funding_amount": amount,
                    "funding_amount_max": 0,
                    "currency": "USD",
                    "grant_type": grant_type,
                    "country": country_name,
                    "country_code": country_code,
                    "region": "MENA",
                    "sector": sector,
                    "sectors": [sector],
                    "eligibility_criteria": "OPEC Fund development project",
                    "eligibility_countries": [country_code],
                    "description": (description or title)[:2000],
                    "description_ar": "",
                    "description_fr": "",
                    "application_deadline": "",
                    "publish_date": "",
                    "status": "open",
                    "contact_info": "OPEC Fund for International Development",
                    "documents_url": source_url,
                    "tags": ["OPEC_Fund"],
                    "metadata": {},
                }
                grants.append(grant)

            time.sleep(0.5)

        except Exception as e:
            logger.error(f"OPEC Fund website page {page_num}: {e}")
            break

    logger.info(f"OPEC Fund website: {len(grants)} MENA projects")
    return grants


def _scrape_iati_opec() -> list[dict]:
    """Scrape OPEC Fund grants from IATI Datastore for MENA countries."""
    grants: list[dict] = []
    seen_ids: set[str] = set()

    for country_code, country_name in MENA_COUNTRIES.items():
        offset = 0
        page_size = 50
        country_count = 0

        while True:
            try:
                params = {
                    "reporting-org": OFID_ORG_ID,
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

                    # Title
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

                    # Classify
                    combined_text = f"{title_en} {desc_en}"
                    sector = classify_sector(combined_text)
                    grant_type = classify_grant_type(combined_text)

                    # Participating organisations
                    participating_orgs = _extract_participating_orgs(act)

                    # Tags
                    tags: list[str] = ["OPEC_Fund"]
                    if budget > 20_000_000:
                        tags.append("large_project")

                    grant = {
                        "id": generate_grant_id("opec_fund", iati_id),
                        "title": title_en,
                        "title_ar": title_ar or "",
                        "title_fr": title_fr or "",
                        "source": "opec_fund",
                        "source_ref": iati_id,
                        "source_url": f"https://opecfund.org/operations/{iati_id}" if iati_id else "",
                        "funding_organization": "OPEC Fund for International Development",
                        "funding_organization_ar": "\u0635\u0646\u062f\u0648\u0642 \u0627\u0644\u0623\u0648\u0628\u0643 \u0644\u0644\u062a\u0646\u0645\u064a\u0629 \u0627\u0644\u062f\u0648\u0644\u064a\u0629",
                        "funding_organization_fr": "Fonds OPEP pour le d\u00e9veloppement international",
                        "funding_amount": round(budget, 2),
                        "funding_amount_max": 0,
                        "currency": currency,
                        "grant_type": grant_type,
                        "country": country_name,
                        "country_code": country_code,
                        "region": "MENA",
                        "sector": sector,
                        "sectors": [sector],
                        "eligibility_criteria": "",
                        "eligibility_countries": [country_code],
                        "description": (desc_en or title_en)[:2000],
                        "description_ar": (desc_ar or "")[:2000],
                        "description_fr": (desc_fr or "")[:2000],
                        "application_deadline": parse_date(deadline) or "",
                        "publish_date": parse_date(publish_date) or "",
                        "status": status,
                        "contact_info": "; ".join(participating_orgs[:3]),
                        "documents_url": "",
                        "tags": tags[:10],
                        "metadata": {
                            "iati_id": iati_id,
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
                if offset >= total_count:
                    break

                time.sleep(0.3)

            except Exception as e:
                logger.error(f"IATI OPEC Fund {country_code}: {e}")
                break

        if country_count > 0:
            logger.info(
                f"OPEC Fund {country_code} ({country_name}): {country_count} grants"
            )

    logger.info(f"OPEC Fund IATI total: {len(grants)} grants")
    return grants


def scrape() -> list[dict]:
    """Scrape OPEC Fund for International Development for MENA grants."""
    logger.info("Starting OPEC Fund grants scraper...")

    # Phase 1: IATI Datastore (structured data)
    iati_grants = _scrape_iati_opec()
    logger.info(f"Phase 1 -- IATI: {len(iati_grants)} grants")

    # Phase 2: OPEC Fund website (supplementary)
    web_grants = _scrape_opec_website()
    logger.info(f"Phase 2 -- Website: {len(web_grants)} grants")

    # Merge and deduplicate by source_ref
    all_grants = iati_grants
    seen_refs = {g["source_ref"] for g in all_grants}
    for g in web_grants:
        if g["source_ref"] not in seen_refs:
            seen_refs.add(g["source_ref"])
            all_grants.append(g)

    logger.info(f"OPEC Fund total grants: {len(all_grants)}")
    return all_grants


if __name__ == "__main__":
    results = scrape()
    save_grants(results, "opec_fund")
    print(f"Scraped {len(results)} grants from OPEC Fund")
