"""
ACIP S04: Automated Critical Path Method (CPM) Recalculation Service
Module: ACIP S04 - Agentic Progress & Delay Intelligence (Module Code: S04)
File: engine/cpm_recalculation_service.py

Increment 1B Service implementing:
1. Dynamic calendar registry parsing from calendars.parquet (weekend_days_json & statutory_holidays_json).
2. Fail-closed calendar resolution rejecting unknown calendar IDs without silent fallback.
3. Authoritative predecessor activity calendar default for relationship lags.
4. Continuous Fractional Day Offsets (Recommended Baseline) with configurable Fail-Closed Guardrail.
5. Exact constraint date matching for driving relationships across FS, SS, FF, and SF.
6. Dynamic critical path duration derivation without hardcoded date or duration fallbacks.
7. Atomic lakehouse snapshot publishing with commit manifests and rollback on fault.
"""

from datetime import date, datetime, time, timedelta
import json
import math
import os
from typing import Dict, List, Optional, Tuple, Any, Set
import pandas as pd

from engine.cpm_engine import (
    ScheduleNetwork,
    Activity,
    Relationship,
    CyclicDependencyError,
    MissingActivityError,
    InvalidRelationshipError,
)
from engine.data_validator import (
    atomic_publish_dataset,
    compute_file_sha256,
    ValidationError,
)


class CPMRecalculationError(Exception):
    """Base exception for CPM recalculation errors."""
    pass


class ParityMismatchError(CPMRecalculationError):
    """Raised when recalculated CPM metrics deviate from declared golden benchmarks."""
    pass


class FractionalLagUnsupportedError(CPMRecalculationError):
    """
    Raised when a relationship specifies a fractional lag and the discrete-workday
    guardrail (enforce_discrete_guardrail=True) is active.
    """
    pass


class UnresolvedCalendarError(CPMRecalculationError):
    """Raised when an activity or relationship references an undefined calendar ID."""
    pass


class MalformedCalendarConfigurationError(CPMRecalculationError):
    """
    Raised when a calendar definition in calendars.parquet contains malformed JSON,
    unrecognized day names, or unparseable ISO date strings (fail-closed policy).
    """
    pass


