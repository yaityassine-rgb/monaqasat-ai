"""
Scraper Orchestrator — HTTP API for triggering and monitoring scrapers from the Admin Dashboard.

Runs as a lightweight Flask server alongside the main app.
The admin dashboard sends requests to start/stop/monitor scraper jobs.

Usage:
    python orchestrator.py                    # Start on port 8787
    python orchestrator.py --port 9090        # Custom port

API Endpoints:
    GET  /api/scrapers              — List all available scrapers
    GET  /api/scrapers/status       — Get status of all scrapers (last run, next scheduled)
    POST /api/scrapers/run          — Trigger a scraper run {scraper_name, type}
    POST /api/scrapers/run-all      — Trigger all scrapers of a type {type: "grants"|"ppp"|...}
    GET  /api/scrapers/runs         — Get recent scraper run history
    GET  /api/scrapers/runs/:id     — Get specific run details
    POST /api/scrapers/runs/:id/cancel — Cancel a running scraper
    GET  /api/scrapers/stats        — Get aggregate stats (total records per type)
    POST /api/scrapers/upload       — Trigger upload to Supabase {type}
"""

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("orchestrator")

try:
    from flask import Flask, jsonify, request
    from flask_cors import CORS
except ImportError:
    if __name__ == "__main__":
        logger.error("Flask not installed. Run: pip install flask flask-cors")
        sys.exit(1)
    else:
        # Allow import for registration purposes without Flask
        Flask = None  # type: ignore

from config import DATA_DIR, GRANTS_DIR, PPP_DIR, COMPANIES_DIR, MARKET_DIR, PREQ_DIR

app = Flask(__name__)
CORS(app)

# ============================================================
# In-memory job tracker (persisted to disk)
# ============================================================
JOBS_FILE = DATA_DIR / "orchestrator_jobs.json"
_jobs: list[dict] = []
_jobs_lock = threading.Lock()
_active_threads: dict[int, threading.Thread] = {}
_cancel_flags: dict[int, bool] = {}


def _load_jobs():
    global _jobs
    if JOBS_FILE.exists():
        with open(JOBS_FILE) as f:
            _jobs = json.load(f)


def _save_jobs():
    with open(JOBS_FILE, "w") as f:
        json.dump(_jobs[-500:], f, indent=2)  # Keep last 500 runs


def _next_job_id() -> int:
    return max((j["id"] for j in _jobs), default=0) + 1


