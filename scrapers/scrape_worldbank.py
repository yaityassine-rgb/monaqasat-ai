"""
Scraper for World Bank Procurement — FULL PAGINATION.
Source: https://search.worldbank.org/api/v2/procnotices

Single global query (no countrycode param) to avoid duplicates.
Country is extracted from the API response fields.
"""

import requests
import logging
import time
from config import HEADERS, MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("worldbank")

API_BASE = "https://search.worldbank.org/api/v2/procnotices"

# Reverse lookup: country name → ISO2 code
_COUNTRY_NAME_TO_CODE: dict[str, str] = {}
for _code, _name in MENA_COUNTRIES.items():
    _COUNTRY_NAME_TO_CODE[_name.lower()] = _code
# Add common WB variants
_COUNTRY_NAME_TO_CODE.update({
    "united arab emirates": "AE",
    "egypt, arab republic of": "EG",
    "egypt, arab rep.": "EG",
    "yemen, republic of": "YE",
    "yemen, rep.": "YE",
    "west bank and gaza": "PS",
    "west bank & gaza": "PS",
    "syrian arab republic": "",  # not MENA target
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

# Non-MENA countries that appear in WB data and must be filtered out
_NON_MENA = {
    "congo", "drc", "democratic republic of congo", "congo, democratic republic of",
    "cameroon", "nigeria", "kenya", "ethiopia", "uganda", "tanzania",
    "mozambique", "zambia", "zimbabwe", "malawi", "madagascar",
    "nepal", "bangladesh", "india", "pakistan", "sri lanka",
    "vietnam", "cambodia", "laos", "myanmar", "philippines",
    "mauritius", "senegal", "mali", "niger", "chad", "burkina faso",
    "ghana", "ivory coast", "cote d'ivoire", "benin", "togo",
    "guinea", "sierra leone", "liberia", "haiti", "honduras",
    "guatemala", "el salvador", "nicaragua", "bolivia", "paraguay",
    "afghanistan", "tajikistan", "kyrgyz republic", "uzbekistan",
}


def _resolve_country(notice: dict) -> tuple[str, str]:
    """Extract MENA country code and name from a WB notice.

    Returns ("", "") if the notice doesn't belong to a MENA country.
    """
    # 1. Try countryshortname from the response
    raw_country = (notice.get("countryshortname") or "").strip()
    if raw_country:
        code = _COUNTRY_NAME_TO_CODE.get(raw_country.lower(), "")
        if code:
            return code, MENA_COUNTRIES[code]
        # Explicitly non-MENA
        if raw_country.lower() in _NON_MENA:
            return "", ""

    # 2. Try title prefix pattern like "DZ - ..." or "MA: ..."
    title = notice.get("notice_text", notice.get("project_name", ""))
    if title and len(title) > 3:
        prefix = title[:2].upper()
        if prefix in MENA_COUNTRIES and title[2:3] in (" ", "-", ":"):
            return prefix, MENA_COUNTRIES[prefix]

    # 3. Scan title for country names
    title_lower = (title or "").lower()
    for name, code in _COUNTRY_NAME_TO_CODE.items():
        if code and name in title_lower:
            return code, MENA_COUNTRIES[code]

    # 4. Check if title mentions a clearly non-MENA country
    for non_mena in _NON_MENA:
        if non_mena in title_lower:
            return "", ""

    return "", ""


def scrape() -> list[dict]:
    """Scrape ALL World Bank procurement notices with a single global query."""
    tenders: list[dict] = []
    seen_refs: set[str] = set()
    offset = 0
    page_size = 100

    while True:
        try:
            params = {
                "format": "json",
                "rows": page_size,
                "os": offset,
                "srt": "new",
            }

            resp = requests.get(API_BASE, params=params, headers=HEADERS, timeout=30)

            if resp.status_code != 200:
                logger.warning(f"WB API {resp.status_code} offset={offset}")
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

                # Resolve country from response (not from request param)
                country_code, country_name = _resolve_country(notice)
                if not country_code:
                    continue  # Not a MENA country

                # Deduplicate by sourceRef
                ref_no = str(notice.get("notice_no", notice.get("id", "")))
                dedup_key = ref_no or title[:80]
                if dedup_key in seen_refs:
                    continue
                seen_refs.add(dedup_key)

                org = notice.get("bid_description", notice.get("borrower", ""))
                project_name = notice.get("project_name", "")
                deadline_raw = notice.get("submission_date", notice.get("deadline_date", ""))
                publish_raw = notice.get("notice_posted_date", notice.get("noticedate", ""))
                notice_type = notice.get("notice_type", "")
                procurement_method = notice.get("procurement_method", "")
                procurement_group = notice.get("procurement_group", "")
                notice_status = notice.get("notice_status", "")
                contact = notice.get("contact_info", "")

                description = " | ".join(filter(None, [
                    project_name, notice_type, procurement_method,
                    procurement_group, org
                ]))

                status = "open"
                if notice_status and "close" in notice_status.lower():
                    status = "closed"

                reqs = []
                if procurement_method:
                    reqs.append(procurement_method)
                if procurement_group:
                    reqs.append(procurement_group)

                tender = {
                    "id": generate_id("wb", dedup_key, ""),
                    "source": "World Bank",
                    "sourceRef": ref_no,
                    "sourceLanguage": "en",
                    "title": {"en": title[:500], "ar": title[:500], "fr": title[:500]},
                    "organization": {
                        "en": org or f"World Bank Project — {country_name}",
                        "ar": org or f"مشروع البنك الدولي — {country_name}",
                        "fr": org or f"Projet Banque mondiale — {country_name}",
                    },
                    "country": country_name,
                    "countryCode": country_code,
                    "sector": classify_sector(title + " " + description),
                    "budget": 0,
                    "currency": "USD",
                    "deadline": parse_date(str(deadline_raw)) or "",
                    "publishDate": parse_date(str(publish_raw)) or "",
                    "status": status,
                    "description": {"en": description, "ar": description, "fr": description},
                    "requirements": reqs,
                    "matchScore": 0,
                    "sourceUrl": notice.get("url", ""),
                    "contact": contact,
                }
                tenders.append(tender)

            offset += page_size

            # Stop when we've exhausted results or hit a reasonable cap
            if offset >= total or offset >= 5000:
                break

            time.sleep(0.3)

        except Exception as e:
            logger.error(f"WB error offset={offset}: {e}")
            break

    logger.info(f"World Bank total: {len(tenders)} unique MENA tenders (scanned {offset} notices)")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "worldbank")
    print(f"Scraped {len(results)} tenders from World Bank")
