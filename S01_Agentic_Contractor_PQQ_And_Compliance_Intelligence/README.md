# <span style="color:red">🛠️ S01: Implementation Guide & Technical Runbook</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to ACIP Platform Overview](../README.md#toc)</span>

[📄 Go to S01 Business Problem Statement & Case Studies](BUSINESS_PROBLEM_STATEMENT.md) | [⬆️ Back to ACIP Platform Overview](../README.md#toc)

---

The **Agentic Contractor Pre-Qualification (PQQ) Framework** is an enterprise AI audit-assist platform designed for developer companies, quantity surveyors, and tender evaluation boards in the Architecture, Engineering, and Construction (AEC) sector.

### 🛡️ Technical Scope & Architectural Boundaries
- **🧪 Working Reference Implementation**: S01 is a functional, end-to-end runnable Proof of Concept with working code, synthetic benchmark registries, deterministic statutory engines, tool servers, and automated verification test suites.
- **✅ What It Is**: An intelligent **Audit-Assist Co-Pilot and Decision-Support Platform**. Powered by the Model Context Protocol (MCP) and multi-agent reasoning, it automates evidence retrieval, deterministic rule checking, multi-agent adversarial debate, and high-throughput Monte Carlo risk simulation across multi-cloud LLMs (AWS Nova Pro, Azure OpenAI GPT-4o, GCP Gemini 2.5 Pro, and sovereign local Llama 3.1).
- **❌ What It Is Not**: It is **NOT** an autonomous replacement for statutory Tender Committees, legal counsel, or professional quantity surveyors. All final pre-qualification and tender award determinations require human-in-the-loop review and sign-off.
- **🧪 Data Modeling**: The current local demonstration runs on a **synthetic benchmark database** (`contractors_registry.db`) modeled after official BCA, MOM, and ACRA schemas. All contractor profiles, UENs, and financial ratios are synthetic test personas generated for technical benchmarking and do not represent actual corporate entities. In enterprise production, MCP tools connect to live enterprise ERPs (SAP/Oracle) and authorized government data APIs.

### 🔄 The Three-Stage Procurement Lifecycle
The framework partitions evaluation into three distinct, non-conflated stages:
1. **Stage 1: Pre-Qualification (PQQ)** -> Screening contractor registration grade, tendering limits, MOM safety records, and balance sheet solvency before bids are considered.
2. **Stage 2: Tender Bid Evaluation (PQM)** -> Scoring dual-envelope commercial submissions against benchmark budgets using the Singapore Price-Quality Method (PQM).
3. **Stage 3: Subcontract Risk Audit** -> Scanning draft project agreements for unenforceable Pay-When-Paid clauses under SOPA Section 9 and onerous liquidated damages clauses.

---

## <span id="toc"></span>📑 Table Of Contents (TOC)

- [0. Pre-requisite Software](#prerequisites)
- [1. Architecture Overview](#overview)
  - [1.1 System Architecture & Multi-Cloud Guardrails](#system-architecture)
  - [1.2 End-to-End Pipeline Workflow & Testing](#pipeline-workflow)
- [2. Directory Structure](#folder-structure)
- [3. Approach 1: Pure Local Sovereign Deployment & Testing (Zero Cost)](#local-deployment)
  - [3.1 Implementation Approach Selection Matrix](#selection-matrix)
  - [3.2 Download Llama 3.1](#download-llama)
  - [3.3 Create and Activate Conda Environment](#conda-env)
  - [3.4 Initialize the Contractor Registry Database](#init-db)
  - [3.5 Launch the Pre-Qualification Agent & Dashboard](#launch-agent)
  - [3.6 Access the Web Dashboard](#web-dashboard)
  - [3.7 Rapid Terminal Simulation (CLI Runner)](#terminal-simulation)
  - [3.8 Quantitative Risk Engine (Rust Axum & Vectorized NumPy Fallback)](#risk-engine)
  - [3.9 Quantity Surveyor Risk Simulation Dashboard](#leptos-dashboard)
- [4. Approach 2: Hybrid Testing Sandbox (Local Application + Cloud LLM APIs)](#api-providers)
  - [4.1 Why Choose Hybrid Testing?](#why-hybrid)
  - [4.2 Pre-requisites for Approach 2](#hybrid-prerequisites)
  - [4.3 Launching with Your Chosen Cloud Model](#hybrid-launch)
  - [4.4 Access the Hybrid Web Dashboard & Audit Terminal](#hybrid-web-dashboard)
- [5. Approach 3: Cloud Workload Direct Provisioning (Single-Project Cloud Deployment)](#omni-cloud-deployment)
  - [5.1 Why Choose Cloud Workload Direct Provisioning?](#why-cloud-native)
  - [5.2 Pre-requisites for Approach 3](#cloud-native-prerequisites)
  - [5.3 AWS Deployment (ECS Fargate + Amazon Bedrock)](#aws-deployment)
  - [5.4 Azure Deployment (Azure Container Apps + Azure OpenAI)](#azure-deployment)
  - [5.5 Google Cloud Deployment (Google Cloud Run + Vertex AI)](#gcp-deployment)
- [6. Approach 4: Enterprise Multi-Account Landing Zone & Sovereign Governance (Planned)](#enterprise-landing-zone)
- [7. Automated Testing & Verification](#automated-testing)
- [8. Clean Up](#cleanup)
  - [8.1 Stopping the Local Server (Approach 1 & Approach 2)](#stop-local-server)
  - [8.2 Destroying Cloud Infrastructure (Approach 3)](#destroy-cloud-infra)
- [9. Frequently Asked Questions (FAQ)](FAQ.md)
- [10. Troubleshooting Guide](TROUBLESHOOTING.md)

---

## <span id="prerequisites"></span><span style="color:red">⚙️ 0. Pre-requisite Software</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

📝 Note: Shell & Minimum Requirements: All terminal commands in this technical runbook are written for Unix/macOS Bash or Zsh shells (execute using Git Bash or WSL2 on Windows). For Approach 1 (Pure Local Sovereign), only Anaconda, Docker Desktop, and Ollama are required. Rust, Cargo, Trunk, Terraform, and Cloud CLIs are only needed if you choose to explore the client-side WebAssembly dashboard (Section 3.9), cloud provider integrations (Approach 2 & 3), or multi-account IaC provisioning.

Before beginning, ensure the following software is installed on the host machine:
- **Anaconda / Miniconda**: Required to manage the Python environments cleanly. Download and install from the [Anaconda Official Website](https://www.anaconda.com/download) or the [Miniconda Official Website](https://docs.conda.io/en/latest/).
  ```bash
  conda --version
  ```
- **Docker Desktop**: Required to containerize and deploy the enterprise solution locally or to cloud registries. Download and install from the [Docker Official Website](https://www.docker.com/products/docker-desktop/).
  ```bash
  docker --version
  ```
- **Ollama**: Required to run the local Llama 3.1 open-weight model with native tool-calling support. Download and install from the [Ollama Official Website](https://ollama.com/).
  ```bash
  ollama --version
  ```
- **Terraform**: Required to automate multi-cloud infrastructure deployments. Download and install from the [HashiCorp Official Website](https://developer.hashicorp.com/terraform/downloads).
  ```bash
  terraform --version
  ```
- **Rust & Cargo**: Required to compile and run the high-performance Axum quantitative Monte Carlo risk sidecar and Leptos WebAssembly application. Download and install from the [Rust Official Website](https://www.rust-lang.org/tools/install).
  ```bash
  rustc --version
  cargo --version
  ```
- **Trunk (WASM Bundler)**: Required to build, package, and serve the client-side Leptos WebAssembly dashboard. Download pre-compiled binaries or review documentation from the [Trunk Official GitHub Repository](https://github.com/trunk-rs/trunk) or install via Cargo.
  ```bash
  trunk --version
  ```
- **Cloud CLIs**: Install the CLI for the specific cloud platform you plan to deploy or test:
  - **[AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)**: For AWS ECS Fargate & Amazon Bedrock deployments.
  - **[Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)**: For Azure Container Apps & Azure OpenAI deployments.
  - **[Google Cloud SDK](https://cloud.google.com/sdk/docs/install)**: For Google Cloud Run & Vertex AI deployments.
  ```bash
  aws --version
  az --version
  gcloud --version
  ```

![Pre-requisite software verification CLI output part 1](images/pre-requisite_software_1.png)

![Pre-requisite software verification CLI output part 2](images/pre-requisite_software_2.png)

---

## <span id="overview"></span><span style="color:red">🏗️ 1. Architecture Overview</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

📝 Note: Executive Business Problem & Case Studies
For full commercial context, statutory liabilities, real-world Singapore case studies (MOM Safety Demerits, Greatearth liquidation, SOPA Section 9), and the tender evaluation comparison matrix, please read the [S01 Business Problem Statement & Case Studies](BUSINESS_PROBLEM_STATEMENT.md).

### <span id="system-architecture"></span>🏛️ 1.1 System Architecture & Multi-Cloud Guardrails <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

The **Agentic Pre-Qualification Framework** is architected to integrate deterministic statutory rules with multi-cloud foundation models via the **Model Context Protocol (MCP)**. To ensure deterministic calculation precision and statutory defensibility, all financial formulas (Current Ratio, Debt-to-Equity, Performance Bond capacity) and statutory checks (MOM Safety Demerits, BCA tendering limits) are executed by pre-tested, deterministic Python engines with no LLM access to the calculation path, while the LLM focuses on high-level evidence synthesis and forensic reporting.

![Enterprise Contractor Pre-Qualification and Compliance MCP Framework Architecture](./images/architecture_pqq_mcp.png)

<details>
<summary><b>📐 Click to view Mermaid Architecture Diagram Source</b></summary>

```mermaid
graph TD
    Client["Tender Assessment Committee / Quantity Surveyor"] -->|Multi-Stage Inquiries (PQQ / PQM / SOPA)| API["Enterprise Web Dashboard & REST API (FastAPI)"]
    API -->|Prompt & State Dispatch| Agent["ReAct Agentic Workflow (LangGraph / LangChain)"]
    Agent -->|Multi-Cloud Reasoning| LLM["Omni-Cloud LLMs (Local Llama 3.1 / Bedrock Nova / Vertex Gemini / Azure GPT)"]
    Agent -->|Secure Tool Requests| MCPServer["Enterprise Compliance Engine (FastMCP Server)"]
    MCPServer -->|Stage 1: Registration Caps| Tool1["Stage 1 PQQ: query_contractor_profile (BCA CRS Workheads)"]
    MCPServer -->|Stage 1: Safety Points| Tool2["Stage 1 PQQ: verify_safety_compliance (MOM SDP Demerits)"]
    MCPServer -->|Stage 1: Balance Sheet| Tool3["Stage 1 PQQ: assess_financial_solvency (Liquidity & Bonds)"]
    MCPServer -->|Stage 2: Tender Scoring| Tool4["Stage 2 PQM: evaluate_pqm_score (Price-Quality Scoring)"]
    MCPServer -->|Stage 3: Subcontract Audit| Tool5["Stage 3 SOPA: audit_contract_risk (Subcontract Clauses)"]
    Tool1 -->|Read Workhead Limits| Reg1[("BCA Registry DB: CW01/CW02 Tendering Caps")]
    Tool2 -->|Verify Demerit Points| Reg2[("MOM Safety DB: SDP Threshold >= 25 & Debarment")]
    Tool3 -->|Audit 3-Yr Financials| Reg3[("Audited Balance Sheets: Liquidity & Debt Ratios")]
    Tool4 -->|Compare Bids to Median| Reg4[("Tender Benchmarks: CONQUAS & Quality Metrics")]
    Tool5 -->|Scan Baseline Rules| Reg5[("Statutory Rules: SOPA, PSSCOC, SIA, REDAS Standards")]
```

</details>

---

### <span id="pipeline-workflow"></span>🔄 1.2 End-to-End Pipeline Workflow & Testing <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

![Tender Pre-Qualification Workflow Dual-Track Comparison](./images/workflow_comparison.png)

<details>
<summary><b>📐 Click to view Mermaid Dual-Track Workflow Diagram Source</b></summary>

```mermaid
graph TD
    Tender["Tender Release: S$120M Public Institutional Hospital Development"] --> TrackA["Track A: Traditional Manual Evaluation (4-8 Weeks)"]
    Tender --> TrackB["Track B: Agentic MCP Compliance Pipeline (Sub-Minute)"]
    
    TrackA --> M1["Manual Registry Searches: Siloed BCA, MOM, ACRA Portals"]
    M1 --> M2["Unstructured Excel Spreadsheets: Manual Data Entry & Formula Errors"]
    M2 --> M3["Fragmented Audit Checks: Human Review Misses Active 25 SDP Limit"]
    M3 --> M4["Unverified Balance Sheets: Hidden Operating Cash Deficits Undetected"]
    M4 --> M5["Severe Commercial Exposure: Late-Stage Site Abandonment & Liquidated Damages"]

    TrackB --> A1["FastAPI Glassmorphic Ingestion: One-Click Contractor Screening"]
    A1 --> A2["Agentic ReAct Orchestration: LangChain / LangGraph Engine"]
    A2 --> A3["Secure Tool Invocations: Deterministic Registry Queries & Statutory Rules"]
    A3 --> A4["Gated Compliance Rules: Stage 1 PQQ (MOM SDP Bar & Solvency)"]
    A4 --> A5["Audit-Assist Dossier: Stage 2 PQM & Stage 3 SOPA Audit with Human Sign-off"]
```

</details>

The execution pipeline moves deterministically through five chronological phases:

```text
[Phase 1: Ingestion] -> [Phase 2: ReAct Planning] -> [Phase 3: Tool Verification] -> [Phase 4: Statutory Heuristics] -> [Phase 5: Synthesis & Verdict]
```

1. **Phase 1: Procurement Ingestion & User Intent Formulation**
   - The user (Senior Quantity Surveyor, Procurement Specialist, or Tender Evaluation Panel Member) interacts with the FastAPI glassmorphic dashboard or submits a REST request.
   - Inquiries can be broad ("Screen `Heng Win` for the S$120M Woodlands Health Campus tender") or highly targeted ("Check MOM demerits and debarment status for `Titan Piling`").

2. **Phase 2: Agentic ReAct Planning & Dynamic Tool Selection**
   - The LangGraph / LangChain ReAct agent ingests the inquiry alongside its specialized domain system prompt.
   - The agent analyzes the evaluation criteria, determines which statutory and financial registries must be consulted across the 3 procurement stages, and formulates a plan of tool invocations.

3. **Phase 3: Secure Tool Invocations & Database Verification**
   - The agent calls dedicated inspection tools through the Model Context Protocol (MCP) connected to the compliance engine (`mcp_server/server.py`).
   - The tool server executes the exact statutory checks, queries the contractor database (`contractors_registry.db`), and streams verified, deterministic outputs back to the agent without granting the AI raw or direct database access.

4. **Phase 4: Deterministic Statutory & Financial Heuristics (Partitioned by Procurement Stage)**
   - **Stage 1: Pre-Qualification (PQQ) Screening (Gated Due Diligence)**:
     - **BCA CRS Workhead Vetting (`query_contractor_profile`)**: Queries registration grade (A1 to C3), workhead scope (CW01 General Building, CW02 Civil Engineering, CR, ME), and checks if the project value exceeds the statutory tendering cap.
     - **MOM Safety Demerits Vetting (`verify_safety_compliance`)**: Checks accumulated Safety Demerit Points against the statutory 25-point cutoff. If `sdp >= 25` or `mom_debarred == 1`, the tool immediately triggers a `CRITICAL STATUTORY BAR (DISQUALIFIED)` status.
     - **Financial Solvency Due Diligence (`assess_financial_solvency`)**: Evaluates audited balance sheets to compute:
       - `Current Ratio = Current Assets / Current Liabilities` (Policy Benchmark: > 1.2)
       - `Quick Ratio = Quick Assets / Current Liabilities` (Policy Benchmark: > 1.0)
       - `Debt-to-Equity = Total Debt / Total Equity` (Policy Benchmark: < 1.5)
       - `10% Performance Bond Capacity`: Verifies whether uncommitted bank credit lines cover the required 5% to 10% Banker Guarantee.
   - **Stage 2: Tender Bid Evaluation (PQM Commercial & Technical Scoring)**:
     - **Price-Quality Method Scoring (`evaluate_pqm_score`)**: Gated execution evaluated only for contractors successfully passing Stage 1 PQQ. Computes price and quality scores aligned with the BCA PQM framework (with configurable weightings per tender board policy, e.g. 70/30, 60/40, or 50/50):
       - Price Component: Scored based on bid variance relative to the median benchmark budget.
       - Quality Component: Weighted breakdown of past CONQUAS score, project delivery track record, safety record (with explicit SDP point penalties), and DfMA productivity adoption.
   - **Stage 3: Subcontract Risk Audit (Statutory Compliance)**:
     - **Contractual Risk Audit (`audit_contract_risk`)**: Analyzes draft clauses against statutory standards (SOPA Section 9 pay-when-paid bars, onerous variation notice periods < 14 days, uninsurable consequential loss indemnities).

5. **Phase 5: Executive Synthesis, Dossier Generation & Actionable Verdict**
   - The LLM receives the factual tool responses and synthesizes a structured procurement evaluation report.
   - Gated Early-Termination: If a contractor fails Stage 1 (e.g. MOM SDP >= 25 or insolvency), the agent immediately issues a `STAGE 1 DISQUALIFIED (PQQ FAIL)` determination. The commercial envelope is never evaluated, saving procurement teams significant evaluation time.
   - Outputs include an explicit verdict (`PASS`, `CONDITIONAL`, `FAIL`, or `STATUTORILY DEBARRED`), numerical scorecard breakdowns, and actionable recommendations for the tender award committee with human sign-off.

---

## <span id="folder-structure"></span><span style="color:red">📂 2. Directory Structure</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

Here is the complete project directory structure matching standard IDE order:

```text
S01_Agentic_Contractor_PQQ_And_Compliance_Intelligence/
├── agent_client/                       # FastAPI web server, ReAct agent, and glassmorphic UI
│   ├── agent_api.py                    # FastAPI application with LangGraph/LangChain ReAct agent and MCP client
│   └── requirements.txt                # Client dependencies for agent orchestration and FastAPI web service
├── images/                             # Core architecture diagrams and evaluation workflows
│   ├── approach_1_local_sovereign.png  # Approach 1 pure local sovereign architecture (Ollama + local MCP)
│   ├── approach_2_hybrid_sandbox.png   # Approach 2 hybrid enterprise sandbox architecture (Local MCP + Cloud LLMs)
│   ├── approach_3_cloud_workload.png   # Approach 3 single-project cloud workload architecture (Serverless Container)
│   ├── approach_4_enterprise_landing_zone.png # Approach 4 enterprise multi-account landing zone architecture
│   ├── architecture_aws.png            # AWS ECS Fargate + Amazon Bedrock serverless architecture
│   ├── architecture_azure.png          # Azure Container Apps + Azure OpenAI serverless architecture
│   ├── architecture_gcp.png            # Google Cloud Run + Vertex AI serverless architecture
│   ├── architecture_pqq_mcp.png        # Multi-agent ReAct & FastMCP statutory inspection architecture
│   └── workflow_comparison.png         # Dual-track manual review vs. autonomous agentic evaluation workflow
├── mcp_server/                         # FastMCP server, regulatory tools, and SQLite registry database
│   ├── contractors_registry.db         # Seeded SQLite database with BCA, MOM, financial, and tender data
│   ├── mock_data.py                    # Database schema generator and Singapore contractor registry seeder
│   ├── requirements.txt                # MCP server runtime dependencies (mcp, pydantic, numpy, requests)
│   └── server.py                       # FastMCP compliance server exposing statutory evaluation tools
├── risk_dashboard_leptos/              # Client-side WebAssembly reactive terminal built with Leptos (v0.6)
│   ├── src/                            # Leptos Rust WebAssembly source code
│   │   ├── components/                 # Reactive UI components
│   │   │   ├── adversarial_challenge.rs # Multi-agent duel & statutory scenario interactive viewer
│   │   │   ├── audit_card.rs           # PQQ compliance badge, CONQUAS score, and demerit limits
│   │   │   ├── mod.rs                  # Component module exports
│   │   │   ├── monte_carlo_chart.rs    # Reactive SVG bell curve, P90 line, and VaR 95% threshold
│   │   │   └── risk_slider.rs          # Zero-lag reactive slider component
│   │   ├── app.rs                      # Main application shell with reactive signal orchestration
│   │   ├── main.rs                     # Client WebAssembly entrypoint mounting Leptos to DOM
│   │   └── models.rs                   # Shared Rust data structures (MonteCarloRequest, Response, RiskFactor)
│   ├── Cargo.toml                      # Cargo manifest and dependencies (leptos, wasm-bindgen, web-sys)
│   ├── Dockerfile                      # Multi-stage container build (Rust -> Trunk -> Nginx Alpine <10MB)
│   ├── index.html                      # Glassmorphic HTML5 shell with Google Fonts Inter & Outfit
│   ├── README.md                       # Operational guide for WebAssembly compilation and Trunk serving
│   └── Trunk.toml                      # Trunk WebAssembly bundler and local development server config
├── risk_engine/                        # High-performance Rust & Axum quantitative Monte Carlo risk sidecar
│   ├── src/                            # Rust source code directory
│   │   └── main.rs                     # Axum microservice executing Monte Carlo risk simulations
│   ├── Cargo.toml                      # Cargo manifest and dependencies (axum, tokio, rayon, rand)
│   ├── Dockerfile                      # Multi-stage Alpine container definition for Rust risk sidecar
│   └── README.md                       # Quantitative model equations, VaR math, and benchmarking guide
├── terraform/                          # Multi-cloud serverless Infrastructure as Code configurations
│   ├── aws/                            # AWS ECS Fargate serverless container deployment configuration
│   │   ├── main.tf                     # AWS ECS cluster, task definition, Fargate service, and IAM policies
│   │   ├── outputs.tf                  # Exported AWS ECS service name, cluster ID, and container endpoints
│   │   └── variables.tf                # AWS region, project naming, and container resource allocations
│   ├── azure/                          # Azure Container Apps serverless deployment configuration
│   │   ├── main.tf                     # Azure Resource Group, Container Apps environment, and ACR registry
│   │   ├── outputs.tf                  # Exported Azure Container App FQDN, resource group, and identity ID
│   │   └── variables.tf                # Azure region location, project naming, and container settings
│   └── gcp/                            # Google Cloud Run serverless deployment configuration
│       ├── main.tf                     # Google Cloud Run v2 service, IAM invoker roles, and Artifact Registry
│       ├── outputs.tf                  # Exported Google Cloud Run service URL and project location
│       └── variables.tf                # GCP project ID, deployment region, and Docker container image tag
├── tests/                              # Automated verification test suite
│   ├── benchmark_rust_vs_python.py     # Rust Monte Carlo vs. Python NumPy quantitative performance benchmark suite
│   └── test_mcp_framework.py           # 12 automated unit and integration tests for MCP tools and statutory rules
├── .env.example                        # Multi-cloud LLM credentials and environment configuration template
├── .gitignore                          # Git ignore patterns for sensitive keys, build artifacts, and state
├── BUSINESS_PROBLEM_STATEMENT.md       # Executive business problem statement, procurement lifecycle, and statutory precedents
├── demo_audit.py                       # Rich-powered interactive terminal CLI audit simulation runner
├── Dockerfile                          # Unified multi-stage container packaging MCP server, agent, and web dashboard
├── environment.yml                     # Conda environment definition with all required Python dependencies
├── FAQ.md                              # Frequently Asked Questions with in-depth technical explanations
├── README.md                           # Comprehensive technical runbook, multi-cloud deployment guides, and benchmarks
└── TROUBLESHOOTING.md                  # Troubleshooting guide with error categories and Before/After fixes
```

---

## <span id="local-deployment"></span><span style="color:red">💻 3. Approach 1: Pure Local Sovereign Deployment & Testing (Zero Cost)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

This framework supports **four progressive implementation approaches** to accommodate different evaluation needs, data sovereignty requirements, and enterprise cloud maturity:

### <span id="selection-matrix"></span>🧭 3.1 Implementation Approach Selection Matrix <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

| Approach | Execution Target | LLM Engine | Cloud Infra & Cost | Best Suited For |
| :--- | :--- | :--- | :--- | :--- |
| **Approach 1: Local / Air-Gapped Sovereign** | Local Workstation | Local Llama 3.1 (8B) via Ollama | No Cloud or API Costs | Immediate evaluation, air-gapped security, offline sovereign testing |
| **Approach 2: Hybrid Testing Sandbox** | Local App + Managed Cloud APIs | Amazon Bedrock, Azure OpenAI, Vertex AI | Cloud API Keys in `.env` (~S$0.01 / query) | High-accuracy reasoning tests on non-sensitive data without server provisioning |
| **Approach 3: Cloud Workload Direct Provisioning** | Dedicated Project Cloud Environment | Same Cloud Models (Bedrock, Azure OpenAI, Vertex AI via IAM) | Dedicated Cloud Environment (Terraform + Registries) | Project teams, departmental deployments, rapid cloud verification |
| **Approach 4: Enterprise Landing Zone Blueprint (Planned)** | Multi-Account Cloud Hierarchy | Multi-Region Governed Cloud AI | Architectural Design Intent (Transit Gateway + Hub/Spoke Blueprint) | Institutional developers, enterprise CISO compliance, production multi-tier |

![Approach 1: Pure Local Sovereign Deployment](./images/approach_1_local_sovereign.png)

Approach 1 executes the entire pre-qualification pipeline locally on your workstation or laptop with zero cloud accounts, zero credentials, and zero external API costs. It uses Ollama with Llama 3.1 (8B) for sovereign local reasoning, communicates with the compliance engine via local MCP stdio IPC, and connects to an embedded SQLite database (`contractors_registry.db`).

### <span id="download-llama"></span>🦙 3.2 Download Llama 3.1 <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
Pull the local open-weight model with native function calling capabilities:
```bash
# Ensure you are at the project root before starting
ollama pull llama3.1
```

![Ollama pull Llama 3.1 open-weight model terminal output](images/ollama_pull.png)

### <span id="conda-env"></span>🐍 3.3 Create and Activate Conda Environment <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
Initialize the isolated environment with all required dependencies:
```bash
# Ensure you are at the project root before starting
conda env create -f environment.yml
conda activate enterprise_mcp_agent
```

![Conda environment creation and activation](images/conda_env_create_activate.png)

### <span id="init-db"></span>🗄️ 3.4 Initialize the Contractor Registry Database <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
Seed the mock Singapore contractor database (`contractors_registry.db`) containing Tier 1 contractors, mid-tier firms, safety-debarred entities, and benchmark tenders:
```bash
# Ensure you are at the project root before starting
python mcp_server/mock_data.py
```

![Database initialization and mock data seeding](images/mock_data_init_terminal.png)

### <span id="launch-agent"></span>🤖 3.5 Launch the Pre-Qualification Agent & Dashboard <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
The FastAPI server automatically launches the Model Context Protocol server as a managed child subprocess using the stdio transport:
```bash
# Ensure you are at the project root before starting
set -a; source .env; set +a
uvicorn agent_client.agent_api:app --reload --host 0.0.0.0 --port 8003
```

![Uvicorn server startup with local Ollama Llama 3.1](images/uvicorn_agent_api_ollama_terminal.png)

### <span id="web-dashboard"></span>🌐 3.6 Access the Web Dashboard <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
Open your web browser and navigate to:
```text
http://localhost:8003
```

The PQQ Cockpit provides three integrated operational tabs:
- **Tab 1: Agentic Audit Chat & Statutory Screening**:
  Execute single-click contractor compliance checks and statutory audits using preset buttons:
  - **`Heng Win` Screening**: "Screen `Heng Win` for the S$120M Woodlands Health Campus Tender (TND-2026-SG-001)"
  - **Statutory Safety Bar Audit**: "Verify MOM Safety Demerit Points and bizSAFE compliance for `Titan Piling & Civil Engineering`"
  - **Solvency Check**: "Conduct financial solvency and bond capacity check for `Starlight Urban Infrastructure` on a S$35M project"
  - **`GemStone` PQM Evaluation**: "Calculate BCA PQM score for `GemStone` with bid of S$116M against benchmark S$120M"
  - **SOPA Clause Audit**: "Audit this contract clause under Singapore SOPA: Subcontractor will be paid within 14 days after main contractor receives payment from Employer (pay when paid)"
- **Tab 2: What-If Risk Cockpit**:
  Interactive quantitative stress-testing tool wired directly to the Rust Axum sidecar (port 8080). Adjust steel price inflation, foreign worker levy escalation, and liquidated damages (LAD) to run real-time stochastic simulations with live VaR 95% and default probability gauges.
- **Tab 3: Dual-Agent Adversarial Debate**:
  Multi-agent debate module pairing an Aggressive Commercial Agent against a Conservative Compliance Agent. Synthesizes conflicting tender trade-offs into an auditable consensus memo for human review and sign-off.

![PQQ Local Engine web interface on port 8003](images/uvicorn_agent_api_ollama_browser_8003_tab_1.png)

![PQQ Local Engine web interface on port 8003](images/uvicorn_agent_api_ollama_browser_8003_tab_2.png)

![PQQ Local Engine web interface on port 8003](images/uvicorn_agent_api_ollama_browser_8003_tab_3.png)

### <span id="terminal-simulation"></span>🚀 3.7 Rapid Terminal Simulation (CLI Runner) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
For quick headless testing, command-line demonstrations, or automated CI verification without launching a browser or web server, execute `demo_audit.py`. It renders formatted terminal tables and summary scorecards in ~1.2 seconds:

```bash
# Ensure you are at the project root before starting
python3 demo_audit.py
```

![Multi-scenario CLI audit output part 1](images/demo_audit_terminal_1.png)

![Multi-scenario CLI audit output part 2](images/demo_audit_terminal_2.png)

Expected Output:
```text
               Executive Audit Synthesis & Multi-Scenario Summary               
┏━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━┓
┃ Scenario /      │ Primary Risk        │ Statutory       │ System     │ Exec  ┃
┃ Contractor      │ Investigated        │ Reference       │ Recommend* │ Time  ┃
┠─────────────────┼─────────────────────┼─────────────────┼────────────┼───────┨
┃ Heng Win        │ PQQ Benchmark & PQM │ BCA CRS /       │ RECOMMEND  │ 0.38s ┃
┃ (Private) Ltd   │ Scoring             │ CONQUAS         │            │       ┃
┃ Titan Piling &  │ MOM SDP 25-Point    │ MOM WSH Act     │ DISQUALIF  │ 0.29s ┃
┃ Civil Eng.      │ Limit               │                 │            │       ┃
┃ Starlight Urban │ Liquidity & Bond    │ Audited Ratios  │ INSOLVENT  │ 0.31s ┃
┃ Infra.          │ Capacity            │ / BCA           │ (FAIL)     │       ┃
┃ Trade           │ Pay-When-Paid       │ SOPA 2004 Sec   │ VOID BY    │ 0.24s ┃
┃ Subcontract Cl. │ Provision           │ 9(1)            │ LAW        │       ┃
┃ 14              │                     │                 │            │       ┃
┗━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━┛

* All system recommendations require human-in-the-loop review and sign-off by the Tender Committee.
All 4 compliance audit scenarios executed and verified in ~1.22 seconds.
```

### <span id="risk-engine"></span>🦀 3.8 Quantitative Risk Engine (Rust Axum & Vectorized NumPy Fallback) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
The compliance framework includes a compiled quantitative risk sidecar executing high-throughput Monte Carlo risk simulations across fluctuating material and labor cost indices to calculate contractor Value at Risk (VaR 95%, CVaR 95%) and scenario-based insolvency risk distributions.

**Direct Integration with PQQ Dashboard**:
The Rust microservice connects directly to the PQQ Dashboard (port 8000/8003):
- **Tab 1 (Agent Chat)**: FastMCP tool `simulate_contractor_monte_carlo_risk` triggers native high-throughput execution on demand (with automatic fallback to vectorized NumPy if the compiled binary is not active).
- **Tab 2 (What-If Cockpit)**: Real-time telemetry banner streaming stochastic simulation runs with live VaR, CVaR, and default probability updates as sliders move.
- **Tab 3 (Dual-Agent Debate)**: Multi-agent adversarial review synthesizes conflicting tender trade-offs into an auditable consensus memo for human review and sign-off.

**Launch the Quantitative Risk Microservice via Docker**
```bash
# Ensure you are at the project root before starting
docker build -t risk-engine risk_engine/
docker run -d -p 8080:8080 --name risk-engine-sidecar risk-engine
```

![Docker build of Rust quantitative risk engine part 1](images/docker_build_risk-engine.png)

![Docker run containerized Rust risk engine microservice](images/docker_run_risk-engine.png)

📝 Note: Alternative Local Execution with Cargo
If Rust is installed natively on your workstation, you can alternatively launch the microservice directly without Docker:
```bash
# Ensure you are at the project root before starting
cd risk_engine
cargo run --release
```

![Native Cargo release build of Rust risk engine](images/cargo_run_release_terminal.png)

📝 Note: Automated Local Execution Fallback
If the standalone Rust microservice is not running on port 8080, the Model Context Protocol compliance server automatically falls back to an internal vectorized NumPy engine. NumPy utilizes your CPU's hardware SIMD (Single Instruction, Multiple Data) vector instructions to execute the matrix calculations locally. Both engines execute the identical mathematical stochastic differential model, ensuring zero test failures on systems without Rust or Docker.

### <span id="leptos-dashboard"></span>📊 3.9 Quantity Surveyor Risk Simulation Dashboard <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
While the main PQQ Cockpit (`http://localhost:8003`) handles regulatory chat and statutory audits, this dedicated **Risk Simulation Workbench** in [`risk_dashboard_leptos/`](./risk_dashboard_leptos/) provides Quantity Surveyors, Commercial Directors, and Risk Consultants with an independent, real-time financial stress-testing lab:

1. **Real-Time What-If Commercial Sensitivity Analysis**: Adjust critical market volatility sliders (structural steel inflation, foreign worker levy escalation, liquidated damages daily rates) to see real-time impact on project contingency budgets.
2. **Defensible Board-Level Contingency Recommendations**: Rapidly computes statistically rigorous **P90 budget estimates** and **Value at Risk (VaR 95%)** thresholds across extensive simulated market scenarios, providing defensible commercial numbers for Tender Committees and Client Boards.
3. **Contractor Default Probability Modeling**: Quantifies the likelihood of contractor working capital collapse before contract award, preventing mid-project defaults.

📝 Note: Under the hood, this dashboard executes directly within your web browser using high-performance WebAssembly, delivering smooth, low-latency recalculations in the browser on workstation hardware without sending sensitive commercial data across external networks.

**Launch the Risk Simulation Dashboard via Docker**
```bash
# Ensure you are at the project root before starting
docker build -t risk-dashboard-leptos risk_dashboard_leptos/
docker run -d -p 3000:80 --name leptos-dashboard-app risk-dashboard-leptos
```

![Docker build multi-stage Leptos WASM dashboard part 1](images/docker_build_leptos_1.png)

![Docker build multi-stage Leptos WASM dashboard part 2](images/docker_build_leptos_2.png)

![Docker run containerized Leptos WASM dashboard on port 3000](images/docker_run_leptos.png)

📝 Note: Alternative Local Execution with Trunk
If Rust and Trunk are installed locally on your workstation, you can alternatively serve the WebAssembly dashboard directly:
```bash
# Ensure you are at the project root before starting
cd risk_dashboard_leptos
trunk serve --port 3000 --open
```

![Trunk serve development server compiling WebAssembly](images/trunk_serve_terminal.png)

Navigate to `http://localhost:3000` to interact with the real-time WebAssembly terminal.

![Leptos WebAssembly risk simulation dashboard in light mode](images/trunk_serve_browser_3000_light_mode.png)

![Leptos WebAssembly risk simulation dashboard in dark mode](images/trunk_serve_browser_3000_dark_mode.png)

---

## <span id="api-providers"></span><span style="color:red">🔌 4. Approach 2: Hybrid Testing Sandbox (Local Application + Cloud LLM APIs)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

![Approach 2: Hybrid Testing Sandbox](./images/approach_2_hybrid_sandbox.png)

Approach 2 runs the application runtime (FastAPI web server, ReAct agent, FastMCP compliance server, and SQLite database) on your local machine, while delegating cognitive synthesis and reasoning to enterprise foundation models hosted on commercial cloud providers (AWS Bedrock, Azure OpenAI, or Google Cloud Vertex AI).

### <span id="why-hybrid"></span>💡 4.1 Why Choose Hybrid Testing? <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
- **Zero Cloud Compute Costs**: You do not need to provision virtual machines, load balancers, VPCs, or serverless container clusters.
- **Enterprise Reasoning & Speed**: Test the reasoning accuracy, speed, and long-context capabilities of frontier foundation models directly against local regulatory tools.
- **Pay-Per-Token Only**: Minimal cost (typically less than S$0.01 per contractor pre-qualification evaluation).

### <span id="hybrid-prerequisites"></span>📋 4.2 Pre-requisites for Approach 2 <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
1. Complete **Step 3.3** (Activate Conda environment) and **Step 3.4** (Initialize SQLite database) once.
2. Copy `.env.example` to `.env` and fill in your cloud credentials for your chosen provider:
   - **AWS Bedrock**: Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_DEFAULT_REGION` in `.env`.
   - **Azure OpenAI**: Set `AZURE_OPENAI_ENDPOINT` in `.env` (uses keyless Azure Entra ID authentication via `az login`).
   - **GCP Vertex AI**: Set `GCP_PROJECT_ID`, `GCP_REGION`, and `GOOGLE_APPLICATION_CREDENTIALS` in `.env`.

### <span id="hybrid-launch"></span>🚀 4.3 Launching with Your Chosen Cloud Model <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
Set the `CLOUD_PROVIDER` variable to select your target model backend (`AWS`, `AZURE`, `GCP`, or `LOCAL`):

```bash
# 1. AWS Bedrock (Amazon Nova Pro via Amazon Bedrock)
# Ensure you are at the project root before starting
set -a; source .env; set +a
CLOUD_PROVIDER=AWS uvicorn agent_client.agent_api:app --reload --host 0.0.0.0 --port 8000

# 2. Azure OpenAI (GPT-4o via Azure OpenAI with Entra ID)
# Ensure you are at the project root before starting
set -a; source .env; set +a
CLOUD_PROVIDER=AZURE uvicorn agent_client.agent_api:app --reload --host 0.0.0.0 --port 8001

# 3. GCP Vertex AI (Gemini 2.5 Pro via Google Cloud Vertex AI)
# Ensure you are at the project root before starting
set -a; source .env; set +a
CLOUD_PROVIDER=GCP uvicorn agent_client.agent_api:app --reload --host 0.0.0.0 --port 8002

# 4. Local Sovereign Fallback (Llama 3.1 via Ollama)
# Ensure you are at the project root before starting
set -a; source .env; set +a
CLOUD_PROVIDER=LOCAL uvicorn agent_client.agent_api:app --reload --host 0.0.0.0 --port 8003
```

![AWS Bedrock Nova Pro hybrid agent server startup](images/uvicorn_agent_api_aws_terminal.png)

![Azure OpenAI GPT-4o hybrid agent server startup](images/uvicorn_agent_api_azure_terminal.png)

![GCP Vertex AI Gemini 2.5 Pro hybrid agent server startup](images/uvicorn_agent_api_gcp_terminal.png)

![Local Ollama hybrid agent server startup](images/uvicorn_agent_api_local_terminal.png)

### <span id="hybrid-web-dashboard"></span>🌐 4.4 Access the Hybrid Web Dashboard & Audit Terminal <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
Once the Uvicorn server is running, open your web browser and navigate to:
```text
#AWS Bedrock (Amazon Nova Pro via Amazon Bedrock)
http://localhost:8000

#Azure OpenAI (GPT-4o via Azure OpenAI with Entra ID)
http://localhost:8001

#GCP Vertex AI (Gemini 2.5 Pro via Google Cloud Vertex AI)
http://localhost:8002

#Local Sovereign Fallback (Llama 3.1 via Ollama)
http://localhost:8003
```

The **Enterprise Contractor Pre-Qualification & Compliance Audit Terminal** will pop up in your browser!

![AWS Bedrock web dashboard interface on port 8000](images/uvicorn_agent_api_aws_browser_8000.png)

![Azure OpenAI web dashboard interface on port 8001](images/uvicorn_agent_api_azure_browser_8001.png)

![GCP Vertex AI web dashboard interface on port 8002](images/uvicorn_agent_api_gcp_browser_8002.png)

![Local sovereign web dashboard interface on port 8003](images/uvicorn_agent_api_local_browser_8003.png)

#### 🧭 What You Are Experiencing in Hybrid Mode:
1. **Interactive Audit Terminal**: The modern web interface provides real-time access to the agentic audit workflow, displaying live prompt inputs, step-by-step tool invocation traces, and structured statutory synthesis reports.
2. **Hybrid Execution in Action**:
   - **Local Sovereign FastMCP Data**: All regulatory database lookups (BCA CRS tendering limits, MOM safety demerit points, audited balance sheets, and Singapore SOPA statutory clauses) run strictly on your local workstation against the local SQLite database (`contractors_registry.db`). Sensitive corporate data remains local.
   - **Cloud Cognitive Synthesis**: The agent delegates high-order statutory reasoning, legal compliance interpretation, and multi-criteria PQM scoring to your selected cloud foundation model (**Amazon Nova Pro via AWS Bedrock**, **Azure OpenAI**, or **Gemini 2.5 Pro via GCP Vertex AI**).
3. **Trigger Compliance Evaluations**:
   Click any of the preset quick action buttons or enter custom inquiries to evaluate the cloud model:
   - **`Heng Win` Screening**: "Screen `Heng Win` for the S$120M Woodlands Health Campus Tender (TND-2026-SG-001)"
   - **Statutory Safety Bar Audit**: "Verify MOM Safety Demerit Points and bizSAFE compliance for `Titan Piling & Civil Engineering`"
   - **Solvency Check**: "Conduct financial solvency and bond capacity check for `Starlight Urban Infrastructure` on a S$35M project"
   - **`GemStone` PQM Evaluation**: "Calculate BCA PQM score for `GemStone` with bid of S$116M against benchmark S$120M"
   - **SOPA Clause Audit**: "Audit this contract clause under Singapore SOPA: Subcontractor will be paid within 14 days after main contractor receives payment from Employer (pay when paid)"

---

## <span id="omni-cloud-deployment"></span><span style="color:red">☁️ 5. Approach 3: Cloud Workload Direct Provisioning (Single-Project Cloud Deployment)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

![Approach 3: Cloud Workload Direct Provisioning](./images/approach_3_cloud_workload.png)

Approach 3 packages the entire framework (FastAPI web server, ReAct agent, FastMCP server, and regulatory database) into a production Docker container, pushes it to your cloud container registry, and deploys it directly into a dedicated project VPC serverlessly using Terraform Infrastructure as Code (IaC).

### <span id="why-cloud-native"></span>💡 5.1 Why Choose Cloud Workload Direct Provisioning? <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
- **Production Availability**: Provides a persistent, publicly accessible HTTPS endpoint backed by cloud load balancers or edge ingresses.
- **Enterprise Security**: Integrates with native cloud IAM roles, Azure Entra ID Managed Identities, and Google Service Accounts with zero hardcoded API keys in runtime containers.
- **Serverless Autoscaling**: Scales compute resources dynamically based on incoming tender evaluation requests, scaling down to zero when idle (on Azure and GCP).

### <span id="cloud-native-prerequisites"></span>📋 5.2 Pre-requisites for Approach 3 <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
- Docker Desktop running locally to build multi-platform container images.
- Terraform CLI installed.
- Cloud CLI authenticated to your cloud account (`aws configure`, `az login`, or `gcloud auth login`).

To package the agent, web UI, and MCP server into a single container and deploy serverlessly to the cloud, select your target Cloud Service Provider (CSP) track below:

---

### <span id="aws-deployment"></span>☁️ 5.3 AWS Deployment (ECS Fargate + Amazon Bedrock) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

<details>
<summary><b>🚀 Click to expand 5.3 AWS Deployment (ECS Fargate + Amazon Bedrock) guide, Terraform IaC, and architecture</b></summary>

![AWS Cloud-Native Deployment Architecture](./images/architecture_aws.png)

```mermaid
graph TD
    Client["Tender Evaluation Committee / Client Browser"] -->|HTTPS Ingress Port 443| Ingress["AWS Application Load Balancer (Dual-AZ Ingress)"]
    Registry["Amazon Elastic Container Registry (Private ARM64 Repo)"] -->|Deploy Container Image| Compute["AWS ECS Fargate Task: FastAPI Web Server & ReAct Agent"]
    Ingress -->|Forward Port 8000| Compute

    Compute -->|Secure Tool Requests| MCPServer["Enterprise Compliance FastMCP Server"]
    MCPServer -->|Direct SQL Queries| RegulatoryDB[("Local SQLite Regulatory DB: BCA, MOM, ACRA, Tenders")]

    Compute -->|IAM Task Role SigV4 Auth| FoundationLLM["Amazon Bedrock: Amazon Nova Pro Foundation Model"]

    Compute -->|Export Structured JSON Telemetry| Observability["Amazon CloudWatch: Audit Logs & Container Metrics"]
```

Deploys the containerized agent and MCP server serverlessly to AWS ECS Fargate:
```bash
# 1. Provision AWS ECS Infrastructure via Terraform
# Ensure you are at the project root before starting
set -a; source .env; set +a
cd terraform/aws
terraform init
terraform apply -var="aws_region=${AWS_DEFAULT_REGION}" -auto-approve

# 2. Build and Push Container Image to Amazon ECR
ECR_URL=$(terraform output -raw ecr_repository_url)
aws ecr get-login-password --region ${AWS_DEFAULT_REGION} | docker login --username AWS --password-stdin ${ECR_URL}
cd ../..
docker build --platform linux/arm64 -t enterprise-mcp-agent .
docker tag enterprise-mcp-agent:latest ${ECR_URL}:latest
docker push ${ECR_URL}:latest

# 3. Access Live Web Dashboard
cd terraform/aws
ALB_URL=$(terraform output -raw alb_url)

# Wait approximately 60 seconds (1 minute) for AWS ECS Fargate to pull the image and pass ALB health checks.
# Pre-warning: Accessing prematurely causes the ALB to return HTTP 503 (Service Temporarily Unavailable).
# Optional: Verify endpoint readiness via terminal
# curl ${ALB_URL}/docs

# Open the live Web Dashboard in your default browser:
open ${ALB_URL}
```

![AWS ECR Docker Multi-Platform Build and Tag](./images/docker_build_tag_push_aws_1.png)

![AWS ECR Push and Application Load Balancer URL Verification](./images/docker_build_tag_push_aws_2.png)

![AWS ECS PQQ Risk Dashboard Home Tab Overview](./images/pqq_dashboard_aws_1_home.png)

![AWS Bedrock Contractor Audit and ReAct Agent Chat Verification](./images/pqq_dashboard_aws_2_agent_chat.png)

![AWS PQQ Risk Dashboard What-If Financial & Demerit Simulation](./images/pqq_dashboard_aws_3_what_if.png)

![AWS PQQ Multi-Agent Adversarial Challenge and Statutory Duel](./images/pqq_dashboard_aws_4_agent_debate.png)

</details>

---

### <span id="azure-deployment"></span>🔷 5.4 Azure Deployment (Azure Container Apps + Azure OpenAI) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

<details>
<summary><b>🚀 Click to expand 5.4 Azure Deployment (Azure Container Apps + Azure OpenAI) guide, Terraform IaC, and architecture</b></summary>

![Azure Cloud-Native Deployment Architecture](./images/architecture_azure.png)

```mermaid
graph TD
    Client["Tender Evaluation Committee / Client Browser"] -->|HTTPS Ingress Port 443| Ingress["Azure Container Apps Ingress (Built-in Envoy Proxy)"]
    Registry["Azure Container Registry (Private AMD64 Repo)"] -->|Deploy Container Image| Compute["Azure Container Apps Dynamic Replica: FastAPI Web Server & ReAct Agent"]
    Ingress -->|Forward Port 8000| Compute

    Compute -->|Secure Tool Requests| MCPServer["Enterprise Compliance FastMCP Server"]
    MCPServer -->|Direct SQL Queries| RegulatoryDB[("Local SQLite Regulatory DB: BCA, MOM, ACRA, Tenders")]

    Compute -->|Entra ID Managed Identity Auth| FoundationLLM["Azure OpenAI Service: GPT-4o Foundation Model"]

    Compute -->|Export Structured JSON Telemetry| Observability["Azure Monitor Log Analytics: Audit Logs & App Metrics"]
```

Deploys the containerized solution to Azure Container Apps with native Entra ID managed identity:
```bash
# 1. Provision Azure Container Apps Infrastructure via Terraform
# Ensure you are at the project root before starting
set -a; source .env; set +a
cd terraform/azure
terraform init
terraform apply -auto-approve

# 2. Build and Push Container Image to Azure Container Registry (ACR)
ACR_LOGIN_SERVER=$(terraform output -raw acr_login_server)
ACR_USERNAME=$(terraform output -raw acr_admin_username)
ACR_PASSWORD=$(terraform output -raw acr_admin_password)
docker login ${ACR_LOGIN_SERVER} -u ${ACR_USERNAME} -p ${ACR_PASSWORD}
cd ../..
docker build --platform linux/amd64 -t enterprise-mcp-agent .
docker tag enterprise-mcp-agent:latest ${ACR_LOGIN_SERVER}/enterprise-mcp-agent:latest
docker push ${ACR_LOGIN_SERVER}/enterprise-mcp-agent:latest

# 3. Deploy Image to Azure Container Apps
az containerapp update \
  --name enterprisemcpagent-app \
  --resource-group enterprisemcpagent-rg \
  --image ${ACR_LOGIN_SERVER}/enterprise-mcp-agent:latest

# 4. Access Live Web Dashboard
cd terraform/azure
CONTAINER_APP_URL=$(terraform output -raw container_app_url)

# Wait approximately 20-30 seconds for Azure Container Apps serverless scale-from-zero and Entra ID authentication.
# Optional: Verify endpoint readiness via terminal
# curl ${CONTAINER_APP_URL}/docs

# Open the live Web Dashboard in your default browser:
open ${CONTAINER_APP_URL}
```

![Azure Container Registry Docker Multi-Platform Build](./images/docker_build_tag_push_azure_1.png)

![Azure Container Registry Docker Image Push](./images/docker_build_tag_push_azure_2.png)

![Azure Container Apps Serverless Deployment Verification](./images/docker_build_tag_push_azure_3.png)

![Azure Container Apps PQQ Risk Dashboard Home Tab Overview](./images/pqq_dashboard_azure_1_home.png)

![Azure OpenAI Contractor Audit and ReAct Agent Chat Verification](./images/pqq_dashboard_azure_2_agent_chat.png)

![Azure PQQ Risk Dashboard What-If Financial & Demerit Simulation](./images/pqq_dashboard_azure_3_what_if.png)

![Azure PQQ Multi-Agent Adversarial Challenge and Statutory Duel](./images/pqq_dashboard_azure_4_agent_debate.png)

</details>

---

### <span id="gcp-deployment"></span>🌐 5.5 Google Cloud Deployment (Google Cloud Run + Vertex AI) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

<details>
<summary><b>🚀 Click to expand 5.5 Google Cloud Deployment (Google Cloud Run + Vertex AI) guide, Terraform IaC, and architecture</b></summary>

![Google Cloud Deployment Architecture](./images/architecture_gcp.png)

```mermaid
graph TD
    Client["Tender Evaluation Committee / Client Browser"] -->|HTTPS Ingress Port 443| Ingress["Google Cloud Run Ingress (Global Edge Load Balancer)"]
    Registry["Google Cloud Artifact Registry (Private Docker OCI Repo)"] -->|Deploy Container Image| Compute["Google Cloud Run v2 Service: FastAPI Web Server & ReAct Agent"]
    Ingress -->|Forward Port 8000| Compute

    Compute -->|Secure Tool Requests| MCPServer["Enterprise Compliance FastMCP Server"]
    MCPServer -->|Direct SQL Queries| RegulatoryDB[("Local SQLite Regulatory DB: BCA, MOM, ACRA, Tenders")]

    Compute -->|Service Account ADC Auth| FoundationLLM["Google Cloud Vertex AI: Gemini 2.5 Pro Foundation Model"]

    Compute -->|Export Structured JSON Telemetry| Observability["Google Cloud Operations Suite: Cloud Logging & Metrics"]
```

Deploys the containerized solution to Google Cloud Run with autoscaling to zero:
```bash
# 1. Provision Google Cloud Run Infrastructure via Terraform
# Ensure you are at the project root before starting
set -a; source .env; set +a
cd terraform/gcp
terraform init
terraform apply -var="project_id=${GCP_PROJECT_ID}" -auto-approve

# 2. Build and Push Container Image to Google Artifact Registry (GAR)
AR_URL=$(terraform output -raw artifact_registry_url)
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
cd ../..
docker build --platform linux/amd64 --provenance=false -t enterprise-mcp-agent .
docker tag enterprise-mcp-agent:latest ${AR_URL}/enterprise-mcp-agent:latest
docker push ${AR_URL}/enterprise-mcp-agent:latest

# 3. Deploy Image to Google Cloud Run
gcloud run deploy enterprise-mcp-agent --image ${AR_URL}/enterprise-mcp-agent:latest --region us-central1 --quiet

# 4. Access Live Web Dashboard
cd terraform/gcp
CLOUD_RUN_URL=$(terraform output -raw cloud_run_url)

# Wait approximately 15-20 seconds for Google Cloud Run revision routing to activate.
# Optional: Verify endpoint readiness via terminal
# curl ${CLOUD_RUN_URL}/docs

# Open the live Web Dashboard in your default browser:
open ${CLOUD_RUN_URL}
```

![GCP Artifact Registry Docker Multi-Platform Build](./images/docker_build_tag_push_run_gcp_1.png)

![Google Cloud Run Container Deployment and Service URL Verification](./images/docker_build_tag_push_run_gcp_2.png)

![Google Cloud Run PQQ Risk Dashboard Home Tab Overview](./images/pqq_dashboard_gcp_1_home.png)

![GCP Vertex AI Contractor Audit and ReAct Agent Chat Verification](./images/pqq_dashboard_gcp_2_agent_chat.png)

![GCP PQQ Risk Dashboard What-If Financial & Demerit Simulation](./images/pqq_dashboard_gcp_3_what_if.png)

![GCP PQQ Multi-Agent Adversarial Challenge and Statutory Duel](./images/pqq_dashboard_gcp_4_agent_debate.png)

</details>

---

## <span id="enterprise-landing-zone"></span><span style="color:red">🏛️ 6. Approach 4: Enterprise Multi-Account Landing Zone & Sovereign Governance (Planned)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

![Approach 4: Enterprise Multi-Account Landing Zone](./images/approach_4_enterprise_landing_zone.png)

📝 Note: Architectural Design Intent (Planned Activity)
Approach 4 represents an architectural design blueprint and governance pattern rather than executable code in this repository. While Approaches 1, 2, and 3 provide working code, automated test suites, and deployable Terraform scripts, Approach 4 documents the target enterprise landing-zone topology (multi-account hierarchy, organizational guardrails, centralized hub-and-spoke networking, and sovereign CISO controls) for institutional and public-sector procurement environments.

While Approach 3 provisions resources directly into a single project VPC, large institutional developers, government bodies, and tier-1 construction conglomerates require **top-down multi-account governance**:

1. **Global DNS & Ingress Routing**: Uses enterprise DNS (AWS Route 53, Azure Traffic Manager, GCP Cloud DNS) coupled with corporate Single Sign-On (Entra ID, Okta) and dedicated VPN / Direct Connect circuits.
2. **Centralized Hub-and-Spoke Networking**: Traffic routes through a centralized Transit Gateway or Shared VPC network hub, ensuring isolated egress and automated packet inspection.
3. **Core Security & Audit Account**: Aggregates centralized audit logs (CloudTrail, GuardDuty, Security Command Center) and provides enterprise FinOps cost visibility.
4. **Environment Segregation**: Isolates Development, Staging (UAT), and Production workloads into dedicated cloud accounts with strict IAM Service Control Policies (SCPs).

---

## <span id="automated-testing"></span><span style="color:red">🧪 7. Automated Testing & Verification</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

📝 Note: Universal Offline Test Verification
The unit test suite verifies the core Python business logic, FastMCP tool functions, SQLite queries, PQM math, and statutory rules locally. You can execute it at any time under any of the 3 executable options without needing active cloud credentials or running containers.

Run the built-in test suite to verify all 12 MCP tool functions, SQLite queries, financial ratio math, and statutory SOPA validation rules:
```bash
# Ensure you are at the project root before starting
python3 -m unittest tests/test_mcp_framework.py -v
```

Expected Output:
```text
test_assess_financial_solvency_distressed (tests.test_mcp_framework.TestMCPComplianceServer.test_assess_financial_solvency_distressed) ... ok
test_assess_financial_solvency_strong (tests.test_mcp_framework.TestMCPComplianceServer.test_assess_financial_solvency_strong) ... ok
test_audit_contract_risk_short_notice (tests.test_mcp_framework.TestMCPComplianceServer.test_audit_contract_risk_short_notice) ... ok
test_audit_contract_risk_sopa_violation (tests.test_mcp_framework.TestMCPComplianceServer.test_audit_contract_risk_sopa_violation) ... ok
test_evaluate_pqm_score (tests.test_mcp_framework.TestMCPComplianceServer.test_evaluate_pqm_score) ... ok
test_list_sample_tenders (tests.test_mcp_framework.TestMCPComplianceServer.test_list_sample_tenders) ... ok
test_query_contractor_profile_not_found (tests.test_mcp_framework.TestMCPComplianceServer.test_query_contractor_profile_not_found) ... ok
test_query_contractor_profile_valid (tests.test_mcp_framework.TestMCPComplianceServer.test_query_contractor_profile_valid) ... ok
test_simulate_contractor_monte_carlo_risk_critical_default (tests.test_mcp_framework.TestMCPComplianceServer.test_simulate_contractor_monte_carlo_risk_critical_default) ... ok
test_simulate_contractor_monte_carlo_risk_prudent (tests.test_mcp_framework.TestMCPComplianceServer.test_simulate_contractor_monte_carlo_risk_prudent) ... ok
test_verify_safety_compliance_compliant (tests.test_mcp_framework.TestMCPComplianceServer.test_verify_safety_compliance_compliant) ... ok
test_verify_safety_compliance_debarred_sdp_breach (tests.test_mcp_framework.TestMCPComplianceServer.test_verify_safety_compliance_debarred_sdp_breach) ... ok

----------------------------------------------------------------------
Ran 12 tests in 0.256s

OK
```

![Unit and integration test suite execution](./images/test_mcp_framework_terminal.png)

---

## <span id="cleanup"></span><span style="color:red">🧹 8. Clean Up</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>

### <span id="stop-local-server"></span>🛑 8.1 Stopping the Local Server (Approach 1 & Approach 2) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
Press `Ctrl + C` in the terminal to cleanly terminate the FastAPI server and close the child MCP stdio connection.

### <span id="destroy-cloud-infra"></span>☁️ 8.2 Destroying Cloud Infrastructure (Approach 3) <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](#toc)</span>
If cloud infrastructure was provisioned via Terraform, navigate to the respective directory (ordered: AWS -> Azure -> GCP) and destroy all resources:

```bash
# For AWS:
# Ensure you are at the project root before starting
set -a; source .env; set +a
cd terraform/aws
terraform destroy -var="aws_region=${AWS_DEFAULT_REGION}" -auto-approve

# For Azure:
# Ensure you are at the project root before starting
cd terraform/azure
terraform destroy -auto-approve

# For GCP:
# Ensure you are at the project root before starting
set -a; source .env; set +a
cd terraform/gcp
terraform destroy -var="project_id=${GCP_PROJECT_ID}" -auto-approve
```

---

## 📄 License
This module is distributed as part of the Agentic Construction Intelligence Platform (ACIP) under the **Apache License 2.0**. See the root [LICENSE](../LICENSE) file for full license terms and conditions.
