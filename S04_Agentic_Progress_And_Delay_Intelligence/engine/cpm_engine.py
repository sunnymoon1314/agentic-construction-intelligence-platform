"""
ACIP S04: Deterministic Critical Path Method (CPM) Calculation Engine
Module: ACIP S04 - Agentic Progress & Delay Intelligence
File: engine/cpm_engine.py

Mathematical implementation of:
1. Discrete-day boundary CPM forward pass and backward pass
2. Relationship types: Finish-to-Start (FS), Start-to-Start (SS),
   Finish-to-Finish (FF), Start-to-Finish (SF) with calendar-aware lags
3. Multi-calendar support (CAL-STD-5D, CAL-SGP-6D, CAL-CONT-7D)
4. Total Float, Free Float, and Critical Path (TF <= 0) identification
5. Milestones (Start Milestone D=0, Finish Milestone D=0)
6. DAG topological sorting and cycle detection via Kahn's algorithm
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Set, Tuple


class CyclicDependencyError(Exception):
    """Raised when the schedule relationship network contains cycles."""
    pass


class InvalidRelationshipError(Exception):
    """Raised when relationship definitions are malformed or duplicate."""
    pass


class MissingActivityError(Exception):
    """Raised when a predecessor or successor activity ID is missing."""
    pass


# Singapore gazetted public holidays for 2026 (illustrative benchmark calendar)
SG_PUBLIC_HOLIDAYS_2026: Set[date] = {
    date(2026, 1, 1),   # New Year's Day
    date(2026, 2, 17),  # Chinese New Year Day 1
    date(2026, 2, 18),  # Chinese New Year Day 2
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 1),   # Labour Day
    date(2026, 5, 31),  # Vesak Day
    date(2026, 6, 1),   # Vesak Day (Observed)
    date(2026, 6, 17),  # Hari Raya Haji
    date(2026, 8, 9),   # National Day
    date(2026, 8, 10),  # National Day (Observed)
    date(2026, 11, 8),  # Deepavali
    date(2026, 11, 9),  # Deepavali (Observed)
    date(2026, 12, 25), # Christmas Day
}


def is_workday(d: date, calendar_id: str) -> bool:
    """Check if date d is a working day under the given calendar."""
    weekday = d.weekday()  # Mon=0, Tue=1, ..., Sat=5, Sun=6
    if calendar_id == "CAL-STD-5D":
        return weekday < 5
    elif calendar_id == "CAL-SGP-6D":
        if weekday == 6:  # Sunday
            return False
        return d not in SG_PUBLIC_HOLIDAYS_2026
    elif calendar_id == "CAL-CONT-7D":
        return True
    else:
        # Default fallback to 5-day standard
        return weekday < 5


def next_workday(d: date, calendar_id: str) -> date:
    """Return the earliest working day strictly after date d."""
    cur = d + timedelta(days=1)
    while not is_workday(cur, calendar_id):
        cur += timedelta(days=1)
    return cur


def prev_workday(d: date, calendar_id: str) -> date:
    """Return the latest working day strictly before date d."""
    cur = d - timedelta(days=1)
    while not is_workday(cur, calendar_id):
        cur -= timedelta(days=1)
    return cur


def ensure_workday(d: date, calendar_id: str) -> date:
    """If d is a workday, return d; otherwise return the next workday."""
    cur = d
    while not is_workday(cur, calendar_id):
        cur += timedelta(days=1)
    return cur


def add_workdays(start_date: date, days: int, calendar_id: str) -> date:
    """Add working days to a date. If days=0, returns start_date if workday or next workday."""
    cur = ensure_workday(start_date, calendar_id)
    if days == 0:
        return cur
    step = 1 if days > 0 else -1
    remaining = abs(days)
    while remaining > 0:
        cur += timedelta(days=step)
        if is_workday(cur, calendar_id):
            remaining -= 1
    return cur


def subtract_workdays(end_date: date, days: int, calendar_id: str) -> date:
    """Subtract working days from a date."""
    return add_workdays(end_date, -days, calendar_id)


def workdays_between(start_date: date, end_date: date, calendar_id: str) -> int:
    """
    Count the number of working days between start_date and end_date.
    If end_date >= start_date, returns positive count.
    If end_date < start_date, returns negative count.
    """
    if start_date == end_date:
        return 0
    if start_date < end_date:
        count = 0
        cur = start_date + timedelta(days=1)
        while cur <= end_date:
            if is_workday(cur, calendar_id):
                count += 1
            cur += timedelta(days=1)
        return count
    else:
        return -workdays_between(end_date, start_date, calendar_id)


@dataclass
class Activity:
    activity_id: str
    activity_name: str
    duration_days: int
    calendar_id: str = "CAL-STD-5D"
    is_milestone: bool = False
    milestone_type: Optional[str] = None  # "START" or "FINISH"
    wbs_code: str = "WBS.01"
    
    # Calculated CPM fields
    early_start: Optional[date] = None
    early_finish: Optional[date] = None
    late_start: Optional[date] = None
    late_finish: Optional[date] = None
    total_float_days: Optional[int] = None
    free_float_days: Optional[int] = None
    is_critical: bool = False


@dataclass
class Relationship:
    predecessor_id: str
    successor_id: str
    relationship_type: str = "FS"  # "FS", "SS", "FF", "SF"
    lag_days: int = 0
    lag_calendar_id: Optional[str] = None
    is_driving: bool = False


class ScheduleNetwork:
    """Represents a project CPM schedule network."""
    
    def __init__(self, project_id: str, schedule_version: str):
        self.project_id = project_id
        self.schedule_version = schedule_version
        self.activities: Dict[str, Activity] = {}
        self.relationships: List[Relationship] = []
        self._adj_out: Dict[str, List[Relationship]] = {}
        self._adj_in: Dict[str, List[Relationship]] = {}

    def add_activity(self, activity: Activity) -> None:
        self.activities[activity.activity_id] = activity
        self._adj_out[activity.activity_id] = []
        self._adj_in[activity.activity_id] = []

    def add_relationship(self, rel: Relationship) -> None:
        if rel.predecessor_id not in self.activities:
            raise MissingActivityError(f"Predecessor activity '{rel.predecessor_id}' does not exist.")
        if rel.successor_id not in self.activities:
            raise MissingActivityError(f"Successor activity '{rel.successor_id}' does not exist.")
        
        # Check duplicate link
        for existing in self._adj_out[rel.predecessor_id]:
            if existing.successor_id == rel.successor_id and existing.relationship_type == rel.relationship_type:
                raise InvalidRelationshipError(
                    f"Duplicate relationship: {rel.predecessor_id} -> {rel.successor_id} ({rel.relationship_type})"
                )
        
        if not rel.lag_calendar_id:
            rel.lag_calendar_id = self.activities[rel.successor_id].calendar_id
            
        self.relationships.append(rel)
        self._adj_out[rel.predecessor_id].append(rel)
        self._adj_in[rel.successor_id].append(rel)

    def topological_sort(self) -> List[str]:
        """Kahn's algorithm for topological sorting and cycle detection."""
        in_degree: Dict[str, int] = {act_id: 0 for act_id in self.activities}
        for rel in self.relationships:
            in_degree[rel.successor_id] += 1
            
        queue: List[str] = [act_id for act_id, deg in in_degree.items() if deg == 0]
        order: List[str] = []
        
        while queue:
            # Deterministic sort by activity_id to ensure reproducible tie-breaking
            queue.sort()
            node = queue.pop(0)
            order.append(node)
            for rel in self._adj_out[node]:
                in_degree[rel.successor_id] -= 1
                if in_degree[rel.successor_id] == 0:
                    queue.append(rel.successor_id)
                    
        if len(order) != len(self.activities):
            cycle_nodes = [act_id for act_id, deg in in_degree.items() if deg > 0]
            raise CyclicDependencyError(
                f"Schedule network contains a circular dependency involving activities: {cycle_nodes}"
            )
        return order

    def calculate_cpm(self, project_start_date: date) -> Tuple[date, date]:
        """
        Executes deterministic forward and backward pass.
        Returns (project_early_start, project_early_finish).
        """
        order = self.topological_sort()
        
        # ----------------------------------------------------
        # 1. FORWARD PASS
        # ----------------------------------------------------
        for act_id in order:
            act = self.activities[act_id]
            cal = act.calendar_id
            incoming = self._adj_in[act_id]
            
            if not incoming:
                # No predecessors: start at project start
                act.early_start = ensure_workday(project_start_date, cal)
                if act.is_milestone and act.duration_days == 0:
                    act.early_finish = act.early_start
                else:
                    act.early_finish = add_workdays(act.early_start, act.duration_days - 1, cal)
            else:
                es_candidates: List[date] = []
                ef_candidates: List[date] = []
                
                for rel in incoming:
                    pred = self.activities[rel.predecessor_id]
                    lag_cal = rel.lag_calendar_id or cal
                    
                    if rel.relationship_type == "FS":
                        if pred.is_milestone and pred.milestone_type == "START":
                            # Predecessor is Start Milestone: link acts from milestone date
                            base_start = pred.early_start
                            es_cand = add_workdays(base_start, rel.lag_days, lag_cal)
                        elif act.is_milestone and act.milestone_type == "FINISH":
                            # Successor is Finish Milestone: represents instantaneous completion at pred finish
                            es_cand = add_workdays(pred.early_finish, rel.lag_days, lag_cal)
                        else:
                            # Standard task-to-task FS: starts on next workday
                            base_start = next_workday(pred.early_finish, lag_cal)
                            es_cand = add_workdays(base_start, rel.lag_days, lag_cal)
                        es_candidates.append(es_cand)
                        
                    elif rel.relationship_type == "SS":
                        es_cand = add_workdays(pred.early_start, rel.lag_days, lag_cal)
                        es_candidates.append(es_cand)
                        
                    elif rel.relationship_type == "FF":
                        ef_cand = add_workdays(pred.early_finish, rel.lag_days, lag_cal)
                        ef_candidates.append(ef_cand)
                        if act.duration_days >= 1:
                            implied_es = subtract_workdays(ef_cand, act.duration_days - 1, cal)
                            es_candidates.append(implied_es)
                        else:
                            es_candidates.append(ef_cand)
                            
                    elif rel.relationship_type == "SF":
                        ef_cand = add_workdays(pred.early_start, rel.lag_days, lag_cal)
                        ef_candidates.append(ef_cand)
                        if act.duration_days >= 1:
                            implied_es = subtract_workdays(ef_cand, act.duration_days - 1, cal)
                            es_candidates.append(implied_es)
                        else:
                            es_candidates.append(ef_cand)
                
                act.early_start = max(es_candidates)
                if act.is_milestone and act.duration_days == 0:
                    act.early_finish = act.early_start
                else:
                    natural_ef = add_workdays(act.early_start, act.duration_days - 1, cal)
                    if ef_candidates:
                        act.early_finish = max(natural_ef, max(ef_candidates))
                    else:
                        act.early_finish = natural_ef

        # Project completion date
        project_finish = max(act.early_finish for act in self.activities.values())
        project_start = min(act.early_start for act in self.activities.values())

        # ----------------------------------------------------
        # 2. BACKWARD PASS
        # ----------------------------------------------------
        for act_id in reversed(order):
            act = self.activities[act_id]
            cal = act.calendar_id
            outgoing = self._adj_out[act_id]
            
            if not outgoing:
                # Terminal activity: late finish = project finish
                act.late_finish = project_finish
                if act.is_milestone and act.duration_days == 0:
                    act.late_start = act.late_finish
                else:
                    act.late_start = subtract_workdays(act.late_finish, act.duration_days - 1, cal)
            else:
                lf_candidates: List[date] = []
                ls_candidates: List[date] = []
                
                for rel in outgoing:
                    succ = self.activities[rel.successor_id]
                    lag_cal = rel.lag_calendar_id or cal
                    
                    if rel.relationship_type == "FS":
                        if succ.is_milestone and succ.milestone_type == "FINISH":
                            lf_cand = subtract_workdays(succ.late_finish, rel.lag_days, lag_cal)
                        elif act.is_milestone and act.milestone_type == "START":
                            # Predecessor is Start Milestone: LF equals successor late start minus lag
                            lf_cand = subtract_workdays(succ.late_start, rel.lag_days, lag_cal)
                        else:
                            target_es = subtract_workdays(succ.late_start, rel.lag_days, lag_cal)
                            lf_cand = prev_workday(target_es, cal)
                        lf_candidates.append(lf_cand)
                        
                    elif rel.relationship_type == "SS":
                        ls_cand = subtract_workdays(succ.late_start, rel.lag_days, lag_cal)
                        ls_candidates.append(ls_cand)
                        if act.duration_days >= 1:
                            implied_lf = add_workdays(ls_cand, act.duration_days - 1, cal)
                            lf_candidates.append(implied_lf)
                        else:
                            lf_candidates.append(ls_cand)
                            
                    elif rel.relationship_type == "FF":
                        lf_cand = subtract_workdays(succ.late_finish, rel.lag_days, lag_cal)
                        lf_candidates.append(lf_cand)
                        
                    elif rel.relationship_type == "SF":
                        ls_cand = subtract_workdays(succ.late_finish, rel.lag_days, lag_cal)
                        ls_candidates.append(ls_cand)
                        if act.duration_days >= 1:
                            implied_lf = add_workdays(ls_cand, act.duration_days - 1, cal)
                            lf_candidates.append(implied_lf)
                        else:
                            lf_candidates.append(ls_cand)

                act.late_finish = min(lf_candidates)
                if act.is_milestone and act.duration_days == 0:
                    act.late_start = act.late_finish
                else:
                    natural_ls = subtract_workdays(act.late_finish, act.duration_days - 1, cal)
                    if ls_candidates:
                        act.late_start = min(natural_ls, min(ls_candidates))
                    else:
                        act.late_start = natural_ls

        # ----------------------------------------------------
        # 3. FLOAT & CRITICAL PATH
        # ----------------------------------------------------
        for act_id, act in self.activities.items():
            cal = act.calendar_id
            # Total Float = LS - ES (in workdays)
            act.total_float_days = workdays_between(act.early_start, act.late_start, cal)
            act.is_critical = (act.total_float_days <= 0)
            
            # Free Float = min slack across immediate successors
            outgoing = self._adj_out[act_id]
            if not outgoing:
                act.free_float_days = act.total_float_days
            else:
                slacks: List[int] = []
                for rel in outgoing:
                    succ = self.activities[rel.successor_id]
                    succ_cal = succ.calendar_id
                    
                    if rel.relationship_type == "FS":
                        if succ.is_milestone and succ.milestone_type == "FINISH":
                            w_diff = workdays_between(act.early_finish, succ.early_finish, succ_cal)
                            slack = w_diff - rel.lag_days
                        else:
                            w_diff = workdays_between(act.early_finish, succ.early_start, succ_cal)
                            slack = w_diff - 1 - rel.lag_days
                        slacks.append(max(0, slack))
                    elif rel.relationship_type == "SS":
                        w_diff = workdays_between(act.early_start, succ.early_start, succ_cal)
                        slack = w_diff - rel.lag_days
                        slacks.append(max(0, slack))
                    elif rel.relationship_type == "FF":
                        w_diff = workdays_between(act.early_finish, succ.early_finish, succ_cal)
                        slack = w_diff - rel.lag_days
                        slacks.append(max(0, slack))
                    elif rel.relationship_type == "SF":
                        w_diff = workdays_between(act.early_start, succ.early_finish, succ_cal)
                        slack = w_diff - rel.lag_days
                        slacks.append(max(0, slack))
                act.free_float_days = min(slacks) if slacks else 0

        return project_start, project_finish


