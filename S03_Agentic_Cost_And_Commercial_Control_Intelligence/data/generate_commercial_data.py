#!/usr/bin/env python3
"""
S03: Synthetic Commercial Control & Cost Intelligence Dataset Generator
Module: ACIP S03 (Agentic Cost & Commercial Control Platform)
Target Engine: DuckDB (commercial_control.duckdb) + Canonical JSON Fixtures

This script synthesizes:
1. Multi-project contract registry (4 scenarios, flagship: PRJ-WHC-COM-001 Woodlands Health Campus Commercial Annex)
   - Includes PSSCOC / SIA retention release stages (50% Practical Completion, 50% Expiry of DLP)
2. Contract baseline Schedules of Rates (SOR) conforming to PSSCOC / SIA conditions
3. Interim Progress Claims with openBIM IFC quantity takeoff reconciliations (detecting over-certification)
   - Tracks previous cumulative certified gross and current period net payable
4. 12 sample Variation Orders (VOs) evaluated under the 4-tier valuation waterfall (PSSCOC Cl 19 / SIA Cl 12)
   - Implements strict 28-day contractual timebar notification checks (triggering TIMEBAR_EXPIRED)
5. MOM workplace safety demerit & Stop-Work Order (SWO) statutory set-off ledger
6. Statutory SOPA Section 11(1) Calendar Engine accounting for Singapore gazetted public holidays and Sundays
7. Cost-to-Complete Earned Value Management (EVM) forecast ledger
"""

import os
import json
import duckdb
from datetime import datetime, date, timedelta

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DATA_DIR, "commercial_control.duckdb")

# -------------------------------------------------------------------------
# Part 1: Singapore Statutory Public Holidays & Business Calendar Engine
# -------------------------------------------------------------------------
SINGAPORE_PUBLIC_HOLIDAYS_2026 = {
    date(2026, 1, 1),   # New Year's Day
    date(2026, 2, 17),  # Chinese New Year Day 1
    date(2026, 2, 18),  # Chinese New Year Day 2
    date(2026, 3, 21),  # Hari Raya Puasa
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 1),   # Labour Day
    date(2026, 5, 27),  # Hari Raya Haji
    date(2026, 5, 31),  # Vesak Day
    date(2026, 8, 9),   # National Day
    date(2026, 8, 10),  # National Day (Observed in lieu)
    date(2026, 11, 8),  # Deepavali
    date(2026, 11, 9),  # Deepavali (Observed in lieu)
    date(2026, 12, 25)  # Christmas Day
}

def calculate_sopa_deadline(date_served: date, contract_days: int = 14) -> date:
    """
    Computes statutory SOPA payment response deadline:
    1. Statutory override: min(contract_payment_response_days, 14)
    2. SOPA Section 2 defines 'day' as excluding Sundays and public holidays.
    """
    effective_days = min(contract_days, 14)
    current_date = date_served
    counted_days = 0

    while counted_days < effective_days:
        current_date += timedelta(days=1)
        # Skip Sundays (weekday() == 6) and Gazetted Public Holidays
        if current_date.weekday() != 6 and current_date not in SINGAPORE_PUBLIC_HOLIDAYS_2026:
            counted_days += 1

    return current_date

# -------------------------------------------------------------------------
# Part 2: MOM Workplace Safety & Demerit Set-Off Formulations
# -------------------------------------------------------------------------
def calculate_mom_safety_set_off(swo_idle_days: int, demerit_points: int, unrem_fines: float = 0.0) -> dict:
    """
    Computes statutory and contractual safety set-offs under Singapore practice:
    1. Mandatory Stop-Work Order (SWO) Liquidated Backcharge:
       SWO Deduction = Idle Days * Daily Preliminaries Extended Cost (S$12,500/day baseline)
    2. Contractual Demerit Point Financial Penalty Schedule:
       - Tiers 1-9 Points: S$1,500 flat deduction per demerit point
       - Tiers 10-24 Points: S$3,500 flat deduction per demerit point
       - Tier >= 25 Points (Debarment Threshold Triggered): S$50,000 corporate liquidated backcharge
    3. Unremediated Site Safety Fine Indemnification:
       Statutory fine + 15% administrative markup
    """
    DAILY_PRELIMS_EXTENDED_COST = 12500.00
    swo_deduction = swo_idle_days * DAILY_PRELIMS_EXTENDED_COST

    sdp_deduction = 0.0
    if demerit_points >= 25:
        sdp_deduction = 50000.00
    elif demerit_points >= 10:
        sdp_deduction = demerit_points * 3500.00
    elif demerit_points > 0:
        sdp_deduction = demerit_points * 1500.00

    admin_markup_rate = 0.15
    fines_deduction = unrem_fines * (1.0 + admin_markup_rate) if unrem_fines > 0 else 0.0

    total_safety_set_off = swo_deduction + sdp_deduction + fines_deduction

    return {
        "swo_idle_days": swo_idle_days,
        "swo_rate_per_day": DAILY_PRELIMS_EXTENDED_COST,
        "swo_deduction": swo_deduction,
        "demerit_points": demerit_points,
        "sdp_deduction": sdp_deduction,
        "unremediated_fines_base": unrem_fines,
        "admin_markup_rate": admin_markup_rate,
        "fines_deduction": fines_deduction,
        "total_safety_set_off": total_safety_set_off
    }

# -------------------------------------------------------------------------
# Part 3: Canonical Ground-Truth Datasets (The Chancellor's Blueprints)
# -------------------------------------------------------------------------

# Primary Flagship Scenario: Woodlands Health Campus Commercial Annex (PRJ-WHC-COM-001)
CONTRACT_BASELINE_WHC = {
    "project_id": "PRJ-WHC-COM-001",
    "project_name": "Woodlands Health Campus Commercial Annex",
    "contract_type": "PSSCOC_2025",
    "employer_name": "MOH Holdings Pte Ltd",
    "main_contractor_uen": "198900123C",
    "main_contractor_name": "WinningPine Construction Pte Ltd",
    "currency": "SGD",
    "financials": {
        "base_contract_sum": 52380952.38,
        "contingency_allocation": 2619047.62,
        "total_approved_budget": 55000000.00,
        "retention_max_cap_pct": 5.0,
        "retention_limit_sgd": 1000000.00,
        "contract_response_days_ceiling": 14,
        "retention_release_stages": [
            {
                "milestone": "PRACTICAL_COMPLETION",
                "release_percentage": 50.0,
                "description": "50% of accumulated retention released upon issuance of Substantial Completion Certificate"
            },
            {
                "milestone": "FINAL_ACCOUNT_EXPIRY_DLP",
                "release_percentage": 50.0,
                "description": "Remaining 50% released upon Defects Liability Certificate (12 months post-PC)"
            }
        ]
    },
    "schedule_of_rates": [
        {
            "item_code": "CIV-01-001",
            "trade_id": "TRD-01",
            "description": "Excavation in soft material not exceeding 2.0m deep",
            "unit": "m3",
            "contract_sor_rate": 45.50,
            "max_allowable_quantity": 12000.00
        },
        {
            "item_code": "STR-02-004",
            "trade_id": "TRD-02",
            "description": "Supply and cast Grade 40 ready-mixed concrete in columns",
            "unit": "m3",
            "contract_sor_rate": 240.00,
            "max_allowable_quantity": 8500.00
        },
        {
            "item_code": "STR-02-005",
            "trade_id": "TRD-02",
            "description": "High tensile steel reinforcement bars (rebar) up to 25mm dia",
            "unit": "TON",
            "contract_sor_rate": 1680.00,
            "max_allowable_quantity": 950.00
        },
        {
            "item_code": "FIN-05-008",
            "trade_id": "TRD-05",
            "description": "Standard 12mm gypsum drywall partitioning with acoustic insulation",
            "unit": "m2",
            "contract_sor_rate": 95.00,
            "max_allowable_quantity": 4200.00
        },
        {
            "item_code": "MNE-06-012",
            "trade_id": "TRD-06",
            "description": "Supply, install, test and commission 500RT water-cooled centrifugal chiller",
            "unit": "SET",
            "contract_sor_rate": 185000.00,
            "max_allowable_quantity": 4.00
        },
        {
            "item_code": "MNE-07-003",
            "trade_id": "TRD-07",
            "description": "Medical gas copper piping distribution and terminal terminal units",
            "unit": "m",
            "contract_sor_rate": 310.00,
            "max_allowable_quantity": 2800.00
        },
        {
            "item_code": "ARC-04-002",
            "trade_id": "TRD-04",
            "description": "Architectural drywall partition & acoustic ceiling assemblies",
            "unit": "m2",
            "contract_sor_rate": 150.00,
            "max_allowable_quantity": 9000.00
        }
    ]
}

