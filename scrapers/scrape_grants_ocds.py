"""
Grant scraper for Open Contracting Data Standard (OCDS) Registry.
Sources:
  - OCDS data registry: https://data.open-contracting.org/
  - OCDS API: https://data.open-contracting.org/api/
  - Individual MENA publisher APIs

OCDS provides standardized procurement data from government publishers.
Several MENA countries publish procurement data in OCDS format:
  - Morocco (OMPIC / e-procurement)
  - Tunisia (HAICOP / TUNEPS)
  - Jordan (JONEPS)
  - Others through international organizations

Currency: Varies by country (MAD, TND, JOD, USD, EUR, etc.)
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

logger = logging.getLogger("grants_ocds")

# OCDS API endpoints
OCDS_REGISTRY_API = "https://data.open-contracting.org/api/"
OCDS_REGISTRY_URL = "https://data.open-contracting.org/"

# Known MENA OCDS publishers with their data endpoints
MENA_OCDS_PUBLISHERS = {
    "morocco": {
        "country_code": "MA",
        "country_name": "Morocco",
        "api_url": "https://data.open-contracting.org/api/v1/publications",
        "publisher": "Morocco",
        "currency": "MAD",
    },
    "tunisia": {
        "country_code": "TN",
        "country_name": "Tunisia",
        "api_url": "https://data.open-contracting.org/api/v1/publications",
        "publisher": "Tunisia",
        "currency": "TND",
    },
    "jordan": {
        "country_code": "JO",
        "country_name": "Jordan",
        "api_url": "https://data.open-contracting.org/api/v1/publications",
        "publisher": "Jordan",
        "currency": "JOD",
    },
}

# Country name -> code mapping
_OCDS_COUNTRY_TO_CODE: dict[str, str] = {}
for _code, _name in MENA_COUNTRIES.items():
    _OCDS_COUNTRY_TO_CODE[_name.lower()] = _code
_OCDS_COUNTRY_TO_CODE.update({
    "united arab emirates": "AE",
    "uae": "AE",
    "morocco": "MA",
    "tunisia": "TN",
    "jordan": "JO",
    "egypt": "EG",
    "iraq": "IQ",
    "saudi arabia": "SA",
    "kingdom of saudi arabia": "SA",
    "kuwait": "KW",
    "qatar": "QA",
    "bahrain": "BH",
    "oman": "OM",
    "algeria": "DZ",
    "libya": "LY",
    "lebanon": "LB",
    "sudan": "SD",
    "yemen": "YE",
    "mauritania": "MR",
    "palestine": "PS",
    "west bank and gaza": "PS",
})

# OCDS status mapping
OCDS_STATUS_MAP = {
    "active": "open",
    "planned": "open",
    "tender": "open",
    "complete": "closed",
    "cancelled": "closed",
    "unsuccessful": "closed",
    "withdrawn": "closed",
    "closed": "closed",
}


def _resolve_country(name_raw: str) -> tuple[str, str]:
    """Resolve a country name to (iso2_code, country_name)."""
    if not name_raw:
        return "", ""
    key = name_raw.strip().lower()
    code = _OCDS_COUNTRY_TO_CODE.get(key, "")
    if code:
        return code, MENA_COUNTRIES[code]
    for pattern, c in _OCDS_COUNTRY_TO_CODE.items():
        if pattern in key or key in pattern:
            return c, MENA_COUNTRIES[c]
    return "", ""


def _detect_mena_country(text: str) -> tuple[str, str]:
    """Detect a MENA country mention in free text."""
    text_lower = text.lower()
    for name, code in _OCDS_COUNTRY_TO_CODE.items():
        if name in text_lower:
            return code, MENA_COUNTRIES.get(code, "")
    return "", ""


def _parse_ocds_release(release: dict, publisher_country_code: str = "", publisher_country_name: str = "", default_currency: str = "USD") -> dict | None:
    """Parse a single OCDS release into a grant dict.

    Args:
        release: OCDS release document.
        publisher_country_code: Default country code from publisher.
        publisher_country_name: Default country name from publisher.
        default_currency: Default currency for this publisher.

    Returns:
        Grant dict or None if not relevant.
    """
    # Get OCID (Open Contracting ID)
    ocid = release.get("ocid", "")
    if not ocid:
        return None

    # Tender data
    tender = release.get("tender", {})
    if not tender:
        # Try top-level fields
        tender = release

    title = tender.get("title", release.get("title", ""))
    if not title or len(title) < 5:
        return None

    description = tender.get("description", release.get("description", ""))

    # Status
    status_raw = tender.get("status", release.get("tag", [""])[0] if release.get("tag") else "")
    if isinstance(status_raw, list):
        status_raw = status_raw[0] if status_raw else ""
    status = OCDS_STATUS_MAP.get(status_raw.lower(), "open")

    # Skip closed unless very recent
    if status == "closed":
        return None

    # Amount
    amount_obj = tender.get("value", {})
    if isinstance(amount_obj, dict):
        amount = parse_amount(amount_obj.get("amount", 0))
        currency = amount_obj.get("currency", default_currency) or default_currency
    else:
        amount = 0
        currency = default_currency

    # Min/Max amounts
    min_value = tender.get("minValue", {})
    max_value = tender.get("maxValue", {})
    amount_max = 0
    if isinstance(max_value, dict):
        amount_max = parse_amount(max_value.get("amount", 0))

    # Dates
    tender_period = tender.get("tenderPeriod", {})
    deadline = ""
    pub_date = ""
    if isinstance(tender_period, dict):
        deadline = parse_date(str(tender_period.get("endDate", ""))) or ""
        pub_date = parse_date(str(tender_period.get("startDate", ""))) or ""

    if not pub_date:
        pub_date = parse_date(str(release.get("date", ""))) or ""

    # Procuring entity (buyer)
    buyer = release.get("buyer", {})
    if isinstance(buyer, dict):
        procuring_entity = buyer.get("name", "")
    else:
        procuring_entity = ""

    if not procuring_entity:
        procuring_entity = tender.get("procuringEntity", {})
        if isinstance(procuring_entity, dict):
            procuring_entity = procuring_entity.get("name", "")
        else:
            procuring_entity = str(procuring_entity) if procuring_entity else ""

    # Country from delivery address or publisher
    country_code = publisher_country_code
    country_name = publisher_country_name

    delivery_locations = tender.get("deliveryLocations", tender.get("items", []))
    if isinstance(delivery_locations, list):
        for loc in delivery_locations:
            if isinstance(loc, dict):
                loc_country = loc.get("deliveryAddress", {}).get("country", "")
                if not loc_country and isinstance(loc.get("deliveryLocation"), dict):
                    loc_country = loc["deliveryLocation"].get("country", "")
                if loc_country:
                    code, name = _resolve_country(str(loc_country))
                    if code:
                        country_code = code
                        country_name = name
                        break

    if not country_code:
        return None

    # Classification / sector
    items = tender.get("items", [])
    classifications = []
    for item in items if isinstance(items, list) else []:
        if isinstance(item, dict):
            classification = item.get("classification", {})
            if isinstance(classification, dict):
                desc = classification.get("description", "")
                if desc:
                    classifications.append(desc)

    combined = f"{title} {description} {' '.join(classifications)}"
    sector = classify_sector(combined)
    grant_type = classify_grant_type(combined)

    # Procurement method
    proc_method = tender.get("procurementMethod", "")
    proc_method_details = tender.get("procurementMethodDetails", "")

    # Tags
    tags = ["OCDS"]
    if proc_method:
        tags.append(proc_method)
    release_tags = release.get("tag", [])
    if isinstance(release_tags, list):
        tags.extend(release_tags[:3])

    # Contact
    contact_point = tender.get("contactPoint", procuring_entity)
    if isinstance(contact_point, dict):
        contact_info = contact_point.get("name", "")
        email = contact_point.get("email", "")
        if email:
            contact_info = f"{contact_info} ({email})" if contact_info else email
    else:
        contact_info = str(contact_point) if contact_point else ""

    # Documents
    documents = tender.get("documents", [])
    docs_url = ""
    if isinstance(documents, list) and documents:
        for doc in documents:
            if isinstance(doc, dict) and doc.get("url"):
                docs_url = doc["url"]
                break

    return {
        "id": generate_grant_id("ocds", ocid),
        "title": title[:500],
        "title_ar": "",
        "title_fr": "",
        "source": "ocds",
        "source_ref": ocid,
        "source_url": release.get("uri", docs_url or ""),
        "funding_organization": procuring_entity or f"Government of {country_name}",
        "funding_organization_ar": MENA_COUNTRIES_AR.get(country_code, ""),
        "funding_organization_fr": MENA_COUNTRIES_FR.get(country_code, ""),
        "funding_amount": amount,
        "funding_amount_max": amount_max,
        "currency": currency,
        "grant_type": grant_type,
        "country": country_name,
        "country_code": country_code,
        "region": "MENA",
        "sector": sector,
        "sectors": [sector],
        "eligibility_criteria": proc_method_details or proc_method or "",
        "eligibility_countries": [country_code],
        "description": (description or title)[:2000],
        "description_ar": "",
        "description_fr": "",
        "application_deadline": deadline,
        "publish_date": pub_date,
        "status": status,
        "contact_info": contact_info,
        "documents_url": docs_url,
        "tags": tags[:10],
        "metadata": {
            "ocid": ocid,
            "procurement_method": proc_method,
            "procurement_method_details": proc_method_details,
            "status_raw": status_raw,
            "classifications": classifications[:5],
        },
    }


def _scrape_ocds_registry() -> list[dict]:
    """Scrape the OCDS data registry for MENA publishers and data."""
    grants: list[dict] = []
    seen_ocids: set[str] = set()

    # Try the OCDS registry API to find MENA data sources
    try:
        resp = requests.get(
            f"{OCDS_REGISTRY_API}",
            headers=HEADERS,
            timeout=30,
        )
        if resp.status_code == 200:
            try:
                registry_data = resp.json()
                # Process registry to find MENA sources
                publications = []
                if isinstance(registry_data, dict):
                    publications = registry_data.get("results", registry_data.get("publications", []))
                elif isinstance(registry_data, list):
                    publications = registry_data

                for pub in publications:
                    if not isinstance(pub, dict):
                        continue

                    # Check if MENA-related
                    pub_country = pub.get("country", pub.get("country_name", ""))
                    code, name = _resolve_country(str(pub_country))
                    if not code:
                        continue

                    # Get data URL
                    data_url = pub.get("data_url", pub.get("url", pub.get("api_url", "")))
                    if data_url:
                        logger.info(f"Found OCDS MENA publisher: {name} -> {data_url}")

            except Exception:
                pass

    except Exception as e:
        logger.warning(f"OCDS registry API: {e}")

    return grants


def _scrape_ocds_api_packages() -> list[dict]:
    """Scrape OCDS release packages from known MENA data endpoints."""
    grants: list[dict] = []
    seen_ocids: set[str] = set()

    # Known OCDS data endpoints for MENA countries
    ocds_endpoints = [
        # Morocco - Kingdom of Morocco e-procurement
        {
            "url": "https://data.open-contracting.org/api/v1/records?country=MA",
            "country_code": "MA",
            "country_name": "Morocco",
            "currency": "MAD",
        },
        # Tunisia - HAICOP
        {
            "url": "https://data.open-contracting.org/api/v1/records?country=TN",
            "country_code": "TN",
            "country_name": "Tunisia",
            "currency": "TND",
        },
        # Jordan - JONEPS
        {
            "url": "https://data.open-contracting.org/api/v1/records?country=JO",
            "country_code": "JO",
            "country_name": "Jordan",
            "currency": "JOD",
        },
        # Try generic search for all MENA
        {
            "url": "https://data.open-contracting.org/api/v1/records?region=MENA",
            "country_code": "",
            "country_name": "",
            "currency": "USD",
        },
    ]

    for endpoint in ocds_endpoints:
        page = 0
        max_pages = 20

        while page < max_pages:
            try:
                url = endpoint["url"]
                if "?" in url:
                    url += f"&page={page}&limit=50"
                else:
                    url += f"?page={page}&limit=50"

                resp = requests.get(url, headers=HEADERS, timeout=30)
                if resp.status_code != 200:
                    break

                try:
                    data = resp.json()
                except Exception:
                    break

                # Handle various OCDS response formats
                releases = []
                if isinstance(data, dict):
                    # Release package format
                    releases = data.get("releases", [])
                    if not releases:
                        releases = data.get("records", [])
                    if not releases:
                        releases = data.get("results", [])
                    if not releases:
                        # Try extracting from nested records
                        records = data.get("records", [])
                        for record in records:
                            if isinstance(record, dict):
                                compiled = record.get("compiledRelease", {})
                                if compiled:
                                    releases.append(compiled)
                                record_releases = record.get("releases", [])
                                releases.extend(record_releases)
                elif isinstance(data, list):
                    releases = data

                if not releases:
                    break

                new_count = 0
                for release in releases:
                    if not isinstance(release, dict):
                        continue

                    ocid = release.get("ocid", "")
                    if ocid and ocid in seen_ocids:
                        continue

                    grant = _parse_ocds_release(
                        release,
                        publisher_country_code=endpoint["country_code"],
                        publisher_country_name=endpoint["country_name"],
                        default_currency=endpoint["currency"],
                    )

                    if grant:
                        if ocid:
                            seen_ocids.add(ocid)
                        grants.append(grant)
                        new_count += 1

                if new_count > 0:
                    logger.info(
                        f"OCDS {endpoint.get('country_name', 'MENA')} page {page}: "
                        f"{new_count} new records"
                    )

                page += 1
                time.sleep(0.5)

                # If fewer results than requested, we are done
                if len(releases) < 50:
                    break

            except Exception as e:
                logger.error(
                    f"OCDS {endpoint.get('country_name', 'MENA')} page {page}: {e}"
                )
                break

    logger.info(f"OCDS API packages: {len(grants)} records")
    return grants


def _scrape_ocds_kingfisher() -> list[dict]:
    """Scrape from OCDS Kingfisher data (OCP mirror) for MENA."""
    grants: list[dict] = []
    seen_ocids: set[str] = set()

    # Kingfisher process API (used by Open Contracting Partnership)
    kingfisher_url = "https://process.kingfisher.open-contracting.org/api/"

    for country_code, country_name in MENA_COUNTRIES.items():
        try:
            params = {
                "country": country_code,
                "limit": 100,
                "offset": 0,
            }

            resp = requests.get(
                f"{kingfisher_url}collections/",
                params=params,
                headers=HEADERS,
                timeout=30,
            )
            if resp.status_code != 200:
                continue

            try:
                data = resp.json()
            except Exception:
                continue

            collections = data if isinstance(data, list) else data.get("results", [])

            for collection in collections:
                if not isinstance(collection, dict):
                    continue

                collection_id = collection.get("id", "")
                source_url = collection.get("source_url", "")

                if not source_url:
                    continue

                # Try to fetch actual data from the collection
                try:
                    data_resp = requests.get(
                        f"{kingfisher_url}collections/{collection_id}/releases/",
                        params={"limit": 50},
                        headers=HEADERS,
                        timeout=30,
                    )
                    if data_resp.status_code != 200:
                        continue

                    releases_data = data_resp.json()
                    releases = releases_data if isinstance(releases_data, list) else releases_data.get("results", [])

                    for release in releases:
                        if not isinstance(release, dict):
                            continue

                        ocid = release.get("ocid", "")
                        if ocid and ocid in seen_ocids:
                            continue

                        grant = _parse_ocds_release(
                            release,
                            publisher_country_code=country_code,
                            publisher_country_name=country_name,
                        )

                        if grant:
                            if ocid:
                                seen_ocids.add(ocid)
                            grants.append(grant)

                except Exception:
                    continue

            time.sleep(0.3)

        except Exception as e:
            logger.error(f"OCDS Kingfisher {country_code}: {e}")
            continue

    logger.info(f"OCDS Kingfisher: {len(grants)} records")
    return grants


def scrape() -> list[dict]:
    """Scrape Open Contracting Data Standard sources for MENA procurement."""
    logger.info("Starting OCDS grants scraper...")

    # Phase 1: OCDS registry for publisher discovery
    registry_grants = _scrape_ocds_registry()
    logger.info(f"Phase 1 -- Registry: {len(registry_grants)} grants")

    # Phase 2: OCDS API release packages
    api_grants = _scrape_ocds_api_packages()
    logger.info(f"Phase 2 -- API: {len(api_grants)} grants")

    # Phase 3: Kingfisher (OCP mirror)
    kingfisher_grants = _scrape_ocds_kingfisher()
    logger.info(f"Phase 3 -- Kingfisher: {len(kingfisher_grants)} grants")

    # Merge and deduplicate by source_ref (OCID)
    all_grants = registry_grants + api_grants
    seen_refs = {g["source_ref"] for g in all_grants}
    for g in kingfisher_grants:
        if g["source_ref"] not in seen_refs:
            seen_refs.add(g["source_ref"])
            all_grants.append(g)

    logger.info(f"OCDS total grants: {len(all_grants)}")
    return all_grants


if __name__ == "__main__":
    results = scrape()
    save_grants(results, "ocds")
    print(f"Scraped {len(results)} grants from OCDS")
