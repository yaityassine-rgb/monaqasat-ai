"""Configuration for Monaqasat AI scrapers — tenders, grants, PPP, companies, market intel."""

import os
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = DATA_DIR / "tenders.json"

# Sub-directories for expansion data
GRANTS_DIR = DATA_DIR / "grants"
GRANTS_DIR.mkdir(exist_ok=True)

PPP_DIR = DATA_DIR / "ppp"
PPP_DIR.mkdir(exist_ok=True)

COMPANIES_DIR = DATA_DIR / "companies"
COMPANIES_DIR.mkdir(exist_ok=True)

MARKET_DIR = DATA_DIR / "market"
MARKET_DIR.mkdir(exist_ok=True)

PREQ_DIR = DATA_DIR / "prequalification"
PREQ_DIR.mkdir(exist_ok=True)

# Supabase connection (used by upload scripts)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

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

# Arabic country names
MENA_COUNTRIES_AR = {
    "MA": "المغرب", "SA": "المملكة العربية السعودية", "AE": "الإمارات",
    "EG": "مصر", "KW": "الكويت", "QA": "قطر", "BH": "البحرين",
    "OM": "عُمان", "JO": "الأردن", "TN": "تونس", "DZ": "الجزائر",
    "LY": "ليبيا", "IQ": "العراق", "LB": "لبنان", "PS": "فلسطين",
    "SD": "السودان", "YE": "اليمن", "MR": "موريتانيا",
}

# French country names
MENA_COUNTRIES_FR = {
    "MA": "Maroc", "SA": "Arabie Saoudite", "AE": "Émirats Arabes Unis",
    "EG": "Égypte", "KW": "Koweït", "QA": "Qatar", "BH": "Bahreïn",
    "OM": "Oman", "JO": "Jordanie", "TN": "Tunisie", "DZ": "Algérie",
    "LY": "Libye", "IQ": "Irak", "LB": "Liban", "PS": "Palestine",
    "SD": "Soudan", "YE": "Yémen", "MR": "Mauritanie",
}

# Sector mapping keywords
SECTOR_KEYWORDS = {
    "construction": ["construction", "building", "road", "bridge", "highway", "infrastructure", "civil works", "renovation"],
    "it": ["IT", "software", "technology", "digital", "computer", "ICT", "information", "system", "platform", "cloud", "cyber"],
    "healthcare": ["health", "medical", "hospital", "pharmaceutical", "clinic", "vaccine", "laboratory"],
    "energy": ["energy", "solar", "power", "electricity", "oil", "gas", "renewable", "wind", "hydrogen", "nuclear"],
    "education": ["education", "school", "university", "training", "learning", "academic"],
    "transport": ["transport", "railway", "road", "airport", "port", "logistics", "vehicle", "fleet", "metro", "rail"],
    "defense": ["defense", "military", "security", "army", "police", "surveillance"],
    "water": ["water", "sanitation", "irrigation", "desalination", "sewage", "wastewater", "environment"],
    "telecom": ["telecom", "communication", "network", "5G", "fiber", "broadband", "mobile"],
    "agriculture": ["agriculture", "farming", "crop", "livestock", "food", "agri"],
    "tourism": ["tourism", "hotel", "resort", "hospitality", "entertainment", "leisure"],
    "real_estate": ["real estate", "housing", "residential", "commercial", "city", "urban", "development"],
    "mining": ["mining", "mineral", "phosphate", "quarry", "cement"],
    "finance": ["banking", "finance", "insurance", "fintech", "payment"],
}

# Grant type classification keywords
GRANT_TYPE_KEYWORDS = {
    "project_grant": ["project", "implementation", "execution", "works", "construction", "procurement"],
    "technical_assistance": ["technical assistance", "advisory", "consultancy", "capacity", "support", "TA"],
    "capacity_building": ["training", "capacity building", "institutional", "strengthening", "workshop"],
    "research": ["research", "study", "survey", "assessment", "evaluation", "analysis"],
    "emergency": ["emergency", "humanitarian", "relief", "crisis", "disaster", "urgent"],
}

# PPP contract type keywords
PPP_CONTRACT_KEYWORDS = {
    "BOT": ["build-operate-transfer", "BOT", "build operate transfer"],
    "BOO": ["build-own-operate", "BOO", "build own operate"],
    "BOOT": ["build-own-operate-transfer", "BOOT"],
    "BTO": ["build-transfer-operate", "BTO"],
    "concession": ["concession", "franchise"],
    "management": ["management contract", "O&M", "operations and maintenance"],
    "lease": ["lease", "affermage"],
    "divestiture": ["divestiture", "privatization", "privatisation"],
}

# Company size thresholds (by employee count)
COMPANY_SIZE_THRESHOLDS = {
    "micro": (0, 10),
    "small": (11, 50),
    "medium": (51, 250),
    "large": (251, 1000),
    "enterprise": (1001, float("inf")),
}

HEADERS = {
    "User-Agent": "MonaqasatAI-DataBot/2.0 (contact@monaqasat.ai)",
    "Accept": "application/json, text/html, application/xml",
    "Accept-Language": "en,ar,fr",
}
