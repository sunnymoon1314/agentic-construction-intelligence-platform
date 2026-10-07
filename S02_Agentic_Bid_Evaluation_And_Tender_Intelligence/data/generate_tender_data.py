#!/usr/bin/env python3
"""
S02: Synthetic Hospital Tender Dataset Generator
Project: Woodlands Health Campus Acute Care Wing (S$120,000,000 Baseline)
Tender ID: TND-WHC-2026-001

This script synthesizes:
1. Master Contractor Registry: 50 BCA registered contractors across Singapore (Grades A1, A2, B1, B2).
2. Tender Project Registry: TND-WHC-2026-001 (Woodlands Health Campus Acute Care Wing, S$120M Baseline).
3. Multi-trade Bill of Quantities (BOQ): 8 core AEC trade packages and 18 detailed line items.
4. Five Shortlisted Bidders (filtered from 50 contractors for TND-WHC-2026-001) reusing canonical S01 contractors:
   - B01: Heng Win (Private) Limited (Compliant Benchmark, S$113.87M, balanced rates)
   - B02: WinningPine Construction Pte Ltd (Cash-Flow Front-Loader, +85% substructure, -35% MEP, FLRI 1.75)
   - B03: Starlight Urban Infrastructure Pte Ltd (Abnormally Low Tender / ALT, S$76.06M, -34% dumping)
   - B04: GemStone Building Contractors Pte Ltd (Concealed Scope Exclusion, QUAL-14.2 on page 38, -S$6.79M med gas)
   - B05: Titan Piling & Civil Engineering Pte Ltd (Outlier Over-Price, S$128.80M, +12.0% defensive premium)
5. Exports structured tables into DuckDB (hospital_tender.duckdb) and individual bidder JSON submissions.
"""

import os
import json
import duckdb

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
SUBMISSIONS_DIR = os.path.join(DATA_DIR, "tender_submissions")
DB_PATH = os.path.join(DATA_DIR, "hospital_tender.duckdb")

os.makedirs(SUBMISSIONS_DIR, exist_ok=True)

