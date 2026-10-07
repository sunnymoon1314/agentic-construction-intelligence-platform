# <span style="color:red">🔧 10. Troubleshooting Guide</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](README.md#toc)</span>

This guide covers categorized issues, symptoms, root causes, and verified resolutions encountered when deploying and running the S02 Agentic Bid Evaluation & Tender Intelligence framework across local environments and cloud providers.

---

## <span id="troubleshooting-toc"></span>📑 Table Of Contents (TOC)

- [10.1 DuckDB Database Locked by Concurrent Process](#issue-10-1)
- [10.2 FastMCP stdio Pipe Broken During Evaluation](#issue-10-2)
- [10.3 Missing Qualification Letter Schema Exception](#issue-10-3)
- [10.4 Missing DuckDB Python Library & Conda Activation](#issue-10-4)
- [10.5 Missing Pandas Dependency During DuckDB Dataframe Export](#issue-10-5)
- [10.6 AWS ECS Fargate Missing IAM Execution Role](#issue-10-6)
- [10.7 AWS ECR Docker Login 400 Bad Request Due to Region Mismatch](#issue-10-7)
- [10.8 Containerized Dashboard Missing Table Data Due to Numpy Dependency](#issue-10-8)
- [10.9 AWS ECR Repository Deletion Blocked Due to Missing force_delete](#issue-10-9)
- [10.10 Google Cloud Run Creation Fails with Image Not Found](#issue-10-10)
- [10.11 Azure Container App Already Exists Due to State Drift](#issue-10-11)
- [10.12 Azure Container App Update Failed with 401 Unauthorized ACR Pull](#issue-10-12)
- [10.13 Error Locating Storage Account During ADLS Gen2 Filesystem Creation](#issue-10-13)

---

## <span id="issue-10-1"></span>🔒 10.1 DuckDB Database Locked by Concurrent Process <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `duckdb.duckdb.IOException: IO Error: Cannot open file "data/hospital_tender.duckdb": The process cannot access the file because it is being used by another process.`

**Symptom**: Running the Medallion ETL pipeline, launching the analytical dashboard, or executing unit tests fails with an unhandled DuckDB IO lock exception.

**Cause**: DuckDB applies exclusive file locks when a connection is opened in read-write mode. If a background process, interactive Python shell, or previous evaluation run left a read-write connection unclosed, subsequent read queries are blocked.

**Solution**: Always open database connections with `read_only=True` for inspection tools, queries, and dashboard servers, and ensure connections are closed inside `finally` blocks.

#### Before (Code causing the error in `mcp_server/server.py`):
```python
# Unprotected read-write connection blocks concurrent queries
con = duckdb.connect("data/hospital_tender.duckdb")
result = con.execute("SELECT * FROM boq_items").fetchall()
```

#### After (Corrected code):
```python
# Open as read-only to permit unlimited concurrent analytical queries
con = duckdb.connect("data/hospital_tender.duckdb", read_only=True)
try:
    result = con.execute("SELECT * FROM boq_items").fetchall()
finally:
    con.close()
```

---

## <span id="issue-10-2"></span>⚡ 10.2 FastMCP stdio Pipe Broken During Evaluation <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `BrokenPipeError: [Errno 32] Broken pipe during FastMCP stdio communication`

**Symptom**: The multi-agent evaluator client abruptly crashes with a JSON-RPC deserialization failure during the rate-leveling or front-loading calculation step.

**Cause**: Printing diagnostic logs or debugging statements directly to standard output (`sys.stdout`) pollutes the JSON-RPC stdio IPC communication stream between the FastMCP server and the agent client.

**Solution**: Redirect all diagnostic logs, telemetry, and debugging outputs to standard error (`sys.stderr`).

#### Before (Code causing the error in `mcp_server/server.py`):
```python
@mcp.tool()
def detect_front_loading(bidder_id: str) -> str:
    print(f"DEBUG: Processing front-loading for bidder: {bidder_id}")  # Pollutes stdout!
    return compute_flri(bidder_id)
```

#### After (Corrected code):
```python
import sys

@mcp.tool()
def detect_front_loading(bidder_id: str) -> str:
    sys.stderr.write(f"DEBUG: Processing front-loading for bidder: {bidder_id}\n")  # Safe logging
    return compute_flri(bidder_id)
```

---

## <span id="issue-10-3"></span>📄 10.3 Missing Qualification Letter Schema Exception <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `KeyError: 'qualification_letter_path' in agent_client/evaluator.py`

**Symptom**: Evaluating legacy contractor JSON tender submissions causes the Commercial & Contracts Risk Agent to crash during scope exclusion parsing.

**Cause**: The submission ingestion parser assumed every contractor payload contained a top-level `qualification_letter` object, failing when compliant contractors submitted clean bids without qualification schedules.

**Solution**: Use dictionary `.get()` with a safe default dictionary structure to handle submissions without qualification schedules gracefully.

#### Before (Code causing the error in `agent_client/evaluator.py`):
```python
qual_clauses = submission["qualification_letter"]["clauses"]
for clause in qual_clauses:
    audit_clause(clause)
```

#### After (Corrected code):
```python
qual_clauses = submission.get("qualification_letter", {}).get("clauses", [])
for clause in qual_clauses:
    audit_clause(clause)
```

---

## <span id="issue-10-4"></span>🐍 10.4 Missing DuckDB Python Library & Conda Activation <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `ModuleNotFoundError: No module named 'duckdb'`

**Symptom**: Attempting to execute `generate_tender_data.py`, `medallion_pipeline.py`, or `test_s02_pipeline.py` fails immediately upon execution.

**Cause**: The user's active shell terminal is running in the global base Python environment where project-specific packages are not installed.

**Solution**: Activate the unified ACIP Conda environment (`acip_mcp_framework`) prior to running any S02 evaluation commands.

#### Before (Code causing the error in terminal):
```bash
# Running in base environment without activating the ACIP Conda environment
python3 -c "import duckdb"
```

#### After (Corrected code):
```bash
# Ensure you are at the S02_Agentic_Bid_Evaluation_And_Tender_Intelligence module root folder before starting
cd "${ACIP_MODULE_DEFAULT_FOLDER}"
conda activate acip_mcp_framework
python3 -c "import duckdb; print('DuckDB successfully imported:', duckdb.__version__)"
```

---

## <span id="issue-10-5"></span>📊 10.5 Missing Pandas Dependency During DuckDB Dataframe Export <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `_duckdb.InvalidInputException: Invalid Input Error: 'pandas' is required for this operation but it was not installed`

**Symptom**: Executing `data/medallion_pipeline.py` or launching `dashboard/server.py` crashes while converting DuckDB query results via `.df()`.

**Cause**: Calling `.df()` on a DuckDB query object triggers DuckDB's PyArrow/Pandas zero-copy conversion bridge, which requires `pandas` to be installed in the active Conda environment.

**Solution**: Install `pandas` into the active Conda environment, or utilize pure Python/DuckDB formatting.

#### Before (Code causing the error in `environment.yml`):
```yaml
      # Columnar In-Process Analytics & High-Performance Pipelines (S02, S03, S07)
      - "duckdb>=1.1.0"
      - polars
      - pyarrow
      - numpy
      # pandas was omitted from pip dependencies
```

#### After (Corrected code):
```yaml
      # Columnar In-Process Analytics & High-Performance Pipelines (S02, S03, S07)
      - "duckdb>=1.1.0"
      - polars
      - pyarrow
      - numpy
      - pandas
```

To immediately resolve in the active environment without rebuilding the Conda environment:
```bash
# Ensure you are at the S02_Agentic_Bid_Evaluation_And_Tender_Intelligence module root folder before starting
pip install pandas
```

---

## <span id="issue-10-6"></span>☁️ 10.6 AWS ECS Fargate Missing IAM Execution Role <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `ClientException: Fargate requires task definition to have execution role ARN to support ECR images.`

**Symptom**: Executing `terraform -chdir=terraform/aws apply` fails while registering the ECS task definition `acip-s02-tender-task`.

**Cause**: AWS ECS Fargate tasks pulling container images from private Amazon ECR repositories require an IAM Task Execution Role with `AmazonECSTaskExecutionRolePolicy` attached. Without `execution_role_arn`, the AWS ECS API rejects the task definition.

**Solution**: Define an `aws_iam_role` with an `ecs-tasks.amazonaws.com` assume-role policy, attach `AmazonECSTaskExecutionRolePolicy`, and supply `execution_role_arn` to the `aws_ecs_task_definition` resource.

#### Before (Code causing the error in `terraform/aws/main.tf`):
```hcl
resource "aws_ecs_task_definition" "tender_task" {
  family                   = "acip-s02-tender-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  # Missing execution_role_arn
  container_definitions    = jsonencode([...])
}
```

#### After (Corrected code):
```hcl
resource "aws_iam_role" "ecs_execution_role" {
  name = "acip-s02-ecs-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_ecs_task_definition" "tender_task" {
  family                   = "acip-s02-tender-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn

  container_definitions    = jsonencode([...])
}
```

---

## <span id="issue-10-7"></span>☁️ 10.7 AWS ECR Docker Login 400 Bad Request Due to Region Mismatch <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `error="login attempt to https://<account_id>.dkr.ecr.ap-southeast-1.amazonaws.com/v2/ failed with status: 400 Bad Request: invalid argument"`

**Symptom**: Executing `aws ecr get-login-password --region ${AWS_DEFAULT_REGION} | docker login --username AWS --password-stdin ${ECR_URL}` fails with status: 400 Bad Request when authenticating against Amazon ECR.

**Cause**: The authentication token was requested using `--region ${AWS_DEFAULT_REGION}` (configured as `us-east-1` in `.env`), whereas the Terraform ECR repository was deployed into `ap-southeast-1` (Singapore). Amazon ECR rejects authentication tokens generated for a different region than the target registry URL.

**Solution**: Dynamically extract the target region directly from `${ECR_URL}` using `$(echo ${ECR_URL} | cut -d'.' -f4)` or align `AWS_DEFAULT_REGION="ap-southeast-1"` in `.env`, ensuring the token's signing region matches the ECR repository endpoint.

#### Before (Code causing the error in `README.md`):
```bash
# Relying on static AWS_DEFAULT_REGION from .env which may point to us-east-1
ECR_URL=$(terraform -chdir=terraform/aws output -raw ecr_repository_url)
aws ecr get-login-password --region ${AWS_DEFAULT_REGION} | docker login --username AWS --password-stdin ${ECR_URL}
```

#### After (Corrected code):
```bash
# Ensure you are at the S02_Agentic_Bid_Evaluation_And_Tender_Intelligence module root folder before starting
cd "${ACIP_MODULE_DEFAULT_FOLDER}"
set -a; source .env; set +a

# Dynamically parse the exact region from the ECR repository URL
ECR_URL=$(terraform -chdir=terraform/aws output -raw ecr_repository_url)
ECR_REGION=$(echo ${ECR_URL} | cut -d'.' -f4)
aws ecr get-login-password --region ${ECR_REGION} | docker login --username AWS --password-stdin ${ECR_URL}
```

---

## <span id="issue-10-8"></span>📊 10.8 Containerized Dashboard Missing Table Data Due to Numpy Dependency <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `ModuleNotFoundError: No module named 'numpy'` in `/api/data`

**Symptom**: The Executive Dashboard UI loads successfully in the browser on `http://localhost:8085`, but the Statutory PQM Leaderboard table and the Trade Cost Allocation chart render empty with zero data rows.

**Cause**: `dashboard/server.py` utilized DuckDB's `.df().to_dict(orient="records")` method to serialize query results into JSON. Inside a minimal container environment where `numpy` or `pandas` is not explicitly installed, `.df()` raises an unhandled `ModuleNotFoundError`, causing the `/api/data` HTTP request to drop with an empty reply.

**Solution**: Refactor `dashboard/server.py` to use a pure native DuckDB cursor dictionary mapping function (`query_dicts`) with zero external C-extension dependencies, and add `pandas>=2.0.0`, `numpy>=1.24.0`, and `pyarrow>=14.0.0` to `requirements.txt`.

#### Before (Code causing the error in `dashboard/server.py`):
```python
# Implicit dependency on numpy and pandas
trades = con.execute("SELECT * FROM trades ORDER BY trade_id").df().to_dict(orient="records")
bidders = con.execute("SELECT * FROM bidders WHERE tender_id = ?", [tender_id]).df().to_dict(orient="records")
```

#### After (Corrected code):
```python
# Pure native DuckDB cursor dictionary mapping with zero external dependencies
def query_dicts(con, sql, params=None):
    cursor = con.execute(sql, params) if params else con.execute(sql)
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

trades = query_dicts(con, "SELECT * FROM trades ORDER BY trade_id")
bidders = query_dicts(con, "SELECT * FROM bidders WHERE tender_id = ?", [tender_id])
```

---

## <span id="issue-10-9"></span>☁️ 10.9 AWS ECR Repository Deletion Blocked Due to Missing force_delete <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `RepositoryNotEmptyException: The repository with name 'acip-s02-tender-engine' in registry with id '<account_id>' cannot be deleted because it still contains images`

**Symptom**: Executing `terraform -chdir=terraform/aws destroy -auto-approve` successfully destroys all VPC, subnet, ALB, and ECS resources, but terminates with a 400 Bad Request error when attempting to delete the Amazon ECR repository.

**Cause**: By default, AWS ECR prevents the accidental deletion of container repositories that contain pushed container image layers. Without `force_delete = true` declared in the Terraform resource, Terraform cannot delete the repository until all image digests have been manually purged.

**Solution**: Add `force_delete = true` to `aws_ecr_repository.tender_engine_repo` in `terraform/aws/main.tf` matching the S01 reference configuration. For an immediate fix on a stuck repository, purge the repository using `aws ecr delete-repository --repository-name acip-s02-tender-engine --region ${AWS_REGION} --force`.

#### Before (Code causing the error in `terraform/aws/main.tf`):
```hcl
resource "aws_ecr_repository" "tender_engine_repo" {
  name                 = "acip-s02-tender-engine"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
```

#### After (Corrected code):
```hcl
resource "aws_ecr_repository" "tender_engine_repo" {
  name                 = "acip-s02-tender-engine"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}
```

---

## <span id="issue-10-10"></span>☁️ 10.10 Google Cloud Run Creation Fails with Image Not Found During Initial Apply <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `Error waiting for Creating Service: Error code 5, message: Revision 'acip-s02-tender-engine-dev-00001-s5f' is not ready and cannot serve traffic. Image 'asia-southeast1-docker.pkg.dev/<project_id>/acip-s02-tender-engine/engine:latest' not found.`

**Symptom**: Executing `terraform -chdir=terraform/gcp apply -auto-approve -var="project_id=${GCP_PROJECT_ID}"` in Step 1 successfully provisions the Cloud Storage bucket and Artifact Registry repository, but terminates with Error Code 5 when attempting to create `google_cloud_run_v2_service.tender_engine_service`.

**Cause**: A chicken-and-egg dependency in the cloud deployment lifecycle. The Terraform blueprint hardcoded the container image directly to the Artifact Registry repository URL (`${var.region}-docker.pkg.dev/${var.project_id}/acip-s02-tender-engine/engine:latest`). Because the Artifact Registry repository was newly provisioned during that exact `terraform apply` run, no Docker image had been built or pushed to the registry yet. When Google Cloud Run attempted to start the initial revision, the image lookup failed.

**Solution**: Replicate the S01 reference architecture by introducing a `docker_image` variable in `terraform/gcp/variables.tf` that defaults to a lightweight public bootstrap image (`us-docker.pkg.dev/cloudrun/container/hello`). This allows Step 1 `terraform apply` to provision the infrastructure and public endpoint cleanly. In Step 2, the user builds and pushes the real application image to Artifact Registry. In Step 3, `gcloud run deploy` updates the Cloud Run revision to the real image.

#### Before (Code causing the error in `terraform/gcp/main.tf`):
```hcl
# Hardcoding non-existent image causes initial terraform apply to crash
resource "google_cloud_run_v2_service" "tender_engine_service" {
  name     = "acip-s02-tender-engine-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/acip-s02-tender-engine/engine:latest"
      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }
    }
  }
}
```

#### After (Corrected code in `terraform/gcp/variables.tf` and `terraform/gcp/main.tf`):
```hcl
# In terraform/gcp/variables.tf:
variable "docker_image" {
  description = "The Docker image for the Cloud Run service. Defaults to a public hello image until you push your real image."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

# In terraform/gcp/main.tf:
resource "google_cloud_run_v2_service" "tender_engine_service" {
  name     = "acip-s02-tender-engine-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = var.docker_image
      ports {
        container_port = 8085
      }
      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "CLOUD_PROVIDER"
        value = "GCP"
      }
      env {
        name  = "GCS_MEDALLION_BUCKET"
        value = google_storage_bucket.tender_data_lake.name
      }
    }
  }
}
```

---

## <span id="issue-10-11"></span>☁️ 10.11 Azure Container App Already Exists Due to State Drift <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `Error: A resource with the ID "/subscriptions/<sub_id>/resourceGroups/rg-acip-s02-dev/providers/Microsoft.App/containerApps/acip-s02-engine-dev" already exists - to be managed via Terraform this resource needs to be imported into the State.`

**Symptom**: Running `terraform -chdir=terraform/azure apply -auto-approve` fails with an "already exists" error during the creation of `azurerm_container_app.tender_engine_app`.

**Cause**: An orphaned Azure Container App resource with the name `acip-s02-engine-dev` exists in Azure from a previous manual run or destroyed state, but Terraform's local state file (`terraform.tfstate`) does not track it. Terraform detects the conflict and halts execution to prevent unintentional overwrite.

**Solution**: Delete the orphaned container app via the Azure CLI so Terraform can perform a clean, managed creation: `az containerapp delete --name acip-s02-engine-dev --resource-group rg-acip-s02-dev --yes`. Alternatively, import the resource into Terraform state using `terraform -chdir=terraform/azure import azurerm_container_app.tender_engine_app <resource_id>`.

#### Before (Error occurring during apply):
```bash
# Orphaned container app exists in Azure, but missing from terraform.tfstate
terraform -chdir=terraform/azure apply -auto-approve
# Error: A resource with the ID ... already exists
```

#### After (Corrected remediation workflow):
```bash
# Ensure you are at the S02_Agentic_Bid_Evaluation_And_Tender_Intelligence module root folder before starting
# 1. Delete the orphaned container app from Azure
az containerapp delete --name acip-s02-engine-dev --resource-group rg-acip-s02-dev --yes

# 2. Re-run Terraform apply to create cleanly under state management
terraform -chdir=terraform/azure apply -auto-approve
```

---

## <span id="issue-10-12"></span>☁️ 10.12 Azure Container App Update Failed with 401 Unauthorized ACR Pull <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `Failed to provision revision for container app 'acip-s02-engine-dev'. Error details: The following field(s) are either invalid or missing. Field 'template.containers.tender-engine.image' is invalid with details: 'Invalid value: "acips02registrydev.azurecr.io/tender-engine:latest": GET https:?scope=repository%3Atender-engine%3Apull&service=acips02registrydev.azurecr.io: UNAUTHORIZED: authentication required'`

**Symptom**: After successfully building and pushing the container image to Azure Container Registry (ACR), running `az containerapp update --name acip-s02-engine-dev --resource-group ${RESOURCE_GROUP} --image ${ACR_LOGIN_SERVER}/tender-engine:latest` fails with an UNAUTHORIZED 401 error.

**Cause**: Azure Container Registry is private by default. Without registry credentials or managed identity access declared on the Container App, Azure Container Apps attempts to pull the container image anonymously, which ACR rejects.

**Solution**: Configure the ACR admin credentials on the Container App either natively in Terraform (`terraform/azure/main.tf`) via `secret` and `registry` blocks, or immediately attach credentials via the Azure CLI using `az containerapp registry set`.

#### Before (Missing registry authentication block in `terraform/azure/main.tf`):
```hcl
resource "azurerm_container_app" "tender_engine_app" {
  name                         = "acip-s02-engine-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.app_env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  # Missing secret and registry blocks for ACR authentication!
  template {
    container {
      name   = "tender-engine"
      image  = var.docker_image
    }
  }
}
```

#### After (Corrected code in `terraform/azure/main.tf`):
```hcl
resource "azurerm_container_app" "tender_engine_app" {
  name                         = "acip-s02-engine-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.app_env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }

  template {
    container {
      name   = "tender-engine"
      image  = var.docker_image
    }
  }
}
```

---

## <span id="issue-10-13"></span>☁️ 10.13 Error Locating Storage Account During ADLS Gen2 Filesystem Creation <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Troubleshooting TOC](#troubleshooting-toc)</span>

❌ **Error**: `Error: locating Storage Account "acips02devlake"`

**Symptom**: Executing `terraform -chdir=terraform/azure apply -auto-approve` fails on resource `azurerm_storage_data_lake_gen2_filesystem.tender_lake` with a failure to locate the parent storage account.

**Cause**: The Terraform resource `azurerm_storage_data_lake_gen2_filesystem` communicates with the Azure storage data plane endpoint (`https://<account>.dfs.core.windows.net/`). When a storage account is freshly created within the same Terraform execution, public DNS propagation across Microsoft global DNS resolvers can take up to 30 to 60 seconds. Attempting to create the Gen2 filesystem immediately triggers a DNS resolution failure.

**Solution**: Use `azurerm_storage_container` instead of `azurerm_storage_data_lake_gen2_filesystem`. In Azure, an ADLS Gen2 filesystem is functionally identical to a blob container with hierarchical namespaces (`is_hns_enabled = true`). `azurerm_storage_container` operates via Azure Resource Manager (ARM) control plane APIs (`management.azure.com`), eliminating DNS propagation race conditions.

#### Before (Code causing the error in `terraform/azure/main.tf`):
```hcl
resource "azurerm_storage_account" "tender_storage" {
  name                     = "acips02${var.environment}lake"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true
}

# Data plane call fails due to DNS propagation delay
resource "azurerm_storage_data_lake_gen2_filesystem" "tender_lake" {
  name               = "tender-lake"
  storage_account_id = azurerm_storage_account.tender_storage.id
}
```

#### After (Corrected code in `terraform/azure/main.tf`):
```hcl
resource "azurerm_storage_account" "tender_storage" {
  name                     = "acips02${var.environment}lake"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true
}

# Control plane container creation succeeds instantly without DNS latency
resource "azurerm_storage_container" "tender_lake" {
  name                  = "tender-lake"
  storage_account_name  = azurerm_storage_account.tender_storage.name
  container_access_type = "private"
}
```


