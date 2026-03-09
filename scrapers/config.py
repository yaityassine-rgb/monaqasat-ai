"""Configuration for tender scrapers."""

import os
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = DATA_DIR / "tenders.json"

# MENA country codes we target
MENA_COUNTRIES = {
    "MA": "Morocco",
    "SA": "Saudi Arabia",
    "AE": "UAE",
    "EG": "Egypt",
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
    "PS": "Palestine",
    "SD": "Sudan",
    "YE": "Yemen",
    "MR": "Mauritania",
}

# Sector mapping keywords
SECTOR_KEYWORDS = {
    "construction": ["construction", "building", "road", "bridge", "highway", "infrastructure", "civil works", "renovation"],
    "it": ["IT", "software", "technology", "digital", "computer", "ICT", "information", "system", "platform", "cloud", "cyber"],
    "healthcare": ["health", "medical", "hospital", "pharmaceutical", "clinic", "vaccine", "laboratory"],
    "energy": ["energy", "solar", "power", "electricity", "oil", "gas", "renewable", "wind"],
    "education": ["education", "school", "university", "training", "learning", "academic"],
    "transport": ["transport", "railway", "road", "airport", "port", "logistics", "vehicle", "fleet"],
    "defense": ["defense", "military", "security", "army", "police", "surveillance"],
    "water": ["water", "sanitation", "irrigation", "desalination", "sewage", "wastewater", "environment"],
    "telecom": ["telecom", "communication", "network", "5G", "fiber", "broadband", "mobile"],
    "agriculture": ["agriculture", "farming", "crop", "livestock", "food", "agri"],
}

HEADERS = {
    "User-Agent": "MonaqasatAI-TenderBot/1.0 (contact@monaqasat.ai)",
    "Accept": "application/json, text/html, application/xml",
    "Accept-Language": "en,ar,fr",
}