class DynamicCalendarRegistry:
    """
    Dynamic calendar evaluation registry parsing working-day rules, weekend sets,
    and statutory holidays directly from calendars.parquet.

    Precedence and Governance:
    - Precedence Level 1 (Authoritative): Governed Parquet lakehouse definitions (df_cal).
      Any calendar ID defined in calendars.parquet overrides built-in defaults.
      Malformed JSON, invalid day names, or unparseable dates in supplied definitions
      fail-closed immediately with MalformedCalendarConfigurationError.
    - Precedence Level 2 (Canonical Baselines): When allow_canonical_fallback=True,
      standard baseline calendars (CAL-STD-5D v2026.1, CAL-CONT-7D v2026.1,
      CAL-SGP-6D v2026.1-CANONICAL) are available if omitted from Parquet.
    - Unregistered / Unmapped calendars fail-closed with UnresolvedCalendarError.
    """

    def __init__(self, df_cal: Optional[pd.DataFrame] = None, allow_canonical_fallback: bool = True):
        self.calendars: Dict[str, Dict[str, Any]] = {}
        day_map = {
            "MONDAY": 0, "TUESDAY": 1, "WEDNESDAY": 2, "THURSDAY": 3,
            "FRIDAY": 4, "SATURDAY": 5, "SUNDAY": 6
        }

        # 1. Authoritative primary source: supplied DataFrame (calendars.parquet)
        if df_cal is not None and not df_cal.empty:
            for _, r in df_cal.iterrows():
                cid = str(r["calendar_id"]).strip()
                w_json = r.get("weekend_days_json")
                h_json = r.get("statutory_holidays_json")

                # Parse weekend days JSON (fail closed on null, missing, or malformed input - A3)
                if pd.isna(w_json) or w_json is None or (isinstance(w_json, str) and not w_json.strip()):
                    raise MalformedCalendarConfigurationError(
                        f"Calendar '{cid}' definition is incomplete: 'weekend_days_json' must be explicitly specified "
                        f"(e.g., '[]' for 7-day continuous or '[\"SATURDAY\", \"SUNDAY\"]' for 5-day). "
                        "Null or missing fields are not permitted in authoritative records."
                    )
                elif isinstance(w_json, str):
                    try:
                        w_list = json.loads(w_json)
                    except Exception as e:
                        raise MalformedCalendarConfigurationError(
                            f"Calendar '{cid}' has malformed weekend_days_json: {w_json} ({e})"
                        )
                elif isinstance(w_json, (list, tuple)):
                    w_list = list(w_json)
                else:
                    raise MalformedCalendarConfigurationError(
                        f"Calendar '{cid}' weekend_days_json must be JSON string or list, got {type(w_json)}"
                    )

                if not isinstance(w_list, list):
                    raise MalformedCalendarConfigurationError(
                        f"Calendar '{cid}' weekend_days_json must parse to a list, got {type(w_list)}"
                    )

                w_set = set()
                for d in w_list:
                    d_upper = str(d).strip().upper()
                    if d_upper not in day_map:
                        raise MalformedCalendarConfigurationError(
                            f"Calendar '{cid}' specifies unrecognized weekend day name: '{d}'"
                        )
                    w_set.add(day_map[d_upper])

                # Parse statutory holidays JSON (fail closed on null, missing, or malformed input - A3)
                if pd.isna(h_json) or h_json is None or (isinstance(h_json, str) and not h_json.strip()):
                    raise MalformedCalendarConfigurationError(
                        f"Calendar '{cid}' definition is incomplete: 'statutory_holidays_json' must be explicitly specified "
                        f"(e.g., '[]' for no holidays). Null or missing fields are not permitted in authoritative records."
                    )
                elif isinstance(h_json, str):
                    try:
                        h_list = json.loads(h_json)
                    except Exception as e:
                        raise MalformedCalendarConfigurationError(
                            f"Calendar '{cid}' has malformed statutory_holidays_json: {h_json} ({e})"
                        )
                elif isinstance(h_json, (list, tuple)):
                    h_list = list(h_json)
                else:
                    raise MalformedCalendarConfigurationError(
                        f"Calendar '{cid}' statutory_holidays_json must be JSON string or list, got {type(h_json)}"
                    )

                if not isinstance(h_list, list):
                    raise MalformedCalendarConfigurationError(
                        f"Calendar '{cid}' statutory_holidays_json must parse to a list, got {type(h_list)}"
                    )

                SG_HOLIDAY_SYMBOLIC_MAP = {
                    "SG_NEW_YEAR": date(2026, 1, 1),
                    "SG_CNY": date(2026, 2, 17),
                    "SG_HARI_RAYA": date(2026, 6, 17),
                    "SG_NATIONAL_DAY": date(2026, 8, 9),
                }

                h_set = set()
                for h in h_list:
                    if isinstance(h, str):
                        h_clean = h.strip()
                        if h_clean in SG_HOLIDAY_SYMBOLIC_MAP:
                            h_set.add(SG_HOLIDAY_SYMBOLIC_MAP[h_clean])
                        else:
                            try:
                                h_set.add(date.fromisoformat(h_clean))
                            except Exception as e:
                                raise MalformedCalendarConfigurationError(
                                    f"Calendar '{cid}' specifies unparseable ISO holiday date string: '{h}' ({e})"
                                )
                    elif isinstance(h, datetime):
                        h_set.add(h.date())
                    elif isinstance(h, date):
                        h_set.add(h)
                    else:
                        raise MalformedCalendarConfigurationError(
                            f"Calendar '{cid}' specifies unparseable holiday date of type {type(h)}"
                        )

                self.calendars[cid] = {
                    "weekend": w_set,
                    "holidays": h_set,
                    "name": str(r.get("calendar_name", cid)),
                    "source": "PARQUET_GOVERNED",
                }

        # 2. Canonical built-in baseline standards (precedence Level 2)
        if allow_canonical_fallback:
            if "CAL-STD-5D" not in self.calendars:
                self.calendars["CAL-STD-5D"] = {
                    "weekend": {5, 6},
                    "holidays": set(),
                    "name": "Canonical Standard 5-Day Workweek (v2026.1)",
                    "source": "CANONICAL_BUILTIN",
                }
            if "CAL-CONT-7D" not in self.calendars:
                self.calendars["CAL-CONT-7D"] = {
                    "weekend": set(),
                    "holidays": set(),
                    "name": "Canonical Continuous 7-Day Operations (v2026.1)",
                    "source": "CANONICAL_BUILTIN",
                }
            if "CAL-SGP-6D" not in self.calendars:
                from engine.cpm_engine import SG_PUBLIC_HOLIDAYS_2026
                self.calendars["CAL-SGP-6D"] = {
                    "weekend": {6},
                    "holidays": set(SG_PUBLIC_HOLIDAYS_2026),
                    "name": "Canonical Singapore 6-Day Workweek (MOM 2026 v2026.1)",
                    "source": "CANONICAL_BUILTIN",
                }

    def is_known(self, calendar_id: str) -> bool:
        return calendar_id in self.calendars

    def get_source(self, calendar_id: str) -> str:
        if calendar_id not in self.calendars:
            raise UnresolvedCalendarError(f"Calendar '{calendar_id}' is not registered.")
        return self.calendars[calendar_id].get("source", "UNKNOWN")

    def is_workday(self, d: date, calendar_id: str) -> bool:
        if calendar_id not in self.calendars:
            raise UnresolvedCalendarError(
                f"Calendar '{calendar_id}' is not registered in the authoritative calendar definitions. "
                "Fail-closed policy rejects unmapped calendar IDs."
            )
        cal = self.calendars[calendar_id]
        if d.weekday() in cal["weekend"]:
            return False
        if d in cal["holidays"]:
            return False
        return True

    def ensure_workday(self, d: date, calendar_id: str) -> date:
        cur = d
        while not self.is_workday(cur, calendar_id):
            cur += timedelta(days=1)
        return cur

    def next_workday(self, d: date, calendar_id: str) -> date:
        cur = d + timedelta(days=1)
        while not self.is_workday(cur, calendar_id):
            cur += timedelta(days=1)
        return cur

    def prev_workday(self, d: date, calendar_id: str) -> date:
        cur = d - timedelta(days=1)
        while not self.is_workday(cur, calendar_id):
            cur -= timedelta(days=1)
        return cur

    def add_workdays(self, start_date: date, days: int, calendar_id: str) -> date:
        cur = self.ensure_workday(start_date, calendar_id)
        if days == 0:
            return cur
        step = 1 if days > 0 else -1
        remaining = abs(days)
        while remaining > 0:
            cur += timedelta(days=step)
            if self.is_workday(cur, calendar_id):
                remaining -= 1
        return cur

    def subtract_workdays(self, end_date: date, days: int, calendar_id: str) -> date:
        return self.add_workdays(end_date, -days, calendar_id)

    def workdays_between(self, start_date: date, end_date: date, calendar_id: str) -> int:
        if start_date == end_date:
            return 0
        if start_date < end_date:
            count = 0
            cur = start_date + timedelta(days=1)
            while cur <= end_date:
                if self.is_workday(cur, calendar_id):
                    count += 1
                cur += timedelta(days=1)
            return count
        else:
            return -self.workdays_between(end_date, start_date, calendar_id)

    def compute_finish_time(
        self,
        start_date: date,
        start_offset: float,
        duration: float,
        calendar_id: str,
    ) -> Tuple[date, float]:
        """
        Computes activity early finish date and sub-day offset given start date, start offset,
        and workday duration under the activity's assigned calendar.
        """
        start_d = self.ensure_workday(start_date, calendar_id)
        if duration == 0:
            return (start_d, round(start_offset, 6))
        total_span = start_offset + duration
        k = int(math.floor(total_span + 1e-9))
        r = round(total_span - k, 6)
        if abs(r) < 1e-6 or abs(r - 1.0) < 1e-6:
            if abs(r - 1.0) < 1e-6:
                k += 1
            ef_date = self.add_workdays(start_d, k - 1, calendar_id)
            ef_offset = 0.0
        else:
            ef_date = self.add_workdays(start_d, k, calendar_id)
            ef_offset = r
        return (ef_date, ef_offset)

    def compute_start_time(
        self,
        finish_date: date,
        finish_offset: float,
        duration: float,
        calendar_id: str,
    ) -> Tuple[date, float]:
        """
        Computes activity late start date and sub-day offset given late finish date, finish offset,
        and workday duration under the activity's assigned calendar (backward pass).
        """
        finish_d = self.ensure_workday(finish_date, calendar_id)
        if duration == 0:
            return (finish_d, round(finish_offset, 6))
        eff_finish_off = 1.0 if abs(finish_offset) < 1e-6 else finish_offset
        net = eff_finish_off - duration
        k = int(math.floor(net + 1e-9))
        r = round(net - k, 6)
        if abs(r) < 1e-6 or abs(r - 1.0) < 1e-6:
            if abs(r - 1.0) < 1e-6:
                k += 1
            ls_date = self.add_workdays(finish_d, k, calendar_id)
            ls_offset = 0.0
        else:
            ls_date = self.add_workdays(finish_d, k, calendar_id)
            ls_offset = r
        return (ls_date, ls_offset)

    def evaluate_constraint_time(
        self,
        base_date: date,
        base_offset: float,
        lag: float,
        lag_calendar_id: str,
        target_calendar_id: str,
        is_finish_constraint: bool = False,
    ) -> Tuple[date, float]:
        """
        Applies relationship lag (positive or negative float) on lag_calendar_id,
        then aligns with target_calendar_id.
        """
        eff_base_off = base_offset
        net = eff_base_off + lag
        k = int(math.floor(net + 1e-9))
        r = round(net - k, 6)
        if abs(r) < 1e-6 or abs(r - 1.0) < 1e-6:
            if abs(r - 1.0) < 1e-6:
                k += 1
            target_d = self.add_workdays(base_date, k, lag_calendar_id)
            target_off = 0.0
        else:
            target_d = self.add_workdays(base_date, k, lag_calendar_id)
            target_off = r
        target_d = self.ensure_workday(target_d, target_calendar_id)
        return (target_d, target_off)

    def evaluate_backward_constraint_time(
        self,
        base_date: date,
        base_offset: float,
        lag: float,
        lag_calendar_id: str,
        target_calendar_id: str,
    ) -> Tuple[date, float]:
        """
        Applies relationship lag in reverse on lag_calendar_id for backward pass late finish calculation.
        """
        eff_base_off = base_offset
        net = eff_base_off - lag
        k = int(math.floor(net + 1e-9))
        r = round(net - k, 6)
        if abs(r) < 1e-6 or abs(r - 1.0) < 1e-6:
            if abs(r - 1.0) < 1e-6:
                k += 1
            target_d = self.subtract_workdays(self.add_workdays(base_date, k, lag_calendar_id), 1, target_calendar_id)
            target_off = 0.0
        else:
            target_d = self.add_workdays(base_date, k, lag_calendar_id)
            target_off = r
        target_d = self.ensure_workday(target_d, target_calendar_id)
        return (target_d, target_off)