# Progress Claim No. 08 - The Over-Certification Trap with Cumulative Accounting
served_date = date(2026, 10, 1)
sopa_deadline = calculate_sopa_deadline(served_date, contract_days=14)

INTERIM_CLAIM_WHC = {
    "claim_id": "CLM-WHC-008",
    "project_id": "PRJ-WHC-COM-001",
    "valuation_month": "2026-10",
    "date_served": str(served_date),
    "statutory_response_deadline": str(sopa_deadline),
    "cumulative_accounting": {
        "previous_cumulative_certified_gross": 24200000.00,
        "contractor_claimed_gross_this_period": 4850000.00,
        "contractor_claimed_cumulative_gross": 29050000.00,
        "openbim_verified_gross_this_period": 3687500.00,
        "openbim_verified_cumulative_gross": 27887500.00,
        "over_certification_disallowance_this_period": 1162500.00,
        "retention_accumulated_to_date": 1000000.00,
        "retention_cap_reached": True,
        "retention_deduction_this_period": 0.00,
        "statutory_safety_set_off": 55000.00,
        "net_payable_certified_this_period": 3632500.00
    },
    "claimed_items": [
        {
            "item_code": "STR-02-004",
            "description": "Supply and cast Grade 40 ready-mixed concrete in columns",
            "contract_unit_rate": 240.00,
            "contractor_claimed_cumulative_qty": 7800.00,
            "contractor_claimed_pct": 91.76,
            "contractor_claimed_cumulative_amount": 1872000.00,
            "ifc_openbim_verified_qty": 6500.00,
            "ifc_openbim_verified_pct": 76.47,
            "ifc_openbim_verified_amount": 1560000.00,
            "discrepancy_amount": 312000.00,
            "discrepancy_status": "FLAGGED_OVER_CERTIFICATION"
        },
        {
            "item_code": "CIV-01-001",
            "description": "Excavation in soft material not exceeding 2.0m deep",
            "contract_unit_rate": 45.50,
            "contractor_claimed_cumulative_qty": 12000.00,
            "contractor_claimed_pct": 100.00,
            "contractor_claimed_cumulative_amount": 546000.00,
            "ifc_openbim_verified_qty": 11850.00,
            "ifc_openbim_verified_pct": 98.75,
            "ifc_openbim_verified_amount": 539175.00,
            "discrepancy_amount": 6825.00,
            "discrepancy_status": "WITHIN_TOLERANCE"
        },
        {
            "item_code": "MNE-07-003",
            "description": "Medical gas copper piping distribution",
            "contract_unit_rate": 310.00,
            "contractor_claimed_cumulative_qty": 2450.00,
            "contractor_claimed_pct": 87.50,
            "contractor_claimed_cumulative_amount": 759500.00,
            "ifc_openbim_verified_qty": 1720.00,
            "ifc_openbim_verified_pct": 61.43,
            "ifc_openbim_verified_amount": 533200.00,
            "discrepancy_amount": 226300.00,
            "discrepancy_status": "FLAGGED_OVER_CERTIFICATION"
        },
        {
            "item_code": "MNE-06-012",
            "description": "500RT water-cooled centrifugal chiller",
            "contract_unit_rate": 185000.00,
            "contractor_claimed_cumulative_qty": 3.00,
            "contractor_claimed_pct": 75.00,
            "contractor_claimed_cumulative_amount": 555000.00,
            "ifc_openbim_verified_qty": 2.00,
            "ifc_openbim_verified_pct": 50.00,
            "ifc_openbim_verified_amount": 370000.00,
            "discrepancy_amount": 185000.00,
            "discrepancy_status": "FLAGGED_OVER_CERTIFICATION"
        },
        {
            "item_code": "ARC-04-002",
            "description": "Architectural drywall partition & acoustic ceiling assemblies",
            "contract_unit_rate": 150.00,
            "contractor_claimed_cumulative_qty": 7450.00,
            "contractor_claimed_pct": 89.76,
            "contractor_claimed_cumulative_amount": 1117500.00,
            "ifc_openbim_verified_qty": 4567.50,
            "ifc_openbim_verified_pct": 55.03,
            "ifc_openbim_verified_amount": 685125.00,
            "discrepancy_amount": 432375.00,
            "discrepancy_status": "FLAGGED_OVER_CERTIFICATION"
        }
    ],
    "site_safety_incidents": {
        "mom_demerit_points_accumulated_this_month": 4,
        "mom_stop_work_order_days": 3,
        "mcm_stop_work_order_days": 3,
        "unremediated_safety_fines": 10000.00
    }
}

