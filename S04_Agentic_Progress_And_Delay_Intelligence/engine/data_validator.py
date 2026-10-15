"""
ACIP S04: Relational Integrity & Schema Validation Engine for Parquet Lakehouse
Module: ACIP S04 - Agentic Progress & Delay Intelligence
File: engine/data_validator.py

Implements rigorous programmatic validation for columnar Parquet storage:
1. Composite Primary Key Uniqueness assertions
2. Composite Foreign Key Referential Integrity (Activities, Lags, S05 Quality, S06 Claims)
3. Schedule Dependency DAG Acyclicity & Duplicate Edge Rejection (Kahn's Algorithm)
4. Delay Revision Lifecycle Semantics & Full Snapshot Immutability (Append-only)
5. Synthetic Data Provenance Enforcement (Rejects FALSE/NULL in synthetic datasets)
6. Source File Provenance Hash Verification (Matches physical XER SHA-256)
7. Contract Parameters Governance & Point-of-Use Authoritative Guardrail
8. Atomic Directory Swap & Rollback Publisher (Fail-closed transaction semantics)
"""
import hashlib
import json
import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
import pandas as pd
import duckdb
import pyarrow.parquet as pq


class ValidationError(Exception):
    """Raised when data fails schema, relational, or lifecycle validation."""
    pass


class LifecycleStateError(ValidationError):
    """Raised when revision lifecycle progression violates rules."""
    pass


class ImmutabilityError(ValidationError):
    """Raised when an existing historical revision is modified or overwritten."""
    pass


class ProvenanceError(ValidationError):
    """Raised when synthetic or actual data provenance is missing or contradictory."""
    pass


class SourceHashMismatchError(ValidationError):
    """Raised when a schedule version recorded source hash does not match the source file."""
    pass


class ContractGovernanceError(ValidationError):
    """Raised when unverified contract particulars are treated as authoritative."""
    pass


class LegacyStorageError(ValidationError):
    """Raised when publication targets an unversioned non-symlink legacy directory."""
    pass


from engine.cpm_engine import CyclicDependencyError


