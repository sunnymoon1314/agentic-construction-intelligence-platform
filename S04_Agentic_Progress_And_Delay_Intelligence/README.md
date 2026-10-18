# <span style="color:red">⏱️ S04: Implementation Guide & Technical Runbook</span>

[📄 Go to S04 Business Problem Statement & Case Studies](BUSINESS_PROBLEM_STATEMENT.md) | [⬆️ Back to ACIP Overview](../README.md#toc)

---

**S04: Agentic Progress & Delay Intelligence** is an assistive construction scheduling and forensic delay decision-support module designed for Project Directors, Planners, Contract Administrators, and Superintending Officers (SO) operating under standard Singapore construction contracts (PSSCOC 2020/2025, SIA 2024, and LTA Conditions).

S04 is not an autonomous scheduling black-box that waives liquidated damages or arbitrarily grants extensions of time. It is an agentic decision-support architecture where deterministic Critical Path Method (CPM) algorithms and Time Impact Analysis (TIA) fragnet simulations are strictly decoupled from generative probabilistic language models. FastMCP-based deterministic engines calculate schedule float, critical path drift, and statutory notice timebars, while multi-agent LLM personas are restricted to qualitative evidence synthesis, delay dispute narratives, and adversarial deliberation.

**💡 Core Architectural Philosophy**: AI can reason. Deterministic systems calculate. Evidence supports. Professionals decide.

**💡 Core Delay Tenet**: A project can report 85% physical progress and still suffer catastrophic critical-path delay. Static progress reporting shows where tasks were planned; S04 provides forensic visibility into where the critical path is drifting, which activity absorbed total float, and how concurrent delay events allocate contractual responsibility.

### 🛡️ Technical Scope & Architectural Boundaries

- **🧪 Working Reference Implementation**: S04 is an active, fully functional module featuring four Singapore infrastructure project profiles, an in-process DuckDB columnar store with Apache Parquet lakehouse partitions, six deterministic FastMCP calculation tools, a 3-agent adversarial deliberation pipeline (Contractor, Employer QS, Superintending Officer), an automated 78-test audit suite across 6 increments, and an interactive single-page forensic delay cockpit on Port 8087.
- **🧱 ACIP Deterministic Execution Boundary**: Foundation models may interpret schedule evidence, but cannot calculate critical path dates, total float, or statutory notice deadlines. All computations are executed exclusively by deterministic algorithms outside the probabilistic path.
- **⚖️ Decision-Support Boundary**: S04 produces auditable P6 XER baseline reconciliations, prospective/retrospective TIA fragnet simulations, float erosion waterwalls, contemporaneous rainfall/biometric radar cross-checks, and statutory PSSCOC Clause 23.1 notice evaluations. S04 cannot autonomously execute binding Extension of Time (EOT) grants or waive Liquidated Damages (LAD). Official delay determination strictly requires authorization by the certified Superintending Officer or formal Adjudicator.

### 🚧 Explicit Scope Boundaries (What S04 Does NOT Do)

To ensure strict legal and governance defensibility, S04 explicitly does NOT:
- Replace the certified Superintending Officer's statutory authority or independent discretion;
- Grant binding Extensions of Time (EOT) or waive liquidated damages autonomously;
- Constitute legal advice or replace formal SOPA adjudication counsel;
- Permit any Large Language Model to alter critical path calculations or float values;
- Assume weather stoppage without corroborating contemporaneous site radar and turnstile telemetry;
- Treat unverified contractor delay claims as authoritative without primary site records.

---

## <span id="toc"></span>📑 Table Of Contents (TOC)

- [0. Pre-requisite Software](#prerequisites)
- [1. Architecture Overview](#architecture-overview)
  - [1.1 System Architecture & Analytical Pillars](#system-architecture)
  - [1.2 The Three Non-Negotiable Delay Logic Gates](#logic-gates)
  - [1.3 Telemetry Radar & Biometric Set-Off Formulations](#telemetry-radar)
  - [1.4 Four Real-World Demonstration Scenarios](#demo-scenarios)
- [2. Directory Structure](#directory-structure)
- [3. Approach 1: Pure Local Sovereign Deployment & Testing (Zero Cost)](#local-deployment)
  - [3.1 Environment Configuration & Dependencies](#env-config)
  - [3.2 Ingesting Baseline Schedules & Lakehouse Partitions](#seed-dataset)
  - [3.3 FastMCP Deterministic Tool Server Execution (stdio IPC)](#fastmcp-server)
  - [3.4 Multi-Agent Delay Deliberation Client](#agent-client)
  - [3.5 Interactive Forensic Delay Cockpit (Port 8087)](#forensic-cockpit)
- [4. Approach 2: Hybrid Testing Sandbox (Local Application + Cloud LLM APIs)](#hybrid-testing)
  - [4.1 Cloud LLM Provider Credentials & Environment (.env)](#hybrid-env)
  - [4.2 Qualitative Delay Dispute Narrative & EOT Memo Generation](#hybrid-memo)
  - [4.3 Cloud-Backed Forensic Delay Cockpit (AWS, Azure, GCP, Local)](#hybrid-dashboard)
- [5. Approach 3: Cloud Workload Direct Provisioning (Multi-Cloud Terraform Deployments)](#cloud-provisioning)
  - [5.1 Why Choose Cloud Workload Direct Provisioning?](#why-cloud-native)
  - [5.2 Pre-requisites for Approach 3](#cloud-native-prerequisites)
  - [5.3 AWS Deployment (ECS Fargate + S3 Lakehouse + ALB on Port 8087)](#terraform-aws)
  - [5.4 Azure Deployment (Azure Container Apps + Blob Lakehouse on Port 8087)](#terraform-azure)
  - [5.5 Google Cloud Deployment (Cloud Run v2 + GCS Lakehouse on Port 8087)](#terraform-gcp)
- [6. Approach 4: Reference Enterprise Deployment Pattern & Sovereign Governance (Planned)](#enterprise-landing-zone)
  - [6.1 Dedicated Sovereign Planning Enclaves & Zero-Egress Storage](#sovereign-enclaves)
  - [6.2 Audit Trails, RBAC & Statutory Adjudication Defense Archive](#audit-rbac)
- [7. Automated Testing & Verification (78 Tests Across 6 Suites)](#automated-testing)
- [8. Clean Up](#cleanup)
  - [8.1 Destroy Cloud Workloads (AWS, Azure, GCP)](#destroy-cloud)
- [9. Frequently Asked Questions (FAQ)](FAQ.md)
- [10. Troubleshooting Guide](TROUBLESHOOTING.md)

---

## <span id="prerequisites"></span><span style="color:red">⚙️ 0. Pre-requisite Software</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

📝 Note: All terminal commands in this technical runbook are written for Unix/macOS Bash or Zsh shells (execute using Git Bash or WSL2 on Windows). For Approach 1 (Pure Local Sovereign), only Python, Conda, and DuckDB are required. Cloud CLIs, Docker, and Terraform are only required if you choose to deploy to cloud providers (Approach 3).

Before beginning, ensure the following software is installed on the host machine:

- **Python 3.11+**: Core runtime environment for multi-agent orchestration and analytical pipelines. Download from the [Python Official Website](https://www.python.org/downloads/).
- **DuckDB 1.1+**: High-performance in-process columnar SQL OLAP database engine for instant zero-copy analytical queries across multi-project schedule baselines. Download from the [DuckDB Official Website](https://duckdb.org/).
- **Conda / Miniconda**: Package and virtual environment management system. Download from the [Miniconda Official Website](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda Official Website](https://www.anaconda.com/download).
- **Docker 24.0+**: Container runtime for building, tagging, and publishing multi-platform container images to enterprise cloud container registries (AWS ECR, Azure ACR, and Google Artifact Registry) in Approach 3. Download from the [Docker Official Website](https://docs.docker.com/get-docker/).
- **Terraform 1.5+**: Infrastructure-as-code automation tool for multi-cloud workload provisioning across AWS, Azure, and Google Cloud Platform. Download from the [HashiCorp Official Website](https://developer.hashicorp.com/terraform/downloads).
- **Cloud CLIs**: Install the CLI for the specific cloud platform you plan to deploy or test:
  - **AWS CLI**: For AWS ECS Fargate & Amazon Bedrock deployments. Download from the [AWS CLI Official Website](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
  - **Azure CLI**: For Azure Container Apps & Azure OpenAI deployments. Download from the [Azure CLI Official Website](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli).
  - **Google Cloud SDK**: For Google Cloud Run & Vertex AI deployments. Download from the [Google Cloud SDK Official Website](https://cloud.google.com/sdk/docs/install).

Software verification commands:

```bash
python3 --version
python3 -c "import duckdb; print('DuckDB Version:', duckdb.__version__)"
conda --version
docker --version
terraform --version
aws --version || true
az --version || true
gcloud --version || true
```

![Pre-requisite software verification terminal](images/pre-requisite_software.png)

---

## <span id="architecture-overview"></span><span style="color:red">🏛️ 1. Architecture Overview</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

### <span id="system-architecture"></span>🌐 1.1 System Architecture & Analytical Pillars <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

![ACIP S04 Architecture Overview](images/s04_architecture_diagram.png)

S04 bridges planning engineering and construction delay forensics through four integrated analytical pillars:

1. **Primavera P6 Ingestion & Dynamic CPM Recalculation Engine**: Ingests raw `.xer` schedule files, builds topological directed acyclic graphs (DAG), enforces discrete-day modulo constraints, and executes forward/backward passes honoring multi-calendar workday patterns.
2. **Controlled Time Impact Analysis (TIA) Fragnet Simulator**: Prospective and retrospective fragnet simulation inserting discrete-day delay events directly into the topological network to quantify total float erosion and project completion drift.
3. **Contemporaneous Site Telemetry Radar**: Cross-references weather station precipitation sensors with biometric turnstile operative counts to repudiate unsubstantiated rain stoppage claims.
4. **FastMCP Deterministic Delay Server**: Exposes 6 statutory typed tools on Port 8087, enforcing strict fail-closed validation and mathematical determinism outside LLM control.

---

### <span id="logic-gates"></span>⚖️ 1.2 The Three Non-Negotiable Delay Logic Gates <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        S04 THREE STATUTORY DELAY LOGIC GATES                           │
├────────────────────┬───────────────────────────────────┬───────────────────────────────┤
│ Statutory Gate     │ Governing Legal & Protocol Basis  │ Deterministic Gate Result     │
├────────────────────┼───────────────────────────────────┼───────────────────────────────┤
│ 1. Notice Window   │ PSSCOC 2020 Clause 23.1           │ If notice > 28 days:          │
│    Timebar Gate    │ Condition Precedent               │ TIME-BARRED (0 EOT days)      │
├────────────────────┼───────────────────────────────────┼───────────────────────────────┤
│ 2. Float Erosion   │ Total Float Absorption            │ Delay absorbed by float:      │
│    Kernel Gate     │ Path Float Governance             │ 0 Critical Path Drift         │
├────────────────────┼───────────────────────────────────┼───────────────────────────────┤
│ 3. Concurrency     │ SCL Protocol Core Principle 10    │ Employer + Contractor Concur: │
│    Apportionment   │ SCL Delay & Disruption 2nd Ed     │ EOT Granted; 0 Prolongation $ │
└────────────────────┴───────────────────────────────────┴───────────────────────────────┘
```

1. **Logic Gate 1 (PSSCOC Clause 23.1 Notice Condition Precedent)**: If a contractor fails to serve written notice within 28 calendar days of event occurrence, statutory entitlement to an Extension of Time is extinguished, capping granted EOT at 0.0 workdays.
2. **Logic Gate 2 (Float Erosion Prior to Critical Path Drift)**: Delays on subcritical paths consume available total float. Critical path drift occurs only after total float is completely exhausted (`Total Float <= 0`).
3. **Logic Gate 3 (SCL Protocol Core Principle 10 Concurrency Gate)**: Where Employer Risk and Contractor Culpable delay events overlap, the contractor receives time relief from Liquidated Damages, but zero prolonged overhead compensation.

---

### <span id="telemetry-radar"></span>🌧️ 1.3 Telemetry Radar & Biometric Set-Off Formulations <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

The Contemporaneous Site Radar reconciles contractor inclemency claims against primary objective sensor records:

- **Rainfall Threshold**: Verified daily precipitation `>= 10.0 mm` classifies as an exceptional inclemency event under PSSCOC Clause 23.1(f).
- **Turnstile Telemetry Check**: If precipitation is `0.0 mm` while biometric turnstiles record regular operative counts (e.g. 39-41 operatives active on site), contractor claims of site weather closure are flagged as `DISCREPANCY_REPUDIATED`.
- **Liquidated Damages Formulation**:
  `contractor_culpable_days = max(0.0, net_critical_delay_days - assessed_eot_workdays)`
  `liquidated_damages_exposure_sgd = contractor_culpable_days * daily_ld_rate_sgd`

---

### <span id="demo-scenarios"></span>🏢 1.4 Four Real-World Demonstration Scenarios <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

1. **WHC Commercial Annex (`PRJ-WHC-COM-001`)**: Baseline PSSCOC 2020 contract with S$15,000/day LAD rate. Severe excavation groundwater ingress, 28-day notice served within 1 day, 2 days weather EOT granted, 12 days contractor culpable delay.
2. **JID Tech Park (`PRJ-JID-ATP-004`)**: High-spec industrial facility under SIA 9th Edition. Star Rate structural variations and MEP ducting clash float erosion.
3. **Marina Bay Fit-Out (`PRJ-MBF-FIT-002`)**: Fast-track commercial fit-out. Night work acoustic permit restrictions and sub-contractor trade stack concurrency.
4. **CRL Shaft Benchmark (`PRJ-CRL-CR108`)**: Deep infrastructure civil engineering contract under LTA Conditions. TBM cutterhead intervention and statutory agency utility diversion delay.

---

## <span id="directory-structure"></span><span style="color:red">📁 2. Directory Structure <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

The following directory tree reflects the complete, un-omitted structure of the S04 module:

```text
S04_Agentic_Progress_And_Delay_Intelligence/
├── agent_client/                               # Multi-agent deliberation pipeline and client
│   ├── __init__.py                             # Package initializer for agent client module
│   ├── client.py                               # MCP agent client invoking delay and TIA tools
│   └── deliberation_pipeline.py                # Tri-agent consensus engine (Contractor, QS, SO)
├── dashboard/                                  # Interactive delay intelligence executive cockpit
│   ├── index.html                              # Single-page reactive GUI with CPM graph and forensic drawers
│   └── server.py                               # Dashboard HTTP server with multi-cloud lakehouse support
├── data/                                       # Project schedules, baselines, and data contracts
│   ├── dictionary/                             # ACIP universal construction domain dictionary
│   │   ├── acip_dictionary_schema.json         # JSON schema for domain dictionary validation
│   │   ├── acip_dictionary.json                # Standard terms, definitions, and contract acronyms
│   │   └── acip_ui_tooltip_bundle.json         # UI tooltips and forensic guidance bundle
│   ├── export/                                 # Downstream cross-module handshake exports
│   │   ├── s05_delay_events_handshake.json     # S05 Quality link handshake event payload
│   │   ├── s05_quality_inspection_schedule_links.json # Activity-to-inspection mapping export
│   │   ├── s06_delay_claims_handshake.json     # S06 SOPA Claims handshake event payload
│   │   └── s06_formal_claims_delay_links.json  # Activity-to-claims dispute linkage export
│   ├── parquet/                                # Canonical Apache Parquet columnar lakehouse tables
│   │   ├── audit_deliberation_log.parquet      # Append-only multi-agent consensus audit log
│   │   ├── calendars.parquet                   # Project calendars with working days and holidays
│   │   ├── contract_parameters.parquet         # Authoritative contract parameters and LD rates
│   │   ├── delay_event_activities.parquet      # Delay event to schedule activity impact mapping
│   │   ├── delay_events.parquet                # Logged delay events with root-cause classifications
│   │   ├── formal_claims_delay_links_manifest.json # SHA-256 cryptographic manifest for S06 links
│   │   ├── formal_claims_delay_links.parquet   # Formal claims dispute linkages Parquet table
│   │   ├── quality_inspection_schedule_links_manifest.json # SHA-256 manifest for S05 links
│   │   ├── quality_inspection_schedule_links.parquet # Quality inspection schedule links Parquet table
│   │   ├── schedule_activities.parquet         # Ingested schedule activities with durations and dates
│   │   ├── schedule_relationships.parquet      # Activity predecessors and successors with lag
│   │   ├── schedule_versions.parquet           # Schedule revisions and data date metadata
│   │   ├── site_record_activities.parquet      # Activity mapping to daily site records
│   │   └── site_records.parquet                # Contemporaneous daily clerk-of-works and weather logs
│   └── xer/                                    # Raw Primavera P6 proprietary schedule exports
│       ├── WHC_COM_BL01_Approved_Baseline.xer  # Contractual approved baseline schedule export
│       └── WHC_COM_UP01_Progress_Update.xer    # Contemporaneous monthly progress update export
├── engine/                                     # Deterministic CPM calculation and TIA analytical core
│   ├── cpm_engine.py                           # Topological DAG forward/backward pass recalculation
│   ├── cpm_recalculation_service.py            # High-level CPM recalculation and float erosion service
│   ├── data_validator.py                       # Parquet schema and referential integrity validator
│   ├── dictionary_engine.py                    # Domain dictionary lookup and acronym resolver
│   ├── handshake_emitters.py                   # S05/S06 Parquet handshake and manifest generator
│   ├── p6_parser.py                            # Robust Primavera P6 XER file tokenizing parser
│   ├── tia_evaluator.py                        # SCL Protocol Time Impact Analysis (TIA) evaluator
│   └── xer_ingestion_pipeline.py               # End-to-end XER to Parquet lakehouse ingestion pipeline
├── images/                                     # System architecture diagrams and deployment visual guides
│   ├── approach_1_local_sovereign.png          # Approach 1 pure local sovereign architecture diagram
│   ├── approach_2_hybrid_sandbox.png           # Approach 2 hybrid cloud LLM sandbox architecture
│   ├── approach_3_cloud_workload.png           # Approach 3 cloud-native serverless architecture
│   ├── approach_4_enterprise_landing_zone.png  # Approach 4 enterprise multi-account landing zone
│   ├── architecture_aws.png                    # AWS ECS Fargate + S3 Parquet Lakehouse architecture
│   ├── architecture_azure.png                  # Azure Container Apps + Blob Lakehouse architecture
│   ├── architecture_gcp.png                    # Google Cloud Run + GCS Lakehouse architecture
│   └── s04_architecture_diagram.png            # ACIP S04 end-to-end platform architecture diagram
├── mcp_server/                                 # Model Context Protocol (FastMCP) calculation server
│   └── server.py                               # FastMCP server exposing 6 deterministic schedule tools
├── terraform/                                  # Multi-cloud serverless Infrastructure-as-Code (IaC)
│   ├── aws/                                    # AWS ECS Fargate, ALB, S3 Lakehouse, and IAM IaC
│   │   ├── main.tf                             # AWS provider, VPC, ECS Fargate, and S3 resources
│   │   ├── outputs.tf                          # Exported ALB URL, ECS cluster name, and S3 bucket
│   │   ├── terraform.tfvars.example            # Example variable inputs for AWS deployment
│   │   └── variables.tf                        # Configurable AWS region, environment, and app port
│   ├── azure/                                  # Azure Container Apps and Blob Storage Lakehouse IaC
│   │   ├── main.tf                             # Azure Resource Group, ACR, and Container App
│   │   ├── outputs.tf                          # Exported Container App URL, FQDN, and storage name
│   │   ├── terraform.tfvars.example            # Example variable inputs for Azure deployment
│   │   └── variables.tf                        # Configurable Azure location, port, and bootstrap image
│   └── gcp/                                    # Google Cloud Run v2 and GCS Parquet Lakehouse IaC
│       ├── main.tf                             # GCP Artifact Registry, Cloud Run v2, and GCS bucket
│       ├── outputs.tf                          # Exported Cloud Run URL and Artifact Registry URL
│       ├── terraform.tfvars.example            # Example variable inputs for GCP deployment
│       └── variables.tf                        # Configurable GCP project ID, region, and bootstrap image
├── tests/                                      # Automated test suite and verification harnesses
│   ├── run_verification_audit.py               # Comprehensive verification audit orchestrator
│   ├── test_dictionary_engine.py               # Unit tests for domain dictionary engine
│   └── test_s04_verification_suite.py          # Gate 2 independent verification test suite
├── .dockerignore                               # Excluded paths for container build optimization
├── .env.example                                # Template environment variables for local and cloud modes
├── .gitignore                                  # Git exclusion rules for secrets, builds, and terraform
├── BUSINESS_PROBLEM_STATEMENT.md               # Domain brief on schedule slippage, TIA, and LD risks
├── Dockerfile                                  # Multi-platform Linux AMD64 container build specification
├── FAQ.md                                      # Frequently asked questions with deep architectural answers
├── README.md                                   # Comprehensive technical documentation and runbook
├── requirements.txt                            # Python dependencies (fastmcp, duckdb, networkx, etc.)
└── TROUBLESHOOTING.md                          # Categorized issues, root cause analyses, and solutions
```

---

## <span id="local-deployment"></span><span style="color:red">💻 3. Approach 1: Pure Local Sovereign Deployment & Testing (Zero Cost)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

![Approach 1: Pure Local Sovereign Architecture](images/approach_1_local_sovereign.png)

Approach 1 operates completely offline on local hardware with zero external cloud egress and zero cloud costs. All analytical operations run via DuckDB and Python.

### <span id="env-config"></span>⚙️ 3.1 Environment Configuration & Dependencies <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Because ACIP contains many modules (S01 to S07) sharing one Conda environment, every bash block in this README starts with `cd "${ACIP_MODULE_DEFAULT_FOLDER}"`. This guarantees commands run inside the S04 module folder no matter which terminal tab or folder you are currently in.

Step 1: Set the module root directory environment variable:

```bash
# If starting from the ACIP platform root:
cd S04_Agentic_Progress_And_Delay_Intelligence

# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
export ACIP_MODULE_DEFAULT_FOLDER="$(pwd)"
echo "${ACIP_MODULE_DEFAULT_FOLDER}"
```

Step 2: Create (first time only) and activate the unified ACIP Conda environment:

We require conda environment `acip_mcp_framework` to be created before you can run the codes documented in this module. If you have not done so, please run the following command to create the environment:

```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
cd "${ACIP_MODULE_DEFAULT_FOLDER}"
conda env create -f ../environment.yml
```

![Conda environment creation step 1](images/conda_env_create_1.png)

![Conda environment creation step 2](images/conda_env_create_2.png)

This is followed by activating the environment:

```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
conda activate acip_mcp_framework
```

![Conda environment activation for ACIP framework](images/conda_activate_acip_mcp_framework.png)

📝 Note: If you have already created `acip_mcp_framework` (e.g. while working in S01, S02, or S03), skip `conda env create` and proceed directly to `conda activate acip_mcp_framework`.

Step 3: Create a local `.env` configuration file from `.env.example`:

```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
cd "${ACIP_MODULE_DEFAULT_FOLDER}"
cp .env.example .env
set -a; source .env; set +a
```

![Environment variable configuration from template](images/copy_env_example.png)

📝 Note: `ACIP_MODULE_DEFAULT_FOLDER` is managed as an environment variable in your shell or Conda environment and is not stored inside `.env`.

---

### <span id="seed-dataset"></span>📊 3.2 Ingesting Baseline Schedules & Lakehouse Partitions <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Ingest the authoritative Primavera P6 XER baseline files (`WHC_BL01_baseline_schedule.xer`) into partition tables:

```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
python engine/xer_ingestion_pipeline.py
```

![alt text](images/python_engine_xer_ingestion_pipeline.png)

To inspect the generated Parquet partitions via DuckDB (using the unified Conda environment):

```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
python -c "import duckdb; duckdb.sql(\"SELECT activity_id, activity_name, early_start_date, early_finish_date, total_float_days, is_critical FROM 'data/parquet/schedule_activities.parquet' LIMIT 6\").show()"
```

![alt text](images/python_duckdb_select_from_schedule_activities.png)

Or via the standalone DuckDB CLI (if installed on your PATH):

```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
duckdb -c "SELECT activity_id, activity_name, early_start_date, early_finish_date, total_float_days, is_critical FROM 'data/parquet/schedule_activities.parquet' LIMIT 6;"
```

---

### <span id="fastmcp-server"></span>⚡ 3.3 FastMCP Deterministic Tool Server Execution (stdio IPC) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Launch the standalone FastMCP server providing the 6 statutory delay analysis tools:

```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
python mcp_server/server.py
```

![alt text](images/python_mcp_server_server.png)

📝 Note: FastMCP operates over standard input/output (stdio IPC). When launched directly in an interactive shell, the server runs continuously and silently listens on stdin for incoming JSON-RPC requests from agent clients (such as the deliberation client in Section 3.4). No console text is output to stdout by design, as raw terminal prints would corrupt the JSON-RPC framing stream. You can press Ctrl+C to stop it.

---

### <span id="agent-client"></span>🤖 3.4 Multi-Agent Delay Deliberation Client <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Execute the 3-agent deliberation pipeline across the ground-truth delay scenarios:

```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
python agent_client/client.py --project-id PRJ-WHC-COM-001 --event-id DLY-2026-001
```

![alt text](images/python_agent_client_client_event_id.png)

---

### <span id="forensic-cockpit"></span>🖥️ 3.5 Interactive Forensic Delay Cockpit (Port 8087) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Start the interactive executive web cockpit serving on Port 8087:

```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
python dashboard/server.py --port 8087
```

![alt text](images/python_dashboard_server.png)

Open `http://localhost:8087` in any modern web browser to access:
- Interactive Topological CPM Network Graph and Gantt baseline drift.
- What-If Fragnet Simulator with dynamic float erosion recalculation.
- Contemporaneous Site Radar weather telemetry and turnstile discrepancy table.
- Adversarial Multi-Agent Deliberation Theater live debate transcript.
- Persistent non-modal Evidence Drawer with keyboard accessibility (Enter/Space).

![alt text](images/s04_dashboard_01a_local_8087_light_mode.png)

![alt text](images/s04_dashboard_01b_local_8087_dark_mode.png)

![alt text](images/s04_dashboard_01c_local_8087_light_mode.png)

![alt text](images/s04_dashboard_01d_local_8087_dark_mode.png)

![alt text](images/s04_dashboard_02a_metric_drawer_forecast_finish.png)

![alt text](images/s04_dashboard_02b_metric_drawer_net_critical_delay.png)

![alt text](images/s04_dashboard_02c_metric_drawer_assessed_eot.png)

![alt text](images/s04_dashboard_02d_metric_drawer_ld_exposure_1.png)

![alt text](images/s04_dashboard_02d_metric_drawer_ld_exposure_2.png)

![alt text](images/s04_dashboard_03aa_tab_schedule_and_critical_path.png)

![alt text](images/s04_dashboard_03ab_tab_drawer_schedule_and_critical_path.png)

![alt text](images/s04_dashboard_03ac_tab_drawer_schedule_and_critical_path_item.png)

![alt text](images/s04_dashboard_03ba_tab_what_if_fragnet_simulator.png)

![alt text](images/s04_dashboard_03bb_tab_drawer_what_if_fragnet_simulator.png)

![alt text](images/s04_dashboard_03ca_tab_clause23.1_claims_ledger.png)

![alt text](images/s04_dashboard_03cb_tab_drawer_clause23.1_claims_ledger.png)

![alt text](images/s04_dashboard_03cc_tab_drawer_clause23.1_claims_ledger_item.png)

![alt text](images/s04_dashboard_03da_tab_contemporaneous_rain_radar.png)

![alt text](images/s04_dashboard_03db_tab_drawer_contemporaneous_rain_radar.png)

![alt text](images/s04_dashboard_03dc_tab_drawer_contemporaneous_rain_radar_item.png)

![alt text](images/s04_dashboard_03ea_tab_ai_consensus_audit.png)

![alt text](images/s04_dashboard_03eb_tab_drawer_ai_consensus_audit.png)

![alt text](images/s04_dashboard_03ec_tab_drawer_ai_consensus_audit_item.png)

---

## <span id="hybrid-testing"></span><span style="color:red">🧪 4. Approach 2: Hybrid Testing Sandbox (Local Application + Cloud LLM APIs)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

![Approach 2: Hybrid Sandbox Architecture](images/approach_2_hybrid_sandbox.png)

Approach 2 establishes the hybrid operational bridge: pairing local, zero-hallucination FastMCP schedule computation with enterprise foundation models (AWS Bedrock Claude 3.5 Sonnet, Azure OpenAI GPT-4o, Google Cloud Vertex AI Gemini 1.5 Pro, or Local Sovereign fallback). This architecture ensures that all mathematical scheduling, float calculations, and financial liquidated damages remain mathematically deterministic, while generative LLMs are strictly channeled into qualitative legal synthesis, multi-agent adversarial deliberation, and statutory Extension of Time (EOT) memorandum drafting.

### <span id="hybrid-env"></span>🔑 4.1 Cloud LLM Provider Credentials & Environment (.env) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
cp .env.example .env
```

Configure your respective provider credentials inside `.env`:

```ini
CLOUD_PROVIDER="AWS" # Options: AWS, AZURE, GCP, LOCAL

# Amazon Web Services (AWS Bedrock Claude 3.5 Sonnet)
AWS_ACCESS_KEY_ID="your_aws_access_key"
AWS_SECRET_ACCESS_KEY="your_aws_secret_key"
AWS_DEFAULT_REGION="ap-southeast-1"
AWS_REGION="ap-southeast-1"

# Microsoft Azure (Azure OpenAI GPT-4o & Container Apps)

# Google Cloud Platform (GCP Vertex AI Gemini 1.5 Pro & Cloud Run)
GCP_PROJECT_ID="your_gcp_project_id"
GCP_REGION="asia-southeast1"
```

#### Engineering Rationale for Key Variables:
- **Dual AWS Region Definitions (`AWS_DEFAULT_REGION` and `AWS_REGION`)**: The AWS CLI (used for S3 sync and ECR authentication) defaults to `AWS_DEFAULT_REGION`. In contrast, modern AWS SDKs (`boto3` in Python, AWS Bedrock runtime, and the Terraform AWS provider) evaluate `AWS_REGION`. Specifying both variables avoids silent authentication failures or region resolution drops across heterogeneous automation scripts.
- **Zero-Cost Sovereign Fallback (`CLOUD_PROVIDER="LOCAL"`)**: If cloud credentials are not yet provisioned, setting `CLOUD_PROVIDER="LOCAL"` enables local execution using deterministic heuristic synthesis. This guarantees that evaluators can run the entire deliberation suite offline without external API keys or cloud billing.

If the `.env` file is missing or invalid, commands default to safe local heuristics. Cloud-backed foundation model deliberation will be bypassed, but local deterministic mathematical tools will continue to function.

---

### <span id="hybrid-memo"></span>📝 4.2 Qualitative Delay Dispute Narrative & EOT Memo Generation <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

#### Why We Run This Step:
In construction dispute adjudication, raw schedule CPM metrics (e.g., 3 days critical delay, 0 days total float) are insufficient on their own to grant relief. Under statutory Singapore construction law, an Extension of Time (EOT) claim requires a contemporaneous, legally defensible determination memorandum. This memorandum must establish cause and effect, evaluate contractual condition precedents (such as the 28-day notice rule), apportion concurrent delays, and determine whether the contractor is relieved from Liquidated Ascertained Damages (LAD).

#### Who This Memorandum Is Prepared For:
1. **Superintending Officer (SO) / Project Director**: Provides the impartial legal and technical foundation required under PSSCOC Clause 23 to issue a formal EOT assessment or certificate.
2. **Contractor Commercial & Planning Team (Claimant)**: Substantiates contractual entitlement to time relief, proving that the delay arose from an Employer Risk Event (e.g. unforeseeable groundwater ingress under PSSCOC Clause 23.2) to defend against LAD deductions.
3. **Employer Commercial & Quantity Surveying Team (Respondent)**: Audits contractor notice timing against the strict 28-day condition precedent clock and quantifies financial LAD exposure (e.g. S$15,000/day daily rate).
4. **SOPA Adjudicators & Arbitration Tribunals**: Serves as admissible contemporaneous expert evidence under the Singapore Building and Construction Industry Security of Payment Act (SOPA) in the event of formal statutory adjudication.

#### What Occurs Behind the Scenes During Execution:
Running this command initiates the **3-Agent Adversarial Deliberation Theater**:
1. **Round 1 - Contractor Claims Agent (Claimant)**: Invokes `s04_simulate_tia_fragnet` to demonstrate that groundwater ingress drove a 3-day critical shift on the driving path, advocating for 3 workdays of EOT and S$0 LAD.
2. **Round 2 - Employer QS Agent (Respondent)**: Invokes `s04_calculate_psscoc_notice_clock` and `s04_assess_liquidated_damages_exposure` to scrutinize the submission date against the notice timebar and calculate maximum employer financial recovery (3 days @ S$15,000/day = S$45,000).
3. **Round 3 - Superintending Officer Agent (Impartial Arbitrator)**: Reconciles the dispute under SCL Delay Protocol Core Principle 10 (neutral event concurrency), verifies notice compliance, rules that contractor culpable delay is 0 days, awards 3 days of candidate EOT relief, and reduces LAD exposure to S$0.00.
4. **Audit Persistence**: Persists the session record and turn transcript into `data/parquet/audit_deliberation_log.parquet` for immutable downstream audit provenance.

#### Implication If Skipped (Does It Make the S04 Dashboard Data Incomplete?):
Without executing the agent client, the data that are displayed on the S04 dashboard only showcases raw mathematical scheduling metrics (Gantt charts and CPM numbers). The platform will miss the core agentic capability: the multi-agent adversarial deliberation and the automated generation of the statutory EOT assessment memo that bridges construction data with legal determination.

#### Command Execution:

```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
python agent_client/client.py --project-id PRJ-WHC-COM-001 --generate-memo
```

![alt text](images/python_agent_client_client_generate_memo.png)

---

### <span id="hybrid-dashboard"></span>📊 4.3 Cloud-Backed Forensic Delay Cockpit (AWS, Azure, GCP, Local) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

#### Why We Run This Step:
This step launches the Forensic Delay Cockpit web interface to visualize schedule topologies, time-scaled network diagrams, float erosion heatmaps, and the multi-agent deliberation hearing room. It demonstrates that the same UI can operate seamlessly across different cloud cognitive backends without code modifications.

```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a

# 1. Launch with Amazon Web Services Engine (AWS Bedrock) on default port 8087
CLOUD_PROVIDER=AWS python3 dashboard/server.py --port 8087

# 2. Launch with Microsoft Azure Engine (Azure OpenAI / Azure Cloud) on default port 8087
CLOUD_PROVIDER=AZURE python3 dashboard/server.py --port 8087

# 3. Launch with Google Cloud Platform Engine (Vertex AI) on default port 8087
CLOUD_PROVIDER=GCP python3 dashboard/server.py --port 8087

# 4. Launch with Local Sovereign Engine on default port 8087
CLOUD_PROVIDER=LOCAL python3 dashboard/server.py --port 8087
```

![alt text](images/python_dashboard_server_aws_8087.png)

![alt text](images/python_dashboard_server_azure_8087.png)
![alt text](images/python_dashboard_server_gcp_8087.png)

![alt text](images/python_dashboard_server_local_8087.png)

#### User-Defined Port Configuration & Concurrent Engine Execution:
- **Configurable Port Parameter**: The `--port` flag is completely user-configurable (defaults to `8087` if omitted).
- **Single Instance on the Same Port**: Only one server instance can bind to a specific network port (e.g., `8087`) at any given time.
- **Running Multiple Engines Simultaneously Across Multiple Ports**: If you wish to run multiple engines concurrently in separate terminals for direct side-by-side comparison during a live presentation, assign different ports to each terminal:
  - Terminal 1: `CLOUD_PROVIDER=LOCAL python3 dashboard/server.py --port 8087` -> opens `http://localhost:8087`
  - Terminal 2: `CLOUD_PROVIDER=AWS python3 dashboard/server.py --port 8088` -> opens `http://localhost:8088`
  - Terminal 3: `CLOUD_PROVIDER=AZURE python3 dashboard/server.py --port 8089` -> opens `http://localhost:8089`
  - Terminal 4: `CLOUD_PROVIDER=GCP python3 dashboard/server.py --port 8090` -> opens `http://localhost:8090`
- **Dynamic Parameter Switching on a Single Running Instance**: If running just one server instance on port `8087`, you can also dynamically switch between engine badges directly in the browser by appending the query parameter (e.g., `http://localhost:8087/?engine=aws`, `http://localhost:8087/?engine=azure`, `http://localhost:8087/?engine=gcp`, or `http://localhost:8087/?engine=local`) without restarting the server.

Open `http://localhost:8087` in any standard web browser to view the interactive forensic delay cockpit with the active cloud cognitive engine badge (`AWS Engine`, `Azure Engine`, `GCP Engine`, or `Local Engine`) dynamically displayed in the top-right command bar.

![alt text](images/s04_dashboard_approach_2_aws_8087_light_mode.png)

![alt text](images/s04_dashboard_approach_2_azure_8087_light_mode.png)

![alt text](images/s04_dashboard_approach_2_gcp_8087_light_mode.png)

![alt text](images/s04_dashboard_approach_2_local_8087_light_mode.png)

---

## <span id="cloud-provisioning"></span><span style="color:red">☁️ 5. Approach 3: Cloud Workload Direct Provisioning (Multi-Cloud Terraform Deployments)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

![Approach 3: Direct Multi-Cloud Provisioning](images/approach_3_cloud_workload.png)

Approach 3 deploys the S04 containerized analytical cockpit and cloud object storage lakehouse directly to public cloud infrastructure using automated Terraform templates.

### <span id="why-cloud-native"></span>🎯 5.1 Why Choose Cloud Workload Direct Provisioning? <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

1. **Enterprise Scalability**: Decouples persistent lakehouse storage from stateless web cockpits, enabling autoscaling across project teams.
2. **Centralized Project Oversight**: Multi-project portfolios access a single, authoritative cloud endpoint backed by cloud object storage.
3. **Cross-Module Integration**: Emits partitioned Parquet link tables directly to enterprise object storage for S05 Quality Inspection and S06 SOPA Claims ingestion.

---

### <span id="cloud-native-prerequisites"></span>📋 5.2 Pre-requisites for Approach 3 <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Ensure Docker Desktop is running locally and authenticate your local CLI to your chosen cloud platform:

#### 1. Cloud Authentication:
Authenticate your local CLI to your respective cloud provider account:
- **AWS**: Run `aws configure` (or `aws sso login`) to configure your AWS Access Key, Secret Access Key, and default region (`ap-southeast-1`).
- **Azure**: Run `az login` to initiate browser-based Azure Entra ID authentication.
- **Google Cloud**: Run `gcloud auth login` and `gcloud auth application-default login` to authenticate the Google Cloud SDK and set your default project via `gcloud config set project ${GCP_PROJECT_ID}`.

#### 2. Verify Active Cloud Authentication & Identity:
Verify that your active cloud identity and credentials are operational:

```bash
# AWS: Verify caller identity
aws sts get-caller-identity

# Azure: Verify active subscription
az account show

# GCP: Verify authorized accounts
gcloud auth list
```

![alt text](images/verify_credentials.png)

---

### <span id="terraform-aws"></span>🟧 5.3 AWS Deployment (ECS Fargate + S3 Lakehouse + ALB on Port 8087) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

<details>
<summary><b>🚀 Click to expand 5.3 AWS Deployment (ECS Fargate + S3 Lakehouse + ALB on Port 8087) guide, Terraform IaC, and architecture</b></summary>

![AWS Cloud-Native Deployment Architecture](images/architecture_aws.png)

Provisions an AWS Application Load Balancer (ALB), an ECS Fargate cluster, an ECR container repository, an IAM task execution role, and a secure S3 Parquet Lakehouse bucket.

Follow the self-contained 5-step workflow:

#### Step 1: Provision Infrastructure with Terraform
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
cd terraform/aws
terraform init
terraform apply -auto-approve
```

#### Step 2: Synchronize Parquet Lakehouse to S3 Bucket
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
S3_BUCKET=$(cd terraform/aws && terraform output -raw delay_lake_bucket)
aws s3 sync data/parquet/ s3://${S3_BUCKET}/parquet/
```

![alt text](images/upload_parquet_to_s3_aws.png)

#### Step 3: Build and Push Docker Image to ECR
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
ECR_URL=$(cd terraform/aws && terraform output -raw ecr_repository_url)
AWS_REGION=$(cd terraform/aws && terraform output -raw aws_region)

aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URL}
docker build --platform linux/amd64 -t ${ECR_URL}:latest .
docker push ${ECR_URL}:latest
```

![alt text](images/docker_build_tag_push_aws.png)

#### Step 4: Trigger ECS Deployment
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
CLUSTER=$(cd terraform/aws && terraform output -raw ecs_cluster_name)
aws ecs update-service --cluster ${CLUSTER} --service acip-s04-delay-service-prod --force-new-deployment
```

![alt text](images/s04_application_run_aws_terminal_1.png)

#### Step 5: Verify Live Cloud Endpoint
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
ALB_URL=$(cd terraform/aws && terraform output -raw alb_url)
open ${ALB_URL}
```

![alt text](images/s04_application_run_aws_terminal_2.png)

![alt text](images/s04_dashboard_approach_3_aws_8087_light_mode.png)

</details>

---

### <span id="terraform-azure"></span>🟦 5.4 Azure Deployment (Azure Container Apps + Blob Lakehouse on Port 8087) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

<details>
<summary><b>🚀 Click to expand 5.4 Azure Deployment (Azure Container Apps + Blob Lakehouse on Port 8087) guide, Terraform IaC, and architecture</b></summary>

![Azure Cloud-Native Deployment Architecture](images/architecture_azure.png)

Provisions an Azure Container Apps Environment, an Azure Container Registry (ACR), a Container App with external HTTP ingress on port 8087, and an Azure Blob Storage Lakehouse container.

Follow the self-contained 5-step workflow:

#### Step 1: Provision Infrastructure with Terraform
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
cd terraform/azure
terraform init
terraform apply -auto-approve
```

#### Step 2: Synchronize Parquet Lakehouse to Azure Blob Storage
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
STORAGE_ACCOUNT=$(cd terraform/azure && terraform output -raw storage_account_name)
CONTAINER_NAME=$(cd terraform/azure && terraform output -raw storage_container_name)

az storage blob upload-batch \
  --account-name ${STORAGE_ACCOUNT} \
  --destination ${CONTAINER_NAME}/parquet \
  --source data/parquet \
  --auth-mode key
```

![alt text](images/upload_parquet_to_blob_storage_azure.png)

#### Step 3: Build and Push Docker Image to ACR
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
ACR_LOGIN=$(cd terraform/azure && terraform output -raw acr_login_server)
ACR_USER=$(cd terraform/azure && terraform output -raw acr_admin_username)
ACR_PASS=$(cd terraform/azure && terraform output -raw acr_admin_password)

docker login ${ACR_LOGIN} -u ${ACR_USER} -p ${ACR_PASS}
docker build --platform linux/amd64 -t ${ACR_LOGIN}/acip-s04-delay-cockpit:latest .
docker push ${ACR_LOGIN}/acip-s04-delay-cockpit:latest
```

![alt text](images/docker_build_tag_push_azure.png)

#### Step 4: Update Container App Revision
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
ACR_LOGIN=$(cd terraform/azure && terraform output -raw acr_login_server)
az containerapp update \
  --name acip-s04-delay-cockpit \
  --resource-group acip-s04-delay-rg-prod \
  --image ${ACR_LOGIN}/acip-s04-delay-cockpit:latest
```

![alt text](images/s04_application_run_azure_terminal_1.png)

#### Step 5: Verify Live Cloud Endpoint
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
CONTAINER_APP_URL=$(cd terraform/azure && terraform output -raw container_app_url)
open ${CONTAINER_APP_URL}
```

![alt text](images/s04_application_run_azure_terminal_2.png)

![alt text](images/s04_dashboard_approach_3_azure_8087_light_mode.png)

</details>

---

### <span id="terraform-gcp"></span>🟥 5.5 Google Cloud Deployment (Cloud Run v2 + GCS Lakehouse on Port 8087) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

<details>
<summary><b>🚀 Click to expand 5.5 Google Cloud Deployment (Cloud Run v2 + GCS Lakehouse on Port 8087) guide, Terraform IaC, and architecture</b></summary>

![Google Cloud-Native Deployment Architecture](images/architecture_gcp.png)

Provisions a Google Cloud Run v2 service, an Artifact Registry Docker repository, and a Google Cloud Storage (GCS) Parquet Lakehouse bucket.

Follow the self-contained 5-step workflow:

#### Step 1: Provision Infrastructure with Terraform
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
cd terraform/gcp
terraform init
terraform apply -auto-approve -var="project_id=${GCP_PROJECT_ID}"
```

#### Step 2: Synchronize Parquet Lakehouse to Google Cloud Storage (GCS)
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
GCS_BUCKET=$(cd terraform/gcp && terraform output -raw delay_lake_bucket)
gcloud storage rsync data/parquet/ gs://${GCS_BUCKET}/parquet/
```

![alt text](images/upload_parquet_to_cloud_storage_gcp.png)

#### Step 3: Build and Push Docker Image to Artifact Registry
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
REPO_URL=$(cd terraform/gcp && terraform output -raw artifact_registry_url)

gcloud auth configure-docker asia-southeast1-docker.pkg.dev --quiet
docker build --platform linux/amd64 --provenance=false -t ${REPO_URL}/acip-s04-delay-cockpit:latest .
docker push ${REPO_URL}/acip-s04-delay-cockpit:latest
```

![alt text](images/docker_build_tag_push_gcp.png)

#### Step 4: Deploy to Cloud Run v2
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
REPO_URL=$(cd terraform/gcp && terraform output -raw artifact_registry_url)
gcloud run deploy acip-s04-delay-cockpit \
  --image ${REPO_URL}/acip-s04-delay-cockpit:latest \
  --region ${GCP_REGION} \
  --quiet
```

![alt text](images/s04_application_run_gcp_terminal_1.png)

#### Step 5: Verify Live Cloud Endpoint
```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
CLOUD_RUN_URL=$(cd terraform/gcp && terraform output -raw cloud_run_url)
open ${CLOUD_RUN_URL}
```

![alt text](images/s04_application_run_gcp_terminal_2.png)

![alt text](images/s04_dashboard_approach_3_gcp_8087_light_mode.png)

</details>

---

## <span id="enterprise-landing-zone"></span><span style="color:red">🏢 6. Approach 4: Reference Enterprise Deployment Pattern & Sovereign Governance (Planned)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

![Approach 4: Enterprise Sovereign Landing Zone](images/approach_4_enterprise_landing_zone.png)

### <span id="sovereign-enclaves"></span>🔐 6.1 Dedicated Sovereign Planning Enclaves & Zero-Egress Storage <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

For public sector infrastructure owners and confidential defense developments, S04 provides an enterprise landing zone reference architecture:
- Dedicated VPC / VNet network boundary with zero public egress.
- Private Link endpoints connecting to AWS S3, Azure Blob, and Google Cloud Storage.
- Sovereign Hardware Security Module (HSM) key rotation for Parquet column-level encryption.

---

### <span id="audit-rbac"></span>🛡️ 6.2 Audit Trails, RBAC & Statutory Adjudication Defense Archive <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

- Cryptographic SHA-256 sidecar manifests on all schedule baseline updates and TIA fragnet runs.
- Append-only lakehouse logs preserving contemporaneous project evidence for 6+ years to satisfy statutory limitation periods under the Singapore Limitation Act.
- Role-Based Access Control (RBAC) strictly separating Contractor Planning input, QS assessment, and Superintending Officer certification roles.

---

## <span id="automated-testing"></span><span style="color:red">🔬 7. Automated Testing & Verification (78 Tests Across 6 Suites)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

The S04 module is certified by a comprehensive 78-test verification harness covering all 6 delivery increments:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   S04 PROGRESS & DELAY INTELLIGENCE VERIFICATION SUITE                 │
├─────────────────┬──────────────────────────────────────────┬──────────────┬────────────┤
│ Test Suite Name │ Scope & Engineering Focus                │ Test Volume  │ Status     │
├─────────────────┼──────────────────────────────────────────┼──────────────┼────────────┤
│ Suite 1         │ Gate 2 Certified Baseline Regressions    │ 8 Tests      │ PASSED     │
│ Suite 2         │ Increment 1A XER Ingestion & Provenance  │ 8 Tests      │ PASSED     │
│ Suite 3         │ Increment 1B Dynamic CPM Recalculation   │ 12 Tests     │ PASSED     │
│ Suite 4         │ Increment 2 Controlled TIA & FastMCP     │ 11 Tests     │ PASSED     │
│ Suite 5         │ Increment 3 Deliberation & Handshakes    │ 20 Tests     │ PASSED     │
│ Suite 6         │ Increment 4 Interactive Forensic Cockpit │ 19 Tests     │ PASSED     │
├─────────────────┴──────────────────────────────────────────┴──────────────┴────────────┤
│ COMBINED TEST SUITE TOTALS: 78 Tests Run across 6 Suites | 0 Failures | 0 Errors       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

To execute the complete 78-test audit runner:

```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
python tests/run_increment_4_audit.py
```

Expected final summary output:
```text
COMBINED TEST SUITE TOTALS: 78 Tests Run across 6 Suites | 0 Failures | 0 Errors | 4.611s
FINAL AUDIT STATUS: PASSED (ALL 6 SUITES GREEN - S04 FULL LIFECYCLE 100% COMPLETE)
```

To execute individual test suites directly via standard unittest:

```bash
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
set -a; source .env; set +a
python -m unittest tests/test_s04_verification_suite.py -v
python -m unittest tests/test_s04_increment_1a.py -v
python -m unittest tests/test_s04_increment_1b.py -v
python -m unittest tests/test_s04_increment_2.py -v
python -m unittest tests/test_s04_increment_3.py -v
python -m unittest tests/test_s04_increment_4.py -v
```

Expected individual suite summary:

```text
Suite 1 (test_s04_verification_suite.py): Ran 8 tests  | 0 failures | 0 errors | OK (0.254s)
Suite 2 (test_s04_increment_1a.py):         Ran 8 tests  | 0 failures | 0 errors | OK (0.148s)
Suite 3 (test_s04_increment_1b.py):         Ran 12 tests | 0 failures | 0 errors | OK (1.128s)
Suite 4 (test_s04_increment_2.py):          Ran 11 tests | 0 failures | 0 errors | OK (2.090s)
Suite 5 (test_s04_increment_3.py):          Ran 20 tests | 0 failures | 0 errors | OK (0.422s)
Suite 6 (test_s04_increment_4.py):          Ran 19 tests | 0 failures | 0 errors | OK (0.731s)
────────────────────────────────────────────────────────────────────────────────────────
COMBINED INDIVIDUAL TOTALS:                 Ran 78 tests across 6 suites | ALL PASSED (OK)
```

---

## <span id="cleanup"></span><span style="color:red">🧹 8. Clean Up</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

### <span id="destroy-cloud"></span>☁️ 8.1 Destroy Cloud Workloads (AWS, Azure, GCP) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

To tear down cloud resources and avoid ongoing cloud provider charges:

```bash
# Destroy AWS ECS Fargate & ALB infrastructure
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
cd terraform/aws && terraform destroy -auto-approve && cd ../..

# Destroy Azure Container Apps & ACR infrastructure
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
cd terraform/azure && terraform destroy -auto-approve && cd ../..

# Destroy Google Cloud Run & Artifact Registry infrastructure
# Ensure you are at the S04_Agentic_Progress_And_Delay_Intelligence module root folder before starting
cd terraform/gcp && terraform destroy -auto-approve -var="project_id=${GCP_PROJECT_ID}" && cd ../..
```

---

## 📄 License
This module is distributed as part of the Agentic Construction Intelligence Platform (ACIP) under the **Apache License 2.0**. See the root [LICENSE](../LICENSE) file for full license terms and conditions.