# 12 Sample Variation Orders - Valuation Waterfall + PSSCOC Clause 19.1 28-Day Timebar Checks
VARIATION_ORDERS_WHC = [
    {
        "vo_id": "VO-WHC-001",
        "instruction_reference": "SOI-2026-042",
        "instruction_date": "2026-08-10",
        "claim_notice_date": "2026-08-25",
        "days_elapsed_notice": 15,
        "contract_timebar_limit_days": 28,
        "timebar_status": "TIMEBAR_COMPLIANT",
        "description": "Additional Grade 40 column structural casting due to architectural core revision",
        "trade_id": "TRD-02",
        "claimed_item_code": "STR-02-004",
        "quantity": 350.00,
        "unit": "m3",
        "proposed_valuation_tier": "TIER_3_STAR_RATE",
        "contractor_proposed_rate": 380.00,
        "contractor_claimed_amount": 133000.00,
        "deterministic_validation": {
            "action_taken": "REJECT_TIER_3_FALLBACK_TO_TIER_1",
            "authoritative_rate_applied": 240.00,
            "certified_amount": 84000.00,
            "deduction_disallowed": 49000.00,
            "fraud_flag": "RATE_DUPLICATION_DETECTED"
        }
    },
    {
        "vo_id": "VO-WHC-002",
        "instruction_reference": "SOI-2026-049",
        "instruction_date": "2026-08-18",
        "claim_notice_date": "2026-09-02",
        "days_elapsed_notice": 15,
        "contract_timebar_limit_days": 28,
        "timebar_status": "TIMEBAR_COMPLIANT",
        "description": "Imported high-spec specialized acoustical wall paneling for main conference lounge",
        "trade_id": "TRD-05",
        "claimed_item_code": "STAR-FIN-901",
        "quantity": 420.00,
        "unit": "m2",
        "proposed_valuation_tier": "TIER_3_STAR_RATE",
        "contractor_proposed_rate": 185.00,
        "contractor_claimed_amount": 77700.00,
        "deterministic_validation": {
            "action_taken": "APPROVE_TIER_3_PENDING_QUOTATION_VERIFICATION",
            "authoritative_rate_applied": 185.00,
            "certified_amount": 77700.00,
            "deduction_disallowed": 0.00,
            "fraud_flag": "NONE_NEW_SCOPE_VALID"
        }
    },
    {
        "vo_id": "VO-WHC-003",
        "instruction_reference": "SOI-2026-051",
        "instruction_date": "2026-08-22",
        "claim_notice_date": "2026-09-10",
        "days_elapsed_notice": 19,
        "contract_timebar_limit_days": 28,
        "timebar_status": "TIMEBAR_COMPLIANT",
        "description": "Deep trench excavation in hard granite rock between gridlines G4-G7",
        "trade_id": "TRD-01",
        "claimed_item_code": "CIV-01-001",
        "quantity": 600.00,
        "unit": "m3",
        "proposed_valuation_tier": "TIER_2_PRO_RATA",
        "contractor_proposed_rate": 115.00,
        "contractor_claimed_amount": 69000.00,
        "deterministic_validation": {
            "action_taken": "APPROVE_TIER_2_PRO_RATA_DIFFERING_GROUND",
            "authoritative_rate_applied": 91.00,
            "certified_amount": 54600.00,
            "deduction_disallowed": 14400.00,
            "fraud_flag": "PARTIAL_MARKUP_TRIMMED"
        }
    },
    {
        "vo_id": "VO-WHC-004",
        "instruction_reference": "SOI-2026-055",
        "instruction_date": "2026-08-28",
        "claim_notice_date": "2026-09-15",
        "days_elapsed_notice": 18,
        "contract_timebar_limit_days": 28,
        "timebar_status": "TIMEBAR_COMPLIANT",
        "description": "Rerouting medical gas pipeline zone B to clear HVAC duct clashes",
        "trade_id": "TRD-07",
        "claimed_item_code": "MNE-07-003",
        "quantity": 180.00,
        "unit": "m",
        "proposed_valuation_tier": "TIER_3_STAR_RATE",
        "contractor_proposed_rate": 450.00,
        "contractor_claimed_amount": 81000.00,
        "deterministic_validation": {
            "action_taken": "REJECT_TIER_3_FALLBACK_TO_TIER_1",
            "authoritative_rate_applied": 310.00,
            "certified_amount": 55800.00,
            "deduction_disallowed": 25200.00,
            "fraud_flag": "RATE_DUPLICATION_DETECTED"
        }
    },
    {
        "vo_id": "VO-WHC-005",
        "instruction_reference": "SOI-2026-058",
        "instruction_date": "2026-07-15",
        "claim_notice_date": "2026-09-22",
        "days_elapsed_notice": 69,
        "contract_timebar_limit_days": 28,
        "timebar_status": "TIMEBAR_EXPIRED_CLAIM_WAIVED",
        "description": "Weekend daywork labor for emergency water pipe diversion without signed clerk chits",
        "trade_id": "TRD-08",
        "claimed_item_code": "DAY-LAB-001",
        "quantity": 120.00,
        "unit": "HRS",
        "proposed_valuation_tier": "TIER_4_DAYWORK",
        "contractor_proposed_rate": 85.00,
        "contractor_claimed_amount": 10200.00,
        "deterministic_validation": {
            "action_taken": "REJECT_TIMEBAR_EXPIRED_AND_UNSUBSTANTIATED",
            "authoritative_rate_applied": 0.00,
            "certified_amount": 0.00,
            "deduction_disallowed": 10200.00,
            "fraud_flag": "TIMEBAR_BREACH_PSSCOC_CL19"
        }
    },
    {
        "vo_id": "VO-WHC-006",
        "instruction_reference": "SOI-2026-061",
        "instruction_date": "2026-09-02",
        "claim_notice_date": "2026-09-18",
        "days_elapsed_notice": 16,
        "contract_timebar_limit_days": 28,
        "timebar_status": "TIMEBAR_COMPLIANT",
        "description": "Additional high tensile rebar 16mm in transfer slab pour 3",
        "trade_id": "TRD-02",
        "claimed_item_code": "STR-02-005",
        "quantity": 25.00,
        "unit": "TON",
        "proposed_valuation_tier": "TIER_1_SOR",
        "contractor_proposed_rate": 1680.00,
        "contractor_claimed_amount": 42000.00,
        "deterministic_validation": {
            "action_taken": "APPROVE_TIER_1_SOR_VERIFIED",
            "authoritative_rate_applied": 1680.00,
            "certified_amount": 42000.00,
            "deduction_disallowed": 0.00,
            "fraud_flag": "NONE_VALID"
        }
    },
    {
        "vo_id": "VO-WHC-007",
        "instruction_reference": "SOI-2026-063",
        "instruction_date": "2026-07-20",
        "claim_notice_date": "2026-09-25",
        "days_elapsed_notice": 67,
        "contract_timebar_limit_days": 28,
        "timebar_status": "TIMEBAR_EXPIRED_CLAIM_WAIVED",
        "description": "Claim for extended plant standing time during architectural coordination review",
        "trade_id": "TRD-09",
        "claimed_item_code": "CLM-PLT-009",
        "quantity": 14.00,
        "unit": "DAYS",
        "proposed_valuation_tier": "TIER_4_DAYWORK",
        "contractor_proposed_rate": 2200.00,
        "contractor_claimed_amount": 30800.00,
        "deterministic_validation": {
            "action_taken": "REJECT_TIMEBAR_EXPIRED_AND_CONCURRENT_DELAY",
            "authoritative_rate_applied": 0.00,
            "certified_amount": 0.00,
            "deduction_disallowed": 30800.00,
            "fraud_flag": "TIMEBAR_BREACH_PSSCOC_CL19"
        }
    },
    {
        "vo_id": "VO-WHC-008",
        "instruction_reference": "SOI-2026-067",
        "instruction_date": "2026-09-08",
        "claim_notice_date": "2026-09-22",
        "days_elapsed_notice": 14,
        "contract_timebar_limit_days": 28,
        "timebar_status": "TIMEBAR_COMPLIANT",
        "description": "Additional 2-hour fire-rated drywall partition around electrical sub-station",
        "trade_id": "TRD-05",
        "claimed_item_code": "FIN-05-008",
        "quantity": 280.00,
        "unit": "m2",
        "proposed_valuation_tier": "TIER_2_PRO_RATA",
        "contractor_proposed_rate": 145.00,
        "contractor_claimed_amount": 40600.00,
        "deterministic_validation": {
            "action_taken": "APPROVE_TIER_2_PRO_RATA_FIRE_RATING",
            "authoritative_rate_applied": 128.00,
            "certified_amount": 35840.00,
            "deduction_disallowed": 4760.00,
            "fraud_flag": "PARTIAL_MARKUP_TRIMMED"
        }
    },
    {
        "vo_id": "VO-WHC-009",
        "instruction_reference": "SOI-2026-070",
        "instruction_date": "2026-09-12",
        "claim_notice_date": "2026-09-24",
        "days_elapsed_notice": 12,
        "contract_timebar_limit_days": 28,
        "timebar_status": "TIMEBAR_COMPLIANT",
        "description": "Supply of spare 500RT centrifugal chiller motor assembly requested by facilities",
        "trade_id": "TRD-06",
        "claimed_item_code": "STAR-MNE-404",
        "quantity": 1.00,
        "unit": "SET",
        "proposed_valuation_tier": "TIER_3_STAR_RATE",
        "contractor_proposed_rate": 48000.00,
        "contractor_claimed_amount": 48000.00,
        "deterministic_validation": {
            "action_taken": "APPROVE_TIER_3_OEM_INVOICE_SUPPORTED",
            "authoritative_rate_applied": 45000.00,
            "certified_amount": 45000.00,
            "deduction_disallowed": 3000.00,
            "fraud_flag": "OEM_DISCOUNT_LEVELING"
        }
    },
    {
        "vo_id": "VO-WHC-010",
        "instruction_reference": "SOI-2026-074",
        "instruction_date": "2026-09-15",
        "claim_notice_date": "2026-09-26",
        "days_elapsed_notice": 11,
        "contract_timebar_limit_days": 28,
        "timebar_status": "TIMEBAR_COMPLIANT",
        "description": "Demolition and re-casting of defective parapet wall rejected by resident engineer",
        "trade_id": "TRD-02",
        "claimed_item_code": "STR-02-004",
        "quantity": 45.00,
        "unit": "m3",
        "proposed_valuation_tier": "TIER_1_SOR",
        "contractor_proposed_rate": 240.00,
        "contractor_claimed_amount": 10800.00,
        "deterministic_validation": {
            "action_taken": "REJECT_DEFECTIVE_WORK_REMEDIAL_OBLIGATION",
            "authoritative_rate_applied": 0.00,
            "certified_amount": 0.00,
            "deduction_disallowed": 10800.00,
            "fraud_flag": "DEFECTIVE_WORK_IMPROPER_VO"
        }
    },
    {
        "vo_id": "VO-WHC-011",
        "instruction_reference": "SOI-2026-079",
        "instruction_date": "2026-09-18",
        "claim_notice_date": "2026-09-28",
        "days_elapsed_notice": 10,
        "contract_timebar_limit_days": 28,
        "timebar_status": "TIMEBAR_COMPLIANT",
        "description": "Epoxy floor coating in medical supply stores not in original drawings",
        "trade_id": "TRD-05",
        "claimed_item_code": "STAR-FIN-882",
        "quantity": 850.00,
        "unit": "m2",
        "proposed_valuation_tier": "TIER_3_STAR_RATE",
        "contractor_proposed_rate": 32.00,
        "contractor_claimed_amount": 27200.00,
        "deterministic_validation": {
            "action_taken": "APPROVE_TIER_3_MARKET_BENCHMARK",
            "authoritative_rate_applied": 29.50,
            "certified_amount": 25075.00,
            "deduction_disallowed": 2125.00,
            "fraud_flag": "PARTIAL_MARKUP_TRIMMED"
        }
    },
    {
        "vo_id": "VO-WHC-012",
        "instruction_reference": "SOI-2026-083",
        "instruction_date": "2026-08-01",
        "claim_notice_date": "2026-09-29",
        "days_elapsed_notice": 59,
        "contract_timebar_limit_days": 28,
        "timebar_status": "TIMEBAR_EXPIRED_CLAIM_WAIVED",
        "description": "Prolongation site overheads claim for rain delays exceeding 10-year statistical average",
        "trade_id": "TRD-10",
        "claimed_item_code": "CLM-EOT-012",
        "quantity": 21.00,
        "unit": "DAYS",
        "proposed_valuation_tier": "TIER_4_DAYWORK",
        "contractor_proposed_rate": 3500.00,
        "contractor_claimed_amount": 73500.00,
        "deterministic_validation": {
            "action_taken": "REJECT_TIMEBAR_EXPIRED_AND_CONTRACTOR_NEUTRAL_RISK",
            "authoritative_rate_applied": 0.00,
            "certified_amount": 0.00,
            "deduction_disallowed": 73500.00,
            "fraud_flag": "TIMEBAR_BREACH_PSSCOC_CL19"
        }
    }
]