def compute_file_sha256(file_path: str) -> str:
    """Compute SHA-256 hex digest of a local file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class ParquetDataValidator:
    """Validates relational integrity, lifecycle rules, provenance, and DAG acyclicity."""

    def __init__(self):
        self.con = duckdb.connect(database=":memory:")

    def register_tables(self, tables: Dict[str, pd.DataFrame]) -> None:
        """Register all DataFrames into in-memory DuckDB instance."""
        for name, df in tables.items():
            self.con.register(name, df)

    def validate_primary_keys(self, tables: Dict[str, pd.DataFrame]) -> None:
        """Assert primary key uniqueness across all registered tables."""
        pk_definitions = {
            "contract_parameters": ["project_id", "contract_id"],
            "schedule_versions": ["project_id", "schedule_version"],
            "schedule_activities": ["project_id", "schedule_version", "activity_id"],
            "schedule_relationships": [
                "project_id", "schedule_version", "predecessor_activity_id",
                "successor_activity_id", "relationship_type"
            ],
            "site_records": ["project_id", "record_date", "log_id"],
            "site_record_activities": [
                "project_id", "record_date", "log_id", "schedule_version", "activity_id"
            ],
            "delay_events": ["project_id", "event_id", "revision_id"],
            "delay_event_activities": [
                "project_id", "event_id", "revision_id", "schedule_version", "activity_id"
            ],
            "quality_inspection_schedule_links": [
                "inspection_id", "project_id", "schedule_version", "activity_id"
            ],
            "formal_claims_delay_links": [
                "claim_dossier_id", "project_id", "event_id", "revision_id"
            ],
        }

        for table_name, pk_cols in pk_definitions.items():
            if table_name not in tables:
                continue
            cols_str = ", ".join(pk_cols)
            query = f"""
                SELECT {cols_str}, COUNT(*) as cnt
                FROM {table_name}
                GROUP BY {cols_str}
                HAVING COUNT(*) > 1
            """
            duplicates = self.con.execute(query).fetchall()
            if duplicates:
                raise ValidationError(
                    f"Duplicate primary key violation in '{table_name}' on columns ({cols_str}): {duplicates}"
                )

    def validate_foreign_keys(self, tables: Dict[str, pd.DataFrame]) -> None:
        """Assert composite foreign key integrity across related tables."""
        # 1. schedule_activities -> schedule_versions
        if "schedule_activities" in tables and "schedule_versions" in tables:
            query = """
                SELECT a.project_id, a.schedule_version, a.activity_id
                FROM schedule_activities a
                LEFT JOIN schedule_versions v
                  ON a.project_id = v.project_id AND a.schedule_version = v.schedule_version
                WHERE v.schedule_version IS NULL
            """
            orphans = self.con.execute(query).fetchall()
            if orphans:
                raise ValidationError(f"Orphaned activities missing valid schedule_version: {orphans}")

        # 2. schedule_relationships -> schedule_activities (Predecessor & Successor)
        if "schedule_relationships" in tables and "schedule_activities" in tables:
            query_p = """
                SELECT r.project_id, r.schedule_version, r.predecessor_activity_id
                FROM schedule_relationships r
                LEFT JOIN schedule_activities a
                  ON r.project_id = a.project_id
                 AND r.schedule_version = a.schedule_version
                 AND r.predecessor_activity_id = a.activity_id
                WHERE a.activity_id IS NULL
            """
            orphans_p = self.con.execute(query_p).fetchall()
            if orphans_p:
                raise ValidationError(f"Relationships referencing missing predecessor activities: {orphans_p}")

            query_s = """
                SELECT r.project_id, r.schedule_version, r.successor_activity_id
                FROM schedule_relationships r
                LEFT JOIN schedule_activities a
                  ON r.project_id = a.project_id
                 AND r.schedule_version = a.schedule_version
                 AND r.successor_activity_id = a.activity_id
                WHERE a.activity_id IS NULL
            """
            orphans_s = self.con.execute(query_s).fetchall()
            if orphans_s:
                raise ValidationError(f"Relationships referencing missing successor activities: {orphans_s}")

        # 3. site_record_activities -> site_records and schedule_activities
        if "site_record_activities" in tables and "site_records" in tables:
            query_sr = """
                SELECT sra.project_id, sra.record_date, sra.log_id
                FROM site_record_activities sra
                LEFT JOIN site_records sr
                  ON sra.project_id = sr.project_id
                 AND sra.record_date = sr.record_date
                 AND sra.log_id = sr.log_id
                WHERE sr.log_id IS NULL
            """
            orphans_sr = self.con.execute(query_sr).fetchall()
            if orphans_sr:
                raise ValidationError(f"site_record_activities referencing missing site_records: {orphans_sr}")

        if "site_record_activities" in tables and "schedule_activities" in tables:
            query_sra = """
                SELECT sra.project_id, sra.schedule_version, sra.activity_id
                FROM site_record_activities sra
                LEFT JOIN schedule_activities a
                  ON sra.project_id = a.project_id
                 AND sra.schedule_version = a.schedule_version
                 AND sra.activity_id = a.activity_id
                WHERE a.activity_id IS NULL
            """
            orphans_sra = self.con.execute(query_sra).fetchall()
            if orphans_sra:
                raise ValidationError(f"site_record_activities referencing missing schedule_activities: {orphans_sra}")

        # 4. delay_event_activities -> delay_events and schedule_activities
        if "delay_event_activities" in tables and "delay_events" in tables:
            query_de = """
                SELECT dea.project_id, dea.event_id, dea.revision_id
                FROM delay_event_activities dea
                LEFT JOIN delay_events de
                  ON dea.project_id = de.project_id
                 AND dea.event_id = de.event_id
                 AND dea.revision_id = de.revision_id
                WHERE de.event_id IS NULL
            """
            orphans_de = self.con.execute(query_de).fetchall()
            if orphans_de:
                raise ValidationError(f"delay_event_activities referencing missing delay_events: {orphans_de}")

        if "delay_event_activities" in tables and "schedule_activities" in tables:
            query_dea = """
                SELECT dea.project_id, dea.schedule_version, dea.activity_id
                FROM delay_event_activities dea
                LEFT JOIN schedule_activities a
                  ON dea.project_id = a.project_id
                 AND dea.schedule_version = a.schedule_version
                 AND dea.activity_id = a.activity_id
                WHERE a.activity_id IS NULL
            """
            orphans_dea = self.con.execute(query_dea).fetchall()
            if orphans_dea:
                raise ValidationError(f"delay_event_activities referencing missing schedule_activities: {orphans_dea}")

        # 5. S05 quality_inspection_schedule_links -> schedule_activities
        if "quality_inspection_schedule_links" in tables and "schedule_activities" in tables:
            query_s05 = """
                SELECT q.inspection_id, q.project_id, q.schedule_version, q.activity_id
                FROM quality_inspection_schedule_links q
                LEFT JOIN schedule_activities a
                  ON q.project_id = a.project_id
                 AND q.schedule_version = a.schedule_version
                 AND q.activity_id = a.activity_id
                WHERE a.activity_id IS NULL
            """
            orphans_s05 = self.con.execute(query_s05).fetchall()
            if orphans_s05:
                raise ValidationError(f"S05 inspection links referencing missing schedule activities: {orphans_s05}")

        # 6. S06 formal_claims_delay_links -> delay_events
        if "formal_claims_delay_links" in tables and "delay_events" in tables:
            query_s06 = """
                SELECT c.claim_dossier_id, c.project_id, c.event_id, c.revision_id
                FROM formal_claims_delay_links c
                LEFT JOIN delay_events d
                  ON c.project_id = d.project_id
                 AND c.event_id = d.event_id
                 AND c.revision_id = d.revision_id
                WHERE d.event_id IS NULL
            """
            orphans_s06 = self.con.execute(query_s06).fetchall()
            if orphans_s06:
                raise ValidationError(f"S06 formal claim links referencing missing delay event revisions: {orphans_s06}")

    def validate_dag_acyclicity(self, tables: Dict[str, pd.DataFrame]) -> None:
        """
        Validates that schedule_relationships form a Directed Acyclic Graph (DAG)
        scoped per (project_id, schedule_version). Rejects duplicate links and cycles.
        """
        if "schedule_relationships" not in tables:
            return

        df_rels = tables["schedule_relationships"]
        groups = df_rels.groupby(["project_id", "schedule_version"])

        for (prj_id, ver_id), group in groups:
            # Check duplicate links within group
            seen_edges: Set[Tuple[str, str, str]] = set()
            adj: Dict[str, List[str]] = {}
            in_degree: Dict[str, int] = {}
            nodes: Set[str] = set()

            for _, row in group.iterrows():
                pred = row["predecessor_activity_id"]
                succ = row["successor_activity_id"]
                rel_type = row["relationship_type"]
                edge_key = (pred, succ, rel_type)

                if edge_key in seen_edges:
                    raise ValidationError(
                        f"Duplicate relationship detected in ({prj_id}, {ver_id}): {pred} -> {succ} ({rel_type})"
                    )
                seen_edges.add(edge_key)

                nodes.add(pred)
                nodes.add(succ)
                if pred not in adj:
                    adj[pred] = []
                adj[pred].append(succ)
                in_degree[succ] = in_degree.get(succ, 0) + 1
                if pred not in in_degree:
                    in_degree[pred] = 0

            # Kahn's algorithm for cycle detection
            queue = [node for node in nodes if in_degree[node] == 0]
            visited_count = 0

            while queue:
                queue.sort()
                curr = queue.pop(0)
                visited_count += 1
                for nxt in adj.get(curr, []):
                    in_degree[nxt] -= 1
                    if in_degree[nxt] == 0:
                        queue.append(nxt)

            if visited_count != len(nodes):
                unresolved = [node for node in nodes if in_degree[node] > 0]
                raise CyclicDependencyError(
                    f"Cyclic dependency detected in project '{prj_id}' version '{ver_id}' involving: {unresolved}"
                )

    def validate_delay_revision_lifecycle(self, tables: Dict[str, pd.DataFrame]) -> None:
        """Validate revision stage semantics and ensure no premature values are invented."""
        if "delay_events" not in tables:
            return

        df = tables["delay_events"]
        for _, row in df.iterrows():
            stage = row["revision_stage"]
            
            # Revision 1: CONTRACTOR_CLAIM
            if stage == "CONTRACTOR_CLAIM":
                prohibited_fields = [
                    "assessed_eot_days", "concurrent_delay_flag", "approved_eot_days",
                    "compensable_days", "determined_by", "determination_date", "determination_doc_reference"
                ]
                for fld in prohibited_fields:
                    if pd.notna(row.get(fld)):
                        raise LifecycleStateError(
                            f"Event {row['event_id']} Rev {row['revision_id']} is CONTRACTOR_CLAIM but has '{fld}' populated."
                        )
            
            # Revision 2: FORENSIC_ASSESSMENT
            elif stage == "FORENSIC_ASSESSMENT":
                if pd.isna(row.get("assessed_eot_days")):
                    raise LifecycleStateError(
                        f"Event {row['event_id']} Rev {row['revision_id']} is FORENSIC_ASSESSMENT but assessed_eot_days is NULL."
                    )
                prohibited_determination_fields = [
                    "approved_eot_days", "compensable_days", "determined_by",
                    "determination_date", "determination_doc_reference"
                ]
                for fld in prohibited_determination_fields:
                    if pd.notna(row.get(fld)):
                        raise LifecycleStateError(
                            f"Event {row['event_id']} Rev {row['revision_id']} is FORENSIC_ASSESSMENT but has '{fld}' populated."
                        )

            # Revision 3: SO_DETERMINATION
            elif stage == "SO_DETERMINATION":
                if pd.isna(row.get("approved_eot_days")):
                    raise LifecycleStateError(
                        f"Event {row['event_id']} Rev {row['revision_id']} is SO_DETERMINATION but approved_eot_days is NULL."
                    )
                if pd.isna(row.get("determined_by")) or pd.isna(row.get("determination_date")):
                    raise LifecycleStateError(
                        f"Event {row['event_id']} Rev {row['revision_id']} is SO_DETERMINATION but lacks formal certificate authority or date."
                    )
                if pd.isna(row.get("determination_doc_reference")):
                    raise LifecycleStateError(
                        f"Event {row['event_id']} Rev {row['revision_id']} lacks official certificate document reference."
                    )

    def validate_revision_immutability(
        self,
        existing_df: pd.DataFrame,
        new_df: pd.DataFrame
    ) -> None:
        """
        Enforces full snapshot immutability: previously committed revisions cannot be altered or deleted.
        Any modification or deletion of existing (project_id, event_id, revision_id) raises ImmutabilityError.
        """
        key_cols = ["project_id", "event_id", "revision_id"]
        existing_map = existing_df.set_index(key_cols)
        new_map = new_df.set_index(key_cols)

        # Check for attempted deletion of existing historical revisions
        missing_keys = existing_map.index.difference(new_map.index)
        if len(missing_keys) > 0:
            sample_missing = list(missing_keys)[:3]
            raise ImmutabilityError(
                f"Attempted deletion of committed historical revision(s): {sample_missing}. "
                "Historical revisions are strictly append-only; deletions are prohibited."
            )

        # Check existing keys in new submission for in-place mutation
        common_keys = existing_map.index.intersection(new_map.index)
        for k in common_keys:
            old_row = existing_map.loc[k]
            new_row = new_map.loc[k]
            
            # Compare non-null values for equality
            for col in existing_df.columns:
                if col in key_cols or col == "created_at":
                    continue
                v_old = old_row[col]
                v_new = new_row[col]
                if pd.isna(v_old) and pd.isna(v_new):
                    continue
                if v_old != v_new:
                    raise ImmutabilityError(
                        f"Attempted in-place modification of committed historical revision {k} on field '{col}': "
                        f"Original='{v_old}' -> Modified='{v_new}'. Historical revisions must be append-only."
                    )

    def validate_synthetic_provenance(self, tables: Dict[str, pd.DataFrame]) -> None:
        """
        Enforce that in synthetic-only datasets, every row has is_synthetic = TRUE.
        Rejects FALSE, NULL, omitted flags, and mismatched benchmark tags.
        """
        synthetic_tables = [
            "site_records", "site_record_activities",
            "delay_events", "delay_event_activities"
        ]
        valid_benchmark_tag = "SIMULATED_TEST_SCENARIO_ACIP_S04"

        for table_name in synthetic_tables:
            if table_name not in tables:
                continue
            df = tables[table_name]
            if "is_synthetic" not in df.columns:
                raise ProvenanceError(f"Table '{table_name}' lacks mandatory 'is_synthetic' column.")
            if "synthetic_benchmark_tag" not in df.columns:
                raise ProvenanceError(f"Table '{table_name}' lacks mandatory 'synthetic_benchmark_tag' column.")

            for idx, row in df.iterrows():
                is_synth = row["is_synthetic"]
                tag = row["synthetic_benchmark_tag"]
                if pd.isna(is_synth):
                    raise ProvenanceError(f"Table '{table_name}' row {idx} has NULL is_synthetic.")
                # Reject is_synthetic == False in synthetic-only datasets
                if is_synth is not True:
                    raise ProvenanceError(
                        f"Table '{table_name}' row {idx} has is_synthetic={is_synth}. "
                        "Synthetic benchmark datasets must contain only rows explicitly declared as TRUE."
                    )
                if pd.isna(tag) or tag != valid_benchmark_tag:
                    raise ProvenanceError(
                        f"Table '{table_name}' row {idx} is marked synthetic but lacks valid benchmark tag: '{tag}'"
                    )

    def validate_schedule_version_source_file_hashes(
        self,
        tables: Dict[str, pd.DataFrame],
        base_dir: str
    ) -> None:
        """
        Verifies that file-backed schedule versions record the exact SHA-256 hash
        of the physical source file on disk. Fails closed if the referenced file is missing or unreadable.
        """
        if "schedule_versions" not in tables:
            return
        df = tables["schedule_versions"]
        for _, row in df.iterrows():
            rel_path = row["source_file_path"]
            recorded_hash = row["source_file_sha256"]
            full_path = os.path.join(base_dir, rel_path) if not os.path.isabs(rel_path) else rel_path

            if not os.path.exists(full_path):
                raise SourceHashMismatchError(
                    f"Referenced source file '{rel_path}' for schedule version '{row['schedule_version']}' "
                    f"is missing or does not exist at '{full_path}'."
                )

            try:
                actual_hash = compute_file_sha256(full_path)
            except Exception as e:
                raise SourceHashMismatchError(
                    f"Referenced source file '{full_path}' for schedule version '{row['schedule_version']}' "
                    f"is unreadable: {e}"
                )

            if actual_hash != recorded_hash:
                raise SourceHashMismatchError(
                    f"Schedule version '{row['schedule_version']}' recorded source hash '{recorded_hash}' "
                    f"does not match physical file hash '{actual_hash}' for '{rel_path}'."
                )

    def validate_contract_parameters(self, tables: Dict[str, pd.DataFrame]) -> None:
        """Validate contract parameters governance."""
        if "contract_parameters" not in tables:
            return
        df = tables["contract_parameters"]
        for _, row in df.iterrows():
            if row["daily_liquidated_damages_rate_sgd"] <= 0:
                raise ContractGovernanceError("Liquidated damages rate must be positive.")
            if row["delay_notice_period_days"] <= 0:
                raise ContractGovernanceError("Delay notice period must be positive.")


def calculate_contractual_exposure(
    project_id: str,
    unmitigated_delay_days: int,
    assessed_eot_days: int,
    contract_params: Dict[str, any],
    force_authoritative: bool = False
) -> Dict[str, any]:
    """
    Point-of-use contract governance guardrail:
    Prevents presenting delay exposure as authoritative if contract parameters are unverified.
    """
    is_verified = contract_params.get("verified_against_signed_contract", False)
    daily_ld_rate = contract_params.get("daily_liquidated_damages_rate_sgd", 0.0)

    if force_authoritative and not is_verified:
        raise ContractGovernanceError(
            f"Cannot produce authoritative contractual conclusion for project '{project_id}': "
            "contract parameters have not been verified against the executed signed contract."
        )

    net_chargeable_delay = max(0, unmitigated_delay_days - assessed_eot_days)
    liquidated_damages_amount = net_chargeable_delay * daily_ld_rate

    return {
        "project_id": project_id,
        "net_chargeable_delay_days": net_chargeable_delay,
        "daily_liquidated_damages_rate_sgd": daily_ld_rate,
        "liquidated_damages_amount_sgd": liquidated_damages_amount,
        "verified_against_signed_contract": is_verified,
        "status": "AUTHORITATIVE_VERIFIED" if is_verified else "ADVISORY_SIMULATION_ONLY",
    }


def atomic_publish_dataset(
    tables: Dict[str, pd.DataFrame],
    target_parquet_dir: str,
    base_dir: Optional[str] = None,
    simulate_interruption: bool = False
) -> None:
    """
    Executes a genuinely atomic publication commit with fail-closed semantics:
    1. Validates all tables in memory (PKs, FKs, DAG acyclicity, Lifecycle, Provenance, Hashes).
    2. If target directory already exists, asserts immutability against existing delay revisions.
    3. Rejects legacy non-symlink directories (fail-closed) to eliminate the two-step migration gap.
    4. Writes complete dataset into an isolated versioned snapshot directory on the same filesystem.
    5. Writes a tamper-evident commit manifest (_manifest.json) into the snapshot directory.
    6. Point of atomic commit: swaps the active symlink pointer directly via os.replace(tmp_link, target_parquet_dir)
       in a single atomic POSIX rename(2) syscall.
    7. If simulate_interruption is True or any exception occurs before or during the commit point,
       the active target remains 100% untouched and readers never observe partial or missing state.
    """
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    validator = ParquetDataValidator()
    validator.register_tables(tables)
    validator.validate_primary_keys(tables)
    validator.validate_foreign_keys(tables)
    validator.validate_dag_acyclicity(tables)
    validator.validate_delay_revision_lifecycle(tables)
    validator.validate_synthetic_provenance(tables)
    validator.validate_schedule_version_source_file_hashes(tables, base_dir)
    validator.validate_contract_parameters(tables)

    # Immutability check against existing delay_events on disk
    target_delay_path = os.path.join(target_parquet_dir, "delay_events.parquet")
    if os.path.exists(target_delay_path) and "delay_events" in tables:
        existing_delay_df = pd.read_parquet(target_delay_path)
        validator.validate_revision_immutability(existing_delay_df, tables["delay_events"])

    target_parquet_dir = os.path.abspath(target_parquet_dir)
    parent_dir = os.path.dirname(target_parquet_dir)
    os.makedirs(parent_dir, exist_ok=True)

    # Atomic publication invariant: Target must be a symlink or not exist yet.
    # Reject unmanaged non-symlink directories to eliminate migration gap from publication guarantee.
    if os.path.exists(target_parquet_dir) and not os.path.islink(target_parquet_dir):
        raise LegacyStorageError(
            f"Atomic publication rejected: target path '{target_parquet_dir}' is an existing non-symlink directory. "
            "To maintain single-syscall atomic publication guarantees (os.replace), legacy directories cannot be migrated "
            "inline during publication. Please run migrate_legacy_directory_to_versioned_store() first."
        )

    snapshots_root = os.path.join(parent_dir, ".snapshots")
    os.makedirs(snapshots_root, exist_ok=True)
    snapshot_id = f"snap_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    snapshot_dir = os.path.join(snapshots_root, snapshot_id)
    os.makedirs(snapshot_dir, exist_ok=True)

    tmp_link = None
    try:
        # Write all tables into the versioned snapshot
        manifest_entries = {}
        for name, df in tables.items():
            file_path = os.path.join(snapshot_dir, f"{name}.parquet")
            df.to_parquet(file_path, index=False)
            manifest_entries[f"{name}.parquet"] = {
                "rows": int(len(df)),
                "sha256": compute_file_sha256(file_path)
            }

        # Write tamper-evident commit manifest into snapshot
        manifest_data = {
            "snapshot_id": snapshot_id,
            "commit_timestamp": datetime.now(timezone.utc).isoformat(),
            "tables": manifest_entries
        }
        with open(os.path.join(snapshot_dir, "_manifest.json"), "w") as f:
            json.dump(manifest_data, f, indent=2)

        # Interruption testing: simulate crash/interruption prior to the atomic commit point
        if simulate_interruption:
            raise RuntimeError("Simulated staging interruption during publication before commit point.")

        # Atomic commit point:
        # Create staging symlink on the same filesystem
        tmp_link = os.path.join(parent_dir, f".tmp_commit_{uuid.uuid4().hex}")
        os.symlink(snapshot_dir, tmp_link)

        # Single-syscall atomic pointer swap: rename(2) replaces symlink instantly without gap
        os.replace(tmp_link, target_parquet_dir)
        tmp_link = None

    except Exception as e:
        # Fail closed: clean up temporary staging link and failed snapshot
        if tmp_link:
            try:
                if os.path.islink(tmp_link) or os.path.lexists(tmp_link):
                    os.unlink(tmp_link)
            except Exception:
                pass
        if os.path.exists(snapshot_dir):
            shutil.rmtree(snapshot_dir, ignore_errors=True)
        raise e


def migrate_legacy_directory_to_versioned_store(
    target_parquet_dir: str,
    base_dir: Optional[str] = None,
    simulate_interruption: bool = False
) -> str:
    """
    Offline Maintenance Utility:
    Safely migrates an existing unmanaged, non-symlink directory into the versioned snapshot store.

    REQUIRED DOWNTIME & MAINTENANCE WINDOW:
    In POSIX file systems, replacing a non-empty directory with a symlink cannot be performed
    in a single atomic syscall (rename(2) returns EISDIR or ENOTDIR). Consequently, migrating
    a legacy directory into a versioned symlinked store is inherently a multi-step operation
    that requires an offline scheduled maintenance window. Active analytical queries and ETL
    pipelines targeting the directory must be paused during migration.

    RECOVERY PROCEDURE:
    1. Journaling: A persistent recovery journal (.migration_journal_<snapshot_id>.json) is
       committed to disk before moving the legacy directory.
    2. Accurate Parquet Inspection: Exact row counts (via PyArrow metadata) and SHA-256 hashes
       are calculated for all migrated Parquet tables and written into _manifest.json.
    3. Failure Recovery:
       - If interrupted prior to symlink installation, the original directory path may be absent.
       - Automatic Recovery: Invoke recover_interrupted_migration(target_parquet_dir) or re-run
         this migration utility, which reads the persistent journal and completes the symlink.
       - Manual Recovery: Locate the staged snapshot in parent_dir/.snapshots/legacy_initial_*
         and execute: ln -s .snapshots/<snapshot_id> <target_parquet_dir>.
    """
    target_parquet_dir = os.path.normpath(os.path.abspath(target_parquet_dir))
    parent_dir = os.path.dirname(target_parquet_dir)
    os.makedirs(parent_dir, exist_ok=True)

    # Check if target is already a valid symlink BEFORE any realpath resolution
    if os.path.islink(target_parquet_dir):
        resolved_snapshot = os.path.realpath(target_parquet_dir)
        # Narrow hardening: verify backing snapshot manifest integrity before accepting existing symlink
        verify_snapshot_manifest(resolved_snapshot)
        return resolved_snapshot

    # Check if an interrupted migration can be recovered first
    if not os.path.exists(target_parquet_dir):
        recovered = recover_interrupted_migration(target_parquet_dir, base_dir)
        if recovered:
            return recovered
        raise FileNotFoundError(f"Target path does not exist: {target_parquet_dir}")

    if not os.path.isdir(target_parquet_dir):
        raise NotADirectoryError(f"Target path is not a directory: {target_parquet_dir}")

    snapshots_root = os.path.join(parent_dir, ".snapshots")
    os.makedirs(snapshots_root, exist_ok=True)

    snapshot_id = f"legacy_initial_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    snapshot_dir = os.path.join(snapshots_root, snapshot_id)
    journal_file = os.path.join(parent_dir, f".migration_journal_{snapshot_id}.json")

    # Step 1: Write persistent recovery journal before moving files
    journal_data = {
        "snapshot_id": snapshot_id,
        "target_parquet_dir": target_parquet_dir,
        "snapshot_dir": snapshot_dir,
        "status": "in_progress",
        "started_at": datetime.now(timezone.utc).isoformat()
    }
    with open(journal_file, "w") as f:
        json.dump(journal_data, f, indent=2)

    try:
        # Step 2: Move existing legacy directory into snapshot staging
        shutil.move(target_parquet_dir, snapshot_dir)

        # Step 3: Inspect Parquet files for actual row counts and SHA-256 hashes
        manifest_entries = {}
        for fname in sorted(os.listdir(snapshot_dir)):
            if fname.endswith(".parquet"):
                fpath = os.path.join(snapshot_dir, fname)
                try:
                    num_rows = int(pq.read_metadata(fpath).num_rows)
                except Exception:
                    try:
                        num_rows = int(len(pd.read_parquet(fpath)))
                    except Exception as exc:
                        raise ValidationError(
                            f"Unable to establish physical row count for Parquet table '{fname}' "
                            f"in snapshot '{snapshot_dir}': file corrupt or unreadable ({str(exc)})"
                        )
                manifest_entries[fname] = {
                    "rows": num_rows,
                    "sha256": compute_file_sha256(fpath)
                }

        manifest_data = {
            "snapshot_id": snapshot_id,
            "commit_timestamp": datetime.now(timezone.utc).isoformat(),
            "migration_note": "Migrated from unversioned legacy directory during scheduled offline maintenance window",
            "tables": manifest_entries
        }
        with open(os.path.join(snapshot_dir, "_manifest.json"), "w") as f:
            json.dump(manifest_data, f, indent=2)

        # Fault injection hook: simulate crash between move and symlink installation
        if simulate_interruption:
            raise RuntimeError("Simulated crash/interruption after moving legacy directory before symlink installation.")

        # Step 4: Establish initial symlink pointer
        os.symlink(snapshot_dir, target_parquet_dir)

        # Step 5: Migration successful: remove recovery journal
        if os.path.exists(journal_file):
            try:
                os.remove(journal_file)
            except Exception:
                pass

        return snapshot_dir

    except Exception as e:
        # If not simulating external crash, attempt best-effort immediate in-process rollback
        if not simulate_interruption and os.path.exists(snapshot_dir) and not os.path.lexists(target_parquet_dir):
            try:
                shutil.move(snapshot_dir, target_parquet_dir)
                if os.path.exists(journal_file):
                    os.remove(journal_file)
            except Exception:
                pass
        raise e


def recover_interrupted_migration(
    target_parquet_dir: str,
    base_dir: Optional[str] = None
) -> Optional[str]:
    """
    Recovers an offline legacy directory migration that was interrupted between
    moving the original directory and installing the initial symlink pointer.

    Recovery logic:
    1. Scans parent_dir for active migration journals (.migration_journal_*.json).
    2. Identifies matching journals for target_parquet_dir.
    3. Verifies that the recorded snapshot_dir exists and contains parquet data.
    4. Ensures _manifest.json exists with accurate parquet row counts and SHA-256 hashes.
    5. Re-installs the target symlink pointer (os.symlink).
    6. Removes the journal upon verified restoration of service.
    7. Returns the restored snapshot path, or None if no recovery was required.
    """
    target_parquet_dir = os.path.normpath(os.path.abspath(target_parquet_dir))
    parent_dir = os.path.dirname(target_parquet_dir)
    if not os.path.exists(parent_dir):
        return None

    # Search for migration journals
    matching_journals = []
    for fname in os.listdir(parent_dir):
        if fname.startswith(".migration_journal_") and fname.endswith(".json"):
            jpath = os.path.join(parent_dir, fname)
            try:
                with open(jpath, "r") as f:
                    data = json.load(f)
                if data.get("target_parquet_dir") == target_parquet_dir:
                    matching_journals.append((jpath, data))
            except Exception:
                continue

    if not matching_journals:
        # Fallback inspection: check if unlinked legacy snapshots exist in .snapshots
        snapshots_root = os.path.join(parent_dir, ".snapshots")
        if os.path.exists(snapshots_root) and not os.path.lexists(target_parquet_dir):
            legacy_snaps = sorted([
                d for d in os.listdir(snapshots_root)
                if d.startswith("legacy_initial_") and os.path.isdir(os.path.join(snapshots_root, d))
            ])
            if legacy_snaps:
                last_snap = os.path.join(snapshots_root, legacy_snaps[-1])
                verify_snapshot_manifest(last_snap)
                os.symlink(last_snap, target_parquet_dir)
                return last_snap
        return None

    # Sort matching journals by file modification time descending
    matching_journals.sort(key=lambda x: os.path.getmtime(x[0]), reverse=True)
    journal_path, journal_data = matching_journals[0]
    snapshot_dir = journal_data.get("snapshot_dir")
    snapshot_id = journal_data.get("snapshot_id")

    if not snapshot_dir or not os.path.exists(snapshot_dir):
        return None

    # Ensure _manifest.json exists with accurate row counts
    manifest_path = os.path.join(snapshot_dir, "_manifest.json")
    if not os.path.exists(manifest_path):
        manifest_entries = {}
        for fname in sorted(os.listdir(snapshot_dir)):
            if fname.endswith(".parquet"):
                fpath = os.path.join(snapshot_dir, fname)
                try:
                    num_rows = int(pq.read_metadata(fpath).num_rows)
                except Exception:
                    try:
                        num_rows = int(len(pd.read_parquet(fpath)))
                    except Exception as exc:
                        raise ValidationError(
                            f"Unable to establish physical row count for Parquet table '{fname}' "
                            f"in snapshot '{snapshot_dir}': file corrupt or unreadable ({str(exc)})"
                        )
                manifest_entries[fname] = {
                    "rows": num_rows,
                    "sha256": compute_file_sha256(fpath)
                }
        manifest_data = {
            "snapshot_id": snapshot_id,
            "commit_timestamp": datetime.now(timezone.utc).isoformat(),
            "migration_note": "Manifest generated during automated recovery by recover_interrupted_migration()",
            "tables": manifest_entries
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2)

    # Step 4: Rigorously verify the staged snapshot manifest before installing or updating symlink pointer!
    # Validate the recorded hashes and physical row counts. If corrupt or mismatched, fail closed.
    verify_snapshot_manifest(snapshot_dir)

    # Step 5: Reinstall target symlink pointer only AFTER snapshot is fully verified
    if not os.path.lexists(target_parquet_dir):
        os.symlink(snapshot_dir, target_parquet_dir)
    elif os.path.islink(target_parquet_dir) and os.path.realpath(target_parquet_dir) != os.path.realpath(snapshot_dir):
        # Atomic swap to corrected snapshot
        tmp_link = os.path.join(parent_dir, f".tmp_recov_{uuid.uuid4().hex}")
        os.symlink(snapshot_dir, tmp_link)
        os.replace(tmp_link, target_parquet_dir)

    # Step 6: Remove journal ONLY after verified link restoration
    try:
        os.remove(journal_path)
    except Exception:
        pass

    return snapshot_dir


def verify_snapshot_manifest(snapshot_or_target_dir: str) -> bool:
    """
    Verifies that the target directory or snapshot contains a valid _manifest.json,
    and that all recorded parquet files exist with matching SHA-256 hashes and row counts.
    Returns True if valid, or raises ValidationError if corrupt or missing.
    """
    resolved_dir = os.path.realpath(snapshot_or_target_dir)
    manifest_path = os.path.join(resolved_dir, "_manifest.json")
    if not os.path.exists(manifest_path):
        raise ValidationError(f"Manifest missing from snapshot: {manifest_path}")

    try:
        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)
    except Exception as e:
        raise ValidationError(f"Manifest JSON corrupt in snapshot {resolved_dir}: {str(e)}")

    tables = manifest_data.get("tables", {})
    if not tables:
        raise ValidationError(f"Manifest contains no table records in snapshot {resolved_dir}")

    for fname, meta in tables.items():
        fpath = os.path.join(resolved_dir, fname)
        if not os.path.exists(fpath):
            raise ValidationError(f"Parquet file referenced in manifest missing: {fpath}")

        current_hash = compute_file_sha256(fpath)
        if current_hash != meta.get("sha256"):
            raise ValidationError(
                f"SHA-256 hash mismatch for {fname}: expected {meta.get('sha256')}, found {current_hash}"
            )

        try:
            current_rows = int(pq.read_metadata(fpath).num_rows)
        except Exception:
            try:
                current_rows = int(len(pd.read_parquet(fpath)))
            except Exception as exc:
                raise ValidationError(
                    f"Unable to establish physical row count for {fname}: {str(exc)}"
                )

        if current_rows != meta.get("rows"):
            raise ValidationError(
                f"Row count mismatch for {fname}: manifest records {meta.get('rows')}, physical file contains {current_rows}"
            )

    return True


