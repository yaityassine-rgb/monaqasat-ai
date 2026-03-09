"""
Upload cleaned tender data to Supabase.

Usage:
    python upload_to_supabase.py
    python upload_to_supabase.py --file path/to/tenders_clean.json
    python upload_to_supabase.py --trigger-embeddings
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("upload")

try:
    from supabase import create_client, Client
except ImportError:
    logger.error("supabase-py not installed. Run: pip install supabase")
    sys.exit(1)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

DEFAULT_FILE = Path(__file__).parent / "data" / "tenders_clean.json"
BATCH_SIZE = 100


def get_supabase() -> Client:
    """Create Supabase client with service role key."""
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    if not SUPABASE_URL or not key:
        logger.error("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables")
        sys.exit(1)
    return create_client(SUPABASE_URL, key)


def tender_to_row(t: dict) -> dict:
    """Convert tender JSON to Supabase row format."""
    title = t.get("title", {})
    org = t.get("organization", {})
    desc = t.get("description", {})

    return {
        "id": t["id"],
        "title_en": title.get("en", "") if isinstance(title, dict) else str(title),
        "title_ar": title.get("ar", "") if isinstance(title, dict) else "",
        "title_fr": title.get("fr", "") if isinstance(title, dict) else "",
        "organization_en": org.get("en", "") if isinstance(org, dict) else str(org),
        "organization_ar": org.get("ar", "") if isinstance(org, dict) else "",
        "organization_fr": org.get("fr", "") if isinstance(org, dict) else "",
        "country": t.get("country", ""),
        "country_code": t.get("countryCode", ""),
        "sector": t.get("sector", ""),
        "budget": float(t.get("budget", 0) or 0),
        "currency": t.get("currency", "USD"),
        "deadline": t.get("deadline", ""),
        "publish_date": t.get("publishDate", ""),
        "status": t.get("status", "open"),
        "description_en": desc.get("en", "") if isinstance(desc, dict) else str(desc),
        "description_ar": desc.get("ar", "") if isinstance(desc, dict) else "",
        "description_fr": desc.get("fr", "") if isinstance(desc, dict) else "",
        "requirements": t.get("requirements", []),
        "match_score": int(t.get("matchScore", 50) or 50),
        "source_language": t.get("sourceLanguage", "en"),
        "source_url": t.get("sourceUrl", ""),
        "source": t.get("source", ""),
    }


def upload_tenders(file_path: Path, trigger_embeddings: bool = False):
    """Upload tenders from JSON file to Supabase."""
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tenders = data.get("tenders", data) if isinstance(data, dict) else data
    logger.info(f"Loaded {len(tenders)} tenders from {file_path}")

    supabase = get_supabase()

    # Batch upsert
    uploaded = 0
    errors = 0

    for i in range(0, len(tenders), BATCH_SIZE):
        batch = tenders[i:i + BATCH_SIZE]
        rows = []
        for t in batch:
            try:
                rows.append(tender_to_row(t))
            except Exception as e:
                logger.warning(f"Skipping tender {t.get('id', '?')}: {e}")
                errors += 1

        if not rows:
            continue

        try:
            supabase.table("tenders").upsert(rows, on_conflict="id").execute()
            uploaded += len(rows)
            logger.info(f"Uploaded {uploaded}/{len(tenders)} tenders...")
        except Exception as e:
            logger.error(f"Batch upsert failed: {e}")
            errors += len(rows)

    logger.info(f"Upload complete: {uploaded} succeeded, {errors} errors")

    # Trigger embedding computation
    if trigger_embeddings:
        logger.info("Triggering embedding computation...")
        try:
            response = supabase.functions.invoke(
                "compute-embeddings",
                invoke_options={"body": {"type": "batch_tenders", "batchSize": 50}},
            )
            logger.info(f"Embedding response: {response}")
        except Exception as e:
            logger.warning(f"Embedding trigger failed (run manually): {e}")

    return uploaded


def main():
    parser = argparse.ArgumentParser(description="Upload tenders to Supabase")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE,
                        help="Path to tenders JSON file")
    parser.add_argument("--trigger-embeddings", action="store_true",
                        help="Trigger embedding computation after upload")
    args = parser.parse_args()
    upload_tenders(args.file, args.trigger_embeddings)


if __name__ == "__main__":
    main()