# Additional 3 Scenarios for Platform Dropdown Multi-Project Selection
ADDITIONAL_PROJECTS = [
    {
        "project_id": "PRJ-JID-ATP-004",
        "project_name": "Jurong Innovation District Advanced Tech Park",
        "contract_type": "PSSCOC_2020",
        "employer_name": "JTC Corporation",
        "main_contractor_uen": "197600888B",
        "main_contractor_name": "Heng Win (Private) Limited",
        "currency": "SGD",
        "financials": {
            "base_contract_sum": 65075000.00,
            "contingency_allocation": 3425000.00,
            "total_approved_budget": 68500000.00,
            "retention_max_cap_pct": 5.0,
            "retention_limit_sgd": 1500000.00,
            "contract_response_days_ceiling": 14,
            "retention_release_stages": [
                {"milestone": "PRACTICAL_COMPLETION", "release_percentage": 50.0},
                {"milestone": "FINAL_ACCOUNT_EXPIRY_DLP", "release_percentage": 50.0}
            ]
        },
        "status": "ACTIVE_DISPUTED_CLAIMS"
    },
    {
        "project_id": "PRJ-TWRP-002",
        "project_name": "Tuas Water Reclamation Plant — Biosolids Facility",
        "contract_type": "PSSCOC_2020",
        "employer_name": "Public Utilities Board (PUB)",
        "main_contractor_uen": "197000345C",
        "main_contractor_name": "DongHae Global Engineering Pte Ltd",
        "currency": "SGD",
        "financials": {
            "base_contract_sum": 74575000.00,
            "contingency_allocation": 3925000.00,
            "total_approved_budget": 78500000.00,
            "retention_max_cap_pct": 5.0,
            "retention_limit_sgd": 2000000.00,
            "contract_response_days_ceiling": 14,
            "retention_release_stages": [
                {"milestone": "PRACTICAL_COMPLETION", "release_percentage": 50.0},
                {"milestone": "FINAL_ACCOUNT_EXPIRY_DLP", "release_percentage": 50.0}
            ]
        },
        "status": "ACTIVE_DISPUTED_CLAIMS"
    },
    {
        "project_id": "PRJ-T5-003",
        "project_name": "Changi Airport Terminal 5 — Substructure & Tunnels",
        "contract_type": "CIVIL_CAG_STANDARDS",
        "employer_name": "Changi Airport Group (CAG)",
        "main_contractor_uen": "194000001A",
        "main_contractor_name": "Vanguard Underground Engineering Pte Ltd",
        "currency": "SGD",
        "financials": {
            "base_contract_sum": 137750000.00,
            "contingency_allocation": 7250000.00,
            "total_approved_budget": 145000000.00,
            "retention_max_cap_pct": 5.0,
            "retention_limit_sgd": 2500000.00,
            "contract_response_days_ceiling": 14,
            "retention_release_stages": [
                {"milestone": "PRACTICAL_COMPLETION", "release_percentage": 50.0},
                {"milestone": "FINAL_ACCOUNT_EXPIRY_DLP", "release_percentage": 50.0}
            ]
        },
        "status": "ACTIVE_DISPUTED_CLAIMS"
    }
]