class CPMRecalculationService:
    """
    Orchestrates automated CPM recalculation on ingested schedule lakehouse datasets
    supporting Fractional Day Offsets, Predecessor Lag Calendars, and Dynamic Calendars.
    """

    def __init__(self, default_calendar_id: str = "CAL-STD-5D"):
        self.default_calendar_id = default_calendar_id

    def load_network_from_parquet(
        self,
        parquet_dir: str,
        enforce_discrete_guardrail: bool = False,
    ) -> Tuple[ScheduleNetwork, date, Dict[str, pd.DataFrame], DynamicCalendarRegistry]:
        """
        Loads schedule tables from Parquet lakehouse directory and instantiates ScheduleNetwork.
        """
        ver_path = os.path.join(parquet_dir, "schedule_versions.parquet")
        act_path = os.path.join(parquet_dir, "schedule_activities.parquet")
        rel_path = os.path.join(parquet_dir, "schedule_relationships.parquet")

        if not os.path.exists(ver_path) or not os.path.exists(act_path) or not os.path.exists(rel_path):
            raise CPMRecalculationError(
                f"Missing required schedule parquet tables in directory: {parquet_dir}"
            )

        df_ver = pd.read_parquet(ver_path)
        df_act = pd.read_parquet(act_path)
        df_rel = pd.read_parquet(rel_path)

        # Load auxiliary tables if present
        aux_tables = {}
        for aux_name in ["calendars", "contract_parameters", "site_records", "site_record_activities", "delay_events", "delay_event_activities"]:
            p = os.path.join(parquet_dir, f"{aux_name}.parquet")
            if os.path.exists(p):
                aux_tables[aux_name] = pd.read_parquet(p)

        if df_ver.empty:
            raise CPMRecalculationError("schedule_versions table contains 0 records.")

        ver_row = df_ver.iloc[0]
        project_id = str(ver_row["project_id"])
        schedule_version = str(ver_row["schedule_version"])

        # Extract planned start date without fabricated fallbacks (R5)
        raw_start = ver_row.get("planned_start_date")
        if pd.isna(raw_start) or raw_start is None:
            raise CPMRecalculationError(
                f"Missing or unparseable planned_start_date in schedule_versions for project '{project_id}'."
            )

        if isinstance(raw_start, str):
            try:
                project_start = datetime.strptime(raw_start, "%Y-%m-%d").date()
            except ValueError:
                raise CPMRecalculationError(f"Unparseable date string '{raw_start}' in schedule_versions.")
        elif isinstance(raw_start, datetime):
            project_start = raw_start.date()
        elif isinstance(raw_start, date):
            project_start = raw_start
        else:
            raise CPMRecalculationError(f"Invalid date type '{type(raw_start)}' in schedule_versions.")

        # Build dynamic calendar registry from calendars.parquet (R3 & R6)
        df_cal = aux_tables.get("calendars")
        registry = DynamicCalendarRegistry(df_cal)

        network = ScheduleNetwork(project_id=project_id, schedule_version=schedule_version)

        # Add activities to network with calendar resolution check (R6)
        for _, r in df_act.iterrows():
            act_id = str(r["activity_id"]).strip()
            act_name = str(r.get("activity_name", act_id)).strip()
            durn = int(r["original_duration_days"])
            cal_id = str(r.get("calendar_id", self.default_calendar_id)).strip()
            wbs = str(r.get("wbs_code", "WHC.SUB")).strip()

            if not registry.is_known(cal_id):
                raise UnresolvedCalendarError(
                    f"Activity '{act_id}' references calendar '{cal_id}', which is not defined in calendars.parquet."
                )

            is_milestone = (durn == 0)
            m_type_raw = r.get("milestone_type")
            if m_type_raw is not None and not pd.isna(m_type_raw):
                m_type = str(m_type_raw).strip().upper()
            elif is_milestone:
                has_preds = (df_rel["successor_activity_id"] == act_id).any() if "successor_activity_id" in df_rel.columns else False
                m_type = "FINISH" if has_preds else "START"
            else:
                m_type = None

            act = Activity(
                activity_id=act_id,
                activity_name=act_name,
                duration_days=durn,
                calendar_id=cal_id,
                is_milestone=is_milestone,
                milestone_type=m_type,
                wbs_code=wbs,
            )
            network.add_activity(act)

        # Add relationships to network with lag calendar predecessor policy (R4) & fractional lag guardrail (R1)
        for _, r in df_rel.iterrows():
            pred = str(r["predecessor_activity_id"]).strip()
            succ = str(r["successor_activity_id"]).strip()
            rel_type = str(r.get("relationship_type", "FS")).strip()
            lag_raw = r.get("lag_days", 0)

            if lag_raw is not None and not pd.isna(lag_raw):
                lag_float = float(lag_raw)
            else:
                lag_float = 0.0

            if enforce_discrete_guardrail and not lag_float.is_integer():
                raise FractionalLagUnsupportedError(
                    f"Relationship '{pred}' -> '{succ}' specifies fractional lag of {lag_raw} workdays. "
                    "Fail-closed guardrail active for discrete-workday mandatory mode."
                )

            # R4: Authoritative default is predecessor activity calendar per ACIP policy
            lag_cal_raw = r.get("lag_calendar_id")
            if lag_cal_raw is not None and not pd.isna(lag_cal_raw):
                s_cal = str(lag_cal_raw).strip()
                lag_cal = s_cal if s_cal not in ("", "None", "nan") else None
            else:
                lag_cal = None

            if not lag_cal:
                pred_act_lookup = network.activities.get(pred)
                lag_cal = pred_act_lookup.calendar_id if pred_act_lookup else self.default_calendar_id

            if not registry.is_known(lag_cal):
                raise UnresolvedCalendarError(
                    f"Relationship '{pred}' -> '{succ}' references lag calendar '{lag_cal}', which is not defined in calendars.parquet."
                )

            # Use int for integer lags to preserve Gate 2 baseline behavior; float for fractional lags
            lag_val = int(lag_float) if lag_float.is_integer() else lag_float

            rel = Relationship(
                predecessor_id=pred,
                successor_id=succ,
                relationship_type=rel_type,
                lag_days=lag_val,
                lag_calendar_id=lag_cal,
            )
            network.add_relationship(rel)

        raw_tables = {
            "schedule_versions": df_ver,
            "schedule_activities": df_act,
            "schedule_relationships": df_rel,
            **aux_tables,
        }

        return network, project_start, raw_tables, registry

    def recalculate_and_update(
        self,
        parquet_dir: str,
        target_parquet_dir: Optional[str] = None,
        base_dir: Optional[str] = None,
        enforce_golden_parity: bool = True,
        enforce_discrete_guardrail: bool = False,
        simulate_interruption: bool = False,
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
        """
        Executes CPM recalculation on Parquet dataset, updates DataFrames, asserts parity,
        and publishes updated dataset atomically.
        """
        network, project_start, tables, registry = self.load_network_from_parquet(
            parquet_dir, enforce_discrete_guardrail=enforce_discrete_guardrail
        )

        order = network.topological_sort()

        # Check if fractional lags exist in network
        has_fractional_lags = any(
            isinstance(rel.lag_days, float) and not float(rel.lag_days).is_integer()
            for rel in network.relationships
        )

        act_offsets: Dict[str, Dict[str, float]] = {
            aid: {"es_offset": 0.0, "ef_offset": 0.0, "ls_offset": 0.0, "lf_offset": 0.0}
            for aid in network.activities
        }

        # Unified forward and backward pass with Dynamic Calendar Registry & Fractional Day Offsets
        # 1. FORWARD PASS with fractional workday offsets
        for act_id in order:
            act = network.activities[act_id]
            cal = act.calendar_id
            incoming = network._adj_in[act_id]

            if not incoming:
                act.early_start = registry.ensure_workday(project_start, cal)
                act_offsets[act_id]["es_offset"] = 0.0
                ef_date, ef_off = registry.compute_finish_time(act.early_start, 0.0, act.duration_days, cal)
                act.early_finish = ef_date
                act_offsets[act_id]["ef_offset"] = ef_off
            else:
                cand_starts = []  # tuple: (date, offset)
                cand_finishes = []  # tuple: (date, offset)

                for rel in incoming:
                    pred = network.activities[rel.predecessor_id]
                    pred_es_off = act_offsets[rel.predecessor_id]["es_offset"]
                    pred_ef_off = act_offsets[rel.predecessor_id]["ef_offset"]
                    lag_cal = rel.lag_calendar_id or pred.calendar_id
                    lag = float(rel.lag_days)

                    if rel.relationship_type == "FS":
                        if pred.is_milestone and pred.milestone_type == "START":
                            base_d = pred.early_start
                            base_off = pred_es_off
                        elif act.is_milestone and act.milestone_type == "FINISH":
                            base_d = pred.early_finish
                            base_off = pred_ef_off
                        elif abs(pred_ef_off) > 1e-6:
                            base_d = pred.early_finish
                            base_off = pred_ef_off
                        else:
                            base_d = registry.next_workday(pred.early_finish, lag_cal)
                            base_off = 0.0
                        c_date, c_off = registry.evaluate_constraint_time(
                            base_d, base_off, lag, lag_cal, cal, is_finish_constraint=False
                        )
                        cand_starts.append((c_date, c_off))

                    elif rel.relationship_type == "SS":
                        base_d = pred.early_start
                        base_off = pred_es_off
                        c_date, c_off = registry.evaluate_constraint_time(
                            base_d, base_off, lag, lag_cal, cal, is_finish_constraint=False
                        )
                        cand_starts.append((c_date, c_off))

                    elif rel.relationship_type == "FF":
                        if abs(pred_ef_off) > 1e-6:
                            base_d = pred.early_finish
                            base_off = pred_ef_off
                        else:
                            base_d = registry.next_workday(pred.early_finish, lag_cal)
                            base_off = 0.0
                        c_date, c_off = registry.evaluate_constraint_time(
                            base_d, base_off, lag, lag_cal, cal, is_finish_constraint=True
                        )
                        cand_finishes.append((c_date, c_off))
                        imp_s_date, imp_s_off = registry.compute_start_time(c_date, c_off, act.duration_days, cal)
                        cand_starts.append((imp_s_date, imp_s_off))

                    elif rel.relationship_type == "SF":
                        base_d = pred.early_start
                        base_off = pred_es_off
                        c_date, c_off = registry.evaluate_constraint_time(
                            base_d, base_off, lag, lag_cal, cal, is_finish_constraint=True
                        )
                        cand_finishes.append((c_date, c_off))
                        imp_s_date, imp_s_off = registry.compute_start_time(c_date, c_off, act.duration_days, cal)
                        cand_starts.append((imp_s_date, imp_s_off))

                # Pick latest candidate start (date, offset)
                cand_starts.sort(key=lambda x: (x[0], x[1]))
                best_start, best_start_off = cand_starts[-1]

                act.early_start = best_start
                act_offsets[act_id]["es_offset"] = best_start_off

                natural_ef, natural_ef_off = registry.compute_finish_time(
                    act.early_start, best_start_off, act.duration_days, cal
                )
                if cand_finishes:
                    cand_finishes.sort(key=lambda x: (x[0], x[1]))
                    best_fin, best_fin_off = cand_finishes[-1]
                    if (best_fin, best_fin_off) > (natural_ef, natural_ef_off):
                        natural_ef, natural_ef_off = best_fin, best_fin_off
                act.early_finish = natural_ef
                act_offsets[act_id]["ef_offset"] = natural_ef_off

        # Determine project finish and start
        term_finishes = [(a.early_finish, act_offsets[aid]["ef_offset"]) for aid, a in network.activities.items()]
        term_finishes.sort(key=lambda x: (x[0], x[1]))
        calc_finish, calc_finish_off = term_finishes[-1]
        calc_start = min(a.early_start for a in network.activities.values())

        # 2. BACKWARD PASS with fractional offsets
        for act_id in reversed(order):
            act = network.activities[act_id]
            cal = act.calendar_id
            outgoing = network._adj_out[act_id]

            if not outgoing:
                act.late_finish = calc_finish
                act_offsets[act_id]["lf_offset"] = calc_finish_off
                ls_date, ls_off = registry.compute_start_time(
                    act.late_finish, calc_finish_off, act.duration_days, cal
                )
                act.late_start = ls_date
                act_offsets[act_id]["ls_offset"] = ls_off
            else:
                cand_lfs = []
                for rel in outgoing:
                    succ = network.activities[rel.successor_id]
                    succ_ls_off = act_offsets[rel.successor_id]["ls_offset"]
                    succ_lf_off = act_offsets[rel.successor_id]["lf_offset"]
                    lag_cal = rel.lag_calendar_id or act.calendar_id
                    lag = float(rel.lag_days)

                    if rel.relationship_type == "FS":
                        base_d = succ.late_start
                        base_off = succ_ls_off
                        if act.is_milestone and act.milestone_type == "START":
                            c_lf, c_lf_off = registry.evaluate_constraint_time(
                                base_d, base_off, -lag, lag_cal, cal, is_finish_constraint=False
                            )
                        elif succ.is_milestone and succ.milestone_type == "FINISH":
                            c_lf, c_lf_off = registry.evaluate_constraint_time(
                                base_d, base_off, -lag, lag_cal, cal, is_finish_constraint=False
                            )
                        else:
                            c_lf, c_lf_off = registry.evaluate_backward_constraint_time(
                                base_d, base_off, lag, lag_cal, cal
                            )
                        cand_lfs.append((c_lf, c_lf_off))

                    elif rel.relationship_type == "SS":
                        base_d = succ.late_start
                        base_off = succ_ls_off
                        net = base_off - lag
                        k = int(math.floor(net + 1e-9))
                        r = round(net - k, 6)
                        if abs(r) < 1e-6 or abs(r - 1.0) < 1e-6:
                            if abs(r - 1.0) < 1e-6:
                                k += 1
                            target_ls = registry.add_workdays(base_d, k, lag_cal)
                            target_ls_off = 0.0
                        else:
                            target_ls = registry.add_workdays(base_d, k, lag_cal)
                            target_ls_off = r
                        target_ls = registry.ensure_workday(target_ls, cal)
                        imp_lf, imp_lf_off = registry.compute_finish_time(target_ls, target_ls_off, act.duration_days, cal)
                        cand_lfs.append((imp_lf, imp_lf_off))

                    elif rel.relationship_type == "FF":
                        base_d = succ.late_finish
                        base_off = succ_lf_off
                        net = base_off - lag
                        k = int(math.floor(net + 1e-9))
                        r = round(net - k, 6)
                        if abs(r) < 1e-6 or abs(r - 1.0) < 1e-6:
                            if abs(r - 1.0) < 1e-6:
                                k += 1
                            target_lf = registry.add_workdays(base_d, k, lag_cal)
                            target_lf_off = 0.0
                        else:
                            target_lf = registry.add_workdays(base_d, k, lag_cal)
                            target_lf_off = r
                        target_lf = registry.ensure_workday(target_lf, cal)
                        cand_lfs.append((target_lf, target_lf_off))

                    elif rel.relationship_type == "SF":
                        base_d = succ.late_finish
                        base_off = succ_lf_off
                        net = base_off - lag
                        k = int(math.floor(net + 1e-9))
                        r = round(net - k, 6)
                        if abs(r) < 1e-6 or abs(r - 1.0) < 1e-6:
                            if abs(r - 1.0) < 1e-6:
                                k += 1
                            target_ls = registry.add_workdays(base_d, k, lag_cal)
                            target_ls_off = 0.0
                        else:
                            target_ls = registry.add_workdays(base_d, k, lag_cal)
                            target_ls_off = r
                        target_ls = registry.ensure_workday(target_ls, cal)
                        imp_lf, imp_lf_off = registry.compute_finish_time(target_ls, target_ls_off, act.duration_days, cal)
                        cand_lfs.append((imp_lf, imp_lf_off))

                cand_lfs.sort(key=lambda x: (x[0], x[1]))
                best_lf, best_lf_off = cand_lfs[0]
                act.late_finish = best_lf
                act_offsets[act_id]["lf_offset"] = best_lf_off
                ls_date, ls_off = registry.compute_start_time(best_lf, best_lf_off, act.duration_days, cal)
                act.late_start = ls_date
                act_offsets[act_id]["ls_offset"] = ls_off

        # 3. FLOAT CALCULATION (exact continuous decimal float without ceiling padding)
        for act_id, act in network.activities.items():
            cal = act.calendar_id
            w_diff = registry.workdays_between(act.early_start, act.late_start, cal)
            off_diff = act_offsets[act_id]["ls_offset"] - act_offsets[act_id]["es_offset"]
            tf = float(w_diff) + float(off_diff)
            act.total_float_days = int(tf) if abs(tf - round(tf)) < 1e-5 else round(tf, 4)
            act.is_critical = (tf <= 1e-5)

            outgoing = network._adj_out[act_id]
            if not outgoing:
                act.free_float_days = act.total_float_days
            else:
                slacks = []
                for rel in outgoing:
                    succ = network.activities[rel.successor_id]
                    succ_cal = succ.calendar_id
                    lag = float(rel.lag_days)
                    if rel.relationship_type == "FS":
                        diff = float(registry.workdays_between(act.early_finish, succ.early_start, succ_cal)) - 1.0 - lag
                        diff += (act_offsets[rel.successor_id]["es_offset"] - act_offsets[act_id]["ef_offset"])
                        slacks.append(max(0.0, diff))
                    elif rel.relationship_type == "SS":
                        diff = float(registry.workdays_between(act.early_start, succ.early_start, succ_cal)) - lag
                        diff += (act_offsets[rel.successor_id]["es_offset"] - act_offsets[act_id]["es_offset"])
                        slacks.append(max(0.0, diff))
                    elif rel.relationship_type == "FF":
                        diff = float(registry.workdays_between(act.early_finish, succ.early_finish, succ_cal)) - lag
                        diff += (act_offsets[rel.successor_id]["ef_offset"] - act_offsets[act_id]["ef_offset"])
                        slacks.append(max(0.0, diff))
                    elif rel.relationship_type == "SF":
                        diff = float(registry.workdays_between(act.early_start, succ.early_finish, succ_cal)) - lag
                        diff += (act_offsets[rel.successor_id]["ef_offset"] - act_offsets[act_id]["es_offset"])
                        slacks.append(max(0.0, diff))
                ff = min(slacks) if slacks else 0.0
                act.free_float_days = int(ff) if abs(ff - round(ff)) < 1e-5 else round(ff, 4)

        df_act = tables["schedule_activities"].copy()
        df_ver = tables["schedule_versions"].copy()
        df_rel = tables["schedule_relationships"].copy()

        # Ensure float column types accommodate fractional float values
        if any(isinstance(a.total_float_days, float) or isinstance(a.free_float_days, float) for a in network.activities.values()):
            if "total_float_days" in df_act.columns:
                df_act["total_float_days"] = df_act["total_float_days"].astype(float)
            else:
                df_act["total_float_days"] = 0.0
            if "free_float_days" in df_act.columns:
                df_act["free_float_days"] = df_act["free_float_days"].astype(float)
            else:
                df_act["free_float_days"] = 0.0

        # Update schedule_activities DataFrame with recalculated CPM values & offsets
        for idx, row in df_act.iterrows():
            aid = row["activity_id"]
            if aid in network.activities:
                act = network.activities[aid]
                df_act.at[idx, "early_start_date"] = act.early_start
                df_act.at[idx, "early_finish_date"] = act.early_finish
                df_act.at[idx, "late_start_date"] = act.late_start
                df_act.at[idx, "late_finish_date"] = act.late_finish
                df_act.at[idx, "total_float_days"] = act.total_float_days
                df_act.at[idx, "free_float_days"] = act.free_float_days
                df_act.at[idx, "is_critical"] = act.is_critical
                df_act.at[idx, "driving_path_rank"] = 1 if act.is_critical else 2
                df_act.at[idx, "early_start_offset_days"] = act_offsets[aid]["es_offset"]
                df_act.at[idx, "early_finish_offset_days"] = act_offsets[aid]["ef_offset"]
                df_act.at[idx, "late_start_offset_days"] = act_offsets[aid]["ls_offset"]
                df_act.at[idx, "late_finish_offset_days"] = act_offsets[aid]["lf_offset"]

        # Update schedule_relationships DataFrame is_driving flag across FS, SS, FF, SF (R1 & R2)
        # Evaluates exact date AND continuous sub-day offset within floating epsilon (1e-5)
        for idx, row in df_rel.iterrows():
            pred_id = row["predecessor_activity_id"]
            succ_id = row["successor_activity_id"]
            rtype = row["relationship_type"]
            lag_raw = row.get("lag_days", 0)
            lag = float(lag_raw) if lag_raw is not None and not pd.isna(lag_raw) else 0.0

            pred_act = network.activities.get(pred_id)
            succ_act = network.activities.get(succ_id)

            if pred_act and succ_act:
                lag_cal_raw = row.get("lag_calendar_id")
                if lag_cal_raw is not None and not pd.isna(lag_cal_raw):
                    s_cal = str(lag_cal_raw).strip()
                    lag_cal = s_cal if s_cal not in ("", "None", "nan") else pred_act.calendar_id
                else:
                    lag_cal = pred_act.calendar_id

                pred_es_off = act_offsets[pred_id]["es_offset"]
                pred_ef_off = act_offsets[pred_id]["ef_offset"]
                succ_es_off = act_offsets[succ_id]["es_offset"]
                succ_ef_off = act_offsets[succ_id]["ef_offset"]

                if rtype == "FS":
                    if pred_act.is_milestone and pred_act.milestone_type == "START":
                        base_d = pred_act.early_start
                        base_off = pred_es_off
                    elif succ_act.is_milestone and succ_act.milestone_type == "FINISH":
                        base_d = pred_act.early_finish
                        base_off = pred_ef_off
                    elif abs(pred_ef_off) > 1e-6:
                        base_d = pred_act.early_finish
                        base_off = pred_ef_off
                    else:
                        base_d = registry.next_workday(pred_act.early_finish, lag_cal)
                        base_off = 0.0
                    c_date, c_off = registry.evaluate_constraint_time(
                        base_d, base_off, lag, lag_cal, succ_act.calendar_id, is_finish_constraint=False
                    )
                    is_drv = bool(succ_act.early_start == c_date and abs(succ_es_off - c_off) < 1e-5)

                elif rtype == "SS":
                    base_d = pred_act.early_start
                    base_off = pred_es_off
                    c_date, c_off = registry.evaluate_constraint_time(
                        base_d, base_off, lag, lag_cal, succ_act.calendar_id, is_finish_constraint=False
                    )
                    is_drv = bool(succ_act.early_start == c_date and abs(succ_es_off - c_off) < 1e-5)

                elif rtype == "FF":
                    if abs(pred_ef_off) > 1e-6:
                        base_d = pred_act.early_finish
                        base_off = pred_ef_off
                    else:
                        base_d = registry.next_workday(pred_act.early_finish, lag_cal)
                        base_off = 0.0
                    c_date, c_off = registry.evaluate_constraint_time(
                        base_d, base_off, lag, lag_cal, succ_act.calendar_id, is_finish_constraint=True
                    )
                    is_drv = bool(succ_act.early_finish == c_date and abs(succ_ef_off - c_off) < 1e-5)

                elif rtype == "SF":
                    base_d = pred_act.early_start
                    base_off = pred_es_off
                    c_date, c_off = registry.evaluate_constraint_time(
                        base_d, base_off, lag, lag_cal, succ_act.calendar_id, is_finish_constraint=True
                    )
                    is_drv = bool(succ_act.early_finish == c_date and abs(succ_ef_off - c_off) < 1e-5)

                else:
                    is_drv = False

                df_rel.at[idx, "is_driving"] = is_drv

        # Calculate critical path duration dynamically on governing project calendar basis (R5)
        cp_durn = registry.workdays_between(calc_start, calc_finish, self.default_calendar_id) + 1

        # Update schedule_versions DataFrame dynamically without hardcoded constants
        start_is_str = isinstance(df_ver["planned_start_date"].iloc[0], str) if "planned_start_date" in df_ver.columns and len(df_ver) > 0 else False
        df_ver.at[0, "planned_start_date"] = calc_start.isoformat() if start_is_str else calc_start
        df_ver.at[0, "planned_start_timestamp"] = datetime.combine(calc_start, time(8, 0, 0))
        df_ver.at[0, "planned_finish_date"] = calc_finish.isoformat() if start_is_str else calc_finish
        df_ver.at[0, "planned_finish_timestamp"] = datetime.combine(calc_finish, time(17, 0, 0))
        df_ver.at[0, "forecast_finish_date"] = calc_finish.isoformat() if start_is_str else calc_finish
        df_ver.at[0, "critical_path_duration_days"] = cp_durn

        updated_tables = {
            **tables,
            "schedule_versions": df_ver,
            "schedule_activities": df_act,
            "schedule_relationships": df_rel,
        }

        # Mathematical parity verification against golden benchmark
        parity_summary = {
            "project_id": network.project_id,
            "schedule_version": network.schedule_version,
            "calculated_start_date": calc_start.isoformat(),
            "calculated_finish_date": calc_finish.isoformat(),
            "critical_path_duration_days": cp_durn,
            "duration_calendar_basis": self.default_calendar_id,
            "total_activities": len(network.activities),
            "critical_activities_count": sum(1 for a in network.activities.values() if a.is_critical),
            "act_04_total_float_days": network.activities["ACT-04"].total_float_days if "ACT-04" in network.activities else None,
            "act_04_free_float_days": network.activities["ACT-04"].free_float_days if "ACT-04" in network.activities else None,
            "recalculation_timestamp": datetime.now().isoformat(),
        }

        if enforce_golden_parity and network.project_id == "PRJ-WHC-COM-001" and network.schedule_version == "BL-01":
            expected_finish = date(2026, 11, 19)
            if calc_finish != expected_finish:
                raise ParityMismatchError(
                    f"Golden benchmark project finish date mismatch: Expected {expected_finish}, got {calc_finish}"
                )
            if "ACT-04" in network.activities:
                act_04 = network.activities["ACT-04"]
                if act_04.total_float_days != 5 or act_04.free_float_days != 5:
                    raise ParityMismatchError(
                        f"ACT-04 float mismatch: Expected TF=5, FF=5, got TF={act_04.total_float_days}, FF={act_04.free_float_days}"
                    )

        # Atomic publish if target directory specified
        if target_parquet_dir:
            atomic_publish_dataset(
                tables=updated_tables,
                target_parquet_dir=target_parquet_dir,
                base_dir=base_dir,
                simulate_interruption=simulate_interruption,
            )

        return updated_tables, parity_summary
