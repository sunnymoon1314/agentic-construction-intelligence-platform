# <span style="color:red">🛠️ S03: Implementation Guide & Technical Runbook</span>

[📄 Go to S03 Business Problem Statement & Case Studies](BUSINESS_PROBLEM_STATEMENT.md) | [⬆️ Back to ACIP Overview](../README.md#toc)

---

**S03: Agentic Cost & Commercial Control Intelligence** is an assistive commercial decision-support module designed for Commercial Managers, Quantity Surveyors (QS), Project Directors, and Adjudication Counsel operating under standard Singapore construction contracts (PSSCOC 2020/2025, SIA 2024, and LTA Conditions).

S03 is not an AI that calculates construction payments. It is an agentic decision-support architecture in which deterministic commercial and statutory calculations are deliberately separated from probabilistic AI reasoning. The system uses FastMCP-based deterministic engines to calculate commercial outcomes and enforce configured contractual and statutory rules, while multi-agent LLMs are restricted to interpretation, synthesis, and decision-support narratives.

**💡 Core Architectural Philosophy**: AI can reason. Deterministic systems calculate. Evidence supports. Professionals decide.

**💡 Core Commercial Tenet**: "A project can be within budget and still be heading towards a commercial problem." Traditional commercial reporting tells management where the project is; S03 attempts to show where the commercial position is heading, and why.

### 🛡️ Technical Scope & Architectural Boundaries

- **🧪 Working Reference Implementation**: S03 is an active, fully functional implementation featuring four real-world Singapore project scenarios, an in-process DuckDB columnar store with Apache Parquet lakehouse partitions, six deterministic FastMCP calculation tools, a collaborative 3-agent deliberation engine, an automated reference test suite, and an interactive single-page web cockpit on configurable port 8086.
- **🧱 ACIP Deterministic Execution Boundary**: The LLM may interpret authoritative outputs, but cannot alter the authoritative execution path. All calculations, statutory timebars, and deduction amounts are executed outside the probabilistic LLM path (LLM-excluded authoritative calculation path) to ensure mathematical and statutory integrity.
- **⚖️ Decision-Support Boundary**: S03 produces auditable BIM measurement reconciliations, 4-tier variation order waterfalls with 28-day notice timebar drops, Ministry of Manpower (MOM) safety set-off deductions, statutory SOPA Section 11 payment responses, and predictive Earned Value Management (EVM) contingency depletion alerts. S03 cannot autonomously issue binding payment certificates or waive statutory rights. Official commercial certification strictly requires authorization by a licensed Quantity Surveyor or certified Superintending Officer.

### 🚧 Explicit Scope Boundaries (What S03 Does NOT Do)

To ensure strict legal and governance defensibility, S03 explicitly does NOT:
- Replace the Quantity Surveyor's professional valuation or certified commercial judgment;
- Determine contractual entitlement independently of the governing contract terms;
- Constitute legal advice or replace formal adjudication counsel;
- Determine statutory entitlement solely from an IFC building model;
- Allow any Large Language Model to alter statutory calculations or payment response amounts;
- Guarantee the outcome of adjudication before the Singapore Mediation Centre (SMC);
- Treat AI-generated narrative as authoritative evidentiary proof without backing primary records.

---

## <span id="toc"></span>📑 Table Of Contents (TOC)

- [0. Pre-requisite Software](#prerequisites)
- [1. Architecture Overview](#architecture-overview)
  - [1.1 System Architecture & Analytical Pillars](#system-architecture)
  - [1.2 The Three Non-Negotiable Statutory Logic Gates](#logic-gates)
  - [1.3 MOM Workplace Safety & Statutory Set-Off Formulations](#mom-safety)
  - [1.4 Four Real-World Demonstration Scenarios](#demo-scenarios)
- [2. Directory Structure](#directory-structure)
- [3. Approach 1: Pure Local Sovereign Deployment & Testing (Zero Cost)](#local-deployment)
  - [3.1 Environment Configuration & Dependencies](#env-config)
  - [3.2 Seeding Ground-Truth Synthetic Dataset & Parquet Lakehouse](#seed-dataset)
  - [3.3 FastMCP Deterministic Tool Server Execution](#fastmcp-server)
  - [3.4 Multi-Agent Commercial Deliberation Client](#agent-client)
  - [3.5 Interactive Commercial Cockpit (Web UI on Port 8086)](#commercial-cockpit)
- [4. Approach 2: Hybrid Testing Sandbox (Local Application + Cloud LLM APIs)](#hybrid-testing)
  - [4.1 Cloud LLM Provider Credentials & Environment (.env)](#hybrid-env)
  - [4.2 Qualitative Dispute Narrative & Executive Memo Generation](#hybrid-memo)
  - [4.3 Cloud-Backed Executive Commercial Cockpit (AWS, Azure, GCP, Local)](#hybrid-dashboard)
- [5. Approach 3: Cloud Workload Direct Provisioning (Multi-Cloud Terraform Deployments)](#cloud-provisioning)
  - [5.1 Why Choose Cloud Workload Direct Provisioning?](#why-cloud-native)
  - [5.2 Pre-requisites for Approach 3](#cloud-native-prerequisites)
  - [5.3 AWS Deployment (ECS Fargate + S3 Lakehouse + ALB on Port 8086)](#terraform-aws)
  - [5.4 Azure Deployment (Azure Container Apps + Blob Lakehouse)](#terraform-azure)
  - [5.5 Google Cloud Deployment (Cloud Run v2 + GCS Lakehouse)](#terraform-gcp)
- [6. Approach 4: Reference Enterprise Deployment Pattern & Sovereign Governance (Planned)](#enterprise-landing-zone)
  - [6.1 Dedicated Sovereign Commercial Enclaves & Zero-Egress Storage](#sovereign-enclaves)
  - [6.2 Audit Trails, RBAC & Statutory Adjudication Defense Archive](#audit-rbac)
- [7. Automated Testing & Verification](#automated-testing)
- [8. Clean Up](#cleanup)
  - [8.1 Destroy Cloud Workloads (AWS, Azure, GCP)](#destroy-cloud)
  - [8.2 Reset Local Database & Parquet Lakehouse](#reset-local)
- [9. Frequently Asked Questions (FAQ)](FAQ.md)
- [10. Troubleshooting Guide](TROUBLESHOOTING.md)

---

## <span id="prerequisites"></span><span style="color:red">⚙️ 0. Pre-requisite Software</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

📝 Note: All terminal commands in this technical runbook are written for Unix/macOS Bash or Zsh shells (execute using Git Bash or WSL2 on Windows). For Approach 1 (Pure Local Sovereign), only Python, Conda, and DuckDB are required. Cloud CLIs, Docker, and Terraform are only required if you choose to deploy to cloud providers (Approach 3).

Before beginning, ensure the following software is installed on the host machine:

- **Python 3.11+**: Core runtime environment for multi-agent orchestration and analytical pipelines. Download from the [Python Official Website](https://www.python.org/downloads/).
- **DuckDB 1.1+**: High-performance in-process columnar SQL OLAP database engine for instant zero-copy analytical queries across multi-bidder BOQ pricing schedules. Download from the [DuckDB Official Website](https://duckdb.org/).
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

![ACIP S03 Architecture Overview](images/s03_architecture_diagram.png)

S03 bridges commercial intelligence and statutory construction law through four integrated analytical pillars and collaborative multi-agent deliberation:

![ACIP S03 Commercial Control & Statutory Analytical Pillars Workflow Architecture](images/s03_analytical_pillars_workflow.png)

<details>
<summary><b>📐 Click to view Mermaid Architecture Diagram Source</b></summary>

The complete Mermaid diagram source has been extracted to [s03_analytical_pillars_workflow.md](images/s03_analytical_pillars_workflow.md).

</details>

- **Pillar 1: 5D openBIM Quantity Reconciler & Medallion Lakehouse Engine**: Ingests multi-source commercial data across a 3-tier Medallion lakehouse pattern:
  - **Bronze Layer (Raw Ingestion)**: Ingests raw JSON interim progress claims, IFC element geometry, and contractor variation notices.
  - **Silver Layer (Cleaned & Partitioned Parquet)**: Cleans, normalizes, and partitions tabular datasets (`claims/`, `openbim_takeoff/`, `rate_schedule/`, `variation_orders/`) queryable via in-process DuckDB columnar SQL. In cloud workloads, DuckDB queries Parquet files directly via HTTP range requests using the `httpfs` extension (performance governed by network latency, query selectivity, and partition layout).
  - **Gold Layer (Curated Commercial Marts)**: Produces authoritative, adjudication-ready deduction ledgers, certified valuation schedules, and predictive EVM cash flow marts.
- **Pillar 2: 4-Tier Variation Order Valuation Waterfall**: Audits contractor variation orders against baseline Schedule of Rates (SOR), detects Star Rate duplication fraud, and waives claims violating the 28-day notice rule.
- **Pillar 3: Singapore SOPA Section 11 Statutory Engine**: Models applicable payment-response deadlines based on Singapore SOPA Section 11(1) and Section 11(3) statutory rules and contract configuration, formatting structured deduction dossiers to preserve employer withholding defenses in adjudication.
- **Pillar 4: Predictive EVM & Contingency Velocity Radar**: Ingests Earned Value metrics (BAC, BCWP, ACWP, CPI) and applies a burn-velocity risk multiplier to forecast the exact month of contingency exhaustion.

---

### <span id="logic-gates"></span>🛡️ 1.2 The Three Non-Negotiable Statutory Logic Gates <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

To establish structured, auditable commercial defensibility before the Singapore Mediation Centre (SMC) and dispute tribunals, S03 enforces three deterministic logic gates:

1. **Gate 1: The SOPA Section 11 Statutory Response Engine**:
   - `Response_Deadline = min(contract_payment_response_days, 21)` (defaulting to 14 days if the contract is silent per Section 11(1)(b))
   - Statutory Configuration: S03 models the applicable payment-response deadline based on Singapore SOPA Section 11(1) and Section 11(3) statutory rules and contract configuration, including the configured PSSCOC payment-response period.
   - Preservation of Withholding Defenses: Under Section 11(3) and Section 15(3) of SOPA, failure to properly itemize reasons for withholding payment can legally preclude the employer from introducing new withholding grounds in subsequent adjudication proceedings.
   - Business Calendar Engine: Automatically omits Sundays and gazetted Singapore Public Holidays per Section 2 of SOPA and the Interpretation Act.
2. **Gate 2: The Multi-Tier VO Valuation Hierarchy & 28-Day Timebars**:
   - Tier 1 (Contract Schedule of Rates): Enforced if work is of similar character.
   - Tier 2 (Pro-Rata SOR): Enforced if work character matches but quantities or conditions differ.
   - Tier 3 (Star Rates / Market Valuation): Only permitted for genuinely new scope substantiated by merchant quotations.
   - Tier 4 (Daywork): Direct labor/plant cost plus markup; strictly requires signed site chits.
   - 28-Day Notice Timebar: Claims with `days_elapsed > 28` are deterministically flagged as `TIMEBAR_EXPIRED_CLAIM_WAIVED` with 100% deduction under configured PSSCOC Clause 19.1 rules, subject to authorized QS and legal review of applicability and contractual exceptions.
   - Star Rate Anti-Fraud: If a claimed Star Rate matches an existing baseline SOR item, the system rejects Tier 3, forces Tier 1 fallback, and flags `RATE_DUPLICATION_DETECTED`.
3. **Gate 3: Deterministic Calculation Gate (LLM Excluded from Authoritative Arithmetic)**:
   - Large Language Models are strictly excluded from the authoritative calculation path. All arithmetic, retention caps, and penalty ledgers are computed deterministically in Python against DuckDB columnar tables outside the probabilistic LLM path (LLM-excluded authoritative calculation path). The agentic models are restricted to drafting legal dispute narratives and executive briefing memos based on unalterable deterministic outputs.

---

### <span id="mom-safety"></span>⚠️ 1.3 MOM Workplace Safety & Statutory Set-Off Formulations <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Under Singapore Ministry of Manpower (MOM) safety frameworks and public sector contract preliminaries, safety infractions are deducted directly from monthly progress certificates:

1. **Mandatory Stop-Work Order (SWO) Liquidated Backcharge**:
   `SWO Deduction = Idle Days * Daily Preliminaries Extended Cost (S$12,500.00 / day)`
2. **Contractual Safety Demerit Point (SDP) Financial Penalty**:
   - Tiers 1 to 9 Demerit Points: S$1,500.00 flat deduction per point.
   - Tiers 10 to 24 Demerit Points: S$3,500.00 flat deduction per point.
   - Tier >= 25 Demerit Points (Debarment Threshold Triggered): S$50,000.00 corporate backcharge.
3. **Unremediated Site Safety Fine Indemnification**:
   `Fine Deduction = Regulatory Statutory Fine * (1.0 + 0.15 Admin Markup)`

---

### <span id="demo-scenarios"></span>🎭 1.4 Four Real-World Demonstration Scenarios <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

| Project ID | Project Name | Contract Sum | Main Contractor | Contract Form | Primary Commercial Challenge |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PRJ-WHC-COM-001** | Woodlands Health Campus Commercial Annex | S$55,000,000 | WinningPine Construction Pte Ltd | PSSCOC 2025 | Month 8 over-certification trap (S$1,162.5k openBIM discrepancy across 5 elements), 12 VOs with Star Rate duplication, and MOM safety set-offs. |
| **PRJ-JID-ATP-004** | Jurong Innovation District Advanced Tech Park | S$68,500,000 | Heng Win (Private) Limited | PSSCOC 2020 | Month 6 cumulative dispute: S$630k openBIM over-claim, deep well dewatering Star Rate duplication, and 70-day timebar breach. |
| **PRJ-MBF-FIT-002** | Marina Bay Financial Tower L28-35 Commercial Fit-Out | S$22,400,000 | GemStone Building Contractors Pte Ltd | SIA Measurement | Month 4 fast-track fit-out: Luxury marble Star Rate markup trim, night shift quiet hours 48-day timebar waiver. |
| **PRJ-CRL-CR108** | Cross Island Line Underground Ancillary Shaft | S$145,000,000 | GrandPillar Infrastructure Pte Ltd | Civil LTA Form | Month 12 heavy civil shaft: Micro-tunneling sleeve Star Rate duplication, off-island barge spoil surcharge timebar breach. |

---

## <span id="directory-structure"></span><span style="color:red">📁 2. Directory Structure</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

The complete file layout on disk:

```text
S03_Agentic_Cost_And_Commercial_Control_Intelligence/
├── agent_client/                               # Multi-agent deliberation pipeline and consensus client
│   └── evaluator.py                            # Tri-agent consensus evaluator (QS, Counsel, Director)
├── dashboard/                                  # Executive commercial cockpit web application
│   ├── index.html                              # Single-page reactive dashboard with surgical forensic drawers
│   └── server.py                               # Python HTTP server with multi-tier cloud auto-detection
├── data/                                       # Contractual baselines, synthetic data, and lakehouse
│   ├── parquet/                                # Approach 3 partitioned Apache Parquet columnar lakehouse
│   │   ├── claim_items.parquet                 # openBIM physical takeoff vs claim line items
│   │   ├── cost_forecast_eac.parquet           # Monthly EVM metrics, CPI/SPI, and EAC forecasts
│   │   ├── interim_claims.parquet              # Contractor progress claims and certified amounts
│   │   ├── projects.parquet                    # Master commercial projects metadata and budgets
│   │   ├── schedule_of_rates.parquet           # Contractual baseline SOR item catalog and unit rates
│   │   ├── site_safety_incidents.parquet       # MOM demerit points and safety backcharge log
│   │   └── variation_orders.parquet            # Variation order log with PSSCOC timebar audit records
│   ├── all_projects_registry.json              # Multi-project metadata for all 4 scenario benchmarks
│   ├── calendar_engine.py                      # MOM and SOPA statutory business day calendar engine
│   ├── commercial_control.duckdb               # Local embedded DuckDB analytical database
│   ├── contract_baseline.json                  # Contract baselines, SOR rates, and initial contingency
│   ├── generate_commercial_data.py             # Data generator seeding DuckDB and Parquet partitions
│   ├── interim_claims.json                     # Raw interim payment claims across project lifecycles
│   ├── statutory_calendars.json                # Singapore statutory gazetted public holiday calendars
│   └── variation_orders.json                   # 12 Variation orders spanning 4 valuation tiers
├── images/                                     # Visual documentation, architecture diagrams, and charts
│   ├── approach_1_local_sovereign.png          # Approach 1 pure local sovereign architecture diagram
│   ├── approach_2_hybrid_sandbox.png           # Approach 2 hybrid cloud LLM sandbox architecture
│   ├── approach_3_cloud_workload.png           # Approach 3 cloud-native serverless architecture
│   ├── approach_4_enterprise_landing_zone.png  # Approach 4 enterprise multi-account landing zone
│   ├── architecture_aws.png                    # AWS ECS Fargate + S3 Parquet Lakehouse architecture
│   ├── architecture_azure.png                  # Azure Container Apps + Blob Lakehouse architecture
│   ├── architecture_gcp.png                    # Google Cloud Run + GCS Lakehouse architecture
│   ├── s03_analytical_pillars_workflow.png     # 4 analytical pillars multi-agent workflow diagram
│   └── s03_architecture_diagram.png            # ACIP S03 end-to-end platform architecture diagram
├── mcp_server/                                 # Model Context Protocol (FastMCP) calculation server
│   └── server.py                               # FastMCP server exposing 6 deterministic audit tools
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
├── tests/                                      # Automated pytest test suite and verification harnesses
│   └── test_s03_pipeline.py                    # End-to-end pipeline validation and deterministic checks
├── .env.example                                # Template environment variables for local and cloud modes
├── BUSINESS_PROBLEM_STATEMENT.md               # Domain brief on SOPA statutory risk and cash-flow leakage
├── Dockerfile                                  # Multi-platform Linux AMD64 container build specification
├── FAQ.md                                      # Frequently asked questions with deep architectural answers
├── README.md                                   # Comprehensive technical documentation and runbook
├── requirements.txt                            # Python dependencies (fastmcp, duckdb, pydantic, etc.)
└── TROUBLESHOOTING.md                          # Categorized issues, root cause analyses, and solutions
```

---

## <span id="local-deployment"></span><span style="color:red">💻 3. Approach 1: Pure Local Sovereign Deployment & Testing (Zero Cost)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

![Approach 1: Pure Local Sovereign Architecture](images/approach_1_local_sovereign.png)

Approach 1 runs 100% locally on standard workstation hardware with zero external API calls or cloud subscription costs.

### <span id="env-config"></span>⚙️ 3.1 Environment Configuration & Dependencies <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Because ACIP contains many modules (S01 to S07) sharing one Conda environment, every bash block in this README starts with `cd "${ACIP_MODULE_DEFAULT_FOLDER}"`. This guarantees commands run inside the S02 module folder no matter which terminal tab or folder you are currently in.

Step 1: Set the module folder once (open a terminal inside the S02 folder in your IDE, or if starting from the ACIP platform root, navigate into the S02 folder first):

```bash
# If starting from the ACIP platform root:
cd S03_Agentic_Cost_And_Commercial_Control_Intelligence

# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
export ACIP_MODULE_DEFAULT_FOLDER="$(pwd)"
echo "${ACIP_MODULE_DEFAULT_FOLDER}"
```

![Setting default module folder in terminal](images/s03_module_default_folder.png)

Step 2: Create (first time only) and activate the unified ACIP Conda environment:

We require conda environment `acip_mcp_framework` to be created before you can run the codes documented in this module. If you have not done so, please run the following command to create the environment:

```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
cd "${ACIP_MODULE_DEFAULT_FOLDER}"
conda env create -f ../environment.yml
```

![Conda environment creation step 1](images/conda_env_create_1.png)

![Conda environment creation step 2](images/conda_env_create_2.png)

This is followed by activating the environment:

```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
conda activate acip_mcp_framework
```

![Conda environment activation for ACIP framework](images/conda_activate_acip_mcp_framework.png)

📝 Note: If you have already created `acip_mcp_framework` (e.g. while working in S01 or another ACIP module), skip `conda env create` and proceed directly to `conda activate acip_mcp_framework`.

Step 3: Create a local `.env` configuration file from `.env.example`:

```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
cd "${ACIP_MODULE_DEFAULT_FOLDER}"
cp .env.example .env
set -a; source .env; set +a
```

![Environment variable configuration from template](images/copy_env_example.png)

📝 Note: `ACIP_MODULE_DEFAULT_FOLDER` is managed as an environment variable in your shell or Conda environment and is not stored inside `.env`.

---

### <span id="seed-dataset"></span>🌱 3.2 Seeding Ground-Truth Synthetic Dataset & Parquet Lakehouse <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Execute the dataset generator to populate the local DuckDB columnar database and export partitioned Apache Parquet tables:

```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
python3 data/generate_commercial_data.py
```

![Synthetic Commercial Data Generation Terminal Output](images/python_data_generate_commercial_data.png)

---

### <span id="fastmcp-server"></span>⚙️ 3.3 FastMCP Deterministic Tool Server Execution <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

The FastMCP server exposes six deterministic calculation tools with Pydantic typing:
1. `list_commercial_projects`
2. `audit_variation_order`
3. `reconcile_progress_valuation`
4. `generate_sopa_response`
5. `serve_sopa_deadline_clock`
6. `get_predictive_eac`

Verify tool execution directly from the command line:

```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
python3 mcp_server/server.py
```

![FastMCP Server Execution Terminal Output](images/python_mcp_server_server.png)

---

### <span id="agent-client"></span>🤖 3.4 Multi-Agent Commercial Deliberation Client <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Run the multi-agent deliberation engine (`agent_client/evaluator.py`) to execute consensus across the Forensic QS Auditor Agent, Contracts & Claims Counsel Agent, and Statutory Commercial Director Agent:

```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
python3 agent_client/evaluator.py
```

![Multi-Agent Deliberation Client Terminal Output](images/python_agent_client_evaluator.png)

---

### <span id="commercial-cockpit"></span>🖥️ 3.5 Interactive Commercial Cockpit (Web UI on Port 8086) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Launch the executive web cockpit server on configurable port 8086:

```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
python3 dashboard/server.py --port 8086
```

![Commercial Cockpit Server Launch Terminal Output](images/python_dashboard_server.png)

Open your browser at `http://localhost:8086` to interact with:
- **Standardized S02 Design System**: Two-row executive header with boxed brand icon, flush subtitle hierarchy, Light Mode by default, and `🌙 Dark Mode` toggle.
- **Dynamic Project Dropdown**: Switch seamlessly between all four scenario projects with reactive sector, contract form, and contractor meta chips.
- **Global Evidence Tooltips**: Informational tooltips (ℹ️) across all KPI metrics, statutory deadline indicators, and table headers explaining domain mechanics without clipping.
- **Live SOPA Countdown Widget**: Real-time traffic-light status powered by `serve_sopa_deadline_clock`.
- **openBIM Model Takeoff Heatmap**: Color-coded table flagging uninstalled quantities exceeding 2.0% variance.
- **VO Valuation Waterfall**: 4-tier waterfall visualizer illustrating PSSCOC Clause 19.1 28-day notice timebars and Star Rate fallbacks.
- **Predictive EVM Radar**: Interactive monthly burn-velocity slider forecasting contingency exhaustion.
- **Statutory SOPA Dossier**: Fully formatted Section 11 Payment Response ready for legal service, complete with interactive Section 11 Withholding review trigger.
- **Non-Modal Floating Surgical Inspectors**: Floating, non-modal right-side panels (VO Forensic Drawer, 5D Takeoff Drawer, SOPA Statutory Grounds Drawer, and SRE Observability Drawer) enabling continuous interaction with the main dashboard while open.

![Interactive Executive Commercial Cockpit in Light Mode](images/s03_dashboard_01a_local_8086_light_mode.png)

![Interactive Executive Commercial Cockpit in Dark Mode](images/s03_dashboard_01b_local_8086_dark_mode.png)

![alt text](images/s03_dashboard_02a_metric_drawer_base_contract_sum.png)

![alt text](images/s03_dashboard_02b_metric_drawer_approved_budget.png)

![alt text](images/s03_dashboard_02c_metric_drawer_interim_claim_gross.png)

![alt text](images/s03_dashboard_02d_metric_drawer_openbim_verify_gross.png)

![alt text](images/s03_dashboard_02e_metric_drawer_statutory_deductions.png)

![alt text](images/s03_dashboard_02f_metric_drawer_net_certified_payable.png)

![alt text](images/s03_dashboard_03aa_tab_5d_openbim_takeoff.png)

![alt text](images/s03_dashboard_03ab_tab_drawer_5d_openbim_takeoff.png)

![alt text](images/s03_dashboard_03ba_tab_variation_order_and_4_tier.png)

![alt text](images/s03_dashboard_03bb_tab_drawer_variation_order_and_4_tier.png)

![alt text](images/s03_dashboard_03c_tab_predictive_evm_radar.png)

![alt text](images/s03_dashboard_03da_tab_formal_sopa_section_11.png)

![alt text](images/s03_dashboard_03db_tab_drawer_formal_sopa_section_11_legal_dispute_memo.png)

![alt text](images/s03_dashboard_03dc_tab_drawer_formal_sopa_section_11_briefing_memo.png)

![alt text](images/s03_dashboard_03e_tab_financial_recovery_simulator.png)

---

## <span id="hybrid-testing"></span><span style="color:red">🧪 4. Approach 2: Hybrid Testing Sandbox (Local Application + Cloud LLM APIs)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

![Approach 2: Hybrid Testing Sandbox Architecture](images/approach_2_hybrid_sandbox.png)

Approach 2 connects local deterministic FastMCP computation with cloud-hosted Large Language Models (AWS Bedrock Claude 3.5 Sonnet, Azure OpenAI, or Google Gemini) for qualitative dispute narrative synthesis.

### <span id="hybrid-env"></span>🔑 4.1 Cloud LLM Provider Credentials & Environment (.env) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Configure your cloud API credentials in `.env`:

```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
cp .env.example .env
```

Set your respective provider API keys inside `.env`:
```ini
CLOUD_PROVIDER="AWS" # Options: AWS, AZURE, GCP, LOCAL

# Amazon Web Services (AWS Bedrock)
AWS_ACCESS_KEY_ID="your_aws_access_key"
AWS_SECRET_ACCESS_KEY="your_aws_secret_key"
AWS_REGION="ap-southeast-1"

# Microsoft Azure (Azure Storage & Container Apps)
AZURE_STORAGE_ACCOUNT="your_azure_storage_account"
AZURE_CONTAINER_NAME="commercial-lake"

# Google Cloud Platform (Vertex AI & Cloud Run)
GCP_PROJECT_ID="your_gcp_project_id"
GCP_REGION="asia-southeast1"
```

---

### <span id="hybrid-memo"></span>📝 4.2 Qualitative Dispute Narrative & Executive Memo Generation <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Run the hybrid agent evaluator with active cloud LLM credentials to generate the formal adjudication legal brief:

```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a
python3 agent_client/evaluator.py
```

![alt text](images/python_agent_client_evaluator.png)

---

### <span id="hybrid-dashboard"></span>📊 4.3 Cloud-Backed Executive Commercial Cockpit (AWS, Azure, GCP, Local) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Launch the Executive Commercial Cockpit configured with your chosen cognitive engine:

```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a

# 1. Launch with Amazon Web Services Engine (AWS Bedrock) on default port 8086
CLOUD_PROVIDER=AWS python3 dashboard/server.py --port 8086

# 2. Launch with Microsoft Azure Engine (Azure OpenAI / Azure Cloud) on default port 8086
CLOUD_PROVIDER=AZURE python3 dashboard/server.py --port 8086

# 3. Launch with Google Cloud Platform Engine (Vertex AI) on default port 8086
CLOUD_PROVIDER=GCP python3 dashboard/server.py --port 8086

# 4. Launch with Local Sovereign Engine on default port 8086
CLOUD_PROVIDER=LOCAL python3 dashboard/server.py --port 8086
```

![alt text](images/python_dashboard_server_aws_8086.png)

![alt text](images/python_dashboard_server_azure_8086.png)

![alt text](images/python_dashboard_server_gcp_8086.png)

![alt text](images/python_dashboard_server_local_8086.png)

#### User-Defined Port Configuration & Concurrent Engine Execution:
- **Configurable Port Parameter**: The `--port` flag is completely user-configurable (defaults to `8086` if omitted).
- **Single Instance on the Same Port**: Only one server instance can bind to a specific network port (e.g., `8086`) at any given time.
- **Running Multiple Engines Simultaneously Across Multiple Ports**: If you wish to run multiple engines concurrently in separate terminals for direct side-by-side comparison, simply assign different ports to each terminal instance:
  - Terminal 1: `CLOUD_PROVIDER=LOCAL python3 dashboard/server.py --port 8086` -> opens `http://localhost:8086`
  - Terminal 2: `CLOUD_PROVIDER=AWS python3 dashboard/server.py --port 8087` -> opens `http://localhost:8087`
  - Terminal 3: `CLOUD_PROVIDER=AZURE python3 dashboard/server.py --port 8088` -> opens `http://localhost:8088`
  - Terminal 4: `CLOUD_PROVIDER=GCP python3 dashboard/server.py --port 8089` -> opens `http://localhost:8089`
- **Dynamic Parameter Switching on a Single Running Instance**: If running just one server instance on port `8086`, you can also dynamically switch between engine badges directly in the browser by appending the query parameter (e.g., `http://localhost:8086/?engine=aws`, `http://localhost:8086/?engine=azure`, `http://localhost:8086/?engine=gcp`, or `http://localhost:8086/?engine=local`) without restarting the server.

Open `http://localhost:8086` in any standard web browser to view the interactive commercial cockpit with the active cloud cognitive engine badge (`AWS Engine`, `Azure Engine`, `GCP Engine`, or `Local Engine`) dynamically displayed in the top-right command bar.

![alt text](images/s03_dashboard_approach_2_aws_8086_light_mode.png)

![alt text](images/s03_dashboard_approach_2_azure_8086_light_mode.png)

![alt text](images/s03_dashboard_approach_2_gcp_8086_light_mode.png)

![alt text](images/s03_dashboard_approach_2_local_8086_light_mode.png)

---

## <span id="cloud-provisioning"></span><span style="color:red">☁️ 5. Approach 3: Cloud Workload Direct Provisioning (Multi-Cloud Terraform Deployments)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

![Approach 3: Cloud Workload Direct Provisioning Architecture](images/approach_3_cloud_workload.png)

### <span id="why-cloud-native"></span>💡 5.1 Why Choose Cloud Workload Direct Provisioning? <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Approach 3 decouples compute containers from persistent storage. By executing direct remote Parquet access using HTTP range requests via DuckDB's `httpfs` extension, the architecture avoids full-object downloads and application-level file duplication. AWS ECS Fargate, Azure Container Apps, and Google Cloud Run remain 100% stateless and horizontally auto-scalable with zero state-loss on container restarts. (Observed benchmark result on reference dataset; query performance is subject to network bandwidth, partition layout, and query selectivity, and does not represent an enterprise SLA guarantee.)

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

### <span id="terraform-aws"></span>🟧 5.3 AWS Deployment (ECS Fargate + S3 Lakehouse + ALB on Port 8086) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

<details>
<summary><b>🚀 Click to expand 5.3 AWS Deployment (ECS Fargate + S3 Lakehouse + ALB on Port 8086) guide, Terraform IaC, and architecture</b></summary>

![AWS Cloud-Native Deployment Architecture](images/architecture_aws.png)

Provisions an AWS Application Load Balancer (ALB), an ECS Fargate cluster, an ECR container repository, an IAM task execution role, and a secure S3 Parquet Lakehouse bucket.

Follow the self-contained 5-step workflow:

#### Step 1: Provision Infrastructure with Terraform
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a
cd terraform/aws
terraform init
terraform apply -auto-approve
```

![alt text](images/terraform_apply_output_aws.png)

#### Step 2: Synchronize Parquet Lakehouse to S3 Bucket
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a
S3_BUCKET=$(cd terraform/aws && terraform output -raw commercial_lake_bucket)
aws s3 sync data/parquet/ s3://${S3_BUCKET}/parquet/
```

![alt text](images/upload_parquet_to_s3_aws.png)

#### Step 3: Build and Push Docker Image to ECR
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
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
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a
CLUSTER=$(cd terraform/aws && terraform output -raw ecs_cluster_name)
aws ecs update-service --cluster ${CLUSTER} --service acip-s03-commercial-service-prod --force-new-deployment
```

![alt text](images/s03_application_run_aws_terminal_1.png)

#### Step 5: Verify Live Cloud Endpoint
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
ALB_URL=$(cd terraform/aws && terraform output -raw alb_url)
open ${ALB_URL}
```

![alt text](images/s03_application_run_aws_terminal_2.png)

![alt text](images/s03_dashboard_approach_3_aws_8086_light_mode.png)

</details>

---

### <span id="terraform-azure"></span>🟦 5.4 Azure Deployment (Azure Container Apps + Blob Lakehouse) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

<details>
<summary><b>🚀 Click to expand 5.4 Azure Deployment (Azure Container Apps + Blob Lakehouse) guide, Terraform IaC, and architecture</b></summary>

![Azure Cloud-Native Deployment Architecture](images/architecture_azure.png)

Provisions an Azure Container Apps Environment, an Azure Container Registry (ACR), a Container App with external HTTP ingress on port 8086, and an Azure Blob Storage Lakehouse container.

Follow the self-contained 5-step workflow:

#### Step 1: Provision Infrastructure with Terraform
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a
cd terraform/azure
terraform init
terraform apply -auto-approve
```

![alt text](images/terraform_apply_output_azure.png)

#### Step 2: Synchronize Parquet Lakehouse to Azure Blob Storage
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
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
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a
ACR_LOGIN=$(cd terraform/azure && terraform output -raw acr_login_server)
ACR_USER=$(cd terraform/azure && terraform output -raw acr_admin_username)
ACR_PASS=$(cd terraform/azure && terraform output -raw acr_admin_password)

docker login ${ACR_LOGIN} -u ${ACR_USER} -p ${ACR_PASS}
docker build --platform linux/amd64 -t ${ACR_LOGIN}/acip-s03-commercial-engine:latest .
docker push ${ACR_LOGIN}/acip-s03-commercial-engine:latest
```

![alt text](images/docker_build_tag_push_azure.png)

#### Step 4: Update Container App Revision
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a
ACR_LOGIN=$(cd terraform/azure && terraform output -raw acr_login_server)
az containerapp update \
  --name acip-s03-commercial-cockpit \
  --resource-group acip-s03-commercial-rg-prod \
  --image ${ACR_LOGIN}/acip-s03-commercial-engine:latest
```

![alt text](images/s03_application_run_azure_terminal_1.png)

#### Step 5: Verify Live Cloud Endpoint
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
CONTAINER_APP_URL=$(cd terraform/azure && terraform output -raw container_app_url)
open ${CONTAINER_APP_URL}
```

![alt text](images/s03_application_run_azure_terminal_2.png)

![alt text](images/s03_dashboard_approach_3_azure_8086_light_mode.png)

</details>

---

### <span id="terraform-gcp"></span>🟥 5.5 Google Cloud Deployment (Cloud Run v2 + GCS Lakehouse) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

<details>
<summary><b>🚀 Click to expand 5.5 Google Cloud Deployment (Cloud Run v2 + GCS Lakehouse) guide, Terraform IaC, and architecture</b></summary>

![Google Cloud-Native Deployment Architecture](images/architecture_gcp.png)

Provisions a Google Cloud Run v2 service, an Artifact Registry Docker repository, and a Google Cloud Storage (GCS) Parquet Lakehouse bucket.

Follow the self-contained 5-step workflow:

#### Step 1: Provision Infrastructure with Terraform
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a
cd terraform/gcp
terraform init
terraform apply -auto-approve -var="project_id=${GCP_PROJECT_ID}"
```

![alt text](images/terraform_apply_output_gcp.png)

#### Step 2: Synchronize Parquet Lakehouse to Google Cloud Storage (GCS)
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a
GCS_BUCKET=$(cd terraform/gcp && terraform output -raw commercial_lake_bucket)
gcloud storage rsync data/parquet/ gs://${GCS_BUCKET}/parquet/
```

![alt text](images/upload_parquet_to_cloud_storage_gcp.png)

#### Step 3: Build and Push Docker Image to Artifact Registry
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a
REPO_URL=$(cd terraform/gcp && terraform output -raw artifact_registry_url)

gcloud auth configure-docker asia-southeast1-docker.pkg.dev --quiet
docker build --platform linux/amd64 --provenance=false -t ${REPO_URL}/acip-s03-commercial-engine:latest .
docker push ${REPO_URL}/acip-s03-commercial-engine:latest
```

![alt text](images/docker_build_tag_push_gcp.png)

#### Step 4: Deploy to Cloud Run v2
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a
REPO_URL=$(cd terraform/gcp && terraform output -raw artifact_registry_url)
gcloud run deploy acip-s03-commercial-cockpit \
  --image ${REPO_URL}/acip-s03-commercial-engine:latest \
  --region ${GCP_REGION} \
  --quiet
```

![alt text](images/s03_application_run_gcp_terminal_1.png)

#### Step 5: Verify Live Cloud Endpoint
```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
CLOUD_RUN_URL=$(cd terraform/gcp && terraform output -raw cloud_run_url)
open ${CLOUD_RUN_URL}
```

![alt text](images/s03_application_run_gcp_terminal_2.png)

![alt text](images/s03_dashboard_approach_3_gcp_8086_light_mode.png)

</details>

---

## <span id="enterprise-landing-zone"></span><span style="color:red">🏰 6. Approach 4: Reference Enterprise Deployment Pattern & Sovereign Governance (Planned)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

![Approach 4: Reference Enterprise Deployment Pattern](images/approach_4_enterprise_landing_zone.png)

Approach 4 represents an architectural design blueprint and reference enterprise governance pattern rather than executable code in this repository. While Approaches 1, 2, and 3 provide working code, automated test suites, and deployable Terraform scripts, Approach 4 documents the target enterprise multi-account landing zone topology (multi-cloud account hierarchies, sovereign commercial enclaves, zero-egress data vaults, and statutory adjudication defense archives) for institutional developers and public-sector procurement authorities. Different client organizations, statutory boards, and general contractors will customize this pattern based on specific corporate identity platforms, enterprise network topologies, data residency mandates, and security baselines.

### <span id="sovereign-enclaves"></span>🔒 6.1 Dedicated Sovereign Commercial Enclaves & Zero-Egress Storage <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

For public hospital projects, rail infrastructure, and defense developments:
- Customer-Managed Encryption Keys (AWS KMS / Azure Key Vault / GCP Cloud KMS) encrypt all Apache Parquet tables at rest.
- Private Link and VPC Service Controls restrict all FastMCP tool execution to air-gapped private subnets without public internet egress.
- Multi-region replication ensures continuous availability across secondary disaster recovery zones.

---

### <span id="audit-rbac"></span>📜 6.2 Audit Trails, RBAC & Statutory Adjudication Defense Archive <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Every variation order audit, openBIM discrepancy flag, and SOPA payment response is cryptographically timestamped and archived. The generated Section 11 markdown dossiers provide immutable evidentiary defense packs admissible under the Singapore Evidence Act and SOPA adjudication rules.

---

## <span id="automated-testing"></span><span style="color:red">🧪 7. Automated Testing & Verification</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Execute the automated reference test suite (100% pass rate across the current automated reference test suite of 10 core platform verification engines):

```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
python3 tests/test_s03_pipeline.py
```

![alt text](images/python_tests_test_s03_pipeline.png)

---

## <span id="cleanup"></span><span style="color:red">🧹 8. Clean Up</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

To tear down provisioned cloud infrastructure and reset local database state:

### <span id="destroy-cloud"></span>☁️ 8.1 Destroy Cloud Workloads (AWS, Azure, GCP) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

If you deployed cloud resources in Approach 3, destroy them to avoid ongoing provider charges:

```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
set -a; source .env; set +a

# 1. Destroy Amazon Web Services Infrastructure
cd terraform/aws && terraform destroy -auto-approve && cd ../..

# 2. Destroy Microsoft Azure Infrastructure
cd terraform/azure && terraform destroy -auto-approve && cd ../..

# 3. Destroy Google Cloud Platform Infrastructure
cd terraform/gcp && terraform destroy -auto-approve -var="project_id=${GCP_PROJECT_ID}" && cd ../..
```

### <span id="reset-local"></span>🗑️ 8.2 Reset Local Database & Parquet Lakehouse <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

To remove the local DuckDB database file and reset local lakehouse artifacts:

```bash
# Ensure you are at the S03_Agentic_Cost_And_Commercial_Control_Intelligence module root folder before starting
rm -f data/commercial_control.duckdb
rm -rf data/parquet/*.parquet
```

---

## 📄 License
This module is distributed as part of the Agentic Construction Intelligence Platform (ACIP) under the **Apache License 2.0**. See the root [LICENSE](../LICENSE) file for full license terms and conditions.
