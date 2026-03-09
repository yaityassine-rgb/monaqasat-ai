"""
Master scraper runner — runs all scrapers and merges results.
"""

import json
import logging
from datetime import datetime
from config import OUTPUT_FILE, DATA_DIR
from base_scraper import load_all_tenders

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("runner")


def run_scraper(name: str, module_name: str) -> int:
    """Run a single scraper and return count."""
    try:
        logger.info(f"Running {name} scraper...")
        mod = __import__(module_name)
        results = mod.scrape()
        mod.save_tenders(results, module_name.replace("scrape_", ""))
        logger.info(f"{name}: {len(results)} tenders")
        return len(results)
    except Exception as e:
        logger.error(f"{name} scraper failed: {e}")
        return 0


def merge_all() -> list[dict]:
    """Merge all scraped data, deduplicate by ID."""
    all_tenders = load_all_tenders()

    # Deduplicate by ID
    seen = set()
    unique = []
    for t in all_tenders:
        if t["id"] not in seen:
            seen.add(t["id"])
            unique.append(t)

    # Sort by publish date (newest first)
    unique.sort(key=lambda x: x.get("publishDate", ""), reverse=True)

    # Save merged output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "lastUpdated": datetime.now().isoformat(),
            "totalCount": len(unique),
            "tenders": unique,
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"Merged: {len(unique)} unique tenders → {OUTPUT_FILE}")
    return unique


def main():
    DATA_DIR.mkdir(exist_ok=True)

    scrapers = [
        ("World Bank", "scrape_worldbank"),
        ("UNGM", "scrape_ungm"),
        ("AfDB", "scrape_afdb"),
        ("dgMarket", "scrape_dgmarket"),
        ("TED (EU)", "scrape_ted"),
    ]

    total = 0
    for name, module in scrapers:
        count = run_scraper(name, module)
        total += count

    logger.info(f"\nTotal scraped: {total} tenders")

    # Merge all into single file
    merged = merge_all()
    logger.info(f"Final merged: {len(merged)} unique tenders")

    # Print summary
    countries: dict[str, int] = {}
    sources: dict[str, int] = {}
    for t in merged:
        c = t.get("countryCode", "XX")
        countries[c] = countries.get(c, 0) + 1
        s = t.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1

    print("\n=== SCRAPING SUMMARY ===")
    print(f"Total unique tenders: {len(merged)}")
    print(f"\nBy source:")
    for s, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {s}: {count}")
    print(f"\nBy country:")
    for c, count in sorted(countries.items(), key=lambda x: -x[1]):
        print(f"  {c}: {count}")


if __name__ == "__main__":
    main()