def build_six_activity_benchmark() -> ScheduleNetwork:
    """
    Constructs the canonical 6-activity CPM reference network (ACT-01 to ACT-06).
    Calendar: CAL-STD-5D
    """
    net = ScheduleNetwork(project_id="PRJ-WHC-COM-001", schedule_version="BL-01")
    
    net.add_activity(Activity("ACT-01", "Project Notice to Proceed", duration_days=0, is_milestone=True, milestone_type="START", calendar_id="CAL-STD-5D"))
    net.add_activity(Activity("ACT-02", "Substructure Piling", duration_days=5, calendar_id="CAL-STD-5D"))
    net.add_activity(Activity("ACT-03", "Basement Excavation", duration_days=4, calendar_id="CAL-STD-5D"))
    net.add_activity(Activity("ACT-04", "Ground Anchor Installation", duration_days=6, calendar_id="CAL-STD-5D"))
    net.add_activity(Activity("ACT-05", "Basement Slab Casting", duration_days=5, calendar_id="CAL-STD-5D"))
    net.add_activity(Activity("ACT-06", "Substructure Complete", duration_days=0, is_milestone=True, milestone_type="FINISH", calendar_id="CAL-STD-5D"))
    
    net.add_relationship(Relationship("ACT-01", "ACT-02", "FS", lag_days=0))
    net.add_relationship(Relationship("ACT-02", "ACT-03", "FS", lag_days=0))
    net.add_relationship(Relationship("ACT-02", "ACT-04", "SS", lag_days=2))
    net.add_relationship(Relationship("ACT-03", "ACT-05", "FS", lag_days=0))
    net.add_relationship(Relationship("ACT-04", "ACT-05", "FF", lag_days=1))
    net.add_relationship(Relationship("ACT-05", "ACT-06", "FS", lag_days=0))
    
    return net


