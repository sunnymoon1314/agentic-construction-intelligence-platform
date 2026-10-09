# <span style="color:red">🔧 10. Troubleshooting Guide</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](README.md#toc)</span>

This guide covers categorized issues, symptoms, root causes, and verified resolutions encountered when deploying and running the S03 Agentic Cost & Commercial Control Platform across local development environments and multi-cloud serverless container runtimes.

---

## <span id="troubleshooting-toc"></span>📑 Table Of Contents (TOC)

- [10.1 Database & Lakehouse Storage Issues](#cat-10-1)
  - [10.1.1 DuckDB Database Locked by Concurrent Process](#issue-10-1-1)
  - [10.1.2 HTTPFS Extension Missing When Querying Cloud Parquet Lakehouse](#issue-10-1-2)
  - [10.1.3 Table Not Found During Multi-Project Dropdown Switching](#issue-10-1-3)
  - [10.1.4 Azure CLI Blob Upload Missing Data-Plane Permissions (Storage Blob Data Contributor)](#issue-10-1-4)
- [10.2 Commercial & Statutory Computation Logic Issues](#cat-10-2)
  - [10.2.1 PSSCOC Clause 19.1 28-Day Timebar Disallows 100% of Legitimate Works](#issue-10-2-1)
  - [10.2.2 Star Rate Duplication Flag Triggers Compulsory Tier 1 Fallback](#issue-10-2-2)
  - [10.2.3 openBIM Physical Takeoff Discrepancy Exceeds 2.0% Tolerance](#issue-10-2-3)
  - [10.2.4 Statutory SOPA Deadline Clock Reaches Zero or Negative Days](#issue-10-2-4)
- [10.3 Dashboard Server & Networking Issues](#cat-10-3)
  - [10.3.1 Address Already in Use on Port 8086 (OSError: [Errno 48])](#issue-10-3-1)
  - [10.3.2 Azure Container Apps Target Port Ingress Mismatch](#issue-10-3-2)
  - [10.3.3 AWS ECS Fargate 503 Service Temporarily Unavailable (Docker Platform Architecture Mismatch)](#issue-10-3-3)
  - [10.3.4 Google Cloud Run Reserved Environment Variable PORT Violation (Error 400)](#issue-10-3-4)
  - [10.3.5 Azure Container Apps Initial Apply Fails with MANIFEST_UNKNOWN (Unpushed Registry Image)](#issue-10-3-5)
  - [10.3.6 Azure Container App Already Exists After Interrupted Apply](#issue-10-3-6)

---

## <span id="cat-10-1"></span>💾 10.1 Database & Lakehouse Storage Issues <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

### <span id="issue-10-1-1"></span>🔒 10.1.1 DuckDB Database Locked by Concurrent Process <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `duckdb.duckdb.IOException: IO Error: Cannot open file "data/commercial_control.duckdb": The process cannot access the file because it is being used by another process.`

**Symptom**: Running the seeding script, launching the dashboard, or executing unit tests fails with an unhandled DuckDB file lock exception.

**Cause**: DuckDB enforces an exclusive single-writer file lock when opened in read-write mode. If an interactive session or previous evaluation process remains running without terminating its connection, subsequent analytical operations are blocked.

**Solution**: Use `duckdb.connect(DB_PATH, read_only=True)` for analytical queries or rely on the stateless Approach 3 Apache Parquet partitioned lakehouse under `data/parquet/` which allows unlimited parallel readers.

#### Before (Code causing the error in `mcp_server/server.py`):
```python
# Unprotected read-write connection blocks concurrent analytical queries
con = duckdb.connect("data/commercial_control.duckdb")
result = con.execute("SELECT * FROM projects").fetchall()
```

#### After (Corrected code in `mcp_server/server.py`):
```python
# Open as read-only or query in-memory connection over Parquet
con = duckdb.connect("data/commercial_control.duckdb", read_only=True)
try:
    result = con.execute("SELECT * FROM projects").fetchall()
finally:
    con.close()
```

---

### <span id="issue-10-1-2"></span>☁️ 10.1.2 HTTPFS Extension Missing When Querying Cloud Parquet Lakehouse <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `duckdb.CatalogException: Catalog Error: Table Function with name read_parquet does not support remote filesystem "s3://"`

**Symptom**: When `COMMERCIAL_LAKE_BUCKET` is configured to point to an S3 bucket or Google Cloud Storage bucket, running `reconcile_progress_valuation` or `generate_sopa_response` raises an unhandled filesystem exception.

**Cause**: DuckDB requires the `httpfs` extension to query remote object storage endpoints over HTTP/HTTPS. In minimal container environments, this extension must be explicitly installed and loaded.

**Solution**: Update `get_connection()` in `mcp_server/server.py` to install and load `httpfs` whenever `COMMERCIAL_LAKE_BUCKET` is populated.

#### Before (Code causing the error in `mcp_server/server.py`):
```python
def get_connection():
    # In-memory connection without httpfs cannot read remote object storage
    return duckdb.connect()
```

#### After (Corrected code in `mcp_server/server.py`):
```python
def get_connection():
    con = duckdb.connect()
    cloud_bucket = os.getenv("COMMERCIAL_LAKE_BUCKET")
    if cloud_bucket:
        try:
            con.execute("INSTALL httpfs; LOAD httpfs;")
        except Exception as e:
            print(f"Warning: Failed to load httpfs: {e}")
    return con
```

---

### <span id="issue-10-1-3"></span>📋 10.1.3 Table Not Found During Multi-Project Dropdown Switching <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `ValueError: PROJECT_NOT_FOUND: Project 'PRJ-JID-ATP-004' has no EVM telemetry data.`

**Symptom**: Selecting Jurong Innovation District (PRJ-JID-ATP-004) or Marina Bay Financial Tower (PRJ-MBF-FIT-002) in the dashboard dropdown causes the UI to crash or display an empty EVM chart.

**Cause**: Baseline data was initially seeded only for the flagship scenario (`PRJ-WHC-COM-001`), leaving secondary projects without records in `cost_forecast_eac` or `interim_claims`.

**Solution**: Ensure `data/generate_commercial_data.py` populates complete baseline records for all four projects and exports them to `data/parquet/*.parquet`.

#### Before (Code causing the error in `data/generate_commercial_data.py`):
```python
# Only Woodlands Health Campus was inserted into cost_forecast_eac
con.execute("INSERT INTO cost_forecast_eac VALUES (?, ?, ...)", [
    CONTRACT_BASELINE_WHC["project_id"], 8, 52380952.38, ...
])
```

#### After (Corrected code in `data/generate_commercial_data.py`):
```python
# Loop across all scenario projects to guarantee complete EVM records
for pid, pdata in PROJECT_SCENARIOS.items():
    cf = pdata["cost_forecast_eac"]
    con.execute("INSERT INTO cost_forecast_eac VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        pid, cf[0], cf[1], cf[2], cf[3], cf[4], cf[5], cf[6], cf[7], cf[8], cf[9], cf[10]
    ])
```

---

### <span id="issue-10-1-4"></span>☁️ 10.1.4 Azure CLI Blob Upload Missing Data-Plane Permissions (Storage Blob Data Contributor) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `You do not have the required permissions needed to perform this operation. Depending on your operation, you may need to be assigned one of the following roles: "Storage Blob Data Owner", "Storage Blob Data Contributor"`

**Symptom**: Running `az storage blob upload-batch` with `--auth-mode login` fails with a permission denied error, blocking Parquet lakehouse synchronization in Step 2.

**Cause**: By default, Azure subscription administrators and management-plane owners do not possess data-plane RBAC roles (`Storage Blob Data Contributor`) on newly created Storage Accounts. Using `--auth-mode login` forces Entra ID data-plane role validation.

**Solution**: Switch the authentication mode to `--auth-mode key`. This instructs the Azure CLI to authenticate the blob upload using the Storage Account's access key retrieved via ARM management plane permissions.

#### Before (Failing code using Entra ID data-plane authentication in `README.md`):
```bash
az storage blob upload-batch \
  --account-name ${STORAGE_ACCOUNT} \
  --destination ${CONTAINER_NAME}/parquet \
  --source data/parquet \
  --auth-mode login
```

#### After (Corrected code using account key authentication in `README.md`):
```bash
az storage blob upload-batch \
  --account-name ${STORAGE_ACCOUNT} \
  --destination ${CONTAINER_NAME}/parquet \
  --source data/parquet \
  --auth-mode key
```

---

## <span id="cat-10-2"></span>⚖️ 10.2 Commercial & Statutory Computation Logic Issues <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

### <span id="issue-10-2-1"></span>⏳ 10.2.1 PSSCOC Clause 19.1 28-Day Timebar Disallows 100% of Legitimate Works <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `TIMEBAR_EXPIRED_CLAIM_WAIVED: Full claimed sum of S$73,500.00 rejected on VO-WHC-012.`

**Symptom**: The contractor submits formal dispute correspondence arguing that extra works were verbally instructed on site and certified as physically necessary by the Resident Technical Officer (RTO).

**Cause**: PSSCOC Clause 19.1 requires written notice within 28 calendar days of the Superintending Officer's instruction as a condition precedent. Verbal authorizations or site chits do not waive the contractual timebar.

**Solution**: Maintain the statutory withholding under Section 11 of SOPA to preserve the Employer's legal position. If the Superintending Officer formally waives the timebar in writing, update the record's `claim_notice_date` to reflect the waived notice date.

#### Before (Code enforcing strict contractual timebar in `mcp_server/server.py`):
```python
days_elapsed = (notice_d - inst_d).days
if days_elapsed > 28:
    return {
        "timebar_status": "TIMEBAR_EXPIRED_CLAIM_WAIVED",
        "certified_amount": 0.0,
        "deduction_disallowed": claimed_amount
    }
```

#### After (Handling verified SO written waivers):
```python
days_elapsed = (notice_d - inst_d).days
so_waiver_granted = check_superintending_officer_waiver(vo_id)
if days_elapsed > 28 and not so_waiver_granted:
    return {
        "timebar_status": "TIMEBAR_EXPIRED_CLAIM_WAIVED",
        "certified_amount": 0.0,
        "deduction_disallowed": claimed_amount
    }
```

---

### <span id="issue-10-2-2"></span>🏷️ 10.2.2 Star Rate Duplication Flag Triggers Compulsory Tier 1 Fallback <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `RATE_DUPLICATION_DETECTED: Proposed Tier 3 Star Rate S$380.00 rejected. Fallback to SOR rate S$240.00 enforced.`

**Symptom**: A contractor variation claim (such as VO-WHC-001) has its valuation reduced by S$49,000.00 because the engine detects an identical item in the Schedule of Rates (SOR).

**Cause**: The contractor proposed a Tier 3 Star Rate for an item that is already defined in the baseline contract Schedule of Rates (`STR-02-004`). Under PSSCOC Clause 19, Tier 3 Star Rates are only permissible when work is of fundamentally different character or executed under different conditions.

**Solution**: Verify whether the work character has fundamentally changed. If it is standard contract work, enforce Tier 1 fallback. If it is fundamentally different, assign a unique item code that does not match baseline codes.

#### Before (Allowing unchecked Star Rates in `mcp_server/server.py`):
```python
# Unchecked valuation accepted contractor-proposed rate directly
certified_amount = quantity * proposed_rate
```

#### After (Corrected code in `mcp_server/server.py`):
```python
# Anti-fraud query checks baseline SOR code before accepting Tier 3 Star Rate
matching_sor = con.execute(f"SELECT contract_sor_rate FROM {sor_source} WHERE item_code = '{item_code}'").fetchone()
if matching_sor and proposed_tier == "TIER_3_STAR_RATE":
    fraud_flag = "RATE_DUPLICATION_DETECTED"
    authoritative_rate = matching_sor[0]
    certified_amount = quantity * authoritative_rate
    deduction_disallowed = contractor_claimed_amount - certified_amount
```

---

### <span id="issue-10-2-3"></span>📐 10.2.3 openBIM Physical Takeoff Discrepancy Exceeds 2.0% Tolerance <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `FLAGGED_OVER_CERTIFICATION: Disallowance of S$312,000.00 enforced on item STR-02-004.`

**Symptom**: The contractor claimed 7,800 m3 of concrete columns, but the openBIM model verified only 6,500 m3 installed, triggering an over-certification disallowance.

**Cause**: Contractor claimed 91.76% completion based on forward procurement orders rather than in-situ cast concrete elements. Under Singapore SOPA Section 15, uninstalled off-site materials cannot be certified unless specifically covered under unfixed materials provisions.

**Solution**: Inspect site reality-capture laser scans and IFC 5D models to confirm physical installation. Only certified volumes physically installed on site are approved.

#### Before (Approving percentage claims without 5D verification):
```python
# Unverified certification accepts contractor claimed quantity
certified_qty = contractor_claimed_qty
```

#### After (Corrected code in `mcp_server/server.py`):
```python
# Reality-capture verification cross-examines contractor claim
discrepancy_qty = max(0.0, contractor_claimed_qty - openbim_verified_qty)
variance_pct = (discrepancy_qty / openbim_verified_qty) * 100.0
if variance_pct > 2.0:
    disallowed_amount = discrepancy_qty * contract_unit_rate
    discrepancy_status = "FLAGGED_OVER_CERTIFICATION"
```

---

### <span id="issue-10-2-4"></span>🚨 10.2.4 Statutory SOPA Deadline Clock Reaches Zero or Negative Days <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `CRITICAL_STATUTORY_RISK: 0 business days remaining to serve formal Section 11 Payment Response.`

**Symptom**: The live countdown widget displays red emergency status, warning that statutory waiver is imminent.

**Cause**: Interim Claim was served more than 14 business days ago, or public holidays were incorrectly omitted from the calendar engine calculation.

**Solution**: Immediately dispatch the generated Formal Section 11 Payment Response dossier to the main contractor via registered delivery and email to prevent default adjudication judgment under SOPA Section 17.

---

## <span id="cat-10-3"></span>🌐 10.3 Dashboard Server & Networking Issues <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

### <span id="issue-10-3-1"></span>🔌 10.3.1 Address Already in Use on Port 8086 (OSError: [Errno 48]) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `OSError: [Errno 48] Address already in use`

**Symptom**: Running `python3 dashboard/server.py --port 8086` fails immediately with an address binding error.

**Cause**: A previous server instance is still bound to port 8086, or the socket remains in `TIME_WAIT` state.

**Solution**: Allow address reuse on the TCP server via `TCPServer.allow_reuse_address = True`, or kill the orphan process holding the port using `lsof -ti :8086 | xargs kill -9`.

#### Before (Code causing socket binding lock in `dashboard/server.py`):
```python
# Default TCPServer does not enable socket reuse
with socketserver.TCPServer(("", port), CommercialDashboardHandler) as httpd:
    httpd.serve_forever()
```

#### After (Corrected code in `dashboard/server.py`):
```python
# Enable socket reuse to prevent TIME_WAIT port binding conflicts
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", port), CommercialDashboardHandler) as httpd:
    httpd.serve_forever()
```

---

### <span id="issue-10-3-2"></span>☁️ 10.3.2 Azure Container Apps Target Port Ingress Mismatch <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `502 Bad Gateway: The container application did not respond to the ingress controller.`

**Symptom**: Navigating to `https://${CONTAINER_APP_FQDN}` produces an HTTP 502 Bad Gateway error.

**Cause**: The Azure Container App configuration set `target_port = 80` while the containerized dashboard was listening on port 8086.

**Solution**: Align the Terraform `target_port` attribute with the container's `PORT` environment variable (`8086`).

#### Before (Code in `terraform/azure/main.tf`):
```terraform
ingress {
  external_enabled = true
  target_port      = 80 # Mismatch: Container listens on 8086!
}
```

#### After (Corrected code in `terraform/azure/main.tf`):
```terraform
ingress {
  external_enabled = true
  target_port      = var.app_port # Correctly configured to 8086
}
```

---

### <span id="issue-10-3-3"></span>🐳 10.3.3 AWS ECS Fargate 503 Service Temporarily Unavailable (Docker Platform Architecture Mismatch) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `CannotPullContainerError: pull image manifest has been retried 7 time(s): image Manifest does not contain descriptor matching platform 'linux/amd64'` / ALB responds with `503 Service Temporarily Unavailable`

**Symptom**: Navigating to `http://${ALB_URL}:8086` returns an HTTP 503 error immediately after running `terraform apply` and pushing the container image to Amazon ECR. Querying stopped ECS tasks reports `TaskFailedToStart`.

**Cause**: Compiling the Docker container on Apple Silicon macOS (`arm64`) defaults to the host machine architecture (`linux/arm64`). AWS ECS Fargate defaults to `linux/amd64` (x86_64). When Fargate attempts to pull the image from ECR, it rejects the manifest due to the architecture mismatch. Because zero containers can start, the ALB target group has zero healthy targets and responds with HTTP 503.

**Solution**: Always supply the explicit `--platform linux/amd64` flag when executing `docker build` on macOS prior to pushing to ECR, and trigger a forced new deployment on the ECS service.

#### Before (Code causing the error in `README.md`):
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a
ECR_URL=$(cd terraform/aws && terraform output -raw ecr_repository_url)

# Missing platform flag builds ARM64 on Apple Silicon Macs, breaking ECS Fargate
docker build -t ${ECR_URL}:latest .
docker push ${ECR_URL}:latest
```

#### After (Corrected code in `README.md`):
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a
ECR_URL=$(cd terraform/aws && terraform output -raw ecr_repository_url)
CLUSTER=$(cd terraform/aws && terraform output -raw ecs_cluster_name)

# Explicitly target linux/amd64 to match AWS ECS Fargate x86_64 architecture
docker build --platform linux/amd64 -t ${ECR_URL}:latest .
docker push ${ECR_URL}:latest
aws ecs update-service --cluster ${CLUSTER} --service acip-s03-commercial-service-prod --force-new-deployment
```

---

### <span id="issue-10-3-4"></span>☁️ 10.3.4 Google Cloud Run Reserved Environment Variable PORT Violation (Error 400) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `googleapi: Error 400: template.containers[0].env: The following reserved env names were provided: PORT. These values are automatically set by the system.`

**Symptom**: Executing `terraform apply` in `terraform/gcp` fails during the creation or update of the `google_cloud_run_v2_service` resource.

**Cause**: Google Cloud Run automatically manages and injects the `PORT` environment variable into the container based on the `ports { container_port = var.app_port }` block. Explicitly declaring `PORT` inside the `env { ... }` block triggers an API validation conflict because Google Cloud Run treats `PORT` as a reserved keyword.

**Solution**: Remove the explicit `PORT` declaration from the `env` blocks in `terraform/gcp/main.tf`. The container port is declared via the `ports` block, and Cloud Run injects `PORT` into the running container automatically.

#### Before (Code causing the error in `terraform/gcp/main.tf`):
```terraform
ports {
  container_port = var.app_port
}

# Explicit PORT env block triggers Google Cloud Run 400 error
env {
  name  = "PORT"
  value = tostring(var.app_port)
}
```

#### After (Corrected code in `terraform/gcp/main.tf`):
```terraform
# ports block defines the listening port; Cloud Run injects PORT automatically
ports {
  container_port = var.app_port
}
```

---

### <span id="issue-10-3-5"></span>☁️ 10.3.5 Azure Container Apps Initial Apply Fails with MANIFEST_UNKNOWN (Unpushed Registry Image) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `Status: "Failed" Code: "ContainerAppOperationError" Message: "Failed to provision revision for container app 'acip-s03-commercial-cockpit'. Field 'template.containers.acip-s03-commercial-cockpit.image' is invalid with details: 'Invalid value: \"acips03acrprod.azurecr.io/acip-s03-commercial-engine:latest\": GET https:: MANIFEST_UNKNOWN: manifest tagged by \"latest\" is not found'"`

**Symptom**: During Step 1 `terraform apply`, Terraform successfully creates the Resource Group, Storage Account, and Azure Container Registry (ACR), but fails when creating `azurerm_container_app.commercial_app`.

**Cause**: In Step 1, ACR has just been provisioned and contains zero Docker images because the container has not yet been built or pushed (which happens in Step 3). Pointing `image` directly to the empty ACR repository in Step 1 causes Azure to attempt pulling a nonexistent manifest, resulting in a provisioning failure.

**Solution**: Follow the proven S01/S02 parity standard by declaring a bootstrap image default in `terraform/azure/variables.tf` (`mcr.microsoft.com/azuredocs/containerapps-helloworld:latest`) and assigning `image = var.docker_image` in `terraform/azure/main.tf`. Step 1 provisions cleanly with the bootstrap image, and Step 4 (`az containerapp update`) deploys the real application image once pushed to ACR in Step 3.

#### Before (Code causing the error in `terraform/azure/main.tf`):
```terraform
container {
  name  = "acip-s03-commercial-cockpit"
  # Hardcoding ACR image before push in Step 3 causes MANIFEST_UNKNOWN error in Step 1
  image = "${azurerm_container_registry.acr.login_server}/acip-s03-commercial-engine:latest"
}
```

#### After (Corrected code in `terraform/azure/main.tf` and `variables.tf`):
```terraform
# variables.tf: Default to public bootstrap image
variable "docker_image" {
  description = "Initial container image for bootstrap"
  type        = string
  default     = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
}

# main.tf: Use var.docker_image for clean Step 1 provisioning
container {
  name  = "acip-s03-commercial-cockpit"
  image = var.docker_image
}
```

---

### <span id="issue-10-3-6"></span>☁️ 10.3.6 Azure Container App Already Exists After Interrupted Apply <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `Error: A resource with the ID ".../providers/Microsoft.App/containerApps/acip-s03-commercial-cockpit" already exists - to be managed via Terraform this resource needs to be imported into the State.`

**Symptom**: Re-running `terraform apply` fails immediately during `azurerm_container_app.commercial_app: Creating...`.

**Cause**: The prior failed `terraform apply` registered the Container App name with the Azure resource group before aborting, but because the provisioning operation exited with an error, Terraform never wrote the resource into `terraform.tfstate`. On subsequent apply runs, Terraform attempts to create a brand new resource with that same name, colliding with the orphaned Azure entity.

**Solution**: Delete the orphaned container app using the Azure CLI so Terraform can provision it cleanly from scratch with the bootstrap image:

#### Before (Failing state where orphaned resource blocks Terraform):
```bash
# Rerunning apply fails with 'already exists' collision
terraform apply -auto-approve
```

#### After (Delete orphaned resource before clean apply):
```bash
# Delete the unmanaged orphaned container app entity
az containerapp delete --name acip-s03-commercial-cockpit --resource-group acip-s03-commercial-rg-prod --yes

# Re-run Terraform apply to provision cleanly from scratch
terraform apply -auto-approve
```




