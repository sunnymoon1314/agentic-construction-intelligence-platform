"""
ACIP S04: Controlled Time Impact Analysis (TIA) Fragnet Evaluator Engine
Module: ACIP S04 - Agentic Progress & Delay Intelligence (Module Code: S04)
File: engine/tia_evaluator.py

Increment 2 Service implementing:
1. Prospective and retrospective Time Impact Analysis (TIA) via sub-network (fragnet) insertion.
2. Unimpacted vs impacted CPM recalculation directly leveraging CPMRecalculationService.
3. Total float erosion and critical path migration tracking across all activities.
4. Society of Construction Law (SCL) Delay Protocol 2nd Edition Core Principle 10 concurrency attribution.
5. Singapore PSSCOC 2020 Clause 23.1 notice condition precedent window verification (28 days).
6. Liquidated damages (LD) financial exposure modeling under daily rate (S$ 15,000.00/day).
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
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
from engine.cpm_recalculation_service import (
    CPMRecalculationService,
    DynamicCalendarRegistry,
    CPMRecalculationError,
    UnresolvedCalendarError,
)


class TIAEvaluationError(Exception):
    """Base exception for Time Impact Analysis evaluation errors."""
    pass


class FragnetTopologyError(TIAEvaluationError):
    """Raised when fragnet relationships or insertion points are invalid or create cycles."""
    pass


class ContractNoticeError(TIAEvaluationError):
    """Raised when notice evaluation encounters malformed dates or missing contract parameters."""
    pass


@dataclass
class FragnetActivity:
    """Represents a delay event sub-activity inserted into the schedule network."""
    activity_id: str
    activity_name: str
    duration_days: float
    calendar_id: str = "CAL-STD-5D"
    predecessor_id: Optional[str] = None
    predecessor_rel: str = "FS"
    predecessor_lag: float = 0.0
    successor_id: Optional[str] = None
    successor_rel: str = "FS"
    successor_lag: float = 0.0
    wbs_code: str = "WHC.SUB.DLY"


@dataclass
class DelayEventDefinition:
    """Represents a formal contractual delay event under PSSCOC or FIDIC."""
    event_id: str
    event_title: str
    cause_category: str  # PHYSICAL_CONDITIONS, EMPLOYER_CHANGE, WEATHER, CONTRACTOR_DEFAULT
    risk_allocation: str  # EMPLOYER_RISK, CONTRACTOR_RISK, NEUTRAL_RISK
    event_start_date: date
    event_end_date: date
    notice_served_date: Optional[date] = None
    claimed_eot_days: float = 0.0
    claimed_prolongation_cost_sgd: float = 0.0
    fragnets: List[FragnetActivity] = field(default_factory=list)


@dataclass
class TIAResult:
    """Formal deterministic output of a Time Impact Analysis run."""
    event_id: str
    event_title: str
    risk_allocation: str
    unimpacted_completion_date: date
    impacted_completion_date: date
    net_critical_delay_workdays: float
    unimpacted_critical_path: List[str]
    impacted_critical_path: List[str]
    float_erosion: Dict[str, Dict[str, float]]
    concurrency_attribution: str  # EMPLOYER_DRIVEN_SOLE, CONTRACTOR_DRIVEN_SOLE, CONCURRENT_SPLIT, NEUTRAL_FORCE_MAJEURE
    candidate_eot_relief_days: float
    contractor_culpable_days: float
    candidate_prolongation_cost_status: str
    notice_compliance_status: str  # COMPLIANT, POTENTIALLY_TIME_BARRED_REQUIRES_LEGAL_DETERMINATION, UNASSESSED
    notice_elapsed_calendar_days: int
    daily_liquidated_damages_sgd: float
    liquidated_damages_exposure_sgd: float
    calculation_timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Converts result to a JSON-serializable dictionary."""
        return {
            "event_id": self.event_id,
            "event_title": self.event_title,
            "risk_allocation": self.risk_allocation,
            "unimpacted_completion_date": self.unimpacted_completion_date.isoformat(),
            "impacted_completion_date": self.impacted_completion_date.isoformat(),
            "net_critical_delay_workdays": self.net_critical_delay_workdays,
            "unimpacted_critical_path": self.unimpacted_critical_path,
            "impacted_critical_path": self.impacted_critical_path,
            "float_erosion": self.float_erosion,
            "concurrency_attribution": self.concurrency_attribution,
            "candidate_eot_relief_days": self.candidate_eot_relief_days,
            "contractor_culpable_days": self.contractor_culpable_days,
            "candidate_prolongation_cost_status": self.candidate_prolongation_cost_status,
            "notice_compliance_status": self.notice_compliance_status,
            "notice_elapsed_calendar_days": self.notice_elapsed_calendar_days,
            "daily_liquidated_damages_sgd": self.daily_liquidated_damages_sgd,
            "liquidated_damages_exposure_sgd": self.liquidated_damages_exposure_sgd,
            "calculation_timestamp": self.calculation_timestamp,
        }


