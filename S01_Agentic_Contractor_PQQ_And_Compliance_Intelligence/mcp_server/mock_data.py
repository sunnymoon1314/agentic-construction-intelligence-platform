import sqlite3
import os

def init_db():
    db_path = os.path.join(os.path.dirname(__file__), 'contractors_registry.db')
    
    # Remove existing database if present for clean seeding
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1. Contractors Table (BCA CRS Workheads & Tendering Limits)
    c.execute('''
        CREATE TABLE contractors (
            uen TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            crs_grade TEXT NOT NULL,
            workheads TEXT NOT NULL,
            tendering_limit_sgd REAL NOT NULL,
            paid_up_capital_sgd REAL NOT NULL,
            net_worth_sgd REAL NOT NULL,
            track_record_3yr_sgd REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE'
        )
    ''')

    # 2. Safety Compliance Table (MOM Safety Demerit Points & bizSAFE)
    c.execute('''
        CREATE TABLE safety_compliance (
            uen TEXT PRIMARY KEY,
            mom_sdp INTEGER NOT NULL,
            bizsafe_level TEXT NOT NULL,
            mom_debarred INTEGER NOT NULL DEFAULT 0,
            ggbs_rating TEXT NOT NULL,
            fatalities_past_18m INTEGER NOT NULL DEFAULT 0,
            stop_work_orders_past_18m INTEGER NOT NULL DEFAULT 0,
            last_audit_date TEXT NOT NULL,
            FOREIGN KEY (uen) REFERENCES contractors(uen)
        )
    ''')

    # 3. Financial Statements Table (Audited Balance Sheets over 3 FYs)
    c.execute('''
        CREATE TABLE financial_statements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uen TEXT NOT NULL,
            fy_year INTEGER NOT NULL,
            current_assets_sgd REAL NOT NULL,
            current_liabilities_sgd REAL NOT NULL,
            quick_assets_sgd REAL NOT NULL,
            cash_reserves_sgd REAL NOT NULL,
            total_debt_sgd REAL NOT NULL,
            total_equity_sgd REAL NOT NULL,
            credit_line_facility_sgd REAL NOT NULL,
            FOREIGN KEY (uen) REFERENCES contractors(uen)
        )
    ''')

    # 4. Performance & CONQUAS Track Record Table
    c.execute('''
        CREATE TABLE track_record_conquas (
            uen TEXT PRIMARY KEY,
            completed_projects_count INTEGER NOT NULL,
            avg_conquas_score REAL NOT NULL,
            on_time_completion_pct REAL NOT NULL,
            open_defect_notices INTEGER NOT NULL,
            liquidated_damages_instances INTEGER NOT NULL,
            dfma_adoption_score REAL NOT NULL,
            FOREIGN KEY (uen) REFERENCES contractors(uen)
        )
    ''')

    # 5. Sample Tenders Table (Projects for Pre-Qualification Benchmarking)
    c.execute('''
        CREATE TABLE sample_tenders (
            tender_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            developer_type TEXT NOT NULL,
            contract_form TEXT NOT NULL,
            estimated_budget_sgd REAL NOT NULL,
            required_workhead TEXT NOT NULL,
            min_crs_grade TEXT NOT NULL,
            max_mom_sdp INTEGER NOT NULL,
            min_bizsafe TEXT NOT NULL,
            min_current_ratio REAL NOT NULL,
            performance_bond_pct REAL NOT NULL
        )
    ''')

    # Seed Contractors Data
    contractors_data = [
        # Tier 1 Leader (Fully Compliant Grade A1)
        ('197600888B', 'Heng Win (Private) Limited', 'A1', 'CW01, CW02, CR01, CR03, ME01', 999999999.0, 50000000.0, 185000000.0, 450000000.0, 'ACTIVE'),
        # Tier 1 Leader (Fully Compliant Grade A1)
        ('197000345C', 'GemStone Building Contractors Pte Ltd', 'A1', 'CW01, CW02, CR09, ME05', 999999999.0, 40000000.0, 142000000.0, 380000000.0, 'ACTIVE'),
        # Tier 2 Builder (Grade A2 - Tendering Cap S$85M)
        ('198900123C', 'WinningPine Construction Pte Ltd', 'A2', 'CW01, CR01, ME01', 85000000.0, 18000000.0, 45000000.0, 115000000.0, 'ACTIVE'),
        # Mid-tier Builder (Grade B1 - Tendering Cap S$40M)
        ('200100999D', 'Apex Builders Pte Ltd', 'B1', 'CW01, CR03', 40000000.0, 10000000.0, 22000000.0, 55000000.0, 'ACTIVE'),
        # Safety-Deficient / Debarred Builder (Grade A2 with >= 25 MOM SDP Demerits)
        ('201000333E', 'Titan Piling & Civil Engineering Pte Ltd', 'A2', 'CW02, CR01', 85000000.0, 15000000.0, 28000000.0, 72000000.0, 'DEBARRED'),
        # Financially Distressed Contractor (Grade B2 - Insufficient Working Capital & Bond Capacity)
        ('201500888F', 'Starlight Urban Infrastructure Pte Ltd', 'B2', 'CW01, CW02', 13000000.0, 3000000.0, 2800000.0, 14000000.0, 'ACTIVE')
    ]
    c.executemany('INSERT INTO contractors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', contractors_data)

    # Seed Safety Compliance Data
    safety_data = [
        # Heng Win: bizSAFE STAR, 0 SDP, Star GGBS
        ('197600888B', 0, 'bizSAFE STAR / ISO 45001', 0, 'Star', 0, 0, '2026-06-15'),
        # GemStone: bizSAFE STAR, 6 SDP, Excellent GGBS
        ('197000345C', 6, 'bizSAFE STAR / ISO 45001', 0, 'Excellent', 0, 0, '2026-05-10'),
        # WinningPine: bizSAFE Level 3, 12 SDP, Merit GGBS
        ('198900123C', 12, 'bizSAFE Level 3', 0, 'Merit', 0, 1, '2026-04-20'),
        # Apex Builders: bizSAFE Level 3, 18 SDP, Certified GGBS
        ('200100999D', 18, 'bizSAFE Level 3', 0, 'Certified', 0, 1, '2026-03-12'),
        # Titan Piling: CRITICAL FAILURE - 28 SDP (Exceeds MOM 25 Demerit Threshold, Debarred from Tenders)
        ('201000333E', 28, 'bizSAFE Level 3', 1, 'None', 1, 3, '2026-08-01'),
        # Starlight Urban: bizSAFE Level 2 (Sub-standard for Major Public Works), 10 SDP
        ('201500888F', 10, 'bizSAFE Level 2', 0, 'None', 0, 1, '2026-02-18')
    ]
    c.executemany('INSERT INTO safety_compliance VALUES (?, ?, ?, ?, ?, ?, ?, ?)', safety_data)

    # Seed Audited Financial Statements (Latest FY 2025 data)
    financials_data = [
        # Heng Win: Strong liquidity (Current Ratio = 1.96, Quick Ratio = 1.63, Debt/Equity = 0.43)
        (None, '197600888B', 2025, 245000000.0, 125000000.0, 204000000.0, 88000000.0, 80000000.0, 185000000.0, 150000000.0),
        # GemStone: Robust liquidity (Current Ratio = 1.74, Quick Ratio = 1.45, Debt/Equity = 0.56)
        (None, '197000345C', 2025, 188000000.0, 108000000.0, 157000000.0, 62000000.0, 79000000.0, 142000000.0, 120000000.0),
        # WinningPine: Adequate liquidity (Current Ratio = 1.48, Quick Ratio = 1.18, Debt/Equity = 0.82)
        (None, '198900123C', 2025, 62000000.0, 42000000.0, 49500000.0, 18000000.0, 37000000.0, 45000000.0, 35000000.0),
        # Apex Builders: Moderate liquidity (Current Ratio = 1.27, Quick Ratio = 1.05, Debt/Equity = 1.14)
        (None, '200100999D', 2025, 28000000.0, 22000000.0, 23100000.0, 7500000.0, 25000000.0, 22000000.0, 15000000.0),
        # Titan Piling: Strained (Current Ratio = 1.15, Quick Ratio = 0.88, Debt/Equity = 1.75)
        (None, '201000333E', 2025, 38000000.0, 33000000.0, 29000000.0, 4200000.0, 49000000.0, 28000000.0, 12000000.0),
        # Starlight Urban: CRITICAL INSOLVENCY RISK (Current Ratio = 0.85, Quick Ratio = 0.62, Debt/Equity = 2.86)
        (None, '201500888F', 2025, 5100000.0, 6000000.0, 3700000.0, 850000.0, 8000000.0, 2800000.0, 1500000.0)
    ]
    c.executemany('INSERT INTO financial_statements VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', financials_data)

    # Seed CONQUAS and Performance Track Record Data
    track_record_data = [
        # Heng Win: CONQUAS 92.4, 98% On-time, 0 defects, 0 LAD
        ('197600888B', 34, 92.4, 98.0, 0, 0, 94.5),
        # GemStone: CONQUAS 89.8, 95% On-time, 1 defect, 0 LAD
        ('197000345C', 28, 89.8, 95.0, 1, 0, 88.0),
        # WinningPine: CONQUAS 84.5, 91% On-time, 2 defects, 0 LAD
        ('198900123C', 18, 84.5, 91.0, 2, 0, 76.5),
        # Apex Builders: CONQUAS 79.2, 86% On-time, 4 defects, 1 LAD
        ('200100999D', 11, 79.2, 86.0, 4, 1, 65.0),
        # Titan Piling: CONQUAS 72.0, 78% On-time, 7 defects, 2 LAD
        ('201000333E', 15, 72.0, 78.0, 7, 2, 58.0),
        # Starlight Urban: CONQUAS 68.5, 71% On-time, 9 defects, 3 LAD
        ('201500888F', 6, 68.5, 71.0, 9, 3, 42.0)
    ]
    c.executemany('INSERT INTO track_record_conquas VALUES (?, ?, ?, ?, ?, ?, ?)', track_record_data)

    # Seed Sample Tenders
    tenders_data = [
        (
            'TND-2026-SG-001',
            'Woodlands Health Campus Specialist Complex (D&B)',
            'Public Sector (MOH / HDB)',
            'PSSCOC D&B 2020',
            120000000.0,
            'CW01',
            'A1',
            15,
            'bizSAFE STAR / ISO 45001',
            1.2,
            10.0
        ),
        (
            'TND-2026-SG-002',
            'Punggol Digital District Substructure & Deep Excavation',
            'Public Sector (JTC)',
            'PSSCOC Measurement 2020',
            45000000.0,
            'CW02',
            'A2',
            18,
            'bizSAFE Level 3',
            1.2,
            5.0
        ),
        (
            'TND-2026-SG-003',
            'Bukit Merah Mixed Commercial & Residential Development',
            'Private Developer (REDAS Member)',
            'SIA Form of Contract 10th Edition',
            35000000.0,
            'CW01',
            'B1',
            20,
            'bizSAFE Level 3',
            1.15,
            5.0
        )
    ]
    c.executemany('INSERT INTO sample_tenders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', tenders_data)

    conn.commit()
    conn.close()
    print(f"Initialized mock contractor registry database at: {db_path}")

if __name__ == '__main__':
    init_db()
