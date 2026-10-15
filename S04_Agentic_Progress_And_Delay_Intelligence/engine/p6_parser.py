"""
ACIP S04: Scoped Primavera P6 XER Parser & Round-Trip Serializer
Module: ACIP S04 - Agentic Progress & Delay Intelligence
File: engine/p6_parser.py

Implements scoped parsing and export for Primavera P6 XER text format.
Supported Tables:
- PROJECT (Project identity, planned dates, data date)
- CALENDAR (Calendar definitions and working days)
- PROJWBS (Work Breakdown Structure elements)
- TASK (Activities, durations, early/late dates, floats)
- TASKPRED (Predecessor/successor dependencies, link types, lags)

Enterprise tables outside the CPM network scope (RSRC, UDFVALUE, etc.)
are preserved with complete semantic fidelity as structured pass-through tables
(preserving table identity, field schemas, and record values identically across
round trips, rather than claiming raw byte-for-byte serialization).
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple


@dataclass
class XERTable:
    name: str
    fields: List[str]
    records: List[List[str]] = field(default_factory=list)


class P6XERParser:
    """Parses and exports Primavera P6 XER files with scoped CPM network extraction."""

    def __init__(self):
        self.tables: Dict[str, XERTable] = {}
        self.raw_header: str = ""
        self.unmapped_tables: Dict[str, XERTable] = {}

    def parse(self, text: str) -> None:
        """Parse XER string content into structured table blocks."""
        lines = text.strip().splitlines()
        current_table: Optional[XERTable] = None
        
        for line in lines:
            line = line.strip("\r\n")
            if not line:
                continue
            if line.startswith("ERMHDR"):
                self.raw_header = line
                continue
            if line.startswith("%T"):
                parts = line.split("\t")
                table_name = parts[1].strip()
                current_table = XERTable(name=table_name, fields=[])
                self.tables[table_name] = current_table
            elif line.startswith("%F"):
                if current_table:
                    parts = line.split("\t")[1:]
                    current_table.fields = [p.strip() for p in parts]
            elif line.startswith("%R"):
                if current_table:
                    parts = line.split("\t")[1:]
                    current_table.records.append(parts)

    def export(self) -> str:
        """Serialize current state back to valid XER format."""
        out_lines: List[str] = []
        if self.raw_header:
            out_lines.append(self.raw_header)
        else:
            out_lines.append("ERMHDR\t8.3\t2026-10-09\tACIP_S04_CPM_EXPORT")

        for table_name, tbl in self.tables.items():
            out_lines.append(f"%T\t{table_name}")
            out_lines.append("%F\t" + "\t".join(tbl.fields))
            for rec in tbl.records:
                out_lines.append("%R\t" + "\t".join(rec))

        return "\n".join(out_lines) + "\n"

    def get_project(self) -> Optional[Dict[str, str]]:
        """Extract project header from PROJECT table."""
        if "PROJECT" not in self.tables or not self.tables["PROJECT"].records:
            return None
        tbl = self.tables["PROJECT"]
        return dict(zip(tbl.fields, tbl.records[0]))

    def get_wbs(self) -> List[Dict[str, str]]:
        """Extract WBS elements from PROJWBS table."""
        if "PROJWBS" not in self.tables:
            return []
        tbl = self.tables["PROJWBS"]
        return [dict(zip(tbl.fields, rec)) for rec in tbl.records]

    def get_activities(self) -> List[Dict[str, str]]:
        """Extract activities from TASK table."""
        if "TASK" not in self.tables:
            return []
        tbl = self.tables["TASK"]
        results = []
        for rec in tbl.records:
            row_dict = dict(zip(tbl.fields, rec))
            results.append(row_dict)
        return results

    def get_relationships(self) -> List[Dict[str, str]]:
        """Extract relationships from TASKPRED table."""
        if "TASKPRED" not in self.tables:
            return []
        tbl = self.tables["TASKPRED"]
        results = []
        for rec in tbl.records:
            row_dict = dict(zip(tbl.fields, rec))
            results.append(row_dict)
        return results

    def get_table_records(self, table_name: str) -> List[Dict[str, str]]:
        """Extract records from any parsed table as a list of dicts."""
        if table_name not in self.tables:
            return []
        tbl = self.tables[table_name]
        return [dict(zip(tbl.fields, rec)) for rec in tbl.records]


def create_sample_xer_fixture() -> str:
    """Creates a valid, representative P6 XER string fixture for testing."""
    lines = [
        "ERMHDR\t8.3\t2026-10-09\tACIP_S04_FIXTURE",
        "%T\tPROJECT",
        "%F\tproj_id\tproj_short_name\tplan_start_date\tplan_end_date\tlast_recalc_date",
        "%R\t1001\tPRJ-WHC-COM-001\t2026-11-02 08:00\t2026-11-19 17:00\t2026-11-02 08:00",
        "%T\tPROJWBS",
        "%F\twbs_id\tproj_id\twbs_short_name\twbs_name",
        "%R\t2001\t1001\tWHC.SUB\tWoodlands Substructure Package",
        "%T\tTASK",
        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttarget_durn_hr_cnt\ttotal_float_hr_cnt",
        "%R\t3001\t1001\t2001\tACT-01\tProject Notice to Proceed\t0.0\t0.0",
        "%R\t3002\t1001\t2001\tACT-02\tSubstructure Piling\t40.0\t0.0",
        "%R\t3003\t1001\t2001\tACT-03\tBasement Excavation\t32.0\t0.0",
        "%R\t3004\t1001\t2001\tACT-04\tGround Anchor Installation\t48.0\t40.0",
        "%R\t3005\t1001\t2001\tACT-05\tBasement Slab Casting\t40.0\t0.0",
        "%R\t3006\t1001\t2001\tACT-06\tSubstructure Complete\t0.0\t0.0",
        "%T\tTASKPRED",
        "%F\ttask_pred_id\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt",
        "%R\t4001\t3002\t3001\tPR_FS\t0.0",
        "%R\t4002\t3003\t3002\tPR_FS\t0.0",
        "%R\t4003\t3004\t3002\tPR_SS\t16.0",
        "%R\t4004\t3005\t3003\tPR_FS\t0.0",
        "%R\t4005\t3005\t3004\tPR_FF\t8.0",
        "%R\t4006\t3006\t3005\tPR_FS\t0.0",
        "%T\tUDFVALUE",
        "%F\tudf_id\tforeign_key\tudf_text",
        "%R\t9001\t3002\tPreserved Pass-Through Enterprise Field Value",
    ]
    return "\n".join(lines) + "\n"