# ============================================================
# Scraper Registry
# ============================================================
SCRAPER_REGISTRY = {
    # Tenders (original)
    "tenders_all": {"name": "All Tenders", "type": "tenders", "module": "run_all", "fn": "main"},
    # Grants
    "grants_worldbank": {"name": "Grants: World Bank", "type": "grants", "module": "scrape_grants_worldbank"},
    "grants_afdb": {"name": "Grants: AfDB", "type": "grants", "module": "scrape_grants_afdb"},
    "grants_isdb": {"name": "Grants: IsDB", "type": "grants", "module": "scrape_grants_isdb"},
    "grants_eu": {"name": "Grants: EU/TED", "type": "grants", "module": "scrape_grants_eu"},
    "grants_ungm": {"name": "Grants: UNGM", "type": "grants", "module": "scrape_grants_ungm"},
    "grants_ebrd": {"name": "Grants: EBRD", "type": "grants", "module": "scrape_grants_ebrd"},
    # PPP
    "ppp_worldbank": {"name": "PPP: World Bank PPI", "type": "ppp", "module": "scrape_ppp_worldbank"},
    "ppp_infraprojects": {"name": "PPP: Infra Projects", "type": "ppp", "module": "scrape_ppp_infraprojects"},
    "ppp_meed": {"name": "PPP: MEED/Zawya", "type": "ppp", "module": "scrape_ppp_meed"},
    "ppp_national": {"name": "PPP: National Portals", "type": "ppp", "module": "scrape_ppp_national"},
    # Companies
    "companies_opencorp": {"name": "Companies: OpenCorporates", "type": "companies", "module": "scrape_companies_opencorp"},
    "companies_vendors": {"name": "Companies: Vendor Registries", "type": "companies", "module": "scrape_companies_vendors"},
    "companies_directories": {"name": "Companies: Directories", "type": "companies", "module": "scrape_companies_directories"},
    "companies_seed": {"name": "Companies: Seed Data", "type": "companies", "module": "scrape_companies_seed"},
    # Grants (new sources)
    "grants_adb": {"name": "Grants: Asian Dev Bank", "type": "grants", "module": "scrape_grants_adb"},
    "grants_idb_latam": {"name": "Grants: Inter-American Dev Bank", "type": "grants", "module": "scrape_grants_idb"},
    "grants_opec": {"name": "Grants: OPEC Fund", "type": "grants", "module": "scrape_grants_opec"},
    "grants_afesd": {"name": "Grants: Arab Fund (AFESD)", "type": "grants", "module": "scrape_grants_afesd"},
    "grants_ocds": {"name": "Grants: Open Contracting (OCDS)", "type": "grants", "module": "scrape_grants_ocds"},
    "grants_un_habitat": {"name": "Grants: UN-Habitat & Agencies", "type": "grants", "module": "scrape_grants_un_habitat"},
    # Tenders (GCC expansion)
    "tenders_nupco": {"name": "Tenders: Saudi NUPCO", "type": "tenders", "module": "scrape_nupco"},
    "tenders_dubai_esupply": {"name": "Tenders: Dubai eSupply", "type": "tenders", "module": "scrape_dubai_esupply"},
    "tenders_sharjah": {"name": "Tenders: Sharjah eProcurement", "type": "tenders", "module": "scrape_sharjah"},
    "tenders_uae_mof": {"name": "Tenders: UAE Ministry of Finance", "type": "tenders", "module": "scrape_uae_mof"},
    "tenders_oman_et": {"name": "Tenders: Oman eTendering", "type": "tenders", "module": "scrape_oman_etendering"},
    "tenders_bahrain_et": {"name": "Tenders: Bahrain eTendering", "type": "tenders", "module": "scrape_bahrain_etendering"},
    # Tenders (North Africa & Levant expansion)
    "tenders_tunisia": {"name": "Tenders: Tunisia TUNEPS", "type": "tenders", "module": "scrape_tunisia"},
    "tenders_bomop": {"name": "Tenders: Algeria BOMOP", "type": "tenders", "module": "scrape_bomop"},
    "tenders_egypt_gpp": {"name": "Tenders: Egypt GPP", "type": "tenders", "module": "scrape_egypt_gpp"},
    "tenders_iraq": {"name": "Tenders: Iraq MOP/IOM", "type": "tenders", "module": "scrape_iraq"},
    "tenders_morocco_mp": {"name": "Tenders: Morocco Marchés Publics", "type": "tenders", "module": "scrape_morocco_marchespublics"},
    "tenders_jordan_gtd": {"name": "Tenders: Jordan GTD", "type": "tenders", "module": "scrape_jordan_gtd"},
    # Pre-Qualification
    "prequalification": {"name": "Pre-Qualification: MENA", "type": "preq", "module": "scrape_prequalification"},
    # Market Intelligence
    "market_worldbank": {"name": "Market: World Bank API", "type": "market", "module": "scrape_market_worldbank"},
    "market_seed": {"name": "Market: Seed Data", "type": "market", "module": "scrape_market_seed"},
}


# ============================================================
# Job execution
# ============================================================
def _run_scraper_job(job_id: int, scraper_key: str):
    """Execute a scraper in a background thread and update job status."""
    info = SCRAPER_REGISTRY[scraper_key]
    module_name = info["module"]
    save_fn_map = {
        "grants": "save_grants",
        "ppp": "save_ppp_projects",
        "companies": "save_companies",
        "preq": "save_prequalification",
        "market": "save_market_data",
        "tenders": None,
    }

    with _jobs_lock:
        job = next(j for j in _jobs if j["id"] == job_id)
        job["status"] = "running"
        job["started_at"] = datetime.now().isoformat()
        _save_jobs()

    try:
        mod = __import__(module_name)

        # Special case for tenders_all
        if scraper_key == "tenders_all":
            mod.main()
            records = 0  # run_all handles its own counting
        else:
            results = mod.scrape()
            records = len(results) if results else 0

            # Save results
            if results and save_fn_map.get(info["type"]):
                from base_scraper import (
                    save_grants, save_ppp_projects, save_companies,
                    save_market_data, save_prequalification,
                )
                save_fns = {
                    "save_grants": save_grants,
                    "save_ppp_projects": save_ppp_projects,
                    "save_companies": save_companies,
                    "save_market_data": save_market_data,
                    "save_prequalification": save_prequalification,
                }
                save_fn = save_fns[save_fn_map[info["type"]]]
                source = module_name.replace("scrape_", "")
                save_fn(results, source)

        with _jobs_lock:
            job["status"] = "completed"
            job["completed_at"] = datetime.now().isoformat()
            job["records_found"] = records
            started = datetime.fromisoformat(job["started_at"])
            job["duration_seconds"] = round((datetime.now() - started).total_seconds(), 1)
            _save_jobs()

    except Exception as e:
        with _jobs_lock:
            job["status"] = "failed"
            job["completed_at"] = datetime.now().isoformat()
            job["error_message"] = str(e)
            if job.get("started_at"):
                started = datetime.fromisoformat(job["started_at"])
                job["duration_seconds"] = round((datetime.now() - started).total_seconds(), 1)
            _save_jobs()
        logger.error(f"Job {job_id} ({scraper_key}) failed: {e}")

    finally:
        with _jobs_lock:
            _active_threads.pop(job_id, None)
            _cancel_flags.pop(job_id, None)


