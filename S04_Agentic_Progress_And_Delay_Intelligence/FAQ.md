# <span style="color:red">❓ 9. Frequently Asked Questions (FAQ)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](README.md#toc)</span>

---

## <span id="faq-toc"></span>📑 Table Of Contents (TOC)

- [Q1: How does the deterministic Oracle Primavera P6 XER parser ingest raw schedules without third-party proprietary DLLs?](#q1)
- [Q2: What is the exact mathematical formulation and calendar handling behind CPM forward and backward topological passes?](#q2)
- [Q3: How does S04 enforce the Fractional Lag and Duration Modulo rejection policy to eliminate synthetic date anomalies?](#q3)
- [Q4: How does S04 implement SCL Delay and Disruption Protocol Core Principle 10 for concurrent delay apportionment?](#q4)
- [Q5: How does the Controlled Time Impact Analysis (TIA) Fragnet Simulator quantify total float erosion and critical path drift?](#q5)
- [Q6: What is the statutory legal foundation and condition precedent mechanism of the PSSCOC Clause 23.1 28-day notice timebar?](#q6)
- [Q7: How is Liquidated Damages (LAD) financial exposure modeled deterministically outside the probabilistic LLM path?](#q7)
- [Q8: How does the 3-Agent Adversarial Deliberation Theater operate without hallucinating schedule outcomes?](#q8)
- [Q9: How do the downstream lakehouse Parquet handshakes to S05 Quality and S06 SOPA Claims preserve cryptographic provenance?](#q9)
- [Q10: Why does the module maintain both a unified Conda environment.yml and a standalone requirements.txt / Dockerfile?](#q10)
- [Q11: Why are both AWS_DEFAULT_REGION and AWS_REGION specified in the .env configuration file?](#q11)
- [Q12: Why is there no persistent .duckdb file on disk, and how does S04 use DuckDB for zero-copy Parquet querying?](#q12)

---

### <span id="q1"></span>🔹 **Q1: How does the deterministic Oracle Primavera P6 XER parser ingest raw schedules without third-party proprietary DLLs?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: In `engine/cpm_engine.py` and `engine/xer_ingestion.py`, S04 implements a native, pure-Python tabular streaming parser for Oracle Primavera P6 XER files. XER files are tab-delimited text files structured into hierarchical database tables denoted by `%T` table header markers, `%F` field definition rows, and `%R` data record rows.

The ingestion pipeline functions as follows:
1. **Header Identification & Validation**: The parser reads the header block to assert encoding (Windows-1252 or UTF-8) and schema revision (e.g., Primavera P6 release 20.12 or 22.12).
2. **Table Isolation**: The engine extracts canonical P6 tables: `CALENDAR` (workday patterns and holidays), `TASK` (activities, durations, and planned dates), `TASKPRED` (predecessor-successor relationships, link types, and lags), and `PROJWBS` (Work Breakdown Structure hierarchies).
3. **Composite Foreign Key Resolution**: In P6 databases, relationships link activities via internal surrogates (`task_id`, `pred_task_id`). S04 reconciles these numeric surrogates against user-defined natural keys (`task_code` or `activity_id`) using an in-memory topological index.
4. **Fail-Closed Structural Checks**: If an activity references an undefined calendar foreign key or if a relationship points to a missing task surrogate, the engine raises an explicit `UnresolvedCalendarError` or `CorruptedTopologyError`, refusing to stage incomplete data.

---

### <span id="q2"></span>🔹 **Q2: What is the exact mathematical formulation and calendar handling behind CPM forward and backward topological passes?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: The Dynamic Calendar CPM Recalculation Engine in `engine/cpm_engine.py` executes strict Critical Path Method (CPM) algorithms over a directed acyclic graph (DAG) `G = (V, E)`:

1. **Topological Sort**: Activities are ordered such that for every directed relationship `(u, v) in E`, activity `u` precedes `v`.
2. **Forward Pass (Early Dates)**:
   - For activities without predecessors: `Early Start (ES) = Planned Project Start Date`.
   - `Early Finish (EF) = AddWorkdays(ES, Duration - 1, Calendar)`.
   - For activity `v` with predecessors `u`:
     - Finish-to-Start (FS): `ES(v) = max(AddWorkdays(EF(u), 1 + lag, Calendar_u))`.
     - Start-to-Start (SS): `ES(v) = max(AddWorkdays(ES(u), lag, Calendar_u))`.
     - Finish-to-Finish (FF): `EF(v) = max(AddWorkdays(EF(u), lag, Calendar_u))`, and `ES(v) = SubtractWorkdays(EF(v), Duration - 1, Calendar_v)`.
     - Start-to-Finish (SF): `EF(v) = max(AddWorkdays(ES(u), lag, Calendar_u))`.
3. **Backward Pass (Late Dates)**:
   - For milestone/terminal activities: `Late Finish (LF) = Project Completion Date`.
   - `Late Start (LS) = SubtractWorkdays(LF, Duration - 1, Calendar)`.
   - For predecessor `u` with successors `v`:
     - `LF(u) = min(SubtractWorkdays(LS(v), 1 + lag, Calendar_u))` for FS links.
4. **Float Calculations**:
   - `Total Float (TF) = DifferenceWorkdays(LS, ES, Calendar) = DifferenceWorkdays(LF, EF, Calendar)`.
   - `Free Float (FF) = min(DifferenceWorkdays(ES(successor), EF, Calendar)) - 1`.
   - Critical Path condition: Any activity where `Total Float <= 0` is flagged as `is_critical = True`.

Multi-calendar support evaluates distinct 5-day, 6-day, and 7-day calendars on individual tasks and relationship lags, preventing calendar drift.

---

### <span id="q3"></span>🔹 **Q3: How does S04 enforce the Fractional Lag and Duration Modulo rejection policy to eliminate synthetic date anomalies?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: Standard construction planning contracts in Singapore (PSSCOC and SIA) define contractual performance in discrete calendar or working days. P6 databases store internal durations in hourly units (e.g. 8 hours = 1 day), which can produce fractional day anomalies (e.g., 14.33 hours = 1.79 days) when planners input ad-hoc timestamps.

In `engine/xer_ingestion.py`:
1. **Modulo Validation**: For every imported activity duration, the engine validates:
   `duration_hours % workday_hours == 0`
   If a non-integral duration is encountered, the ingestion pipeline immediately aborts and raises a `FractionalWorkdayConversionError` rather than rounding arbitrarily.
2. **Relationship Lag Policy (Rule R1)**: Relationship lags are strictly checked against integer day boundaries. Fractional lags (e.g., 2.5 days) are rejected fail-closed.
3. **Zero Synthetic Date Fallbacks**: Fallback dates (such as defaulting missing dates to arbitrary timestamps like 2026-11-02) are strictly prohibited. Missing dates cause immediate validation rejection.

---

### <span id="q4"></span>🔹 **Q4: How does S04 implement SCL Delay and Disruption Protocol Core Principle 10 for concurrent delay apportionment?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: The Society of Construction Law (SCL) Delay and Disruption Protocol (2nd Edition, Core Principle 10) governs concurrent delay: where an Employer Risk Event and a Contractor Risk Event occur simultaneously, and each, in the absence of the other, would delay the Completion Date.

In `engine/fragnet_simulator.py`:
1. **Separation of Relief and Compensation**: Under SCL Protocol Core Principle 10, when true concurrency occurs:
   - The contractor is entitled to an Extension of Time (EOT) to prevent the application of Liquidated Damages (preventing unjust employer penalty).
   - The contractor is NOT entitled to prolong costs or monetary compensation for the period of concurrency (because the contractor would have been on site regardless due to its own culpable delay).
2. **Three-Way Attribution**: S04 classifies every day of critical path drift into one of three buckets:
   - `EMPLOYER_RISK_COMPENSABLE`: Unilateral employer delay (e.g. late possession or major variation); gives both EOT and cost relief.
   - `NEUTRAL_FORCE_MAJEURE`: Inclemency, exceptional rainfall, or unforeseen site conditions; gives EOT relief but no cost compensation.
   - `CONTRACTOR_CULPABLE`: Contractor equipment failure, labor shortage, or defective workmanship; results in zero EOT and accrues Liquidated Damages exposure.
3. **Contemporaneous Telemetry Cross-Check**: Weather radar precipitation logs and biometric turnstile worker counts from `data/parquet/contemporaneous_site_radar.parquet` are cross-referenced to verify if physical site operations were stopped by weather or equipment faults.

---

### <span id="q5"></span>🔹 **Q5: How does the Controlled Time Impact Analysis (TIA) Fragnet Simulator quantify total float erosion and critical path drift?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: Time Impact Analysis (TIA) is the preferred prospective delay analysis methodology endorsed by PSSCOC 2020 Clause 23 and the SCL Delay Protocol. In `engine/fragnet_simulator.py` and FastMCP tool `s04_simulate_tia_fragnet`:

1. **Baseline Snapshot**: The engine loads the unimpacted scheduled baseline `BL-01` from `data/parquet/schedule_activities.parquet` and `data/parquet/schedule_relationships.parquet`.
2. **Subnetwork (Fragnet) Insertion**: A chronological fragnet representing the delay event is inserted:
   - The fragnet specifies `fragnet_name`, `inserted_after_activity_id`, `fragnet_duration_days`, and `risk_allocation`.
   - Predecessor and successor links are re-routed through the fragnet activities.
3. **Dynamic Topological Reschedule**: The full CPM forward and backward passes are re-executed over the impacted network.
4. **Variance Quantification**:
   - `Critical Path Drift = New Project Completion Date - Baseline Project Completion Date`.
   - `Float Erosion = Baseline Total Float - Post-Impact Total Float`.
   - If the impacted activity had positive total float (e.g., 5 days) and the fragnet duration is 3 days, `Critical Path Drift = 0 days` and `Float Erosion = 3 days`. The delay is absorbed by existing float without shifting the project completion date.
   - Once total float reaches zero, any additional delay day shifts the critical completion date 1:1.

---

### <span id="q6"></span>🔹 **Q6: What is the statutory legal foundation and condition precedent mechanism of the PSSCOC Clause 23.1 28-day notice timebar?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: Under PSSCOC 2020 Clause 23.1, if the contractor considers itself entitled to any extension of time for completion of the works, it must give notice in writing to the Superintending Officer (SO) within **28 calendar days** of the occurrence of the delay event.

In Singapore construction law:
1. **Condition Precedent Effect**: Serving notice within the 28-day statutory window is a strict condition precedent to contractual relief. Failure to serve timely notice extinguishes the contractor's entitlement to an EOT.
2. **Automated Notice Verification**: In `mcp_server/server.py` inside `s04_evaluate_delay_event`:
   `days_elapsed = (notice_served_date - event_start_date).days`
3. **Statutory Logic Gate**:
   - If `days_elapsed <= 28`: `is_notice_compliant = True`, notice is labeled `COMPLIANT`, and the claim proceeds to substantive CPM float analysis.
   - If `days_elapsed > 28`: `is_notice_compliant = False`, notice is labeled `TIME-BARRED`. The granted EOT is capped at 0.0 workdays, and the contractor remains fully liable for Liquidated Damages.

---

### <span id="q7"></span>🔹 **Q7: How is Liquidated Damages (LAD) financial exposure modeled deterministically outside the probabilistic LLM path?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: In compliance with the **ACIP Deterministic Execution Boundary**, Large Language Models are strictly prohibited from calculating financial exposure or critical path figures. All mathematical operations are executed by deterministic Python algorithms:

1. **Input Verification**: The engine retrieves the contract daily liquidated damages rate (`daily_ld_rate_sgd`) from the project profile registry (e.g. S$15,000.00/day for Woodlands Health Campus `PRJ-WHC-COM-001`).
2. **Net Culpable Delay Derivation**:
   `contractor_culpable_days = max(0.0, net_critical_delay_days - assessed_eot_workdays)`
3. **Exposure Quantification**:
   `liquidated_damages_exposure_sgd = contractor_culpable_days * daily_ld_rate_sgd`
   For example, in event `DLY-2026-001`:
   - Net Critical Delay = 14.0 days
   - Relief Granted (Neutral Weather) = 2.0 days
   - Contractor Culpable Delay = 12.0 days
   - Daily LAD Rate = S$15,000.00
   - Assessed LAD Exposure = `12 * 15,000 = S$180,000.00`
4. **Advisory Qualifier**: All generated LAD exposure figures are tagged as `INTERNAL_ADVISORY_ESTIMATE`, preserving the sole legal authority of the certified Superintending Officer.

---

### <span id="q8"></span>🔹 **Q8: How does the 3-Agent Adversarial Deliberation Theater operate without hallucinating schedule outcomes?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: The Multi-Agent Deliberation Theater implemented in `engine/deliberation_engine.py` coordinates structured debates among three specialized personas:
1. **Contractor Claims Agent (Claimant)**: Argues for maximum EOT entitlement citing unforeseen site conditions and weather stoppage.
2. **Employer Quantity Surveyor Agent (Respondent)**: Enforces strict Clause 23.1 notice timebars and counter-claims for concurrent contractor culpable equipment downtime.
3. **Superintending Officer Agent (Adjudicator)**: Synthesizes evidence, applies SCL Protocol Core Principle 10, and issues an advisory EOT determination.

**Deterministic Guardrails**:
- The deliberation agents consume pre-calculated CPM floats and TIA metrics from FastMCP deterministic tools.
- The agents cannot alter total float values, shift completion dates, or modify the daily LAD rate.
- LLM outputs are confined to qualitative evaluation narratives, argument positioning, and evidentiary cross-referencing.

---

### <span id="q9"></span>🔹 **Q9: How do the downstream lakehouse Parquet handshakes to S05 Quality and S06 SOPA Claims preserve cryptographic provenance?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: In `engine/handshake_emitters.py`, S04 generates revision-pinned downstream lakehouse tables formatted in Apache Parquet:

1. **S05 Quality Inspection Hold Point Schedule Links**:
   - Destination: `data/parquet/quality_inspection_schedule_links.parquet`
   - Maps 6 critical schedule activities to mandatory Qualified Person (QP) structural inspection hold points and defect risk tiers.
   - Enforces composite foreign key: `(project_id, schedule_version, activity_id)`.
2. **S06 SOPA Formal Claims Delay Links**:
   - Destination: `data/parquet/formal_claims_delay_links.parquet`
   - Links delay event `DLY-2026-001` (Rev 1) to S06 SOPA Section 11 payment dispute triage.
   - Sets `candidate_for_sopa_claim_review = True`, carried claimed EOT of 4.0 workdays, and an illustrative baseline estimate of S$60,000.00.
3. **Cryptographic Integrity Verification**:
   - Every Parquet export is paired with an immutable JSON sidecar manifest (`*_manifest.json`) containing the exact file byte length, generation UTC timestamp, row count, and `SHA-256` digest.
   - If a downstream module encounters a digest mismatch or corrupted binary chunk, ingestion immediately fails closed.

---

### <span id="q10"></span>🔹 **Q10: Why does the module maintain both a unified Conda environment.yml and a standalone requirements.txt / Dockerfile?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: The coexistence of `environment.yml` and `requirements.txt` / `Dockerfile` represents a deliberate separation of concerns between local developer workstation ergonomics and serverless cloud container runtime efficiency:

1. **Local Developer Workstation (Approach 1 & Approach 2)**:
   - All ACIP sub-modules (S01 through S07) share a single, unified Conda environment named `acip_mcp_framework` defined at the repository root (`../environment.yml`).
   - Using a unified Conda environment ensures that binary dependencies (such as DuckDB, PyArrow C++ bindings, and network drivers) are compiled and linked uniformly across macOS (Apple Silicon ARM64) and Linux x86_64 systems without ad-hoc `pip install` conflicts or virtual environment fragmentation.
   - Platform governance strictly prohibits running `pip install` on developer workstations to prevent non-reproducible local environment drift.

2. **Serverless Cloud Container Deployments (Approach 3)**:
   - Cloud container engines (AWS ECS Fargate, Azure Container Apps, Google Cloud Run v2) require standard Open Container Initiative (OCI) images compiled for `linux/amd64`.
   - Installing Miniconda or Anaconda inside a container image inflates the uncompressed image footprint to 3.5GB to 5.0GB, causing unacceptable container cold-start latencies and excessive cloud registry storage charges.
   - The [Dockerfile](Dockerfile) uses a minimal Debian Linux base image (`python:3.11-slim`), copies the application source directories (`dashboard/`, `engine/`, `mcp_server/`, `data/`, `agent_client/`), and installs runtime dependencies via `pip install --no-cache-dir -r requirements.txt`.
   - This keeps the final container image compact (under 400MB), enables sub-second layer caching during incremental CI/CD builds, and ensures rapid autoscaling in production.

---

### <span id="q11"></span>🔹 **Q11: Why are both AWS_DEFAULT_REGION and AWS_REGION specified in the .env configuration file?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: Defining both `AWS_DEFAULT_REGION="ap-southeast-1"` and `AWS_REGION="ap-southeast-1"` in `.env` guarantees 100% interoperability across the heterogeneous tooling ecosystem used throughout S04:

1. **Tooling Precedence & Historical Divergence**:
   - `AWS_DEFAULT_REGION`: Originally introduced with the AWS CLI (`aws`). Shell scripts, CI/CD runners, and older AWS utilities look specifically for `AWS_DEFAULT_REGION` when executing CLI commands such as `aws s3 sync` or `aws ecr get-login-password`.
   - `AWS_REGION`: The official standard adopted across modern AWS SDKs, including Python's `boto3`, the AWS SDK for Go, and the Terraform AWS Provider (`hashicorp/aws`). Furthermore, managed AWS compute runtimes (such as AWS Lambda, AWS ECS Task Definitions, and AWS CodeBuild) automatically inject `AWS_REGION` into their container environments.

2. **Python `boto3` Resolution Hierarchy**:
   When Python code initializes a client (e.g., `boto3.client('bedrock-runtime')`), the SDK evaluates region configuration in the following strict order:
   - Explicit `region_name` passed to the constructor.
   - Environment variable `AWS_REGION`.
   - Environment variable `AWS_DEFAULT_REGION`.
   - Configuration files (`~/.aws/config`).
   - Amazon ECS task metadata or EC2 instance metadata service (IMDS).

3. **Preventing Silent Failures in Automation**:
   If only `AWS_REGION` is set, certain AWS CLI subcommands fail or fallback to `us-east-1`. Conversely, if only `AWS_DEFAULT_REGION` is set, third-party libraries or modern SDK wrappers may fail to resolve the region and throw unhandled `NoRegionError` exceptions. Setting both variables explicitly to `"ap-southeast-1"` ensures that CLI operations, Terraform automation, and Python Bedrock callers authenticate without regional ambiguity.

---

### <span id="q12"></span>🔹 **Q12: Why is there no persistent .duckdb file on disk, and how does S04 use DuckDB for zero-copy Parquet querying?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: In S04, DuckDB is deployed strictly as an embedded, in-memory analytical query engine rather than an on-disk database file:

1. **Architectural Separation of Storage and Compute**:
   - In earlier iterations (and in modules like S03), DuckDB maintained an on-disk catalog file (e.g., `data/commercial_control.duckdb`). However, maintaining a persistent `.duckdb` file introduces concurrent file-lock contention (`duckdb.IOException: IO Error: Cannot open file... being used by another process`) whenever multiple FastMCP server workers, HTTP dashboard processes, or unittest runners attempt concurrent access.
   - S04 decouples storage from compute: all authoritative datasets reside exclusively as immutable Apache Parquet columnar files under `data/parquet/` (such as `schedule_activities.parquet`, `delay_events.parquet`, `calendars.parquet`).

2. **In-Memory Connection Semantics (`con = duckdb.connect()`)**:
   - In `mcp_server/server.py`, `engine/handshake_emitters.py`, and `agent_client/deliberation_pipeline.py`, every DuckDB connection initializes an ephemeral, in-memory instance via `duckdb.connect()` or `duckdb.connect(database=":memory:")`.
   - DuckDB directly scans and filters the Parquet partitions at the C++ layer using zero-copy memory mapping (`SELECT ... FROM 'data/parquet/schedule_activities.parquet' WHERE project_id = ?`).
   - This eliminates persistent file corruption, bypasses OS file-locking limits, and allows parallel unittests and HTTP threads to execute concurrent analytical SQL queries without blocking.

3. **Lakehouse State Reset Semantics**:
   - Because no `.duckdb` catalog file is generated, cleaning up local state does not involve deleting a database file.
   - To reset the S04 lakehouse to its clean authoritative state, the ingestion adapter `python engine/xer_ingestion_pipeline.py` reads the pristine source Oracle Primavera P6 XER baseline schedules from `data/xer/` and atomically overwrites the Parquet partitions with validated cryptographic manifests.

