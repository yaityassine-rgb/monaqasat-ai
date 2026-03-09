"""
Scraper for World Bank Documents API — procurement plans and bidding documents.
Source: https://search.worldbank.org/api/v3/wds

Country extracted from response fields, not from request loop variable.
Deduplicates by (title, projectid) before saving.
"""

import requests
import logging
import time
from config import HEADERS, MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("wb_docs")

API_BASE = "https://search.worldbank.org/api/v3/wds"

# World Bank uses full country names (some different from ours)
WB_COUNTRY_NAMES = {
    "MA": "Morocco",
    "SA": "Saudi Arabia",
    "AE": "United Arab Emirates",
    "EG": "Egypt, Arab Republic of",
    "KW": "Kuwait",
    "QA": "Qatar",
    "BH": "Bahrain",
    "OM": "Oman",
    "JO": "Jordan",
    "TN": "Tunisia",
    "DZ": "Algeria",
    "LY": "Libya",
    "IQ": "Iraq",
    "LB": "Lebanon",
    "PS": "West Bank and Gaza",
    "SD": "Sudan",
    "YE": "Yemen, Republic of",
    "MR": "Mauritania",
}

# Reverse lookup: WB response country name → ISO2
_RESPONSE_NAME_TO_CODE: dict[str, str] = {}
for _code, _wb_name in WB_COUNTRY_NAMES.items():
    _RESPONSE_NAME_TO_CODE[_wb_name.lower()] = _code
# Also add our canonical names
for _code, _name in MENA_COUNTRIES.items():
    _RESPONSE_NAME_TO_CODE[_name.lower()] = _code

DOC_TYPES = [
    "Procurement Plan",
    "Bidding Document",
    "Request for Proposal",
]


def _resolve_country_from_doc(doc: dict) -> tuple[str, str]:
    """Extract country from WB document response fields."""
    # Try countryshortname field in the response
    for field in ("countryshortname", "country", "countryname"):
        raw = (doc.get(field) or "").strip()
        if raw:
            code = _RESPONSE_NAME_TO_CODE.get(raw.lower(), "")
            if code:
                return code, MENA_COUNTRIES[code]
    return "", ""


def scrape() -> list[dict]:
    """Scrape World Bank documents API for procurement-related docs."""
    tenders: list[dict] = []
    seen: set[str] = set()  # (normalized_title, projectid) dedup

    for iso2, wb_name in WB_COUNTRY_NAMES.items():
        for doc_type in DOC_TYPES:
            try:
                params = {
                    "format": "json",
                    "docty_exact": doc_type,
                    "countryshortname": wb_name,
                    "rows": 50,
                    "os": 0,
                }

                resp = requests.get(API_BASE, params=params, headers=HEADERS, timeout=30)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                total = int(data.get("total", 0))
                documents = data.get("documents", {})

                if isinstance(documents, dict):
                    doc_list = [v for v in documents.values() if isinstance(v, dict)]
                elif isinstance(documents, list):
                    doc_list = documents
                else:
                    continue

                for doc in doc_list:
                    title = doc.get("display_title", doc.get("doctitle", ""))
                    if not title or len(title) < 10:
                        continue

                    project = doc.get("projectid", "")

                    # Deduplicate by (title, projectid)
                    dedup_key = f"{title.strip().lower()}|{project}"
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)

                    # Extract country from response, not loop variable
                    resp_code, resp_name = _resolve_country_from_doc(doc)
                    # Fall back to the request country if response doesn't have it
                    country_code = resp_code or iso2
                    country_name = resp_name or MENA_COUNTRIES.get(iso2, wb_name)

                    pub_date = doc.get("docdt", doc.get("discdt", ""))
                    doc_url = doc.get("url", doc.get("pdfurl", ""))
                    abstract = doc.get("abstracts", doc.get("textcont", ""))

                    tender = {
                        "id": generate_id("wbd", title[:80], ""),
                        "source": "World Bank Documents",
                        "sourceRef": project,
                        "sourceLanguage": "en",
                        "title": {
                            "en": f"{title} ({doc_type})",
                            "ar": f"{title} ({doc_type})",
                            "fr": f"{title} ({doc_type})",
                        },
                        "organization": {
                            "en": f"World Bank — {country_name}",
                            "ar": f"البنك الدولي — {country_name}",
                            "fr": f"Banque mondiale — {country_name}",
                        },
                        "country": country_name,
                        "countryCode": country_code,
                        "sector": classify_sector(title + " " + str(abstract)),
                        "budget": 0,
                        "currency": "USD",
                        "deadline": "",
                        "publishDate": parse_date(str(pub_date)) or "",
                        "status": "open",
                        "description": {
                            "en": str(abstract)[:500] if abstract else title,
                            "ar": str(abstract)[:500] if abstract else title,
                            "fr": str(abstract)[:500] if abstract else title,
                        },
                        "requirements": [doc_type],
                        "matchScore": 0,
                        "sourceUrl": doc_url,
                    }
                    tenders.append(tender)

                if total > 0:
                    logger.info(f"WB Docs {iso2} {doc_type}: {len(doc_list)} of {total}")

                time.sleep(0.2)

            except Exception as e:
                logger.error(f"WB Docs {iso2} {doc_type}: {e}")

    logger.info(f"World Bank Documents total: {len(tenders)} unique")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "wb_docs")
    print(f"Scraped {len(results)} documents from World Bank")
