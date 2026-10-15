# <span style="color:red">🔧 10. Troubleshooting Guide</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](README.md#toc)</span>

This guide covers categorized issues, symptoms, root causes, and verified resolutions encountered when deploying and running the S04 Agentic Progress & Delay Intelligence module across local development environments and multi-cloud container runtimes.

---

## <span id="troubleshooting-toc"></span>📑 Table Of Contents (TOC)

- [10.1 Schedule Parsing & Topological CPM Ingestion Issues](#cat-10-1)
  - [10.1.1 Non-Integral Activity Duration Triggers FractionalWorkdayConversionError](#issue-10-1-1)
  - [10.1.2 Unresolved Calendar Foreign Key Triggers Ingestion Failure](#issue-10-1-2)
  - [10.1.3 Cyclic Relationship Dependency in Schedule Network](#issue-10-1-3)
- [10.2 Lakehouse Parquet & DuckDB Storage Issues](#cat-10-2)
  - [10.2.1 DuckDB Database Locked by Concurrent Process](#issue-10-2-1)
  - [10.2.2 SHA-256 Manifest Checksum Mismatch on Downstream Lakehouse Parquet](#issue-10-2-2)
- [10.3 Dashboard Server & Multi-Cloud Networking Issues](#cat-10-3)
  - [10.3.1 Address Already in Use on Port 8087 (OSError: [Errno 48])](#issue-10-3-1)
  - [10.3.2 AWS ECS Fargate 503 Service Unavailable (Docker Architecture Mismatch)](#issue-10-3-2)
  - [10.3.3 Azure Container Apps Initial Provisioning Fails with MANIFEST_UNKNOWN](#issue-10-3-3)
  - [10.3.4 Google Cloud Run Ingress Target Port Mismatch](#issue-10-3-4)

---

## <span id="cat-10-1"></span>⏱️ 10.1 Schedule Parsing & Topological CPM Ingestion Issues <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

### <span id="issue-10-1-1"></span>❌ 10.1.1 Non-Integral Activity Duration Triggers FractionalWorkdayConversionError <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `engine.exceptions.FractionalWorkdayConversionError: Non-integral workday duration detected: activity 'ACT-03' has 18.5 hours (expected modulo 8.0 == 0). Aborting fail-closed.`

**Symptom**: Ingestion of a raw Primavera P6 XER file halts immediately during table validation.

**Cause**: The source P6 schedule contains an ad-hoc duration entered in hours rather than discrete working days. S04 enforces a strict integer-day boundary policy to prevent synthetic fractional-day calendar drift.

**Solution**: Sanitize the duration in the source schedule to an exact multiple of the workday hours (e.g. 16.0 or 24.0 hours for an 8-hour shift calendar) before executing ingestion.

#### Before (Code causing the error in `engine/xer_ingestion.py`):
```python
# Raw import without modulo check allowed fractional day drift
duration_days = float(row["target_drtn_hr_cnt"]) / 8.0
```

#### After (Corrected code in `engine/xer_ingestion.py`):
```python
# Strict fail-closed modulo assertion enforces discrete-day compliance
hours = float(row["target_drtn_hr_cnt"])
if hours % workday_hours != 0.0:
    raise FractionalWorkdayConversionError(
        f"Non-integral workday duration detected: activity '{task_id}' has {hours} hours"
    )
duration_days = int(hours // workday_hours)
```

---

### <span id="issue-10-1-2"></span>❌ 10.1.2 Unresolved Calendar Foreign Key Triggers Ingestion Failure <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `engine.exceptions.UnresolvedCalendarError: Activity 'ACT-05' references calendar_id 'CAL-UNKNOWN-99' which is missing from CALENDAR table.`

**Symptom**: Parsing fails with an unhandled calendar foreign key exception.

**Cause**: The XER export omitted the global calendar definition, or an activity references a project-specific calendar that was deleted.

**Solution**: Ensure the XER export includes all referenced calendar tables, or apply the authoritative default project calendar (`CAL-WHC-STANDARD-5D`) during preflight validation.

#### Before (Code causing the error in `engine/xer_ingestion.py`):
```python
# Unchecked dictionary lookup crashes with KeyError
cal = calendar_lookup[row["clndr_id"]]
```

#### After (Corrected code in `engine/xer_ingestion.py`):
```python
# Fallback to project default with strict warning or fail-closed on explicit invalid ID
cal_id = row.get("clndr_id")
if not cal_id or cal_id not in calendar_lookup:
    if default_calendar_id in calendar_lookup:
        cal = calendar_lookup[default_calendar_id]
    else:
        raise UnresolvedCalendarError(f"Activity '{task_id}' references invalid calendar '{cal_id}'")
else:
    cal = calendar_lookup[cal_id]
```

---

### <span id="issue-10-1-3"></span>❌ 10.1.3 Cyclic Relationship Dependency in Schedule Network <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `engine.exceptions.CyclicDependencyError: Schedule graph contains a cycle: ACT-02 -> ACT-04 -> ACT-02.`

**Symptom**: Topological sorting raises a cyclic dependency error during CPM forward pass computation.

**Cause**: Contradictory predecessor-successor logic exists in the schedule network, creating an infinite loop.

**Solution**: Inspect the network using Kahn's algorithm in `engine/cpm_engine.py` to isolate and remove the circular link.

#### Before (Code causing the error in `engine/cpm_engine.py`):
```python
# Unprotected recursion causing RecursionError on circular graph
def forward_pass(node):
    for pred in predecessors[node]:
        forward_pass(pred)
```

#### After (Corrected code in `engine/cpm_engine.py`):
```python
# Kahn's algorithm detects cycles in O(V + E) time
in_degree = {u: 0 for u in activities}
for u, v in relationships:
    in_degree[v] += 1
queue = [u for u in activities if in_degree[u] == 0]
sorted_nodes = []
while queue:
    u = queue.pop(0)
    sorted_nodes.append(u)
    for v in successors[u]:
        in_degree[v] -= 1
        if in_degree[v] == 0:
            queue.append(v)
if len(sorted_nodes) != len(activities):
    raise CyclicDependencyError("Schedule graph contains a cycle")
```

---

## <span id="cat-10-2"></span>💾 10.2 Lakehouse Parquet & DuckDB Storage Issues <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

### <span id="issue-10-2-1"></span>🔒 10.2.1 DuckDB Database Locked by Concurrent Process <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `duckdb.duckdb.IOException: IO Error: Cannot open file "data/progress_delay.duckdb": The process cannot access the file because it is being used by another process.`

**Symptom**: Launching the dashboard server fails while unit tests or another process are running.

**Cause**: DuckDB single-writer file locking prevents multiple processes from opening the same `.duckdb` file concurrently in read-write mode.

**Solution**: Open DuckDB connections in read-only mode (`read_only=True`), or query Apache Parquet files directly under `data/parquet/` using in-memory DuckDB sessions.

#### Before (Code causing the error in `mcp_server/server.py`):
```python
# Unprotected persistent file connection blocks concurrent analytical queries
con = duckdb.connect("data/progress_delay.duckdb")
result = con.execute("SELECT * FROM schedule_activities").fetchall()
```

#### After (Corrected code in `mcp_server/server.py`):
```python
# Connect in-memory and query Apache Parquet lakehouse partitions directly with zero file-locking
con = duckdb.connect()
try:
    result = con.execute("SELECT * FROM 'data/parquet/schedule_activities.parquet'").fetchall()
finally:
    con.close()
```

---

### <span id="issue-10-2-2"></span>🔐 10.2.2 SHA-256 Manifest Checksum Mismatch on Downstream Lakehouse Parquet <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `engine.exceptions.ManifestIntegrityError: SHA-256 digest mismatch for quality_inspection_schedule_links.parquet: expected '81e62081...' but computed '38706ada...'.`

**Symptom**: Downstream modules (S05 or S06) reject the handoff package during preflight verification.

**Cause**: The Parquet binary file was regenerated by a fresh test run without updating the companion JSON manifest.

**Solution**: Regenerate both the Parquet binary and the cryptographic sidecar manifest atomically using `engine/handshake_emitters.py`.

#### Before (Code causing the error in `engine/handshake_emitters.py`):
```python
# Writing parquet without updating manifest leaves stale checksum
pq.write_table(table, "data/parquet/quality_inspection_schedule_links.parquet")
```

#### After (Corrected code in `engine/handshake_emitters.py`):
```python
# Atomic write with SHA-256 digest generation
pq.write_table(table, parquet_path)
with open(parquet_path, "rb") as f:
    sha256_digest = hashlib.sha256(f.read()).hexdigest()
manifest = {
    "package_sha256": sha256_digest,
    "output_package_sha256": sha256_digest,
    "row_count": len(table),
    "generated_at_utc": datetime.now(timezone.utc).isoformat()
}
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2)
```

---

## <span id="cat-10-3"></span>🌐 10.3 Dashboard Server & Multi-Cloud Networking Issues <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

### <span id="issue-10-3-1"></span>🚪 10.3.1 Address Already in Use on Port 8087 (OSError: [Errno 48]) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `OSError: [Errno 48] Address already in use`

**Symptom**: `python dashboard/server.py --port 8087` terminates immediately on launch.

**Cause**: A previously spawned dashboard server or background test process is holding Port 8087.

**Solution**: Identify and terminate the lingering process on Port 8087:
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
lsof -ti :8087 | xargs kill -9
```

---

### <span id="issue-10-3-2"></span>🏗️ 10.3.2 AWS ECS Fargate 503 Service Unavailable (Docker Architecture Mismatch) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `HTTP 503 Service Temporarily Unavailable` on AWS ALB endpoint; ECS task stops with `CannotPullContainerError: platform 'linux/amd64' mismatch`.

**Symptom**: The AWS Application Load Balancer returns 503, and target group health checks fail continuously.

**Cause**: The Docker image was built on an Apple Silicon (M1/M2/M3/M4) macOS workstation without specifying `--platform linux/amd64`, producing an ARM64 binary that cannot execute on AWS Fargate x86_64 runtimes.

**Solution**: Always pass `--platform linux/amd64` when building Docker images:

#### Before (Command causing the error):
```bash
# Produced ARM64 image on macOS host
docker build -t ${ECR_URL}:latest .
```

#### After (Corrected command):
```bash
# Explicitly compile for Linux x86_64 architecture
docker build --platform linux/amd64 -t ${ECR_URL}:latest .
```

---

### <span id="issue-10-3-3"></span>📦 10.3.3 Azure Container Apps Initial Provisioning Fails with MANIFEST_UNKNOWN <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `Resource deployment failed: Container app failed to start: MANIFEST_UNKNOWN: manifest unknown`.

**Symptom**: Step 1 `terraform apply` on Azure fails immediately.

**Cause**: The Terraform template pointed directly to the Azure Container Registry (ACR) image repository before the user had built and pushed the container. Because the ACR repository is completely empty, the container runtime crashes.

**Solution**: Default `var.docker_image` in `terraform/azure/variables.tf` to the public bootstrap image `mcr.microsoft.com/azuredocs/containerapps-helloworld:latest`. Deploy the real image in Step 3 after `docker push`.

#### Before (Code causing the error in `terraform/azure/variables.tf`):
```terraform
# Pointing to unpushed ACR image causes MANIFEST_UNKNOWN
variable "docker_image" {
  default = "acips04acrprod.azurecr.io/acip-s04-delay-engine:latest"
}
```

#### After (Corrected code in `terraform/azure/variables.tf`):
```terraform
# Public bootstrap image succeeds reliably in Step 1
variable "docker_image" {
  default = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
}
```

---

### <span id="issue-10-3-4"></span>☁️ 10.3.4 Google Cloud Run Ingress Target Port Mismatch <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `Google Cloud Run container failed to start and listen on the port defined by the PORT environment variable (port 8080).`

**Symptom**: Google Cloud Run deployment fails during service provisioning with a health check timeout.

**Cause**: Google Cloud Run reserves the `PORT` environment variable and defaults it to 8080 unless configured. If S04 listens only on 8087, the runtime health probe fails.

**Solution**: Configure `dashboard/server.py` to read `os.environ.get("PORT", 8087)` and ensure `ports { container_port = var.app_port }` in `terraform/gcp/main.tf` matches.
