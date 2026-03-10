"""
Grant scraper for World Bank Projects & Procurement.
Sources:
  - Projects API: https://search.worldbank.org/api/v2/projects
  - Procurement notices (grant-type): https://search.worldbank.org/api/v2/procnotices

Focuses on IBRD/IDA lending projects in MENA that represent grant/funding
opportunities, plus procurement notices containing grant keywords.
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

logger = logging.getLogger("grants_worldbank")

PROJECTS_API = "https://search.worldbank.org/api/v2/projects"
PROCNOTICES_API = "https://search.worldbank.org/api/v2/procnotices"

# Map World Bank country names to ISO-2 codes
_WB_COUNTRY_TO_CODE: dict[str, str] = {}
for _code, _name in MENA_COUNTRIES.items():
    _WB_COUNTRY_TO_CODE[_name.lower()] = _code
_WB_COUNTRY_TO_CODE.update({
    "united arab emirates": "AE",
    "egypt, arab republic of": "EG",
    "egypt, arab rep.": "EG",
    "yemen, republic of": "YE",
    "yemen, rep.": "YE",
    "west bank and gaza": "PS",
    "west bank & gaza": "PS",
    "morocco": "MA",
    "saudi arabia": "SA",
    "uae": "AE",
    "bahrain": "BH",
    "kuwait": "KW",
    "qatar": "QA",
    "oman": "OM",
    "jordan": "JO",
    "tunisia": "TN",
    "algeria": "DZ",
    "libya": "LY",
    "iraq": "IQ",
    "lebanon": "LB",
    "palestine": "PS",
    "sudan": "SD",
    "mauritania": "MR",
})

# Project fields to request from the API
PROJECT_FIELDS = (
    "id,project_name,boardapprovaldate,closingdate,totalamt,"
    "countryname,countryshortname,sector1,sector2,theme1,theme2,"
    "lendinginstr,status,url,borrower,impagency,"
    "project_abstract,projectdocs"
)


def _resolve_country(name_raw: str) -> tuple[str, str]:
    """Resolve a WB country name to (iso2_code, country_name).

    Returns ("", "") if not a MENA country.
    """
    if not name_raw:
        return "", ""
    key = name_raw.strip().lower()
    code = _WB_COUNTRY_TO_CODE.get(key, "")
    if code:
        return code, MENA_COUNTRIES[code]
    # Try partial match
    for pattern, c in _WB_COUNTRY_TO_CODE.items():
        if pattern in key or key in pattern:
            return c, MENA_COUNTRIES[c]
    return "", ""


def _scrape_projects() -> list[dict]:
    """Scrape World Bank IBRD/IDA projects for MENA countries."""
    grants: list[dict] = []
    seen_ids: set[str] = set()

    for lending_type in ("IBRD", "IDA"):
        offset = 0
        page_size = 100

        while True:
            try:
                params = {
                    "format": "json",
                    "fl": PROJECT_FIELDS,
                    "rows": page_size,
                    "os": offset,
                    "lending_type_exact": lending_type,
                    "status_exact": "Active",
                    "srt": "boardapprovaldate",
                    "order": "desc",
                }

                resp = requests.get(
                    PROJECTS_API, params=params, headers=HEADERS, timeout=30
                )
                if resp.status_code != 200:
                    logger.warning(
                        f"WB Projects API {resp.status_code} "
                        f"lending={lending_type} offset={offset}"
                    )
                    break

                data = resp.json()
                total = int(data.get("total", 0))
                projects_raw = data.get("projects", {})

                # Response is a dict of dicts keyed by project ID
                if isinstance(projects_raw, dict):
                    project_list = [
                        v for v in projects_raw.values() if isinstance(v, dict)
                    ]
                elif isinstance(projects_raw, list):
                    project_list = projects_raw
                else:
                    break

                if not project_list:
                    break

                for proj in project_list:
                    project_id = str(proj.get("id", ""))
                    if not project_id or project_id in seen_ids:
                        continue

                    # Resolve country — skip non-MENA
                    country_raw = proj.get(
                        "countryshortname",
                        proj.get("countryname", ""),
                    )
                    # Handle multi-country projects (e.g., "Morocco;Tunisia")
                    country_parts = [
                        c.strip() for c in country_raw.split(";") if c.strip()
                    ]
                    primary_code, primary_name = "", ""
                    eligibility_countries: list[str] = []

                    for part in country_parts:
                        code, name = _resolve_country(part)
                        if code:
                            eligibility_countries.append(code)
                            if not primary_code:
                                primary_code = code
                                primary_name = name

                    if not primary_code:
                        continue  # Not a MENA project

                    seen_ids.add(project_id)

                    # Extract fields
                    title = proj.get("project_name", "")
                    if not title:
                        continue

                    total_amt = parse_amount(proj.get("totalamt", 0))
                    approval_date = parse_date(
                        str(proj.get("boardapprovaldate", ""))
                    )
                    closing_date = parse_date(
                        str(proj.get("closingdate", ""))
                    )
                    sector1 = proj.get("sector1", "")
                    sector2 = proj.get("sector2", "")
                    theme1 = proj.get("theme1", "")
                    lending_instr = proj.get("lendinginstr", "")
                    status_raw = proj.get("status", "Active")
                    borrower = proj.get("borrower", "")
                    impl_agency = proj.get("impagency", "")
                    abstract = proj.get("project_abstract", "")
                    project_url = proj.get("url", "")

                    # Build description
                    desc_parts = []
                    if abstract:
                        desc_parts.append(abstract)
                    if lending_instr:
                        desc_parts.append(f"Lending instrument: {lending_instr}")
                    if borrower:
                        desc_parts.append(f"Borrower: {borrower}")
                    if impl_agency:
                        desc_parts.append(f"Implementing agency: {impl_agency}")
                    description = " | ".join(desc_parts) if desc_parts else title

                    # Classify
                    combined_text = f"{title} {description} {sector1} {theme1}"
                    sector = classify_sector(combined_text)
                    grant_type = classify_grant_type(combined_text)

                    # Determine multiple sectors
                    sectors_list = list({
                        classify_sector(s)
                        for s in [sector1, sector2, theme1]
                        if s
                    })
                    if sector not in sectors_list:
                        sectors_list.insert(0, sector)

                    # Status
                    status = "open"
                    if status_raw and "close" in status_raw.lower():
                        status = "closed"

                    # Tags
                    tags = []
                    if lending_type == "IDA":
                        tags.append("IDA")
                    if lending_type == "IBRD":
                        tags.append("IBRD")
                    if lending_instr:
                        tags.append(lending_instr)

                    grant = {
                        "id": generate_grant_id("world_bank", project_id),
                        "title": title,
                        "title_ar": "",
                        "title_fr": "",
                        "source": "world_bank",
                        "source_ref": project_id,
                        "source_url": project_url or f"https://projects.worldbank.org/en/projects-operations/project-detail/{project_id}",
                        "funding_organization": "World Bank",
                        "funding_organization_ar": "البنك الدولي",
                        "funding_organization_fr": "Banque mondiale",
                        "funding_amount": total_amt,
                        "funding_amount_max": 0,
                        "currency": "USD",
                        "grant_type": grant_type,
                        "country": primary_name,
                        "country_code": primary_code,
                        "region": "MENA",
                        "sector": sector,
                        "sectors": sectors_list,
                        "eligibility_criteria": f"{lending_type} lending. Borrower: {borrower}" if borrower else f"{lending_type} lending project",
                        "eligibility_countries": eligibility_countries,
                        "description": description[:2000],
                        "description_ar": "",
                        "description_fr": "",
                        "application_deadline": closing_date or "",
                        "publish_date": approval_date or "",
                        "status": status,
                        "contact_info": impl_agency or borrower or "",
                        "documents_url": project_url or "",
                        "tags": tags,
                        "metadata": {
                            "lending_type": lending_type,
                            "lending_instrument": lending_instr,
                            "sector1": sector1,
                            "sector2": sector2,
                            "theme1": theme1,
                        },
                    }
                    grants.append(grant)

                offset += page_size
                if offset >= total or offset >= 5000:
                    break

                time.sleep(0.3)

            except Exception as e:
                logger.error(
                    f"WB Projects error lending={lending_type} offset={offset}: {e}"
                )
                break

        logger.info(
            f"World Bank {lending_type}: scanned {offset} projects, "
            f"total grants so far: {len(grants)}"
        )

    return grants


def _scrape_grant_procnotices() -> list[dict]:
    """Scrape WB procurement notices filtered for grant-related keywords."""
    grants: list[dict] = []
    seen_refs: set[str] = set()

    # Search for notices mentioning "grant" in notice type or text
    grant_keywords = ["grant", "subsidy", "call for proposals", "donation"]
    offset = 0
    page_size = 100

    while True:
        try:
            params = {
                "format": "json",
                "rows": page_size,
                "os": offset,
                "qterm": "grant OR subsidy OR \"call for proposals\"",
                "srt": "new",
            }

            resp = requests.get(
                PROCNOTICES_API, params=params, headers=HEADERS, timeout=30
            )
            if resp.status_code != 200:
                logger.warning(f"WB Procnotices API {resp.status_code} offset={offset}")
                break

            data = resp.json()
            total = int(data.get("total", 0))
            notices = data.get("procnotices", {})

            if isinstance(notices, dict):
                notice_list = [v for v in notices.values() if isinstance(v, dict)]
            elif isinstance(notices, list):
                notice_list = notices
            else:
                break

            if not notice_list:
                break

            for notice in notice_list:
                title = notice.get("notice_text", notice.get("project_name", ""))
                if not title:
                    continue

                # Resolve country
                country_raw = (
                    notice.get("countryshortname", "")
                    or notice.get("countryname", "")
                )
                country_code, country_name = _resolve_country(country_raw)
                if not country_code:
                    # Try to find country in title
                    for name, code in _WB_COUNTRY_TO_CODE.items():
                        if code and name in title.lower():
                            country_code = code
                            country_name = MENA_COUNTRIES[code]
                            break
                if not country_code:
                    continue  # Skip non-MENA

                ref_no = str(notice.get("notice_no", notice.get("id", "")))
                dedup_key = ref_no or title[:80]
                if dedup_key in seen_refs:
                    continue
                seen_refs.add(dedup_key)

                # Verify this is actually grant-related
                combined = (
                    f"{title} {notice.get('notice_type', '')} "
                    f"{notice.get('procurement_group', '')}"
                ).lower()
                is_grant = any(kw in combined for kw in grant_keywords)
                if not is_grant:
                    continue

                notice_type = notice.get("notice_type", "")
                procurement_method = notice.get("procurement_method", "")
                project_name = notice.get("project_name", "")
                deadline_raw = notice.get(
                    "submission_date", notice.get("deadline_date", "")
                )
                publish_raw = notice.get(
                    "notice_posted_date", notice.get("noticedate", "")
                )
                contact = notice.get("contact_info", "")

                description = " | ".join(filter(None, [
                    project_name, notice_type, procurement_method,
                ]))

                grant = {
                    "id": generate_grant_id("world_bank_proc", dedup_key),
                    "title": title[:500],
                    "title_ar": "",
                    "title_fr": "",
                    "source": "world_bank",
                    "source_ref": ref_no,
                    "source_url": notice.get("url", ""),
                    "funding_organization": "World Bank",
                    "funding_organization_ar": "البنك الدولي",
                    "funding_organization_fr": "Banque mondiale",
                    "funding_amount": 0,
                    "funding_amount_max": 0,
                    "currency": "USD",
                    "grant_type": classify_grant_type(combined),
                    "country": country_name,
                    "country_code": country_code,
                    "region": "MENA",
                    "sector": classify_sector(title + " " + description),
                    "sectors": [classify_sector(title + " " + description)],
                    "eligibility_criteria": procurement_method or "",
                    "eligibility_countries": [country_code],
                    "description": description or title,
                    "description_ar": "",
                    "description_fr": "",
                    "application_deadline": parse_date(str(deadline_raw)) or "",
                    "publish_date": parse_date(str(publish_raw)) or "",
                    "status": "open",
                    "contact_info": contact,
                    "documents_url": notice.get("url", ""),
                    "tags": ["procurement_grant", notice_type] if notice_type else ["procurement_grant"],
                    "metadata": {
                        "notice_type": notice_type,
                        "procurement_method": procurement_method,
                    },
                }
                grants.append(grant)

            offset += page_size
            if offset >= total or offset >= 3000:
                break

            time.sleep(0.3)

        except Exception as e:
            logger.error(f"WB Procnotices error offset={offset}: {e}")
            break

    logger.info(f"World Bank grant procurement notices: {len(grants)}")
    return grants


def scrape() -> list[dict]:
    """Scrape World Bank for MENA grant opportunities from both APIs."""
    logger.info("Starting World Bank grants scraper...")

    # Phase 1: IBRD/IDA projects
    project_grants = _scrape_projects()
    logger.info(f"Phase 1 — Projects: {len(project_grants)} grants")

    # Phase 2: Grant-type procurement notices
    proc_grants = _scrape_grant_procnotices()
    logger.info(f"Phase 2 — Procurement: {len(proc_grants)} grants")

    # Merge and deduplicate by source_ref
    all_grants = project_grants
    seen_refs = {g["source_ref"] for g in all_grants}
    for g in proc_grants:
        if g["source_ref"] not in seen_refs:
            seen_refs.add(g["source_ref"])
            all_grants.append(g)

    logger.info(f"World Bank total grants: {len(all_grants)}")
    return all_grants


if __name__ == "__main__":
    results = scrape()
    save_grants(results, "world_bank")
    print(f"Scraped {len(results)} grants from World Bank")
