"""Clean scraped tender data — deduplicate, validate countries, score quality."""

import json
import re
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent / "data"
INPUT = DATA_DIR / "tenders.json"
OUTPUT = DATA_DIR / "tenders_clean.json"

# MENA country codes (canonical)
MENA_CODES = {
    "MA", "SA", "AE", "EG", "KW", "QA", "BH", "OM",
    "JO", "TN", "DZ", "LY", "IQ", "LB", "PS", "SD", "YE", "MR",
}

# MENA country names for title scanning
MENA_NAMES: dict[str, str] = {
    "morocco": "MA", "saudi arabia": "SA", "uae": "AE",
    "united arab emirates": "AE", "egypt": "EG", "kuwait": "KW",
    "qatar": "QA", "bahrain": "BH", "oman": "OM", "jordan": "JO",
    "tunisia": "TN", "algeria": "DZ", "libya": "LY", "iraq": "IQ",
    "lebanon": "LB", "palestine": "PS", "sudan": "SD", "yemen": "YE",
    "mauritania": "MR",
}

# Non-MENA country names — if title mentions these, discard
NON_MENA_NAMES = {
    "democratic republic of congo", "drc", "congo", "cameroon", "nigeria",
    "kenya", "ethiopia", "uganda", "tanzania", "mozambique", "zambia",
    "zimbabwe", "malawi", "madagascar", "mauritius", "nepal", "bangladesh",
    "india", "pakistan", "sri lanka", "vietnam", "cambodia", "laos",
    "myanmar", "philippines", "senegal", "mali", "niger", "chad",
    "burkina faso", "ghana", "ivory coast", "benin", "togo",
    "guinea", "sierra leone", "liberia", "haiti", "honduras",
    "guatemala", "el salvador", "nicaragua", "bolivia", "paraguay",
    "afghanistan", "tajikistan", "kyrgyz republic", "uzbekistan",
    "djibouti", "somalia", "comoros", "seychelles",
}


def strip_html(text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "lxml")
    clean = soup.get_text(separator=" ")
    clean = re.sub(r"\s+", " ", clean).strip()
    clean = clean.replace("\xa0", " ").replace("&nbsp;", " ")
    return clean[:500]


def _normalize_title(title: str) -> str:
    """Normalize a title for deduplication."""
    t = title.lower().strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s]", "", t)
    return t


def _filter_closed(tenders: list[dict]) -> list[dict]:
    """Remove closed/expired tenders and tenders without apply links.

    Filters out:
    - Tenders with status == "closed"
    - Tenders whose deadline is >7 days in the past
    - Tenders without a sourceUrl (user can't apply → useless)
    """
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    result = []
    for t in tenders:
        if t.get("status") == "closed":
            continue
        deadline = t.get("deadline", "")
        if deadline and deadline < cutoff:
            continue
        if not t.get("sourceUrl"):
            continue
        result.append(t)
    return result


def _validate_country(tender: dict) -> dict | None:
    """Validate and potentially reassign country based on title content.

    Returns None if the tender should be discarded.
    """
    title_en = (tender.get("title", {}).get("en", "") or "").lower()
    desc_en = (tender.get("description", {}).get("en", "") or "").lower()
    text = f"{title_en} {desc_en}"
    country_code = tender.get("countryCode", "")

    # Check for explicit non-MENA country mentions in title
    for non_mena in NON_MENA_NAMES:
        if non_mena in title_en:
            return None  # Discard

    # Check if title mentions a different MENA country than assigned
    mentioned_codes: list[str] = []
    for name, code in MENA_NAMES.items():
        if name in text:
            mentioned_codes.append(code)

    if mentioned_codes:
        if country_code not in mentioned_codes:
            # Reassign to the first mentioned MENA country
            tender["countryCode"] = mentioned_codes[0]
            from config import MENA_COUNTRIES
            tender["country"] = MENA_COUNTRIES.get(mentioned_codes[0], tender.get("country", ""))

    return tender


