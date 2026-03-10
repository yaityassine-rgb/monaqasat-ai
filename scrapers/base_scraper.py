"""Base scraper class with common utilities for tenders, grants, PPP, companies, market intel."""

import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from config import (
    SECTOR_KEYWORDS, GRANT_TYPE_KEYWORDS, PPP_CONTRACT_KEYWORDS,
    COMPANY_SIZE_THRESHOLDS, DATA_DIR, GRANTS_DIR, PPP_DIR,
    COMPANIES_DIR, MARKET_DIR, PREQ_DIR,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


def classify_sector(text: str) -> str:
    """Classify into a sector based on keyword matching."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for sector, keywords in SECTOR_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[sector] = score
    if scores:
        return max(scores, key=scores.get)  # type: ignore
    return "it"  # default


def classify_grant_type(text: str) -> str:
    """Classify grant type from description text."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for gtype, keywords in GRANT_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[gtype] = score
    if scores:
        return max(scores, key=scores.get)  # type: ignore
    return "project_grant"


def classify_ppp_contract(text: str) -> str:
    """Classify PPP contract type from description text."""
    text_lower = text.lower()
    for ctype, keywords in PPP_CONTRACT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return ctype
    return "concession"


def classify_company_size(employee_count: Optional[int] = None, revenue: Optional[float] = None) -> str:
    """Classify company size based on employee count or revenue."""
    if employee_count and employee_count > 0:
        for size, (low, high) in COMPANY_SIZE_THRESHOLDS.items():
            if low <= employee_count <= high:
                return size
    if revenue and revenue > 0:
        if revenue > 1_000_000_000:
            return "enterprise"
        elif revenue > 100_000_000:
            return "large"
        elif revenue > 10_000_000:
            return "medium"
        elif revenue > 1_000_000:
            return "small"
        else:
            return "micro"
    return "medium"


def generate_id(source: str, ref: str, _country: str = "") -> str:
    """Generate a deterministic tender ID.

    Country is intentionally ignored so the same tender content
    always produces the same ID regardless of which API call found it.
    """
    raw = f"{source}:{ref}"
    h = hashlib.md5(raw.encode()).hexdigest()[:8]
    return f"TND-{h.upper()}"


def generate_grant_id(source: str, ref: str) -> str:
    """Generate a deterministic grant ID."""
    raw = f"grant:{source}:{ref}"
    h = hashlib.md5(raw.encode()).hexdigest()[:10]
    return f"GRT-{h.upper()}"


def generate_ppp_id(source: str, ref: str) -> str:
    """Generate a deterministic PPP project ID."""
    raw = f"ppp:{source}:{ref}"
    h = hashlib.md5(raw.encode()).hexdigest()[:10]
    return f"PPP-{h.upper()}"


def generate_company_id(source: str, ref: str) -> str:
    """Generate a deterministic company ID."""
    raw = f"company:{source}:{ref}"
    h = hashlib.md5(raw.encode()).hexdigest()[:10]
    return f"CMP-{h.upper()}"


def parse_date(date_str: str) -> Optional[str]:
    """Try to parse a date string into ISO format."""
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d-%b-%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
        "%Y",
    ]
    if not date_str:
        return None
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_amount(amount_str) -> float:
    """Parse a monetary amount from various formats."""
    if not amount_str:
        return 0
    if isinstance(amount_str, (int, float)):
        return float(amount_str)
    try:
        cleaned = str(amount_str).replace(",", "").replace("$", "").replace("€", "").replace("£", "").strip()
        # Handle "M" suffix (millions)
        if cleaned.upper().endswith("M"):
            return float(cleaned[:-1]) * 1_000_000
        # Handle "B" suffix (billions)
        if cleaned.upper().endswith("B"):
            return float(cleaned[:-1]) * 1_000_000_000
        # Handle "K" suffix (thousands)
        if cleaned.upper().endswith("K"):
            return float(cleaned[:-1]) * 1_000
        return float(cleaned)
    except (ValueError, TypeError):
        return 0


def save_tenders(tenders: list[dict], source: str) -> None:
    """Save scraped tenders to a JSON file."""
    out_file = DATA_DIR / f"{source}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(tenders, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved {len(tenders)} tenders to {out_file}")


def save_grants(grants: list[dict], source: str) -> None:
    """Save scraped grants to a JSON file."""
    out_file = GRANTS_DIR / f"{source}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(grants, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved {len(grants)} grants to {out_file}")


def save_ppp_projects(projects: list[dict], source: str) -> None:
    """Save scraped PPP projects to a JSON file."""
    out_file = PPP_DIR / f"{source}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved {len(projects)} PPP projects to {out_file}")


def save_companies(companies: list[dict], source: str) -> None:
    """Save scraped companies to a JSON file."""
    out_file = COMPANIES_DIR / f"{source}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(companies, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved {len(companies)} companies to {out_file}")


def save_market_data(data: list[dict], source: str) -> None:
    """Save market intelligence data to a JSON file."""
    out_file = MARKET_DIR / f"{source}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved {len(data)} market records to {out_file}")


def save_prequalification(data: list[dict], source: str) -> None:
    """Save pre-qualification data to a JSON file."""
    out_file = PREQ_DIR / f"{source}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved {len(data)} prequalification records to {out_file}")


def load_all_tenders() -> list[dict]:
    """Load all scraped tenders from all source files."""
    skip = {"tenders.json", "tenders_clean.json"}
    all_tenders = []
    for f in DATA_DIR.glob("*.json"):
        if f.name in skip:
            continue
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, list):
                all_tenders.extend(data)
            elif isinstance(data, dict) and "tenders" in data:
                all_tenders.extend(data["tenders"])
    return all_tenders


def load_all_from_dir(directory: Path) -> list[dict]:
    """Load all JSON records from a subdirectory."""
    all_items = []
    for f in directory.glob("*.json"):
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, list):
                all_items.extend(data)
    return all_items
