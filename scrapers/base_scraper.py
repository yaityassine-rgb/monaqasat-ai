"""Base scraper class with common utilities."""

import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from config import SECTOR_KEYWORDS, DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


def classify_sector(text: str) -> str:
    """Classify tender into a sector based on keyword matching."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for sector, keywords in SECTOR_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[sector] = score
    if scores:
        return max(scores, key=scores.get)  # type: ignore
    return "it"  # default


def generate_id(source: str, ref: str, _country: str = "") -> str:
    """Generate a deterministic tender ID.

    Country is intentionally ignored so the same tender content
    always produces the same ID regardless of which API call found it.
    """
    raw = f"{source}:{ref}"
    h = hashlib.md5(raw.encode()).hexdigest()[:8]
    return f"TND-{h.upper()}"


def parse_date(date_str: str) -> Optional[str]:
    """Try to parse a date string into ISO format."""
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
    ]
    if not date_str:
        return None
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def save_tenders(tenders: list[dict], source: str) -> None:
    """Save scraped tenders to a JSON file."""
    out_file = DATA_DIR / f"{source}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(tenders, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved {len(tenders)} tenders to {out_file}")


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