def _compute_quality_score(tender: dict) -> int:
    """Compute a quality/match score based on data completeness."""
    score = 40  # base

    # Has budget
    if tender.get("budget", 0) > 0:
        score += 15

    # Has deadline
    if tender.get("deadline"):
        score += 10

    # Has description longer than just the title
    desc = tender.get("description", {}).get("en", "")
    title = tender.get("title", {}).get("en", "")
    if len(desc) > len(title) + 20:
        score += 10

    # Has source URL
    if tender.get("sourceUrl"):
        score += 5

    # Has requirements
    if tender.get("requirements") and len(tender["requirements"]) > 0:
        score += 5

    # Has publish date
    if tender.get("publishDate"):
        score += 5

    # Has contact info
    if tender.get("contact"):
        score += 5

    # Add deterministic variation (0-4) to avoid all same scores
    h = int(hashlib.md5(tender["id"].encode()).hexdigest()[:2], 16)
    score += h % 5

    return min(score, 99)


def clean_tender(tender: dict) -> dict | None:
    """Clean a single tender record."""
    # Clean multilingual text fields
    for field in ["title", "organization", "description"]:
        if isinstance(tender.get(field), dict):
            for lang in ["en", "ar", "fr"]:
                if lang in tender[field]:
                    tender[field][lang] = strip_html(tender[field][lang])

    # Remove tenders with empty/garbage titles
    title_en = tender.get("title", {}).get("en", "")
    if len(title_en) < 10:
        return None

    # Ensure status
    if not tender.get("status"):
        tender["status"] = "open"

    # Default sourceLanguage
    if not tender.get("sourceLanguage"):
        tender["sourceLanguage"] = "en"

    return tender


def deduplicate(tenders: list[dict]) -> list[dict]:
    """Content-based deduplication by (source, normalized_title) or sourceRef."""
    seen_titles: dict[str, dict] = {}  # dedup_key → best tender
    seen_refs: set[str] = set()
    result: list[dict] = []

    for t in tenders:
        # Dedup by sourceRef first (if present and non-empty)
        source_ref = t.get("sourceRef", "")
        source = t.get("source", "")
        if source_ref:
            ref_key = f"{source}:{source_ref}"
            if ref_key in seen_refs:
                continue
            seen_refs.add(ref_key)

        # Dedup by normalized title
        title_en = t.get("title", {}).get("en", "")
        norm = _normalize_title(title_en)
        title_key = f"{source}:{norm}"

        if title_key in seen_titles:
            existing = seen_titles[title_key]
            # Keep the one with better data (more fields filled)
            existing_score = _compute_quality_score(existing)
            new_score = _compute_quality_score(t)
            if new_score > existing_score:
                seen_titles[title_key] = t
            continue

        seen_titles[title_key] = t

    return list(seen_titles.values())


def main():
    with open(INPUT, encoding="utf-8") as f:
        data = json.load(f)

    raw_tenders = data.get("tenders", [])
    print(f"Raw tenders: {len(raw_tenders)}")

    # Step 1: Clean individual records
    cleaned = []
    for t in raw_tenders:
        result = clean_tender(t)
        if result:
            cleaned.append(result)
    print(f"After cleaning: {len(cleaned)}")

    # Step 2: Deduplicate
    deduped = deduplicate(cleaned)
    print(f"After deduplication: {len(deduped)}")

    # Step 3: Filter closed/expired tenders
    active = _filter_closed(deduped)
    print(f"After filtering closed/expired: {len(active)} (removed {len(deduped) - len(active)})")

    # Step 4: Validate countries
    validated = []
    discarded_country = 0
    for t in active:
        result = _validate_country(t)
        if result:
            validated.append(result)
        else:
            discarded_country += 1
    print(f"After country validation: {len(validated)} (discarded {discarded_country} non-MENA)")

    # Step 5: Compute quality scores
    for t in validated:
        t["matchScore"] = _compute_quality_score(t)

    # Save cleaned data
    output = {
        "lastUpdated": data.get("lastUpdated", ""),
        "totalCount": len(validated),
        "tenders": validated,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Final tenders: {len(validated)}")
    print(f"Saved to: {OUTPUT}")

    # Print sample
    if validated:
        sample = validated[0]
        print(f"\nSample tender:")
        print(f"  ID: {sample['id']}")
        print(f"  Title: {sample['title']['en'][:100]}")
        print(f"  Country: {sample['country']} ({sample['countryCode']})")
        print(f"  Sector: {sample['sector']}")
        print(f"  Match: {sample['matchScore']}%")
        print(f"  Language: {sample.get('sourceLanguage', '?')}")


if __name__ == "__main__":
    main()