class TIAEvaluator:
    """
    Forensic Schedule Delay & Time Impact Analysis (TIA) Engine.
    Executes mathematically bounded fragnet insertions and attribution calculations outside the LLM.
    """

    def __init__(
        self,
        cpm_service: Optional[CPMRecalculationService] = None,
        default_calendar_id: str = "CAL-STD-5D",
    ):
        self.cpm_service = cpm_service or CPMRecalculationService(default_calendar_id=default_calendar_id)
        self.default_calendar_id = default_calendar_id

    def clone_network(self, network: ScheduleNetwork) -> ScheduleNetwork:
        """Creates a deep copy of a ScheduleNetwork for isolated what-if simulation."""
        proj_id = getattr(network, "project_id", "PRJ-WHC-COM-001")
        sch_ver = getattr(network, "schedule_version", "BL-01")
        cloned = ScheduleNetwork(project_id=proj_id, schedule_version=sch_ver)
        for act_id, act in network.activities.items():
            new_act = Activity(
                activity_id=act.activity_id,
                activity_name=act.activity_name,
                duration_days=act.duration_days,
                calendar_id=act.calendar_id,
                is_milestone=act.is_milestone,
                milestone_type=act.milestone_type,
                wbs_code=act.wbs_code,
            )
            cloned.add_activity(new_act)

        for rel in network.relationships:
            new_rel = Relationship(
                predecessor_id=rel.predecessor_id,
                successor_id=rel.successor_id,
                relationship_type=rel.relationship_type,
                lag_days=rel.lag_days,
                lag_calendar_id=rel.lag_calendar_id,
            )
            cloned.add_relationship(new_rel)

        return cloned

    def run_cpm_pass(
        self,
        network: ScheduleNetwork,
        project_start: date,
        registry: DynamicCalendarRegistry,
    ) -> Tuple[date, List[str], Dict[str, Dict[str, Any]]]:
        """
        Executes a complete forward/backward CPM pass on network and extracts completion date,
        critical path activities, and per-activity schedule dates/float metrics.
        """
        order = network.topological_sort()
        act_metrics: Dict[str, Dict[str, Any]] = {}
        act_offsets: Dict[str, Dict[str, float]] = {
            aid: {"es_offset": 0.0, "ef_offset": 0.0, "ls_offset": 0.0, "lf_offset": 0.0}
            for aid in network.activities
        }

        # 1. Forward Pass
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
                cand_starts = []
                cand_finishes = []
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

                cand_starts.sort(key=lambda x: (x[0], x[1]), reverse=True)
                act.early_start, act_offsets[act_id]["es_offset"] = cand_starts[0]
                ef_date, ef_off = registry.compute_finish_time(
                    act.early_start, act_offsets[act_id]["es_offset"], act.duration_days, cal
                )
                act.early_finish = ef_date
                act_offsets[act_id]["ef_offset"] = ef_off

        term_finishes = [(a.early_finish, act_offsets[aid]["ef_offset"]) for aid, a in network.activities.items()]
        term_finishes.sort(key=lambda x: (x[0], x[1]))
        project_finish, proj_fin_off = term_finishes[-1]

        # 2. Backward Pass
        rev_order = list(reversed(order))
        for act_id in rev_order:
            act = network.activities[act_id]
            cal = act.calendar_id
            outgoing = network._adj_out[act_id]

            if not outgoing:
                act.late_finish = project_finish
                act_offsets[act_id]["lf_offset"] = proj_fin_off
                ls_date, ls_off = registry.compute_start_time(
                    project_finish, proj_fin_off, act.duration_days, cal
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

            # Float calculation
            tf_workdays = registry.workdays_between(act.early_start, act.late_start, cal)
            tf_exact = tf_workdays + (act_offsets[act_id]["ls_offset"] - act_offsets[act_id]["es_offset"])
            act.total_float_days = int(round(tf_exact)) if abs(tf_exact - round(tf_exact)) < 1e-6 else tf_exact
            act.is_critical = (abs(tf_exact) <= 1e-6) or (tf_exact < 0)

            act_metrics[act_id] = {
                "early_start": act.early_start,
                "early_finish": act.early_finish,
                "late_start": act.late_start,
                "late_finish": act.late_finish,
                "total_float": act.total_float_days,
                "is_critical": act.is_critical,
                "es_offset": act_offsets[act_id]["es_offset"],
                "ef_offset": act_offsets[act_id]["ef_offset"],
                "ls_offset": act_offsets[act_id]["ls_offset"],
                "lf_offset": act_offsets[act_id]["lf_offset"],
            }

        critical_path = [aid for aid in order if act_metrics[aid]["is_critical"]]
        return project_finish, critical_path, act_metrics

    def evaluate_psscoc_notice(
        self,
        event_start_date: date,
        notice_served_date: Optional[date],
        notice_window_days: int = 28,
        is_contract_verified: bool = False,
    ) -> Tuple[str, int]:
        """
        Evaluates Singapore PSSCOC 2020 Clause 23.1 notice condition precedent window.
        Returns: (notice_compliance_status, elapsed_calendar_days)
        """
        if not is_contract_verified:
            elapsed = (notice_served_date - event_start_date).days if notice_served_date else 0
            return ("UNASSESSED", elapsed)

        if not notice_served_date:
            return ("POTENTIALLY_TIME_BARRED_REQUIRES_LEGAL_DETERMINATION", 999)

        elapsed = (notice_served_date - event_start_date).days
        if elapsed <= notice_window_days:
            return ("COMPLIANT", elapsed)
        else:
            return ("POTENTIALLY_TIME_BARRED_REQUIRES_LEGAL_DETERMINATION", elapsed)

    def evaluate_fragnet_impact(
        self,
        base_network: ScheduleNetwork,
        project_start: date,
        registry: DynamicCalendarRegistry,
        event: DelayEventDefinition,
        daily_ld_rate_sgd: float = 15000.0,
        notice_window_days: int = 28,
        is_contract_verified: bool = False,
    ) -> TIAResult:
        """
        Executes a deterministic Time Impact Analysis by cloning the base network,
        inserting fragnet sub-activities, recalculating forward/backward passes,
        and attributing critical path variance under SCL Core Principle 10.
        """
        # 1. Unimpacted Base Run
        unimp_net = self.clone_network(base_network)
        unimp_fin, unimp_cp, unimp_metrics = self.run_cpm_pass(unimp_net, project_start, registry)

        # 2. Build Impacted Network by Injecting Fragnets
        imp_net = self.clone_network(base_network)
        for frag in event.fragnets:
            # Validate calendar
            if not registry.is_known(frag.calendar_id):
                raise UnresolvedCalendarError(
                    f"Fragnet activity '{frag.activity_id}' references unknown calendar '{frag.calendar_id}'."
                )

            # Insert Activity
            act = Activity(
                activity_id=frag.activity_id,
                activity_name=frag.activity_name,
                duration_days=int(frag.duration_days) if float(frag.duration_days).is_integer() else frag.duration_days,
                calendar_id=frag.calendar_id,
                wbs_code=frag.wbs_code,
            )
            imp_net.add_activity(act)

            # Insert Predecessor Link
            if frag.predecessor_id:
                if frag.predecessor_id not in imp_net.activities:
                    raise FragnetTopologyError(
                        f"Fragnet predecessor '{frag.predecessor_id}' does not exist in network."
                    )
                rel_in = Relationship(
                    predecessor_id=frag.predecessor_id,
                    successor_id=frag.activity_id,
                    relationship_type=frag.predecessor_rel,
                    lag_days=int(frag.predecessor_lag) if float(frag.predecessor_lag).is_integer() else frag.predecessor_lag,
                    lag_calendar_id=frag.calendar_id,
                )
                imp_net.add_relationship(rel_in)

            # Insert Successor Link
            if frag.successor_id:
                if frag.successor_id not in imp_net.activities:
                    raise FragnetTopologyError(
                        f"Fragnet successor '{frag.successor_id}' does not exist in network."
                    )
                rel_out = Relationship(
                    predecessor_id=frag.activity_id,
                    successor_id=frag.successor_id,
                    relationship_type=frag.successor_rel,
                    lag_days=int(frag.successor_lag) if float(frag.successor_lag).is_integer() else frag.successor_lag,
                    lag_calendar_id=frag.calendar_id,
                )
                imp_net.add_relationship(rel_out)

        # 3. Impacted Run
        imp_fin, imp_cp, imp_metrics = self.run_cpm_pass(imp_net, project_start, registry)

        # 4. Net Delay Workdays
        proj_cal = self.default_calendar_id
        if imp_fin > unimp_fin:
            net_delay_workdays = float(registry.workdays_between(unimp_fin, imp_fin, proj_cal))
        else:
            net_delay_workdays = 0.0

        # 5. Total Float Erosion
        float_erosion: Dict[str, Dict[str, float]] = {}
        for aid in base_network.activities:
            tf_before = float(unimp_metrics[aid]["total_float"])
            tf_after = float(imp_metrics[aid]["total_float"]) if aid in imp_metrics else tf_before
            float_consumed = max(0.0, tf_before - tf_after)
            float_erosion[aid] = {
                "total_float_before": tf_before,
                "total_float_after": tf_after,
                "float_consumed": float_consumed,
            }

        # 6. Notice Window Evaluation (PSSCOC 23.1)
        notice_status, elapsed_days = self.evaluate_psscoc_notice(
            event_start_date=event.event_start_date,
            notice_served_date=event.notice_served_date,
            notice_window_days=notice_window_days,
            is_contract_verified=is_contract_verified,
        )

        # 7. SCL Delay Protocol Core Principle 10 Concurrency Attribution & LD Assessment
        risk = event.risk_allocation.upper()
        if risk in ("EMPLOYER_RISK", "EMPLOYER_COMPENSABLE", "EMPLOYER"):
            concurrency = "EMPLOYER_DRIVEN_SOLE"
            candidate_eot = net_delay_workdays
            culpable_days = 0.0
            prolongation_status = "COMPENSABLE_SUBJECT_TO_PROOF"
        elif risk in ("CONTRACTOR_RISK", "CONTRACTOR_CULPABLE", "CONTRACTOR"):
            concurrency = "CONTRACTOR_DRIVEN_SOLE"
            candidate_eot = 0.0
            culpable_days = net_delay_workdays
            prolongation_status = "NON_COMPENSABLE"
        elif risk in ("NEUTRAL_RISK", "NEUTRAL_FORCE_MAJEURE", "FORCE_MAJEURE", "NEUTRAL"):
            concurrency = "NEUTRAL_FORCE_MAJEURE"
            candidate_eot = net_delay_workdays
            culpable_days = 0.0
            prolongation_status = "NON_COMPENSABLE_RELIEF_FROM_LD_ONLY"
        elif risk in ("CONCURRENT_SPLIT", "CONCURRENT"):
            concurrency = "CONCURRENT_SPLIT"
            candidate_eot = net_delay_workdays
            culpable_days = 0.0
            prolongation_status = "REQUIRES_SO_DETERMINATION"
        else:
            concurrency = "UNCLASSIFIED_RISK"
            candidate_eot = 0.0
            culpable_days = net_delay_workdays
            prolongation_status = "REQUIRES_SO_DETERMINATION"

        ld_exposure = culpable_days * daily_ld_rate_sgd

        return TIAResult(
            event_id=event.event_id,
            event_title=event.event_title,
            risk_allocation=event.risk_allocation,
            unimpacted_completion_date=unimp_fin,
            impacted_completion_date=imp_fin,
            net_critical_delay_workdays=net_delay_workdays,
            unimpacted_critical_path=unimp_cp,
            impacted_critical_path=imp_cp,
            float_erosion=float_erosion,
            concurrency_attribution=concurrency,
            candidate_eot_relief_days=candidate_eot,
            contractor_culpable_days=culpable_days,
            candidate_prolongation_cost_status=prolongation_status,
            notice_compliance_status=notice_status,
            notice_elapsed_calendar_days=elapsed_days,
            daily_liquidated_damages_sgd=daily_ld_rate_sgd,
            liquidated_damages_exposure_sgd=ld_exposure,
            calculation_timestamp=datetime.now().isoformat(),
        )

    def evaluate_parquet_delay_event(
        self,
        parquet_dir: str,
        event_id: str,
    ) -> TIAResult:
        """
        Loads base schedule, calendars, and delay event definitions from the Parquet lakehouse,
        constructs the fragnet model, and executes TIA evaluation.
        """
        # Load schedule network
        network, proj_start, tables, registry = self.cpm_service.load_network_from_parquet(parquet_dir)

        # Load delay events & activities
        df_dly = tables.get("delay_events")
        df_dly_act = tables.get("delay_event_activities")
        df_contract = tables.get("contract_parameters")

        if df_dly is None or df_dly_act is None:
            raise TIAEvaluationError(
                f"Missing delay_events or delay_event_activities tables in {parquet_dir}."
            )

        event_rows = df_dly[df_dly["event_id"] == event_id]
        if event_rows.empty:
            raise TIAEvaluationError(f"Delay event ID '{event_id}' not found in delay_events.parquet.")

        erow = event_rows.iloc[0]
        event_title = str(erow.get("event_title", "Unspecified Delay Event"))
        cause_cat = str(erow.get("cause_category", "PHYSICAL_CONDITIONS"))
        risk_alloc = str(erow.get("risk_allocation", "EMPLOYER_RISK"))
        ev_start = erow["event_start_date"]
        ev_end = erow["event_end_date"]
        ev_start_d = ev_start if isinstance(ev_start, date) else date.fromisoformat(str(ev_start)[:10])
        ev_end_d = ev_end if isinstance(ev_end, date) else date.fromisoformat(str(ev_end)[:10])

        notice_raw = erow.get("notice_served_date")
        if notice_raw is not None and not pd.isna(notice_raw):
            notice_d = notice_raw if isinstance(notice_raw, date) else date.fromisoformat(str(notice_raw)[:10])
        else:
            notice_d = None

        # Contract parameters (Fail-Closed Policy: Finding 1)
        daily_ld = 15000.0
        notice_win = 28
        is_verified = False
        if df_contract is not None and not df_contract.empty:
            crow = df_contract.iloc[0]
            daily_ld = float(crow.get("daily_liquidated_damages_rate_sgd", 15000.0))
            notice_win = int(crow.get("delay_notice_period_days", 28))
            if "verified_against_signed_contract" in crow and not pd.isna(crow["verified_against_signed_contract"]):
                raw_val = crow["verified_against_signed_contract"]
                if isinstance(raw_val, (bool,)):
                    is_verified = bool(raw_val)
                elif str(raw_val).strip().lower() == "true":
                    is_verified = True
                else:
                    is_verified = False
            else:
                is_verified = False
        else:
            is_verified = False

        # Build fragnets from delay_event_activities
        act_rows = df_dly_act[df_dly_act["event_id"] == event_id]
        fragnets: List[FragnetActivity] = []

        for idx, arow in act_rows.iterrows():
            target_act_id = str(arow["activity_id"]).strip()
            delay_impact_workdays = float(arow.get("delay_impact_workdays", 0.0))
            frag_id = f"FRAG-{event_id}-{idx+1}"
            frag_name = f"Fragnet Delay on {target_act_id} ({event_title})"

            # Tie fragnet as FS successor to affected activity, and FS predecessor to target's successors
            target_succs = list(network._adj_out.get(target_act_id, []))
            target_succ_id = target_succs[0].successor_id if target_succs else None

            fragnets.append(
                FragnetActivity(
                    activity_id=frag_id,
                    activity_name=frag_name,
                    duration_days=delay_impact_workdays,
                    calendar_id=network.activities[target_act_id].calendar_id if target_act_id in network.activities else self.default_calendar_id,
                    predecessor_id=target_act_id,
                    predecessor_rel="FS",
                    predecessor_lag=0.0,
                    successor_id=target_succ_id,
                    successor_rel="FS",
                    successor_lag=0.0,
                )
            )

        event_def = DelayEventDefinition(
            event_id=event_id,
            event_title=event_title,
            cause_category=cause_cat,
            risk_allocation=risk_alloc,
            event_start_date=ev_start_d,
            event_end_date=ev_end_d,
            notice_served_date=notice_d,
            fragnets=fragnets,
        )

        return self.evaluate_fragnet_impact(
            base_network=network,
            project_start=proj_start,
            registry=registry,
            event=event_def,
            daily_ld_rate_sgd=daily_ld,
            notice_window_days=notice_win,
            is_contract_verified=is_verified,
        )