def _start_job(scraper_key: str, triggered_by: str = "admin") -> dict:
    """Create and start a scraper job. Returns job dict."""
    info = SCRAPER_REGISTRY[scraper_key]
    with _jobs_lock:
        job = {
            "id": _next_job_id(),
            "scraper_key": scraper_key,
            "scraper_name": info["name"],
            "scraper_type": info["type"],
            "status": "pending",
            "triggered_by": triggered_by,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "records_found": 0,
            "duration_seconds": 0,
            "error_message": "",
        }
        _jobs.append(job)
        _save_jobs()

    thread = threading.Thread(target=_run_scraper_job, args=(job["id"], scraper_key), daemon=True)
    _active_threads[job["id"]] = thread
    thread.start()

    return job


# ============================================================
# Data stats
# ============================================================
def _count_files_in_dir(directory: Path) -> tuple[int, int]:
    """Count JSON files and total records in a directory."""
    files = 0
    records = 0
    for f in directory.glob("*.json"):
        files += 1
        try:
            with open(f) as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    records += len(data)
        except Exception:
            pass
    return files, records


# ============================================================
# Flask API Routes
# ============================================================

@app.route("/api/scrapers", methods=["GET"])
def list_scrapers():
    """List all available scrapers."""
    scrapers = []
    for key, info in SCRAPER_REGISTRY.items():
        # Find last run
        last_run = None
        with _jobs_lock:
            runs = [j for j in _jobs if j["scraper_key"] == key and j["status"] == "completed"]
            if runs:
                last_run = runs[-1]

        scrapers.append({
            "key": key,
            "name": info["name"],
            "type": info["type"],
            "module": info["module"],
            "last_run": last_run,
            "is_running": any(
                j["scraper_key"] == key and j["status"] in ("pending", "running")
                for j in _jobs
            ),
        })
    return jsonify({"scrapers": scrapers})


@app.route("/api/scrapers/status", methods=["GET"])
def scrapers_status():
    """Get status overview of all scrapers."""
    status = {}
    for stype in ["tenders", "grants", "ppp", "companies", "preq", "market"]:
        dir_map = {
            "tenders": DATA_DIR,
            "grants": GRANTS_DIR,
            "ppp": PPP_DIR,
            "companies": COMPANIES_DIR,
            "preq": PREQ_DIR,
            "market": MARKET_DIR,
        }
        files, records = _count_files_in_dir(dir_map[stype])
        running = sum(
            1 for j in _jobs
            if j["scraper_type"] == stype and j["status"] in ("pending", "running")
        )
        status[stype] = {
            "files": files,
            "records": records,
            "running_jobs": running,
        }
    return jsonify({"status": status})


@app.route("/api/scrapers/run", methods=["POST"])
def run_scraper():
    """Trigger a specific scraper."""
    data = request.get_json() or {}
    scraper_key = data.get("scraper_key", data.get("scraper_name", ""))

    if scraper_key not in SCRAPER_REGISTRY:
        return jsonify({"error": f"Unknown scraper: {scraper_key}"}), 400

    # Check if already running
    with _jobs_lock:
        if any(j["scraper_key"] == scraper_key and j["status"] in ("pending", "running") for j in _jobs):
            return jsonify({"error": f"Scraper {scraper_key} is already running"}), 409

    job = _start_job(scraper_key, triggered_by=data.get("triggered_by", "admin"))
    return jsonify({"job": job}), 201