# ---------------------------------------------------------
# 1. Master Contractors Registry (50 BCA Registered Builders)
# ---------------------------------------------------------
MASTER_CONTRACTORS = [
    # Canonical S01 Contractors (6 Core Profiles)
    {"uen": "197600888B", "name": "Heng Win (Private) Limited", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01, CR03, ME01", "tendering_limit": 999999999.0, "net_worth": 185000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 93.5, "status": "ACTIVE"},
    {"uen": "197000345C", "name": "GemStone Building Contractors Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR09, ME05", "tendering_limit": 999999999.0, "net_worth": 142000000.0, "sdp": 6, "bizsafe": "bizSAFE STAR", "conquas": 89.2, "status": "ACTIVE"},
    {"uen": "198900123C", "name": "WinningPine Construction Pte Ltd", "grade": "CW01-A2", "workheads": "CW01, CR01, ME01", "tendering_limit": 85000000.0, "net_worth": 45000000.0, "sdp": 12, "bizsafe": "bizSAFE Level 3", "conquas": 88.0, "status": "ACTIVE"},
    {"uen": "200100999D", "name": "Apex Builders Pte Ltd", "grade": "CW01-B1", "workheads": "CW01, CR03", "tendering_limit": 40000000.0, "net_worth": 22000000.0, "sdp": 18, "bizsafe": "bizSAFE Level 3", "conquas": 84.5, "status": "ACTIVE"},
    {"uen": "201000333E", "name": "Titan Piling & Civil Engineering Pte Ltd", "grade": "CW01-A2", "workheads": "CW02, CR01", "tendering_limit": 85000000.0, "net_worth": 28000000.0, "sdp": 28, "bizsafe": "bizSAFE Level 3", "conquas": 85.0, "status": "DEBARRED"},
    {"uen": "201500888F", "name": "Starlight Urban Infrastructure Pte Ltd", "grade": "CW01-B2", "workheads": "CW01, CW02", "tendering_limit": 13000000.0, "net_worth": 2800000.0, "sdp": 10, "bizsafe": "bizSAFE Level 2", "conquas": 79.5, "status": "ACTIVE"},

    # 44 Additional Authentic Singapore Main Contractors (Master Registry Expansion)
    {"uen": "194000001A", "name": "GrandPillar Infrastructure Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01, ME01", "tendering_limit": 999999999.0, "net_worth": 310000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 96.0, "status": "ACTIVE"},
    {"uen": "197000012B", "name": "Everest Building & Civil Engineering Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 195000000.0, "sdp": 2, "bizsafe": "bizSAFE STAR", "conquas": 92.5, "status": "ACTIVE"},
    {"uen": "197600023C", "name": "Soilbuild Construction Group Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01, ME01", "tendering_limit": 999999999.0, "net_worth": 125000000.0, "sdp": 4, "bizsafe": "bizSAFE STAR", "conquas": 91.0, "status": "ACTIVE"},
    {"uen": "198800034D", "name": "Lian Beng Construction (1988) Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 210000000.0, "sdp": 5, "bizsafe": "bizSAFE STAR", "conquas": 90.5, "status": "ACTIVE"},
    {"uen": "198300045E", "name": "Koh Brothers Building & Civil Engineering Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 160000000.0, "sdp": 3, "bizsafe": "bizSAFE STAR", "conquas": 92.0, "status": "ACTIVE"},
    {"uen": "197500056F", "name": "Kimly Construction Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 140000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 94.0, "status": "ACTIVE"},
    {"uen": "198800067G", "name": "Chip Eng Seng Contractors (1988) Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 180000000.0, "sdp": 2, "bizsafe": "bizSAFE STAR", "conquas": 91.5, "status": "ACTIVE"},
    {"uen": "199200078H", "name": "Teambuild Engineering & Construction Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 130000000.0, "sdp": 4, "bizsafe": "bizSAFE STAR", "conquas": 93.0, "status": "ACTIVE"},
    {"uen": "196900089J", "name": "Straits Construction Singapore Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 175000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 94.5, "status": "ACTIVE"},
    {"uen": "198400091K", "name": "Vanguard Underground Engineering Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 240000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 95.0, "status": "ACTIVE"},
    {"uen": "196500102L", "name": "Kuraishi Engineering & Construction Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 280000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 96.5, "status": "ACTIVE"},
    {"uen": "197300113M", "name": "Shinsei Precision Builders Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 350000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 97.0, "status": "ACTIVE"},
    {"uen": "197400124N", "name": "Takenaka Corporation (Singapore Branch)", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 320000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 96.0, "status": "ACTIVE"},
    {"uen": "198800135P", "name": "Kajima Overseas Asia Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 290000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 95.5, "status": "ACTIVE"},
    {"uen": "196400146Q", "name": "Penta-Ocean Construction Co Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 270000000.0, "sdp": 2, "bizsafe": "bizSAFE STAR", "conquas": 94.0, "status": "ACTIVE"},
    {"uen": "198400157R", "name": "Nishimatsu Construction Co Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 220000000.0, "sdp": 3, "bizsafe": "bizSAFE STAR", "conquas": 93.0, "status": "ACTIVE"},
    {"uen": "196500168S", "name": "Sato Kogyo (S) Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 185000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 93.5, "status": "ACTIVE"},
    {"uen": "198100179T", "name": "DongHae Global Engineering Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 450000000.0, "sdp": 4, "bizsafe": "bizSAFE STAR", "conquas": 94.0, "status": "ACTIVE"},
    {"uen": "198000181U", "name": "SsangYong Engineering & Construction Co Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 260000000.0, "sdp": 2, "bizsafe": "bizSAFE STAR", "conquas": 93.0, "status": "ACTIVE"},
    {"uen": "196900192V", "name": "Low Keng Huat (Singapore) Limited", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 150000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 91.5, "status": "ACTIVE"},
    {"uen": "199900203W", "name": "Chiu Teng Construction Co Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 110000000.0, "sdp": 6, "bizsafe": "bizSAFE STAR", "conquas": 89.0, "status": "ACTIVE"},
    {"uen": "199300214X", "name": "BBR Construction Systems Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 95000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 92.0, "status": "ACTIVE"},
    {"uen": "195900225Y", "name": "Tiong Seng Contractors (Pte) Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 165000000.0, "sdp": 2, "bizsafe": "bizSAFE STAR", "conquas": 94.0, "status": "ACTIVE"},
    {"uen": "200000236Z", "name": "Expand Construction Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 105000000.0, "sdp": 8, "bizsafe": "bizSAFE Level 3", "conquas": 88.5, "status": "ACTIVE"},
    {"uen": "200400247A", "name": "HPC Builders Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 90000000.0, "sdp": 4, "bizsafe": "bizSAFE STAR", "conquas": 89.5, "status": "ACTIVE"},
    {"uen": "198300258B", "name": "Santarli Construction Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 115000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 91.0, "status": "ACTIVE"},
    {"uen": "198000269C", "name": "Wee Hur Construction Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 145000000.0, "sdp": 2, "bizsafe": "bizSAFE STAR", "conquas": 92.5, "status": "ACTIVE"},
    {"uen": "197000271D", "name": "Singapore Piling & Civil Engineering Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 135000000.0, "sdp": 6, "bizsafe": "bizSAFE STAR", "conquas": 90.0, "status": "ACTIVE"},
    {"uen": "198800282E", "name": "KTC Civil Engineering & Construction Pte Ltd", "grade": "CW01-A1", "workheads": "CW01, CW02, CR01", "tendering_limit": 999999999.0, "net_worth": 120000000.0, "sdp": 4, "bizsafe": "bizSAFE STAR", "conquas": 89.5, "status": "ACTIVE"},
    {"uen": "197800293F", "name": "Eng Seng Lee Construction Pte Ltd", "grade": "CW01-A2", "workheads": "CW01, CR01", "tendering_limit": 85000000.0, "net_worth": 52000000.0, "sdp": 2, "bizsafe": "bizSAFE Level 3", "conquas": 87.0, "status": "ACTIVE"},
    {"uen": "199200304G", "name": "Hwa Seng Builder Pte Ltd", "grade": "CW01-A2", "workheads": "CW01, CW02", "tendering_limit": 85000000.0, "net_worth": 48000000.0, "sdp": 6, "bizsafe": "bizSAFE Level 3", "conquas": 86.5, "status": "ACTIVE"},
    {"uen": "199000315H", "name": "Ley Choon Constructions and Engineering Pte Ltd", "grade": "CW01-A2", "workheads": "CW01, CW02", "tendering_limit": 85000000.0, "net_worth": 42000000.0, "sdp": 8, "bizsafe": "bizSAFE Level 3", "conquas": 85.0, "status": "ACTIVE"},
    {"uen": "197500326J", "name": "Samwoh Corporation Pte Ltd", "grade": "CW01-A2", "workheads": "CW01, CW02", "tendering_limit": 85000000.0, "net_worth": 65000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 88.5, "status": "ACTIVE"},
    {"uen": "196900337K", "name": "Hock Lian Seng Infrastructure Pte Ltd", "grade": "CW01-A2", "workheads": "CW01, CW02", "tendering_limit": 85000000.0, "net_worth": 70000000.0, "sdp": 0, "bizsafe": "bizSAFE STAR", "conquas": 90.0, "status": "ACTIVE"},
    {"uen": "198800348L", "name": "Chye Joo Construction Pte Ltd", "grade": "CW01-A2", "workheads": "CW01, CW02", "tendering_limit": 85000000.0, "net_worth": 39000000.0, "sdp": 10, "bizsafe": "bizSAFE Level 3", "conquas": 84.0, "status": "ACTIVE"},
    {"uen": "199000359M", "name": "Progressive Builders Pte Ltd", "grade": "CW01-A2", "workheads": "CW01, CR01", "tendering_limit": 85000000.0, "net_worth": 36000000.0, "sdp": 4, "bizsafe": "bizSAFE Level 3", "conquas": 86.0, "status": "ACTIVE"},
    {"uen": "198700361N", "name": "Welltech Construction Pte Ltd", "grade": "CW01-A2", "workheads": "CW01, CR01", "tendering_limit": 85000000.0, "net_worth": 44000000.0, "sdp": 6, "bizsafe": "bizSAFE Level 3", "conquas": 87.5, "status": "ACTIVE"},
    {"uen": "199100372P", "name": "Unison Construction Pte Ltd", "grade": "CW01-A2", "workheads": "CW01, CR01", "tendering_limit": 85000000.0, "net_worth": 38000000.0, "sdp": 2, "bizsafe": "bizSAFE Level 3", "conquas": 88.0, "status": "ACTIVE"},
    {"uen": "198900383Q", "name": "Ken-Pal (S) Pte Ltd", "grade": "CW01-B1", "workheads": "CW01, CR01", "tendering_limit": 40000000.0, "net_worth": 25000000.0, "sdp": 4, "bizsafe": "bizSAFE Level 3", "conquas": 83.5, "status": "ACTIVE"},
    {"uen": "200300394R", "name": "Sunhuan Construction Pte Ltd", "grade": "CW01-B1", "workheads": "CW01, CR01", "tendering_limit": 40000000.0, "net_worth": 21000000.0, "sdp": 8, "bizsafe": "bizSAFE Level 3", "conquas": 82.0, "status": "ACTIVE"},
    {"uen": "197300405S", "name": "Guan Ho Construction Co (Pte) Ltd", "grade": "CW01-B1", "workheads": "CW01, CR01", "tendering_limit": 40000000.0, "net_worth": 26000000.0, "sdp": 2, "bizsafe": "bizSAFE Level 3", "conquas": 85.0, "status": "ACTIVE"},
    {"uen": "198000416T", "name": "Thye Chuan Construction Pte Ltd", "grade": "CW01-B1", "workheads": "CW01, CR01", "tendering_limit": 40000000.0, "net_worth": 19000000.0, "sdp": 6, "bizsafe": "bizSAFE Level 3", "conquas": 84.0, "status": "ACTIVE"},
    {"uen": "198200427U", "name": "Fong Soon Engineering Pte Ltd", "grade": "CW01-B1", "workheads": "CW01, ME01", "tendering_limit": 40000000.0, "net_worth": 18000000.0, "sdp": 12, "bizsafe": "bizSAFE Level 3", "conquas": 81.5, "status": "ACTIVE"},
    {"uen": "199500438V", "name": "Singa Development Pte Ltd", "grade": "CW01-B2", "workheads": "CW01, CW02", "tendering_limit": 13000000.0, "net_worth": 7500000.0, "sdp": 14, "bizsafe": "bizSAFE Level 2", "conquas": 78.0, "status": "ACTIVE"}
]

# ---------------------------------------------------------
# 2. Multi-Project Registry (Executive Project Selection)
# ---------------------------------------------------------
TENDER_PROJECTS = [
    {
        "project_id": "PRJ-WHC-001",
        "tender_id": "TND-WHC-2026-001",
        "project_name": "Woodlands Health Campus — Acute Care Wing",
        "client_name": "Ministry of Health Holdings (MOHH)",
        "sector": "Healthcare Infrastructure",
        "pte_budget_sgd": 120000000.0,
        "currency": "SGD",
        "closing_date": "2026-10-15",
        "status": "EVALUATION_ACTIVE",
        "description": "700-bed regional acute care hospital wing including deep basement ERSS, bored piling, and medical gas pipeline networks."
    },
    {
        "project_id": "PRJ-TWRP-002",
        "tender_id": "TND-TWRP-2026-002",
        "project_name": "Tuas Water Reclamation Plant — Biosolids Facility",
        "client_name": "Public Utilities Board (PUB)",
        "sector": "Environmental & Water Utilities",
        "pte_budget_sgd": 240000000.0,
        "currency": "SGD",
        "closing_date": "2026-11-20",
        "status": "EVALUATION_PENDING",
        "description": "Deep tunnel sewerage scheme water reclamation plant contract 2A, specialized anaerobic digestion and energy recovery."
    },
    {
        "project_id": "PRJ-T5-003",
        "tender_id": "TND-T5-2026-003",
        "project_name": "Changi Airport Terminal 5 — Substructure & APM Tunnels",
        "client_name": "Changi Airport Group (CAG)",
        "sector": "Aviation & Transportation",
        "pte_budget_sgd": 380000000.0,
        "currency": "SGD",
        "closing_date": "2026-12-05",
        "status": "TENDER_CLOSED",
        "description": "Deep underground Automated People Mover (APM) transit tunnels, diaphragm perimeter walls, and heavy luggage transfer basements."
    }
]

# Legacy alias for backward compatibility
TENDER_PROJECT = TENDER_PROJECTS[0]

# ---------------------------------------------------------
# 3. Trade Package Definitions & Work Stages
# ---------------------------------------------------------
TRADES = [
    {"trade_id": "TRD-01", "name": "Demolition & Site Clearance", "stage": "Early Works", "category": "Substructure"},
    {"trade_id": "TRD-02", "name": "Deep Basement Excavation & ERSS", "stage": "Early Works", "category": "Substructure"},
    {"trade_id": "TRD-03", "name": "Bored Piling & Diaphragm Walls", "stage": "Early Works", "category": "Substructure"},
    {"trade_id": "TRD-04", "name": "Reinforced Concrete Superstructure", "stage": "Mid Works", "category": "Superstructure"},
    {"trade_id": "TRD-05", "name": "Architectural Finishes & Facade", "stage": "Late Works", "category": "Finishes"},
    {"trade_id": "TRD-06", "name": "Mechanical, Electrical & HVAC Services", "stage": "Late Works", "category": "Services"},
    {"trade_id": "TRD-07", "name": "Medical Gas & Cleanroom Piping", "stage": "Late Works", "category": "Services"},
    {"trade_id": "TRD-08", "name": "External Works, Drainage & Landscaping", "stage": "Late Works", "category": "External"},
]

# ---------------------------------------------------------
# 4. Bill of Quantities (BOQ) Items with PTE Benchmark Rates
# Total Target PTE Base = S$114,999,998.90 Base + S$5.0M Contingency = S$120.0M Total
# ---------------------------------------------------------
BOQ_ITEMS = [
    # TRD-01: Demolition & Site Clearance (Total PTE: S$3,500,000)
    {"item_code": "01.01", "trade_id": "TRD-01", "desc": "Demolition of existing structures & hardstanding", "unit": "m2", "qty": 45000, "pte_rate": 55.0},
    {"item_code": "01.02", "trade_id": "TRD-01", "desc": "Tree protection, grubbing and site hoardings", "unit": "m", "qty": 1850, "pte_rate": 554.054},

    # TRD-02: Deep Basement Excavation & ERSS (Total PTE: S$8,500,000)
    {"item_code": "02.01", "trade_id": "TRD-02", "desc": "Bulk excavation in soft marine clay down to -14m", "unit": "m3", "qty": 140000, "pte_rate": 35.0},
    {"item_code": "02.02", "trade_id": "TRD-02", "desc": "Temporary steel strutting and instrumentation monitoring", "unit": "ton", "qty": 2400, "pte_rate": 1500.0},

    # TRD-03: Bored Piling & Diaphragm Walls (Total PTE: S$14,000,000)
    {"item_code": "03.01", "trade_id": "TRD-03", "desc": "1200mm dia cast-in-place bored piles with sonic logging", "unit": "m", "qty": 16000, "pte_rate": 625.0},
    {"item_code": "03.02", "trade_id": "TRD-03", "desc": "800mm thick reinforced concrete diaphragm perimeter wall", "unit": "m2", "qty": 8000, "pte_rate": 500.0},

    # TRD-04: Reinforced Concrete Superstructure (Total PTE: S$26,000,000)
    {"item_code": "04.01", "trade_id": "TRD-04", "desc": "Grade 50 ready-mix concrete in columns and corewalls", "unit": "m3", "qty": 35000, "pte_rate": 280.0},
    {"item_code": "04.02", "trade_id": "TRD-04", "desc": "High-tensile steel reinforcement bars (Grade 500B)", "unit": "ton", "qty": 8500, "pte_rate": 1500.0},
    {"item_code": "04.03", "trade_id": "TRD-04", "desc": "Engineered modular formwork system for suspended slabs", "unit": "m2", "qty": 70000, "pte_rate": 49.2857},

    # TRD-05: Architectural Finishes & Facade (Total PTE: S$18,000,000)
    {"item_code": "05.01", "trade_id": "TRD-05", "desc": "Unitized double-glazed low-E curtain walling system", "unit": "m2", "qty": 18000, "pte_rate": 650.0},
    {"item_code": "05.02", "trade_id": "TRD-05", "desc": "Anti-microbial vinyl floor finishes & hospital wall cladding", "unit": "m2", "qty": 42000, "pte_rate": 150.0},

    # TRD-06: Mechanical, Electrical & HVAC Services (Total PTE: S$28,000,000)
    {"item_code": "06.01", "trade_id": "TRD-06", "desc": "Central water-cooled chiller plant (4x 800 RT) & cooling towers", "unit": "item", "qty": 1, "pte_rate": 9500000.0},
    {"item_code": "06.02", "trade_id": "TRD-06", "desc": "HEPA air-handling units and precision isolation pressurization", "unit": "nr", "qty": 65, "pte_rate": 130769.23},
    {"item_code": "06.03", "trade_id": "TRD-06", "desc": "Dual 22kV HT substations, switchgears and 2000kVA UPS systems", "unit": "item", "qty": 1, "pte_rate": 10000000.0},

    # TRD-07: Medical Gas & Cleanroom Piping (Total PTE: S$12,000,000)
    {"item_code": "07.01", "trade_id": "TRD-07", "desc": "Degreased medical copper pipeline distribution (O2, N2O, Air, Vac)", "unit": "m", "qty": 28000, "pte_rate": 250.0},
    {"item_code": "07.02", "trade_id": "TRD-07", "desc": "Digital medical gas manifold, area alarms and bedhead terminal units", "unit": "nr", "qty": 850, "pte_rate": 5882.353},

    # TRD-08: External Works & Landscaping (Total PTE: S$5,000,000)
    {"item_code": "08.01", "trade_id": "TRD-08", "desc": "Heavy-duty reinforced asphalt access roads and taxi drop-offs", "unit": "m2", "qty": 16000, "pte_rate": 180.0},
    {"item_code": "08.02", "trade_id": "TRD-08", "desc": "Covered linkways, therapeutic sensory gardens & bioswales", "unit": "m2", "qty": 10600, "pte_rate": 200.0},
]

# ---------------------------------------------------------
# 5. Shortlisted Bidders across Projects (M:M Cardinality Demonstration)
# Reusing Canonical S01 Contractor Names and Profiles
# ---------------------------------------------------------
PROJECT_BIDDERS_CONFIG = [
    # Project 1: Woodlands Health Campus (PRJ-WHC-001) - 5 Canonical Bidders
    {
        "project_id": "PRJ-WHC-001",
        "tender_id": "TND-WHC-2026-001",
        "bidder_id": "B01",
        "name": "Heng Win (Private) Limited",
        "uen": "197600888B",
        "bca_grade": "CW01-A1",
        "track_record_years": 28,
        "conquas_score": 93.5,
        "safety_demerit_points": 0,
        "net_worth_sgd": 185000000.0,
        "bidder_status": "AWARD_RECOMMENDED",
        "strategy": "Compliant Benchmark: Balanced market pricing within 1.0% of client baseline.",
        "early_skew": 1.01,
        "late_skew": 0.98,
        "scope_exclusion": None
    },
    {
        "project_id": "PRJ-WHC-001",
        "tender_id": "TND-WHC-2026-001",
        "bidder_id": "B02",
        "name": "WinningPine Construction Pte Ltd",
        "uen": "198900123C",
        "bca_grade": "CW01-A1",
        "track_record_years": 18,
        "conquas_score": 88.0,
        "safety_demerit_points": 4,
        "net_worth_sgd": 45000000.0,
        "bidder_status": "UNDER_CLARIFICATION",
        "strategy": "Cash-Flow Front-Loader: Massively marked up substructure (+85%) while deflating late MEP (-35%).",
        "early_skew": 1.85,
        "late_skew": 0.65,
        "scope_exclusion": None
    },
    {
        "project_id": "PRJ-WHC-001",
        "tender_id": "TND-WHC-2026-001",
        "bidder_id": "B03",
        "name": "Starlight Urban Infrastructure Pte Ltd",
        "uen": "201500888F",
        "bca_grade": "CW01-A2",
        "track_record_years": 10,
        "conquas_score": 79.5,
        "safety_demerit_points": 12,
        "net_worth_sgd": 8200000.0,
        "bidder_status": "STATUTORY_ALT_DISQUALIFIED",
        "strategy": "Abnormally Low Tender (ALT): Aggressive 34% discount below PTE with -42% MEP dumping.",
        "early_skew": 0.82,
        "late_skew": 0.58,
        "scope_exclusion": None
    },
    {
        "project_id": "PRJ-WHC-001",
        "tender_id": "TND-WHC-2026-001",
        "bidder_id": "B04",
        "name": "GemStone Building Contractors Pte Ltd",
        "uen": "197000345C",
        "bca_grade": "CW01-A1",
        "track_record_years": 25,
        "conquas_score": 89.2,
        "safety_demerit_points": 2,
        "net_worth_sgd": 142000000.0,
        "bidder_status": "CONDITIONAL_BID_FLAGGED",
        "strategy": "Concealed Scope Exclusion: Submits attractive rate but completely zeroes out S$6.79M medical gas pipework via Schedule 14 clause QUAL-14.2.",
        "early_skew": 0.98,
        "late_skew": 0.97,
        "scope_exclusion": {
            "clause_id": "QUAL-14.2",
            "page_nr": 38,
            "clause_text": "Item 07.01 Degreased medical copper pipeline distribution is deemed excluded from base lump sum and shall be procured under Client Direct Nominated Subcontract (NSC).",
            "omitted_item": "07.01",
            "omitted_amount": 7000000.0 * 0.97
        }
    },
    {
        "project_id": "PRJ-WHC-001",
        "tender_id": "TND-WHC-2026-001",
        "bidder_id": "B05",
        "name": "Titan Piling & Civil Engineering Pte Ltd",
        "uen": "201000333E",
        "bca_grade": "CW01-A1",
        "track_record_years": 22,
        "conquas_score": 85.0,
        "safety_demerit_points": 0,
        "net_worth_sgd": 28000000.0,
        "bidder_status": "NON_COMPETITIVE_OUTLIER",
        "strategy": "Outlier Over-Price: High defensive bid priced 12.0% above client estimate.",
        "early_skew": 1.12,
        "late_skew": 1.12,
        "scope_exclusion": None
    },

    # Project 2: Tuas Water Reclamation Plant (PRJ-TWRP-002) - Cross Bidders Demonstration
    {
        "project_id": "PRJ-TWRP-002",
        "tender_id": "TND-TWRP-2026-002",
        "bidder_id": "B01",
        "name": "Heng Win (Private) Limited",  # Bidding across multiple projects (M:M)
        "uen": "197600888B",
        "bca_grade": "CW01-A1",
        "track_record_years": 28,
        "conquas_score": 93.5,
        "safety_demerit_points": 0,
        "net_worth_sgd": 185000000.0,
        "bidder_status": "AWARD_RECOMMENDED",
        "strategy": "Competitive Civil & M&E integration tender priced at 1.8% under PTE baseline.",
        "early_skew": 0.98,
        "late_skew": 0.98,
        "scope_exclusion": None
    },
    {
        "project_id": "PRJ-TWRP-002",
        "tender_id": "TND-TWRP-2026-002",
        "bidder_id": "B02",
        "name": "GrandPillar Infrastructure Pte Ltd",
        "uen": "194000001A",
        "bca_grade": "CW01-A1",
        "track_record_years": 86,
        "conquas_score": 96.0,
        "safety_demerit_points": 0,
        "net_worth_sgd": 310000000.0,
        "bidder_status": "COMPLIANT_BAND",
        "strategy": "Tier-1 Heavy Civil Engineering benchmark with advanced slipforming expertise.",
        "early_skew": 1.04,
        "late_skew": 1.01,
        "scope_exclusion": None
    },
    {
        "project_id": "PRJ-TWRP-002",
        "tender_id": "TND-TWRP-2026-002",
        "bidder_id": "B03",
        "name": "Kuraishi Engineering & Construction Pte Ltd",
        "uen": "196500102L",
        "bca_grade": "CW01-A1",
        "track_record_years": 61,
        "conquas_score": 96.5,
        "safety_demerit_points": 0,
        "net_worth_sgd": 280000000.0,
        "bidder_status": "ELEVATED_RISK",
        "strategy": "Precision Japanese diaphragm and deep excavation automation proposal with +30% substructure.",
        "early_skew": 1.35,
        "late_skew": 0.92,
        "scope_exclusion": None
    },
    {
        "project_id": "PRJ-TWRP-002",
        "tender_id": "TND-TWRP-2026-002",
        "bidder_id": "B04",
        "name": "Vanguard Underground Engineering Pte Ltd",
        "uen": "198400091K",
        "bca_grade": "CW01-A1",
        "track_record_years": 42,
        "conquas_score": 95.0,
        "safety_demerit_points": 0,
        "net_worth_sgd": 240000000.0,
        "bidder_status": "UNDER_CLARIFICATION",
        "strategy": "Heavy Front-Loading: +72% substructure markup creating S$36.2M early cash extraction exposure.",
        "early_skew": 1.72,
        "late_skew": 0.70,
        "scope_exclusion": None
    },

    # Project 3: Changi Airport Terminal 5 (PRJ-T5-003) - Cross Bidders Demonstration
    {
        "project_id": "PRJ-T5-003",
        "tender_id": "TND-T5-2026-003",
        "bidder_id": "B01",
        "name": "Shinsei Precision Builders Pte Ltd",
        "uen": "197300113M",
        "bca_grade": "CW01-A1",
        "track_record_years": 53,
        "conquas_score": 97.0,
        "safety_demerit_points": 0,
        "net_worth_sgd": 350000000.0,
        "bidder_status": "AWARD_RECOMMENDED",
        "strategy": "Aviation terminal underground baggage handling and automated tunneling package (-1.2% vs PTE).",
        "early_skew": 1.02,
        "late_skew": 1.01,
        "scope_exclusion": None
    },
    {
        "project_id": "PRJ-T5-003",
        "tender_id": "TND-T5-2026-003",
        "bidder_id": "B02",
        "name": "DongHae Global Engineering Pte Ltd",
        "uen": "198100179T",
        "bca_grade": "CW01-A1",
        "track_record_years": 45,
        "conquas_score": 94.0,
        "safety_demerit_points": 4,
        "net_worth_sgd": 450000000.0,
        "bidder_status": "UNDER_CLARIFICATION",
        "strategy": "Mega-scale international civil tunneling proposal with +65% substructure front-loading (FLRI 1.61).",
        "early_skew": 1.65,
        "late_skew": 0.72,
        "scope_exclusion": None
    },
    {
        "project_id": "PRJ-T5-003",
        "tender_id": "TND-T5-2026-003",
        "bidder_id": "B03",
        "name": "GrandPillar Infrastructure Pte Ltd",  # Bidding on both TWRP and T5 (M:M)
        "uen": "194000001A",
        "bca_grade": "CW01-A1",
        "track_record_years": 86,
        "conquas_score": 96.0,
        "safety_demerit_points": 0,
        "net_worth_sgd": 310000000.0,
        "bidder_status": "COMPLIANT_BAND",
        "strategy": "Domestic consortium leadership with balanced pricing aligned within 1.0% of PTE.",
        "early_skew": 0.99,
        "late_skew": 1.00,
        "scope_exclusion": None
    },
    {
        "project_id": "PRJ-T5-003",
        "tender_id": "TND-T5-2026-003",
        "bidder_id": "B04",
        "name": "Everest Building & Civil Engineering Pte Ltd",
        "uen": "197000012B",
        "bca_grade": "CW01-A1",
        "track_record_years": 56,
        "conquas_score": 92.5,
        "safety_demerit_points": 2,
        "net_worth_sgd": 195000000.0,
        "bidder_status": "STATUTORY_ALT_DISQUALIFIED",
        "strategy": "Statutory Abnormally Low Tender (ALT): Aggressive 29% price dumping across structural packages.",
        "early_skew": 0.76,
        "late_skew": 0.60,
        "scope_exclusion": None
    }
]

# Backward compatibility alias for WHC bidders
SHORTLISTED_BIDDERS = [b for b in PROJECT_BIDDERS_CONFIG if b["project_id"] == "PRJ-WHC-001"]

def generate_database():
    """Generates DuckDB database and populates schema with 50 contractors and S02 tender project."""
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass

    con = duckdb.connect(DB_PATH)

    # 1. Master Contractors Registry (50 Contractors)
    con.execute("""
    CREATE TABLE contractors (
        uen VARCHAR PRIMARY KEY,
        company_name VARCHAR NOT NULL,
        bca_grade VARCHAR NOT NULL,
        workheads VARCHAR NOT NULL,
        tendering_limit_sgd DOUBLE NOT NULL,
        net_worth_sgd DOUBLE NOT NULL,
        mom_sdp INTEGER NOT NULL,
        bizsafe_level VARCHAR NOT NULL,
        conquas_score DOUBLE NOT NULL,
        status VARCHAR NOT NULL
    );
    """)
    for c in MASTER_CONTRACTORS:
        con.execute("""
        INSERT INTO contractors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [c["uen"], c["name"], c["grade"], c["workheads"], c["tendering_limit"],
              c["net_worth"], c["sdp"], c["bizsafe"], c["conquas"], c["status"]])

    # 2. Projects & Tenders Tables
    con.execute("""
    CREATE TABLE projects (
        project_id VARCHAR PRIMARY KEY,
        tender_id VARCHAR UNIQUE NOT NULL,
        project_name VARCHAR NOT NULL,
        client_name VARCHAR NOT NULL,
        sector VARCHAR NOT NULL,
        pte_budget_sgd DOUBLE NOT NULL,
        currency VARCHAR NOT NULL,
        closing_date VARCHAR NOT NULL,
        status VARCHAR NOT NULL,
        description VARCHAR NOT NULL
    );
    """)
    for p in TENDER_PROJECTS:
        con.execute("""
        INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [p["project_id"], p["tender_id"], p["project_name"], p["client_name"],
              p["sector"], p["pte_budget_sgd"], p["currency"], p["closing_date"],
              p["status"], p["description"]])

    con.execute("""
    CREATE TABLE tenders (
        tender_id VARCHAR PRIMARY KEY,
        project_name VARCHAR NOT NULL,
        client_name VARCHAR NOT NULL,
        pte_budget_sgd DOUBLE NOT NULL,
        closing_date VARCHAR NOT NULL
    );
    """)
    for p in TENDER_PROJECTS:
        con.execute("""
        INSERT INTO tenders VALUES (?, ?, ?, ?, ?)
        """, [p["tender_id"], p["project_name"], p["client_name"], p["pte_budget_sgd"], p["closing_date"]])

    # 3. Trades table
    con.execute("""
    CREATE TABLE trades (
        trade_id VARCHAR PRIMARY KEY,
        trade_name VARCHAR NOT NULL,
        work_stage VARCHAR NOT NULL,
        category VARCHAR NOT NULL
    );
    """)
    for t in TRADES:
        con.execute("INSERT INTO trades VALUES (?, ?, ?, ?)", [t["trade_id"], t["name"], t["stage"], t["category"]])

    # 4. BOQ Line Items (Client Benchmark / PTE)
    con.execute("""
    CREATE TABLE boq_items (
        item_code VARCHAR PRIMARY KEY,
        trade_id VARCHAR REFERENCES trades(trade_id),
        item_description VARCHAR NOT NULL,
        unit VARCHAR NOT NULL,
        quantity DOUBLE NOT NULL,
        pte_unit_rate DOUBLE NOT NULL,
        pte_total_amount DOUBLE NOT NULL
    );
    """)
    for b in BOQ_ITEMS:
        total = round(b["qty"] * b["pte_rate"], 2)
        con.execute("INSERT INTO boq_items VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [b["item_code"], b["trade_id"], b["desc"], b["unit"], b["qty"], b["pte_rate"], total])

    # 5. Cross Table: Project Bidders (M:M Junction Table between projects and contractors)
    con.execute("""
    CREATE TABLE project_bidders (
        project_id VARCHAR NOT NULL REFERENCES projects(project_id),
        contractor_uen VARCHAR NOT NULL REFERENCES contractors(uen),
        bidder_id VARCHAR NOT NULL,
        bidder_status VARCHAR NOT NULL,
        total_submitted_bid DOUBLE NOT NULL,
        submission_timestamp VARCHAR NOT NULL,
        commercial_strategy VARCHAR NOT NULL,
        flri_index DOUBLE,
        variance_vs_pte_pct DOUBLE,
        scope_exclusions_count INTEGER DEFAULT 0,
        PRIMARY KEY (project_id, contractor_uen)
    );
    """)

    # 6. Shortlisted Bidders Table (Maintained for backward compatibility)
    con.execute("""
    CREATE TABLE bidders (
        tender_id VARCHAR NOT NULL REFERENCES tenders(tender_id),
        bidder_id VARCHAR NOT NULL,
        bidder_name VARCHAR NOT NULL,
        uen VARCHAR NOT NULL REFERENCES contractors(uen),
        bca_grade VARCHAR NOT NULL,
        track_record_years INTEGER NOT NULL,
        conquas_score DOUBLE NOT NULL,
        safety_demerit_points INTEGER NOT NULL,
        net_worth_sgd DOUBLE NOT NULL,
        total_submitted_bid DOUBLE NOT NULL,
        commercial_strategy VARCHAR NOT NULL,
        PRIMARY KEY (tender_id, bidder_id)
    );
    """)

    # 7. Bid Line Items
    con.execute("""
    CREATE TABLE bid_line_items (
        tender_id VARCHAR NOT NULL REFERENCES tenders(tender_id),
        bidder_id VARCHAR NOT NULL,
        item_code VARCHAR REFERENCES boq_items(item_code),
        submitted_unit_rate DOUBLE NOT NULL,
        submitted_total_amount DOUBLE NOT NULL,
        variance_vs_pte_pct DOUBLE NOT NULL
    );
    """)

    # 8. Qualifications & Exclusions
    con.execute("""
    CREATE TABLE bidder_qualifications (
        tender_id VARCHAR NOT NULL REFERENCES tenders(tender_id),
        bidder_id VARCHAR NOT NULL,
        clause_id VARCHAR NOT NULL,
        page_nr INTEGER NOT NULL,
        clause_text VARCHAR NOT NULL,
        omitted_item_code VARCHAR,
        potential_cost_exposure DOUBLE NOT NULL,
        severity VARCHAR NOT NULL
    );
    """)

    # Clean existing JSON submissions
    for existing_f in os.listdir(SUBMISSIONS_DIR):
        if existing_f.endswith(".json"):
            try:
                os.remove(os.path.join(SUBMISSIONS_DIR, existing_f))
            except Exception:
                pass

    # Populate Bidders across all projects
    project_scales = {
        "PRJ-WHC-001": 1.0,
        "PRJ-TWRP-002": 2.0,      # S$240M / S$120M
        "PRJ-T5-003": 3.166667    # S$380M / S$120M
    }

    for b in PROJECT_BIDDERS_CONFIG:
        total_bid = 0.0
        bid_items = []
        scale_factor = project_scales.get(b["project_id"], 1.0)
        proj_pte_total = sum(item["qty"] * scale_factor * item["pte_rate"] for item in BOQ_ITEMS)

        for item in BOQ_ITEMS:
            trade_id = item["trade_id"]
            cat = next(t["category"] for t in TRADES if t["trade_id"] == trade_id)

            if cat == "Substructure":
                multiplier = b["early_skew"]
            elif cat in ["Finishes", "Services", "External"]:
                multiplier = b["late_skew"]
            else:
                multiplier = (b["early_skew"] + b["late_skew"]) / 2.0

            scaled_qty = round(item["qty"] * scale_factor, 2)
            if b.get("scope_exclusion") and item["item_code"] == b["scope_exclusion"]["omitted_item"]:
                submitted_rate = 0.0
            else:
                submitted_rate = round(item["pte_rate"] * multiplier, 2)

            submitted_amount = round(scaled_qty * submitted_rate, 2)
            total_bid += submitted_amount
            variance_pct = round(((submitted_rate - item["pte_rate"]) / item["pte_rate"]) * 100.0, 2)

            bid_items.append((b["tender_id"], b["bidder_id"], item["item_code"], submitted_rate, submitted_amount, variance_pct))

        var_vs_pte = round(((total_bid - proj_pte_total) / proj_pte_total) * 100.0, 2)
        flri_val = round(b["early_skew"] / ((b["early_skew"] + b["late_skew"]) / 2.0), 2)
        scope_count = 1 if b.get("scope_exclusion") else 0

        # Insert into project_bidders cross table (M:M)
        con.execute("""
        INSERT INTO project_bidders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [b["project_id"], b["uen"], b["bidder_id"], b["bidder_status"],
              round(total_bid, 2), "2026-10-04 14:00:00", b["strategy"],
              flri_val, var_vs_pte, scope_count])

        # Insert into bidders table
        con.execute("""
        INSERT INTO bidders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [b["tender_id"], b["bidder_id"], b["name"], b["uen"], b["bca_grade"], b["track_record_years"],
              b["conquas_score"], b["safety_demerit_points"], b["net_worth_sgd"],
              round(total_bid, 2), b["strategy"]])

        # Insert Line items for all projects
        for bi in bid_items:
            con.execute("INSERT INTO bid_line_items VALUES (?, ?, ?, ?, ?, ?)", bi)

        if b.get("scope_exclusion"):
            ex = b["scope_exclusion"]
            con.execute("""
            INSERT INTO bidder_qualifications VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [b["tender_id"], b["bidder_id"], ex["clause_id"], ex["page_nr"], ex["clause_text"],
                  ex["omitted_item"], ex["omitted_amount"] * scale_factor, "CRITICAL_SCOPE_OMISSION"])

        # Standalone JSON file for WHC
        if b["project_id"] == "PRJ-WHC-001":
            submission_json = {
                "tender_id": b["tender_id"],
                "bidder_id": b["bidder_id"],
                "bidder_name": b["name"],
                "uen": b["uen"],
                "total_bid_sum": round(total_bid, 2),
                "line_items": [
                    {
                        "item_code": bi[2],
                        "submitted_unit_rate": bi[3],
                        "submitted_total_amount": bi[4],
                        "variance_pct": bi[5]
                    }
                    for bi in bid_items
                ],
                "qualifications": [b["scope_exclusion"]] if b.get("scope_exclusion") else []
            }
            json_path = os.path.join(SUBMISSIONS_DIR, f"{b['bidder_id']}_{b['uen']}_submission.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(submission_json, f, indent=2)

    # ---------------------------------------------------------
    # 7. National Historical Market Rates Lakehouse (1,000,000 Records)
    # ---------------------------------------------------------
    print("Synthesizing National Historical Market Rates Lakehouse (1,000,000 records across 500 projects)...")
    con.execute("""
    CREATE OR REPLACE TABLE historical_market_rates AS
    SELECT 
        i as record_id,
        'PRJ-HIST-' || lpad(((i % 500) + 1)::text, 4, '0') as project_id,
        'UEN-SG-' || lpad(((i % 50) + 1)::text, 4, '0') as contractor_uen,
        'TRD-0' || ((i % 8) + 1)::text as trade_id,
        'BOQ-LINE-' || lpad(((i % 250) + 1)::text, 4, '0') as item_code,
        (50.0 + ((i % 400) * 2.25) + (random() * 15.0 - 7.5))::DECIMAL(12,2) as unit_rate,
        ((i % 80) + 1) * 10 as quantity,
        ((50.0 + ((i % 400) * 2.25) + (random() * 15.0 - 7.5)) * (((i % 80) + 1) * 10))::DECIMAL(16,2) as total_amount,
        DATE '2016-01-01' + INTERVAL (i % 3800) DAY as tender_award_date
    FROM generate_series(1, 1000000) as t(i);
    """)

    master_cnt = con.execute("SELECT count(*) FROM contractors").fetchone()[0]
    projects_cnt = con.execute("SELECT count(*) FROM projects").fetchone()[0]
    project_bidders_cnt = con.execute("SELECT count(*) FROM project_bidders").fetchone()[0]
    whc_bidders_cnt = con.execute("SELECT count(*) FROM bidders WHERE tender_id = 'TND-WHC-2026-001'").fetchone()[0]
    hist_cnt = con.execute("SELECT count(*) FROM historical_market_rates").fetchone()[0]
    total_records = con.execute("""
        SELECT 
            (SELECT count(*) FROM contractors) +
            (SELECT count(*) FROM projects) +
            (SELECT count(*) FROM tenders) +
            (SELECT count(*) FROM trades) +
            (SELECT count(*) FROM boq_items) +
            (SELECT count(*) FROM bidders) +
            (SELECT count(*) FROM project_bidders) +
            (SELECT count(*) FROM bid_line_items) +
            (SELECT count(*) FROM bidder_qualifications) +
            (SELECT count(*) FROM historical_market_rates)
    """).fetchone()[0]
    con.close()

    print(f"Hospital Tender Database generated at: {DB_PATH}")
    print(f"Master Contractor Registry: {master_cnt} contractors.")
    print(f"Multi-Project Registry: {projects_cnt} infrastructure projects.")
    print(f"Many-to-Many Project Bidders Junction Records: {project_bidders_cnt} bidder participations.")
    print(f"Tender TND-WHC-2026-001 Shortlisted Bidders: {whc_bidders_cnt} bidders.")
    print(f"National Historical Market Rate Lakehouse: {hist_cnt:,} records across 500 past projects.")
    print(f"Total Database Records: {total_records:,} records.")

if __name__ == "__main__":
    generate_database()
