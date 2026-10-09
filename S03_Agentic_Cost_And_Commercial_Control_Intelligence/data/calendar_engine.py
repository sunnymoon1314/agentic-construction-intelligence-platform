#!/usr/bin/env python3
"""
Multi-Jurisdiction Statutory Calendar Engine for ACIP S03
Module: S03_Agentic_Cost_And_Commercial_Control_Intelligence
File: data/calendar_engine.py

Supports:
1. Air-Gapped / Offline Local Calendar Lookup (data/statutory_calendars.json)
2. Dynamic Live Public REST API Ingestion (https://date.nager.at/api/v3/PublicHolidays)
3. Configurable Custom Non-Working Days & Country Presets (SG, MY, UK, AU, etc.)
"""

import os
import json
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta
from typing import Set, Optional, Dict, Any

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CALENDARS_PATH = os.path.join(DATA_DIR, "statutory_calendars.json")

class StatutoryCalendarEngine:
    """Computes statutory response deadlines across multiple national jurisdictions."""

    def __init__(self, fallback_to_api: bool = True):
        self.fallback_to_api = fallback_to_api
        self.registry = self._load_local_registry()

    def _load_local_registry(self) -> Dict[str, Any]:
        """Loads the air-gapped local statutory calendar file."""
        if os.path.exists(CALENDARS_PATH):
            with open(CALENDARS_PATH, "r") as f:
                return json.load(f)
        return {"jurisdictions": {}}

    def fetch_live_holidays_from_api(self, country_code: str, year: int) -> Set[date]:
        """Fetches gazetted public holidays dynamically via standard public REST API."""
        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code.upper()}"
        holidays_set: Set[date] = set()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ACIP-Statutory-Calendar-Engine/1.0"})
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    payload = json.loads(response.read().decode("utf-8"))
                    for item in payload:
                        holidays_set.add(datetime.strptime(item["date"], "%Y-%m-%d").date())
        except (urllib.error.URLError, Exception):
            # Gracefully fail over to local registry in air-gapped / offline mode
            pass
        return holidays_set

    def get_public_holidays(self, country_code: str, year: int) -> Set[date]:
        """Returns public holidays for the specified country and year."""
        country_code = country_code.upper()
        holidays: Set[date] = set()

        # 1. Try local registry first (fast & offline)
        jurisdictions = self.registry.get("jurisdictions", {})
        if country_code in jurisdictions:
            j_data = jurisdictions[country_code]
            holiday_list = j_data.get(f"public_holidays_{year}", [])
            for item in holiday_list:
                holidays.add(datetime.strptime(item["date"], "%Y-%m-%d").date())

        # 2. If year not cached or empty, try live REST API if enabled
        if not holidays and self.fallback_to_api:
            live_holidays = self.fetch_live_holidays_from_api(country_code, year)
            if live_holidays:
                holidays.update(live_holidays)

        return holidays

    def calculate_statutory_deadline(
        self,
        date_served: date,
        contract_days: int = 14,
        jurisdiction: str = "SG",
        custom_non_working_days: Optional[Set[date]] = None
    ) -> Dict[str, Any]:
        """
        Computes statutory response deadline accounting for statutory caps,
        national public holidays, and statutory non-working weekend days.
        """
        jurisdiction = jurisdiction.upper()
        jurisdictions = self.registry.get("jurisdictions", {})
        j_data = jurisdictions.get(jurisdiction, {})

        # Default cap (e.g. 14 days in SG, 10 days in MY, 10 in AU)
        statutory_cap = j_data.get("default_payment_response_days_cap", 14)
        effective_days = min(contract_days, statutory_cap)

        # Weekend days to omit (e.g. SG omits Sunday [6], UK/MY/AU omit Saturday [5] and Sunday [6])
        omitted_weekdays = set(j_data.get("weekend_days_omitted", [6]))

        holidays = self.get_public_holidays(jurisdiction, date_served.year)
        if custom_non_working_days:
            holidays.update(custom_non_working_days)

        current_date = date_served
        counted_days = 0
        skipped_dates = []

        while counted_days < effective_days:
            current_date += timedelta(days=1)
            is_weekend = current_date.weekday() in omitted_weekdays
            is_holiday = current_date in holidays

            if is_weekend or is_holiday:
                skipped_dates.append({
                    "date": str(current_date),
                    "reason": "STATUTORY_WEEKEND" if is_weekend else "PUBLIC_HOLIDAY"
                })
            else:
                counted_days += 1

        return {
            "date_served": str(date_served),
            "contract_response_days": contract_days,
            "statutory_cap_days": statutory_cap,
            "effective_statutory_days": effective_days,
            "statutory_deadline": str(current_date),
            "jurisdiction": jurisdiction,
            "statutory_act": j_data.get("statutory_act", "Security of Payment Act"),
            "days_skipped_count": len(skipped_dates),
            "skipped_dates": skipped_dates
        }

if __name__ == "__main__":
    engine = StatutoryCalendarEngine()
    test_date = date(2026, 10, 1)
    
    # Singapore SOPA test
    sg_res = engine.calculate_statutory_deadline(test_date, contract_days=21, jurisdiction="SG")
    print(f"Singapore SOPA Deadline for claim served {test_date}: {sg_res['statutory_deadline']} (Cap: {sg_res['effective_statutory_days']} days)")

    # Malaysia CIPAA test
    my_res = engine.calculate_statutory_deadline(test_date, contract_days=14, jurisdiction="MY")
    print(f"Malaysia CIPAA Deadline for claim served {test_date}: {my_res['statutory_deadline']} (Cap: {my_res['effective_statutory_days']} days)")

    # UK Construction Act test
    uk_res = engine.calculate_statutory_deadline(test_date, contract_days=14, jurisdiction="UK")
    print(f"UK HGCRA Deadline for claim served {test_date}: {uk_res['statutory_deadline']} (Cap: {uk_res['effective_statutory_days']} days)")