@app.route("/api/scrapers/run-all", methods=["POST"])
def run_all_scrapers():
    """Trigger all scrapers of a given type."""
    data = request.get_json() or {}
    stype = data.get("type", "all")

    if stype not in ["all", "tenders", "grants", "ppp", "companies", "preq", "market"]:
        return jsonify({"error": f"Unknown type: {stype}"}), 400

    jobs = []
    for key, info in SCRAPER_REGISTRY.items():
        if stype != "all" and info["type"] != stype:
            continue
        # Skip if already running
        with _jobs_lock:
            if any(j["scraper_key"] == key and j["status"] in ("pending", "running") for j in _jobs):
                continue
        job = _start_job(key, triggered_by=data.get("triggered_by", "admin"))
        jobs.append(job)
        time.sleep(0.1)  # Stagger starts slightly

    return jsonify({"jobs": jobs, "count": len(jobs)}), 201


@app.route("/api/scrapers/runs", methods=["GET"])
def list_runs():
    """Get recent scraper run history."""
    limit = request.args.get("limit", 50, type=int)
    stype = request.args.get("type", "")

    with _jobs_lock:
        runs = list(reversed(_jobs))
        if stype:
            runs = [j for j in runs if j["scraper_type"] == stype]
        runs = runs[:limit]

    return jsonify({"runs": runs, "total": len(_jobs)})


@app.route("/api/scrapers/runs/<int:run_id>", methods=["GET"])
def get_run(run_id: int):
    """Get specific run details."""
    with _jobs_lock:
        job = next((j for j in _jobs if j["id"] == run_id), None)
    if not job:
        return jsonify({"error": "Run not found"}), 404
    return jsonify({"run": job})


@app.route("/api/scrapers/runs/<int:run_id>/cancel", methods=["POST"])
def cancel_run(run_id: int):
    """Cancel a running scraper (best effort)."""
    with _jobs_lock:
        job = next((j for j in _jobs if j["id"] == run_id), None)
        if not job:
            return jsonify({"error": "Run not found"}), 404
        if job["status"] not in ("pending", "running"):
            return jsonify({"error": "Run is not active"}), 400
        job["status"] = "cancelled"
        job["completed_at"] = datetime.now().isoformat()
        _cancel_flags[run_id] = True
        _save_jobs()

    return jsonify({"message": f"Run {run_id} cancelled", "run": job})


@app.route("/api/scrapers/stats", methods=["GET"])
def scraper_stats():
    """Get aggregate statistics."""
    stats = {
        "data_counts": {},
        "total_runs": len(_jobs),
        "successful_runs": sum(1 for j in _jobs if j["status"] == "completed"),
        "failed_runs": sum(1 for j in _jobs if j["status"] == "failed"),
        "active_runs": sum(1 for j in _jobs if j["status"] in ("pending", "running")),
    }

    dir_map = {
        "tenders": DATA_DIR,
        "grants": GRANTS_DIR,
        "ppp": PPP_DIR,
        "companies": COMPANIES_DIR,
        "prequalification": PREQ_DIR,
        "market": MARKET_DIR,
    }
    for dtype, directory in dir_map.items():
        files, records = _count_files_in_dir(directory)
        stats["data_counts"][dtype] = {"files": files, "records": records}

    return jsonify(stats)


@app.route("/api/scrapers/upload", methods=["POST"])
def trigger_upload():
    """Trigger upload to Supabase."""
    data = request.get_json() or {}
    upload_type = data.get("type", "all")

    try:
        sys.argv = ["upload_all.py"]
        if upload_type != "all":
            sys.argv.extend(["--type", upload_type])

        from upload_all import main as upload_main

        # Run in background thread
        thread = threading.Thread(target=upload_main, daemon=True)
        thread.start()

        return jsonify({"message": f"Upload started for type: {upload_type}"}), 202
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "monaqasat-scraper-orchestrator",
        "timestamp": datetime.now().isoformat(),
        "scrapers_registered": len(SCRAPER_REGISTRY),
        "active_jobs": sum(1 for j in _jobs if j["status"] in ("pending", "running")),
    })


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper Orchestrator API")
    parser.add_argument("--port", type=int, default=8787, help="Port to listen on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    _load_jobs()
    logger.info(f"Loaded {len(_jobs)} historical job records")
    logger.info(f"Registered {len(SCRAPER_REGISTRY)} scrapers")
    logger.info(f"Starting orchestrator on {args.host}:{args.port}")

    app.run(host=args.host, port=args.port, debug=False)