# Scenario Packages for Additional Projects
PROJECT_SCENARIOS = {
    "PRJ-JID-ATP-004": {
        "schedule_of_rates": [
            {"item_code": "CIV-01-002", "trade_id": "TRD-01", "description": "Bulk Earthworks in Hard Rock", "unit": "m3", "contract_sor_rate": 85.00, "max_allowable_quantity": 25000.00},
            {"item_code": "STR-02-008", "trade_id": "TRD-02", "description": "Precast Post-Tensioned Beams", "unit": "m", "contract_sor_rate": 520.00, "max_allowable_quantity": 5000.00},
            {"item_code": "ARC-04-001", "trade_id": "TRD-04", "description": "Curtain Wall Glazing Unitized Panels", "unit": "m2", "contract_sor_rate": 420.00, "max_allowable_quantity": 6000.00},
            {"item_code": "MNE-03-005", "trade_id": "TRD-03", "description": "High Voltage Transformer 22kV 2MVA", "unit": "SET", "contract_sor_rate": 145000.00, "max_allowable_quantity": 4.00}
        ],
        "interim_claim": {
            "claim_id": "CLM-JID-006",
            "project_id": "PRJ-JID-ATP-004",
            "valuation_month": "2026-10",
            "date_served": "2026-10-02",
            "statutory_response_deadline": "2026-10-19",
            "cumulative_accounting": {
                "previous_cumulative_certified_gross": 18400000.00,
                "contractor_claimed_gross_this_period": 3850000.00,
                "openbim_verified_gross_this_period": 3220000.00,
                "over_certification_disallowance_this_period": 630000.00,
                "retention_accumulated_to_date": 1081000.00,
                "statutory_safety_set_off": 27500.00,
                "net_payable_certified_this_period": 3192500.00
            },
            "claimed_items": [
                {
                    "item_code": "CIV-01-002", "description": "Bulk Earthworks in Hard Rock", "contract_unit_rate": 85.00,
                    "contractor_claimed_cumulative_qty": 12000.00, "contractor_claimed_pct": 48.00, "contractor_claimed_cumulative_amount": 1020000.00,
                    "ifc_openbim_verified_qty": 10000.00, "ifc_openbim_verified_pct": 40.00, "ifc_openbim_verified_amount": 850000.00,
                    "discrepancy_amount": 170000.00, "discrepancy_status": "FLAGGED_OVER_CERTIFICATION"
                },
                {
                    "item_code": "STR-02-008", "description": "Precast Post-Tensioned Beams", "contract_unit_rate": 520.00,
                    "contractor_claimed_cumulative_qty": 3000.00, "contractor_claimed_pct": 60.00, "contractor_claimed_cumulative_amount": 1560000.00,
                    "ifc_openbim_verified_qty": 2500.00, "ifc_openbim_verified_pct": 50.00, "ifc_openbim_verified_amount": 1300000.00,
                    "discrepancy_amount": 260000.00, "discrepancy_status": "FLAGGED_OVER_CERTIFICATION"
                },
                {
                    "item_code": "ARC-04-001", "description": "Curtain Wall Glazing Unitized Panels", "contract_unit_rate": 420.00,
                    "contractor_claimed_cumulative_qty": 3023.81, "contractor_claimed_pct": 50.40, "contractor_claimed_cumulative_amount": 1270000.00,
                    "ifc_openbim_verified_qty": 2547.62, "ifc_openbim_verified_pct": 42.46, "ifc_openbim_verified_amount": 1070000.00,
                    "discrepancy_amount": 200000.00, "discrepancy_status": "FLAGGED_OVER_CERTIFICATION"
                }
            ],
            "safety": {
                "demerit_points": 2, "swo_idle_days": 1, "unremediated_fines": 8000.00,
                "swo_deduction": 12500.00, "sdp_deduction": 3000.00, "fines_deduction": 9200.00, "total_safety_set_off": 24700.00
            }
        },
        "variation_orders": [
            {
                "vo_id": "VO-JID-001", "instruction_reference": "JTC-SOI-014", "instruction_date": "2026-08-15", "claim_notice_date": "2026-08-28",
                "days_elapsed_notice": 13, "timebar_status": "TIMEBAR_COMPLIANT", "description": "Soil stabilization grouting for utility corridor",
                "trade_id": "TRD-01", "claimed_item_code": "CIV-01-002", "quantity": 560.00, "unit": "m3", "proposed_valuation_tier": "TIER_1_SOR",
                "contractor_proposed_rate": 85.00, "contractor_claimed_amount": 47600.00, "action_taken": "APPROVE_TIER_1_SOR",
                "authoritative_rate_applied": 85.00, "certified_amount": 47600.00, "deduction_disallowed": 0.00, "fraud_flag": "VALID_TIER_1_CLAIM"
            },
            {
                "vo_id": "VO-JID-002", "instruction_reference": "JTC-SOI-019", "instruction_date": "2026-08-20", "claim_notice_date": "2026-09-05",
                "days_elapsed_notice": 16, "timebar_status": "TIMEBAR_COMPLIANT", "description": "Deep well dewatering pumps operational surcharge",
                "trade_id": "TRD-01", "claimed_item_code": "CIV-01-002", "quantity": 20.00, "unit": "DAYS", "proposed_valuation_tier": "TIER_3_STAR_RATE",
                "contractor_proposed_rate": 2200.00, "contractor_claimed_amount": 44000.00, "action_taken": "FALLBACK_TO_TIER_1_SOR_DUE_TO_DUPLICATION",
                "authoritative_rate_applied": 1200.00, "certified_amount": 24000.00, "deduction_disallowed": 20000.00, "fraud_flag": "RATE_DUPLICATION_DETECTED"
            },
            {
                "vo_id": "VO-JID-003", "instruction_reference": "JTC-SOI-025", "instruction_date": "2026-07-10", "claim_notice_date": "2026-09-18",
                "days_elapsed_notice": 70, "timebar_status": "TIMEBAR_EXPIRED_CLAIM_WAIVED", "description": "Prolongation site overheads for utility diversion delays",
                "trade_id": "TRD-10", "claimed_item_code": "CLM-EOT-008", "quantity": 15.00, "unit": "DAYS", "proposed_valuation_tier": "TIER_4_DAYWORK",
                "contractor_proposed_rate": 3000.00, "contractor_claimed_amount": 45000.00, "action_taken": "REJECT_TIMEBAR_EXPIRED_PSSCOC_CL19",
                "authoritative_rate_applied": 0.00, "certified_amount": 0.00, "deduction_disallowed": 45000.00, "fraud_flag": "TIMEBAR_BREACH_PSSCOC_CL19"
            }
        ],
        "cost_forecast_eac": [14, 65075000.00, 48000000.00, 52600000.00, 0.9125, 71315068.49, 3425000.00, 2900000.00, 525000.00, 350000.00, 16]
    },
    "PRJ-TWRP-002": {
        "schedule_of_rates": [
            {"item_code": "BIO-01-005", "trade_id": "TRD-05", "description": "Anaerobic Digester Reinforced Concrete Shell", "unit": "m3", "contract_sor_rate": 380.00, "max_allowable_quantity": 8000.00},
            {"item_code": "BIO-03-010", "trade_id": "TRD-05", "description": "Centrifugal Sludge Dewatering Mechanical Skid", "unit": "SET", "contract_sor_rate": 185000.00, "max_allowable_quantity": 6.00},
            {"item_code": "MEP-02-004", "trade_id": "TRD-06", "description": "Biogas Cogeneration Scrubber Distribution Grid", "unit": "SET", "contract_sor_rate": 95000.00, "max_allowable_quantity": 4.00}
        ],
        "interim_claim": {
            "claim_id": "CLM-TWRP-005",
            "project_id": "PRJ-TWRP-002",
            "valuation_month": "2026-10",
            "date_served": "2026-10-03",
            "statutory_response_deadline": "2026-10-20",
            "cumulative_accounting": {
                "previous_cumulative_certified_gross": 24800000.00,
                "contractor_claimed_gross_this_period": 3950000.00,
                "openbim_verified_gross_this_period": 3420000.00,
                "over_certification_disallowance_this_period": 530000.00,
                "retention_accumulated_to_date": 1426000.00,
                "statutory_safety_set_off": 18500.00,
                "net_payable_certified_this_period": 3401500.00
            },
            "claimed_items": [
                {
                    "item_code": "BIO-01-005", "description": "Anaerobic Digester Reinforced Concrete Shell", "contract_unit_rate": 380.00,
                    "contractor_claimed_cumulative_qty": 6000.00, "contractor_claimed_pct": 75.00, "contractor_claimed_cumulative_amount": 2280000.00,
                    "ifc_openbim_verified_qty": 5200.00, "ifc_openbim_verified_pct": 65.00, "ifc_openbim_verified_amount": 1976000.00,
                    "discrepancy_amount": 304000.00, "discrepancy_status": "FLAGGED_OVER_CERTIFICATION"
                },
                {
                    "item_code": "BIO-03-010", "description": "Centrifugal Sludge Dewatering Mechanical Skid", "contract_unit_rate": 185000.00,
                    "contractor_claimed_cumulative_qty": 4.00, "contractor_claimed_pct": 66.67, "contractor_claimed_cumulative_amount": 740000.00,
                    "ifc_openbim_verified_qty": 3.00, "ifc_openbim_verified_pct": 50.00, "ifc_openbim_verified_amount": 555000.00,
                    "discrepancy_amount": 185000.00, "discrepancy_status": "FLAGGED_OVER_CERTIFICATION"
                },
                {
                    "item_code": "MEP-02-004", "description": "Biogas Cogeneration Scrubber Distribution Grid", "contract_unit_rate": 95000.00,
                    "contractor_claimed_cumulative_qty": 3.00, "contractor_claimed_pct": 75.00, "contractor_claimed_cumulative_amount": 285000.00,
                    "ifc_openbim_verified_qty": 2.57, "ifc_openbim_verified_pct": 64.25, "ifc_openbim_verified_amount": 244000.00,
                    "discrepancy_amount": 41000.00, "discrepancy_status": "FLAGGED_OVER_CERTIFICATION"
                }
            ],
            "safety": {
                "demerit_points": 2, "swo_idle_days": 0, "unremediated_fines": 8000.00,
                "swo_deduction": 0.00, "sdp_deduction": 3000.00, "fines_deduction": 9200.00, "total_safety_set_off": 12200.00
            }
        },
        "variation_orders": [
            {
                "vo_id": "VO-TWRP-001", "instruction_reference": "PUB-SOI-014", "instruction_date": "2026-09-02", "claim_notice_date": "2026-09-15",
                "days_elapsed_notice": 13, "timebar_status": "TIMEBAR_COMPLIANT", "description": "Deep piling obstruction removal in reclaimed Tuas marine clay",
                "trade_id": "TRD-05", "claimed_item_code": "BIO-01-005", "quantity": 250.00, "unit": "m3", "proposed_valuation_tier": "TIER_3_STAR_RATE",
                "contractor_proposed_rate": 520.00, "contractor_claimed_amount": 130000.00, "action_taken": "APPROVE_TIER_3_MARKET_BENCHMARK",
                "authoritative_rate_applied": 460.00, "certified_amount": 115000.00, "deduction_disallowed": 15000.00, "fraud_flag": "PARTIAL_MARKUP_TRIMMED"
            },
            {
                "vo_id": "VO-TWRP-002", "instruction_reference": "PUB-SOI-022", "instruction_date": "2026-08-05", "claim_notice_date": "2026-09-22",
                "days_elapsed_notice": 48, "timebar_status": "TIMEBAR_EXPIRED_CLAIM_WAIVED", "description": "Explosion-proof ATEX methane gas sensor grid addition",
                "trade_id": "TRD-10", "claimed_item_code": "CLM-ATEX-002", "quantity": 14.00, "unit": "DAYS", "proposed_valuation_tier": "TIER_4_DAYWORK",
                "contractor_proposed_rate": 2800.00, "contractor_claimed_amount": 39200.00, "action_taken": "REJECT_TIMEBAR_EXPIRED_PSSCOC_CL19",
                "authoritative_rate_applied": 0.00, "certified_amount": 0.00, "deduction_disallowed": 39200.00, "fraud_flag": "TIMEBAR_BREACH_PSSCOC_CL19"
            }
        ],
        "cost_forecast_eac": [8, 74575000.00, 28000000.00, 29200000.00, 0.9589, 77771428.57, 3925000.00, 1200000.00, 2725000.00, 150000.00, 18]
    },
    "PRJ-T5-003": {
        "schedule_of_rates": [
            {"item_code": "TUN-01-001", "trade_id": "TRD-01", "description": "Diaphragm Wall 1200mm thk Reinforcement & Concreting", "unit": "m2", "contract_sor_rate": 950.00, "max_allowable_quantity": 6000.00},
            {"item_code": "TUN-02-005", "trade_id": "TRD-02", "description": "Jet Grouting Piles for Shaft Base Plugs", "unit": "m", "contract_sor_rate": 380.00, "max_allowable_quantity": 10000.00},
            {"item_code": "TUN-03-010", "trade_id": "TRD-03", "description": "Structural Steel Struts Level 3 Pre-loading", "unit": "TON", "contract_sor_rate": 1800.00, "max_allowable_quantity": 1500.00}
        ],
        "interim_claim": {
            "claim_id": "CLM-T5-012",
            "project_id": "PRJ-T5-003",
            "valuation_month": "2026-10",
            "date_served": "2026-10-01",
            "statutory_response_deadline": "2026-10-17",
            "cumulative_accounting": {
                "previous_cumulative_certified_gross": 64110000.00,
                "contractor_claimed_gross_this_period": 8450000.00,
                "openbim_verified_gross_this_period": 7890000.00,
                "over_certification_disallowance_this_period": 560000.00,
                "retention_accumulated_to_date": 2500000.00,
                "statutory_safety_set_off": 82500.00,
                "net_payable_certified_this_period": 7807500.00
            },
            "claimed_items": [
                {
                    "item_code": "TUN-01-001", "description": "Diaphragm Wall 1200mm thk Reinforcement & Concreting", "contract_unit_rate": 950.00,
                    "contractor_claimed_cumulative_qty": 4200.00, "contractor_claimed_pct": 70.00, "contractor_claimed_cumulative_amount": 3990000.00,
                    "ifc_openbim_verified_qty": 3900.00, "ifc_openbim_verified_pct": 65.00, "ifc_openbim_verified_amount": 3705000.00,
                    "discrepancy_amount": 285000.00, "discrepancy_status": "FLAGGED_OVER_CERTIFICATION"
                },
                {
                    "item_code": "TUN-02-005", "description": "Jet Grouting Piles for Shaft Base Plugs", "contract_unit_rate": 380.00,
                    "contractor_claimed_cumulative_qty": 7000.00, "contractor_claimed_pct": 70.00, "contractor_claimed_cumulative_amount": 2660000.00,
                    "ifc_openbim_verified_qty": 6500.00, "ifc_openbim_verified_pct": 65.00, "ifc_openbim_verified_amount": 2470000.00,
                    "discrepancy_amount": 190000.00, "discrepancy_status": "FLAGGED_OVER_CERTIFICATION"
                },
                {
                    "item_code": "TUN-03-010", "description": "Structural Steel Struts Level 3 Pre-loading", "contract_unit_rate": 1800.00,
                    "contractor_claimed_cumulative_qty": 1000.00, "contractor_claimed_pct": 66.67, "contractor_claimed_cumulative_amount": 1800000.00,
                    "ifc_openbim_verified_qty": 952.78, "ifc_openbim_verified_pct": 63.52, "ifc_openbim_verified_amount": 1715000.00,
                    "discrepancy_amount": 85000.00, "discrepancy_status": "FLAGGED_OVER_CERTIFICATION"
                }
            ],
            "safety": {
                "demerit_points": 8, "swo_idle_days": 4, "unremediated_fines": 20000.00,
                "swo_deduction": 50000.00, "sdp_deduction": 12000.00, "fines_deduction": 23000.00, "total_safety_set_off": 85000.00
            }
        },
        "variation_orders": [
            {
                "vo_id": "VO-T5-001", "instruction_reference": "T5-SOI-041", "instruction_date": "2026-08-10", "claim_notice_date": "2026-08-22",
                "days_elapsed_notice": 12, "timebar_status": "TIMEBAR_COMPLIANT", "description": "Ground fissure polymer injection for APM tunnel stability",
                "trade_id": "TRD-01", "claimed_item_code": "TUN-01-001", "quantity": 400.00, "unit": "m3", "proposed_valuation_tier": "TIER_1_SOR",
                "contractor_proposed_rate": 230.00, "contractor_claimed_amount": 92000.00, "action_taken": "APPROVE_TIER_1_SOR",
                "authoritative_rate_applied": 230.00, "certified_amount": 92000.00, "deduction_disallowed": 0.00, "fraud_flag": "VALID_TIER_1_CLAIM"
            },
            {
                "vo_id": "VO-T5-002", "instruction_reference": "T5-SOI-048", "instruction_date": "2026-08-18", "claim_notice_date": "2026-09-02",
                "days_elapsed_notice": 15, "timebar_status": "TIMEBAR_COMPLIANT", "description": "Micro-tunneling utility clearance sleeve protection under taxiway",
                "trade_id": "TRD-01", "claimed_item_code": "TUN-01-001", "quantity": 100.00, "unit": "m", "proposed_valuation_tier": "TIER_3_STAR_RATE",
                "contractor_proposed_rate": 1100.00, "contractor_claimed_amount": 110000.00, "action_taken": "FALLBACK_TO_TIER_1_SOR_DUE_TO_DUPLICATION",
                "authoritative_rate_applied": 650.00, "certified_amount": 65000.00, "deduction_disallowed": 45000.00, "fraud_flag": "RATE_DUPLICATION_DETECTED"
            },
            {
                "vo_id": "VO-T5-003", "instruction_reference": "T5-SOI-055", "instruction_date": "2026-07-15", "claim_notice_date": "2026-09-08",
                "days_elapsed_notice": 55, "timebar_status": "TIMEBAR_EXPIRED_CLAIM_WAIVED", "description": "Off-island barge spoil disposal fee surcharge for airside excavation",
                "trade_id": "TRD-10", "claimed_item_code": "CLM-DISP-005", "quantity": 32.00, "unit": "TRIPS", "proposed_valuation_tier": "TIER_4_DAYWORK",
                "contractor_proposed_rate": 3500.00, "contractor_claimed_amount": 112000.00, "action_taken": "REJECT_TIMEBAR_EXPIRED_PSSCOC_CL19",
                "authoritative_rate_applied": 0.00, "certified_amount": 0.00, "deduction_disallowed": 112000.00, "fraud_flag": "TIMEBAR_BREACH_PSSCOC_CL19"
            }
        ],
        "cost_forecast_eac": [18, 137750000.00, 110000000.00, 109200000.00, 1.0073, 136751712.50, 7250000.00, 3600000.00, 3650000.00, 200000.00, 0]
    }
}