def build_sf_and_mixed_calendar_benchmark() -> ScheduleNetwork:
    """
    Constructs an independent test network specifically validating:
    1. Start-to-Finish (SF) relationship type
    2. Mixed calendars (CAL-STD-5D 5-day week and CAL-SGP-6D 6-day week)
    3. Positive lag on FS link
    """
    net = ScheduleNetwork(project_id="PRJ-WHC-COM-001", schedule_version="BL-01-SF")
    
    # SF-01: Start milestone (CAL-STD-5D)
    net.add_activity(Activity("SF-01", "Early Mobilisation Start", duration_days=0, is_milestone=True, milestone_type="START", calendar_id="CAL-STD-5D"))
    
    # SF-02: Temporary Power Installation (CAL-STD-5D, duration 4 days)
    net.add_activity(Activity("SF-02", "Temporary Power Installation", duration_days=4, calendar_id="CAL-STD-5D"))
    
    # SF-03: Generator Decommissioning (CAL-SGP-6D, duration 3 days)
    # Linked by SF with lag=2: Generator cannot finish until Temp Power has started + 2 days
    net.add_activity(Activity("SF-03", "Diesel Generator Phase-Out", duration_days=3, calendar_id="CAL-SGP-6D"))
    
    # SF-04: Substation Energization (CAL-STD-5D, duration 5 days)
    net.add_activity(Activity("SF-04", "Main Substation Energization", duration_days=5, calendar_id="CAL-STD-5D"))
    
    # SF-05: Energization Complete (Finish Milestone, CAL-STD-5D)
    net.add_activity(Activity("SF-05", "Energization Milestone", duration_days=0, is_milestone=True, milestone_type="FINISH", calendar_id="CAL-STD-5D"))
    
    net.add_relationship(Relationship("SF-01", "SF-02", "FS", lag_days=0))
    net.add_relationship(Relationship("SF-02", "SF-03", "SF", lag_days=2))
    net.add_relationship(Relationship("SF-02", "SF-04", "FS", lag_days=1))
    net.add_relationship(Relationship("SF-04", "SF-05", "FS", lag_days=0))
    
    return net