def generate_database_and_json_files():
    """Builds the DuckDB columnar store and writes out canonical JSON baseline files."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # 1. Write canonical JSON files
    with open(os.path.join(DATA_DIR, "contract_baseline.json"), "w") as f:
        json.dump(CONTRACT_BASELINE_WHC, f, indent=2)
    print("✓ Wrote data/contract_baseline.json (with retention release stages)")

    with open(os.path.join(DATA_DIR, "interim_claims.json"), "w") as f:
        json.dump(INTERIM_CLAIM_WHC, f, indent=2)
    print("✓ Wrote data/interim_claims.json (with cumulative accounting and SOPA deadline)")

    with open(os.path.join(DATA_DIR, "variation_orders.json"), "w") as f:
        json.dump({"variation_orders": VARIATION_ORDERS_WHC}, f, indent=2)
    print("✓ Wrote data/variation_orders.json (with 28-day PSSCOC Clause 19 timebar checks)")

    all_projects = [CONTRACT_BASELINE_WHC] + ADDITIONAL_PROJECTS
    with open(os.path.join(DATA_DIR, "all_projects_registry.json"), "w") as f:
        json.dump({"projects": all_projects}, f, indent=2)
    print("✓ Wrote data/all_projects_registry.json")

    # 2. Build DuckDB columnar database
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    con = duckdb.connect(DB_PATH)

    # Projects Table
    con.execute("""
    CREATE TABLE projects (
        project_id VARCHAR PRIMARY KEY,
        project_name VARCHAR,
        contract_type VARCHAR,
        employer_name VARCHAR,
        main_contractor_uen VARCHAR,
        main_contractor_name VARCHAR,
        currency VARCHAR,
        base_contract_sum DOUBLE,
        contingency_allocation DOUBLE,
        total_approved_budget DOUBLE,
        retention_max_cap_pct DOUBLE,
        retention_limit_sgd DOUBLE,
        contract_response_days_ceiling INTEGER
    );
    """)

    p = CONTRACT_BASELINE_WHC
    con.execute("""
    INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        p["project_id"], p["project_name"], p["contract_type"], p["employer_name"],
        p["main_contractor_uen"], p["main_contractor_name"], p["currency"],
        p["financials"]["base_contract_sum"], p["financials"]["contingency_allocation"],
        p["financials"]["total_approved_budget"], p["financials"]["retention_max_cap_pct"],
        p["financials"]["retention_limit_sgd"], p["financials"]["contract_response_days_ceiling"]
    ])

    for ap in ADDITIONAL_PROJECTS:
        con.execute("""
        INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ap["project_id"], ap["project_name"], ap["contract_type"], ap["employer_name"],
            ap["main_contractor_uen"], ap["main_contractor_name"], ap["currency"],
            ap["financials"]["base_contract_sum"], ap["financials"]["contingency_allocation"],
            ap["financials"]["total_approved_budget"], ap["financials"]["retention_max_cap_pct"],
            ap["financials"]["retention_limit_sgd"], ap["financials"]["contract_response_days_ceiling"]
        ])

    # Schedule of Rates (SOR) Table
    con.execute("""
    CREATE TABLE schedule_of_rates (
        project_id VARCHAR,
        item_code VARCHAR,
        trade_id VARCHAR,
        description VARCHAR,
        unit VARCHAR,
        contract_sor_rate DOUBLE,
        max_allowable_quantity DOUBLE,
        PRIMARY KEY (project_id, item_code)
    );
    """)

    for sor in CONTRACT_BASELINE_WHC["schedule_of_rates"]:
        con.execute("""
        INSERT INTO schedule_of_rates VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            CONTRACT_BASELINE_WHC["project_id"], sor["item_code"], sor["trade_id"],
            sor["description"], sor["unit"], sor["contract_sor_rate"], sor["max_allowable_quantity"]
        ])

    for pid, pdata in PROJECT_SCENARIOS.items():
        for sor in pdata["schedule_of_rates"]:
            con.execute("""
            INSERT INTO schedule_of_rates VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                pid, sor["item_code"], sor["trade_id"],
                sor["description"], sor["unit"], sor["contract_sor_rate"], sor["max_allowable_quantity"]
            ])

    # Interim Claims Table
    con.execute("""
    CREATE TABLE interim_claims (
        claim_id VARCHAR PRIMARY KEY,
        project_id VARCHAR,
        valuation_month VARCHAR,
        date_served DATE,
        statutory_response_deadline DATE,
        previous_cumulative_certified_gross DOUBLE,
        contractor_claimed_gross_this_period DOUBLE,
        openbim_verified_gross_this_period DOUBLE,
        over_certification_disallowance DOUBLE,
        retention_held_to_date DOUBLE,
        statutory_safety_set_off DOUBLE,
        net_payable_certified_this_period DOUBLE
    );
    """)

    clm = INTERIM_CLAIM_WHC
    c_acc = clm["cumulative_accounting"]
    con.execute("""
    INSERT INTO interim_claims VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        clm["claim_id"], clm["project_id"], clm["valuation_month"],
        clm["date_served"], clm["statutory_response_deadline"],
        c_acc["previous_cumulative_certified_gross"],
        c_acc["contractor_claimed_gross_this_period"],
        c_acc["openbim_verified_gross_this_period"],
        c_acc["over_certification_disallowance_this_period"],
        c_acc["retention_accumulated_to_date"],
        c_acc["statutory_safety_set_off"],
        c_acc["net_payable_certified_this_period"]
    ])

    for pid, pdata in PROJECT_SCENARIOS.items():
        ic = pdata["interim_claim"]
        ia = ic["cumulative_accounting"]
        con.execute("""
        INSERT INTO interim_claims VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ic["claim_id"], ic["project_id"], ic["valuation_month"],
            ic["date_served"], ic["statutory_response_deadline"],
            ia["previous_cumulative_certified_gross"],
            ia["contractor_claimed_gross_this_period"],
            ia["openbim_verified_gross_this_period"],
            ia["over_certification_disallowance_this_period"],
            ia["retention_accumulated_to_date"],
            ia["statutory_safety_set_off"],
            ia["net_payable_certified_this_period"]
        ])

    # Claim Line Items with openBIM Reconciliation
    con.execute("""
    CREATE TABLE claim_items (
        claim_id VARCHAR,
        item_code VARCHAR,
        description VARCHAR,
        contract_unit_rate DOUBLE,
        contractor_claimed_cumulative_qty DOUBLE,
        contractor_claimed_pct DOUBLE,
        contractor_claimed_cumulative_amount DOUBLE,
        ifc_openbim_verified_qty DOUBLE,
        ifc_openbim_verified_pct DOUBLE,
        ifc_openbim_verified_amount DOUBLE,
        discrepancy_amount DOUBLE,
        discrepancy_status VARCHAR,
        PRIMARY KEY (claim_id, item_code)
    );
    """)

    for item in clm["claimed_items"]:
        con.execute("""
        INSERT INTO claim_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            clm["claim_id"], item["item_code"], item["description"], item["contract_unit_rate"],
            item["contractor_claimed_cumulative_qty"], item["contractor_claimed_pct"],
            item["contractor_claimed_cumulative_amount"], item["ifc_openbim_verified_qty"],
            item["ifc_openbim_verified_pct"], item["ifc_openbim_verified_amount"],
            item["discrepancy_amount"], item["discrepancy_status"]
        ])

    for pid, pdata in PROJECT_SCENARIOS.items():
        cid = pdata["interim_claim"]["claim_id"]
        for item in pdata["interim_claim"]["claimed_items"]:
            con.execute("""
            INSERT INTO claim_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                cid, item["item_code"], item["description"], item["contract_unit_rate"],
                item["contractor_claimed_cumulative_qty"], item["contractor_claimed_pct"],
                item["contractor_claimed_cumulative_amount"], item["ifc_openbim_verified_qty"],
                item["ifc_openbim_verified_pct"], item["ifc_openbim_verified_amount"],
                item["discrepancy_amount"], item["discrepancy_status"]
            ])

    # Variation Orders Table
    con.execute("""
    CREATE TABLE variation_orders (
        vo_id VARCHAR PRIMARY KEY,
        project_id VARCHAR,
        instruction_reference VARCHAR,
        instruction_date DATE,
        claim_notice_date DATE,
        days_elapsed_notice INTEGER,
        timebar_status VARCHAR,
        description VARCHAR,
        trade_id VARCHAR,
        claimed_item_code VARCHAR,
        quantity DOUBLE,
        unit VARCHAR,
        proposed_valuation_tier VARCHAR,
        contractor_proposed_rate DOUBLE,
        contractor_claimed_amount DOUBLE,
        action_taken VARCHAR,
        authoritative_rate_applied DOUBLE,
        certified_amount DOUBLE,
        deduction_disallowed DOUBLE,
        fraud_flag VARCHAR
    );
    """)

    for vo in VARIATION_ORDERS_WHC:
        v = vo["deterministic_validation"]
        con.execute("""
        INSERT INTO variation_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            vo["vo_id"], CONTRACT_BASELINE_WHC["project_id"], vo["instruction_reference"],
            vo["instruction_date"], vo["claim_notice_date"], vo["days_elapsed_notice"],
            vo["timebar_status"], vo["description"], vo["trade_id"], vo["claimed_item_code"],
            vo["quantity"], vo["unit"], vo["proposed_valuation_tier"], vo["contractor_proposed_rate"],
            vo["contractor_claimed_amount"], v["action_taken"], v["authoritative_rate_applied"],
            v["certified_amount"], v["deduction_disallowed"], v["fraud_flag"]
        ])

    for pid, pdata in PROJECT_SCENARIOS.items():
        for vo in pdata["variation_orders"]:
            con.execute("""
            INSERT INTO variation_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                vo["vo_id"], pid, vo["instruction_reference"],
                vo["instruction_date"], vo["claim_notice_date"], vo["days_elapsed_notice"],
                vo["timebar_status"], vo["description"], vo["trade_id"], vo["claimed_item_code"],
                vo["quantity"], vo["unit"], vo["proposed_valuation_tier"], vo["contractor_proposed_rate"],
                vo["contractor_claimed_amount"], vo["action_taken"], vo["authoritative_rate_applied"],
                vo["certified_amount"], vo["deduction_disallowed"], vo["fraud_flag"]
            ])

    # MOM Safety Incidents & Deductions
    con.execute("""
    CREATE TABLE site_safety_incidents (
        claim_id VARCHAR PRIMARY KEY,
        project_id VARCHAR,
        mom_demerit_points INTEGER,
        swo_idle_days INTEGER,
        unremediated_fines DOUBLE,
        swo_deduction DOUBLE,
        sdp_deduction DOUBLE,
        fines_deduction DOUBLE,
        total_safety_set_off DOUBLE
    );
    """)

    safety = calculate_mom_safety_set_off(
        swo_idle_days=clm["site_safety_incidents"]["mom_stop_work_order_days"],
        demerit_points=clm["site_safety_incidents"]["mom_demerit_points_accumulated_this_month"],
        unrem_fines=clm["site_safety_incidents"]["unremediated_safety_fines"]
    )

    con.execute("""
    INSERT INTO site_safety_incidents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        clm["claim_id"], clm["project_id"], safety["demerit_points"],
        safety["swo_idle_days"], safety["unremediated_fines_base"],
        safety["swo_deduction"], safety["sdp_deduction"],
        safety["fines_deduction"], safety["total_safety_set_off"]
    ])

    for pid, pdata in PROJECT_SCENARIOS.items():
        cid = pdata["interim_claim"]["claim_id"]
        s = pdata["interim_claim"]["safety"]
        con.execute("""
        INSERT INTO site_safety_incidents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            cid, pid, s["demerit_points"], s["swo_idle_days"], s["unremediated_fines"],
            s["swo_deduction"], s["sdp_deduction"], s["fines_deduction"], s["total_safety_set_off"]
        ])

    # Predictive Cost-to-Complete & Contingency Burn Forecaster Table
    con.execute("""
    CREATE TABLE cost_forecast_eac (
        project_id VARCHAR PRIMARY KEY,
        month_index INTEGER,
        bac_budget_at_completion DOUBLE,
        bcwp_earned_value DOUBLE,
        acwp_actual_cost DOUBLE,
        cpi_cost_performance_index DOUBLE,
        eac_estimate_at_completion DOUBLE,
        contingency_original DOUBLE,
        contingency_depleted DOUBLE,
        contingency_remaining DOUBLE,
        contingency_depletion_velocity_monthly DOUBLE,
        forecasted_breach_month INTEGER
    );
    """)

    con.execute("""
    INSERT INTO cost_forecast_eac VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        CONTRACT_BASELINE_WHC["project_id"],
        8,                     # Month 8
        52380952.38,           # BAC
        28450000.00,           # BCWP
        30150000.00,           # ACWP
        0.9436,                # CPI = BCWP / ACWP
        55511818.00,           # EAC = BAC / CPI (Predicts S$511k breach of S$55M budget!)
        2619047.62,            # Contingency Original
        1850000.00,            # Contingency Depleted
        769047.62,             # Contingency Remaining
        231250.00,             # Contingency Depletion Velocity Monthly
        11                     # Forecasted breach at Month 11 (5 months before practical completion!)
    ])

    for pid, pdata in PROJECT_SCENARIOS.items():
        cf = pdata["cost_forecast_eac"]
        con.execute("""
        INSERT INTO cost_forecast_eac VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            pid, cf[0], cf[1], cf[2], cf[3], cf[4], cf[5], cf[6], cf[7], cf[8], cf[9], cf[10]
        ])

    # 3. Export to partitioned Parquet files for Approach 3 Cloud Storage Lakehouse
    parquet_dir = os.path.join(DATA_DIR, "parquet")
    os.makedirs(parquet_dir, exist_ok=True)
    
    tables = [
        "projects", "schedule_of_rates", "interim_claims", 
        "claim_items", "variation_orders", "site_safety_incidents", 
        "cost_forecast_eac"
    ]
    for tbl in tables:
        pq_path = os.path.join(parquet_dir, f"{tbl}.parquet")
        con.execute(f"COPY {tbl} TO '{pq_path}' (FORMAT PARQUET, COMPRESSION ZSTD);")
    print(f"✓ Exported {len(tables)} Parquet lakehouse tables to: data/parquet/")

    con.close()
    print("✓ Successfully populated DuckDB database: data/commercial_control.duckdb")

if __name__ == "__main__":
    print("=" * 70)
    print("ACIP S03: Seeding Commercial Control & Cost Intelligence Dataset")
    print("=" * 70)
    generate_database_and_json_files()
    print("=" * 70)
    print("Stage 1 Dataset Seeding Completed Successfully.")
    print("=" * 70)
