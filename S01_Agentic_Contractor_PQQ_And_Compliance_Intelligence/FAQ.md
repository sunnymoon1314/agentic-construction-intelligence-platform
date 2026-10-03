# <span style="color:red">❓ 9. Frequently Asked Questions (FAQ)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](README.md#toc)</span>

---

## <span id="faq-toc"></span>📑 Table Of Contents (TOC)

- [Q1: How does the BCA Contractors Registration System (CRS) determine tendering limits and statutory eligibility?](#q1)
- [Q2: How do Ministry of Manpower (MOM) Safety Demerit Points (SDP) trigger automatic contractor debarment?](#q2)
- [Q3: How does the Model Context Protocol (MCP) stdio client-server IPC mechanism work?](#q3)
- [Q4: Why are Pay-When-Paid clauses considered unenforceable under Section 9 of the Singapore SOPA?](#q4)
- [Q5: How is the Price-Quality Method (PQM) composite score computed?](#q5)
- [Q6: How should an enterprise or Chief Technology Officer (CTO) strategically select a Cloud Service Provider (AWS vs. Microsoft Azure vs. Google Cloud)?](#q6)
- [Q7: What FinOps strategies optimize compute expenditure for quantitative Monte Carlo risk simulations (Spot vs. Reserved Instances)?](#q7)
- [Q8: How does graceful interruption and state checkpointing work across AWS, Azure, and Google Cloud Spot instances?](#q8)
- [Q9: What is the estimated Total Cost of Ownership (TCO) and operational budget for implementing this MCP Framework for a Quantity Surveying (QS) firm or Property Developer?](#q9)
- [Q10: Why was Leptos WebAssembly chosen for the Quantity Surveyor frontend instead of traditional Python web frameworks like Streamlit?](#q10)
- [Q11: Why does the AWS deployment URL require an explicit port (:8000), whereas the Azure and Google Cloud URLs are completely port-free over HTTPS?](#q11)
- [Q12: What are the step-by-step mathematical formulas, statutory thresholds, and decision trees used in the What-If Stress Testing Cockpit?](#q12)

---

### <span id="q1"></span>🔹 **Q1: How does the BCA Contractors Registration System (CRS) determine tendering limits and statutory eligibility?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: The Building and Construction Authority (BCA) Contractors Registration System (CRS) serves as the statutory pre-qualification benchmark for construction procurement across Singapore. Contractors are evaluated and categorized under specific technical Workheads:
- **CW01**: General Building
- **CW02**: Civil Engineering
- **CR Categories**: Construction-Related specialties (e.g. CR01 Piling Works, CR03 Demolition, CR09 Structural Steel Work)
- **ME Categories**: Mechanical and Electrical specialties (e.g. ME01 Air-Conditioning, ME05 Fire Prevention)

Within major workheads such as CW01 and CW02, the BCA enforces a rigid seven-tier financial and operational grading hierarchy:
1. **Grade A1**: Unlimited tendering limit. Demands a minimum paid-up capital of S$15,000,000, an audited net worth of S$15,000,000, and a proven three-year track record exceeding S$150,000,000 in completed building projects.
2. **Grade A2**: Tendering limit capped at S$105,000,000. Demands a minimum paid-up capital of S$6,500,000 and a 3-year track record exceeding S$65,000,000.
3. **Grade B1**: Tendering limit capped at S$50,000,000. Demands a minimum paid-up capital of S$3,000,000 and a 3-year track record exceeding S$30,000,000.
4. **Grade B2**: Tendering limit capped at S$16,000,000. Demands a minimum paid-up capital of S$1,000,000 and a 3-year track record exceeding S$10,000,000.
5. **Grades C1 / C2 / C3**: Tendering limits stepped down at S$5,000,000 (C1), S$1,600,000 (C2), and S$800,000 (C3) respectively.

In this framework, the tool `query_contractor_profile` implemented in `mcp_server/server.py` queries the SQLite database at `mcp_server/contractors_registry.db`. It queries the `contractors` table, extracts the contractor registered CRS grade, compares the estimated project budget against `tendering_limit_sgd`, and alerts the evaluation committee if a contractor attempts to bid on a contract exceeding their statutory limit.

---

### <span id="q2"></span>🔹 **Q2: How do Ministry of Manpower (MOM) Safety Demerit Points (SDP) trigger automatic contractor debarment?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: Under the Singapore Workplace Safety and Health (WSH) Act, the Ministry of Manpower (MOM) maintains a cumulative Safety Demerit Points (SDP) registry for all construction companies operating within the country. Demerit points are issued following workplace fatalities, dangerous structural collapses, major bodily injuries, and Stop Work Orders (SWOs) issued by MOM safety inspectors.

Demerit points remain active across a rolling 18-month audit cycle. The critical statutory threshold is 25 points:
- **0 to 14 Points**: Warning zone. No immediate administrative restriction, but tracked for trend analysis.
- **15 to 24 Points**: Heightened surveillance. Contractors are monitored closely, mandatory third-party safety audits are required, and private developers often impose quality deductions during tender reviews.
- **25 Points and Above**: Immediate statutory sanctions take effect. Under MOM rules, any contractor accumulating 25 or more SDPs within an 18-month window is automatically blocked from hiring any new foreign workers (Work Permit and S-Pass holders) and prohibited from renewing existing foreign worker permits.

Because major construction projects in Singapore depend heavily on specialized foreign construction crews, an active 25-point SDP freeze renders the contractor operationally incapable of mobilizing site labor. Consequently, public procurement guidelines issued by the BCA mandate that any contractor with >= 25 demerit points must be statutorily disqualified from public tenders.

In this framework, the `verify_safety_compliance` tool in `mcp_server/server.py` queries the `safety_compliance` table. If `mom_sdp >= 25` or `mom_debarred == 1`, it immediately generates a `CRITICAL STATUTORY BAR (DISQUALIFIED)` status flag, warning the agent and evaluation committee that the contractor is legally barred from participation.

---

### <span id="q3"></span>🔹 **Q3: How does the Model Context Protocol (MCP) stdio client-server IPC mechanism work?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: The Model Context Protocol (MCP) standardized by Anthropic operates on a decoupled client-server architecture using JSON-RPC 2.0 messages. While remote MCP servers can run over Server-Sent Events (SSE) via HTTP, enterprise tools running locally or inside containerized microservices utilize the `stdio` transport.

Under `stdio` transport:
1. The client process (`agent_client/agent_api.py`) initiates a child subprocess executing `python mcp_server/server.py` using standard operating system pipes.
2. The client context manager `stdio_client(server_params)` opens two asynchronous streams: a readable pipe capturing stdout from the child process, and a writable pipe delivering input to stdin of the child process.
3. During the FastAPI startup lifespan, `ClientSession(read, write)` performs an asynchronous JSON-RPC handshake (`initialize` method).
4. When the LangChain ReAct agent decides to invoke a tool (e.g. `assess_financial_solvency`), the client formats a JSON-RPC request containing the tool name and argument payload, serializes it as a single line of text, and flushes it to the child process stdin.
5. The FastMCP server process (`mcp_server/server.py`) receives the stream on stdin, executes the Python function, queries `contractors_registry.db`, and writes the JSON-RPC response back to stdout.
6. The client deserializes the text payload and returns the structured response back into the agent context window.

This architecture enforces strict process boundary isolation: the LLM reasoning agent never interacts directly with the database or file system, while tools can be authored, patched, and audited independently without restarting the core web server.

---

### <span id="q4"></span>🔹 **Q4: Why are Pay-When-Paid clauses considered unenforceable under Section 9 of the Singapore SOPA?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: Prior to 2004, downstream subcontractors and suppliers in the Singapore construction industry suffered frequent insolvency because main contractors withheld payments under conditional clauses known as **Pay-When-Paid** or **Pay-If-Paid**. Under these terms, the main contractor had no obligation to pay the subcontractor until the main contractor first received funds from the Employer/Developer.

To protect cash flow across the supply chain, the Singapore Parliament enacted the **Building and Construction Industry Security of Payment Act (SOPA)** (Cap. 30B). Section 9 of SOPA states explicitly:
"A pay when paid provision of a contract has no effect in relation to any payment for construction work carried out or undertaken to be carried out, or for goods or services supplied or undertaken to be supplied, under the contract."

Key legal consequences under SOPA:
- Any contract clause making payment contingent on the receipt of payment from a third party is legally void ab initio.
- If a main contractor relies on a pay-when-paid clause to reject a progress claim, the subcontractor can initiate expedited statutory adjudication under the Singapore Mediation Centre (SMC).
- Adjudication determinations are enforceable in the Singapore High Court as a court judgment.

In this framework, the `audit_contract_risk` tool in `mcp_server/server.py` scans contract text using pattern detection algorithms. If terms like "pay when paid", "pay if paid", or "condition precedent on payment received from Employer" are identified, the tool flags an immediate `CRITICAL STATUTORY VIOLATION: SOPA BREACH (SECTION 9)`.

---

### <span id="q5"></span>🔹 **Q5: How is the Price-Quality Method (PQM) composite score computed?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: The Price-Quality Method (PQM) is mandated by BCA for public sector construction tenders valued at S$3 million and above to avoid the race to the bottom caused by purely price-driven award decisions. 

Tenders are evaluated in a two-envelope format:
- **Price Component (typically 60% to 70% weight)**
- **Quality Component (typically 30% to 40% weight)**

The mathematical implementation in `evaluate_pqm_score` follows standard BCA benchmarking:

1. **Price Competitiveness Score (P)**:
   - Evaluated relative to the Tender Benchmark Budget (`tender_benchmark_sgd`).
   - If the contractor bid (`B`) is less than or equal to the benchmark (`M`):
     `Raw_Price_Score = max(0, 100 - (abs(B - M) / M) x 50)`
   - If the contractor bid exceeds the benchmark:
     `Raw_Price_Score = max(0, 100 - ((B - M) / M) x 120)`
   - This rewards competitive, realistic bids while penalizing bids that significantly exceed the estimated budget.

2. **Quality Attributes Score (Q)**:
   - Past Quality Performance (CONQUAS Benchmark): 40 points maximum (`(CONQUAS / 100) x 40`).
   - Delivery Track Record: 30 points maximum, computed from on-time completion percentage and penalized for open defect notices.
   - Workplace Safety and Health Factor: 20 points maximum, with explicit deductions for accumulated MOM Safety Demerit Points (`20 - (SDP x 0.8)`).
   - Productivity & Innovation: 10 points maximum for Design for Manufacturing and Assembly (DfMA) / PPVC adoption.

3. **Composite Weighted Score**:
   `Composite_Score = (Raw_Price_Score x Price_Weight) + (Raw_Quality_Score x Quality_Weight)`

Bids achieving composite scores of 85 and above are flagged as `HIGHLY RECOMMENDED FOR AWARD`, ensuring balanced fiscal responsibility and high construction quality.

---

### <span id="q6"></span>🔹 **Q6: How should an enterprise or Chief Technology Officer (CTO) strategically select a Cloud Service Provider (AWS vs. Microsoft Azure vs. Google Cloud)?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: Enterprise cloud selection is a strategic decision that extends beyond raw compute benchmarks. CTOs and Lead Architects evaluate three core dimensions: enterprise ecosystem alignment, data sovereignty and regulatory compliance, and commercial FinOps leverage.

1. **Enterprise Ecosystem Alignment**:
   - **Microsoft Azure**: The natural choice for organizations operating deep within the Microsoft productivity and security stack. If an enterprise heavily utilizes Microsoft 365, Windows Server, SQL Server, and Microsoft Entra ID (formerly Azure Active Directory), Azure provides unified single sign-on (SSO) and substantial licensing savings through the **Azure Hybrid Benefit (AHB)**, reducing Windows and SQL Server compute costs by up to 40% to 50%.
   - **Amazon Web Services (AWS)**: The premier choice for technical organizations prioritizing catalog breadth, mature third-party integrations, and battle-tested global scale. AWS boasts over 200 fully featured services and the largest talent pool of certified cloud practitioners and DevOps engineers. It is particularly strong for high-concurrency e-commerce, complex multi-tier microservices, and organizations demanding advanced networking primitives.
   - **Google Cloud Platform (GCP)**: The dominant provider for data-intensive organizations, predictive machine learning, and container orchestration. With native innovations such as **BigQuery** (serverless petabyte-scale data warehouse), **Vertex AI** (unified foundation model governance and long-context Gemini models), and **Google Kubernetes Engine (GKE)**, GCP is the preferred destination for data science teams and AI-first engineering firms. Furthermore, Google operates its own private global fiber network, minimizing cross-region latency.

2. **Data Sovereignty & Local Regulatory Compliance (Singapore Precedents)**:
   - In Singapore, financial institutions, healthcare operators, and statutory bodies are strictly governed by the Monetary Authority of Singapore (MAS) Technology Risk Management (TRM) Guidelines and the Cyber Security Agency (CSA) Multi-Tier Cloud Security (MTCS SS 584) standard.
   - All three hyperscalers operate local Singapore cloud regions with Tier 3 / MTCS Level 3 certification: AWS (`ap-southeast-1`), Azure (`Southeast Asia`), and Google Cloud (`asia-southeast1`).
   - For public sector projects under Singapore Government Commercial Cloud (GCC 2.0), all three providers offer compliant enclaves, meaning architectural fit and team capability typically dictate the final selection.

3. **Commercial FinOps Levers**:
   - Enterprises leverage volume discount commitments to lower operational expenditure: AWS Enterprise Discount Programs (EDP), Microsoft Azure Consumption Commitments (MACC), and Google Cloud Committed Use Discounts (CUD). If an organization already has an active multi-million dollar MACC or EDP agreement, hosting the MCP compliance framework on that provider contributes directly toward fulfilling that contractual spending commitment.

---

### <span id="q7"></span>🔹 **Q7: What FinOps strategies optimize compute expenditure for quantitative Monte Carlo risk simulations (Spot vs. Reserved Instances)?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: In quantitative construction risk management, simulating contractor default risk, supply chain disruptions, and liquidated damages requires executing 100,000 to 1,000,000 stochastic differential equation draws. How compute is provisioned for this workload represents a critical FinOps decision.

1. **Workload Profile Classification**:
   - Monte Carlo simulation is an **embarrassingly parallel, stateless, batch-oriented workload**. Each simulation iteration (drawing correlated random variables for material price spikes, labor delays, and cash flow deficits) is mathematically independent of every other iteration.
   - Unlike relational databases (e.g. PostgreSQL) or customer-facing API servers that require guaranteed 24/7/365 uninterrupted availability, batch simulations do not require single-node continuous uptime as long as intermediate progress is checkpointed.

2. **Reserved Instances (RI) / Savings Plans vs. Spot Instances**:
   - **Reserved Instances (RI) / Savings Plans**: Require committing to a 1-year or 3-year term in exchange for a 30% to 60% discount off standard on-demand pricing. While ideal for steady-state baseline servers (such as the FastAPI web dashboard), paying for reserved capacity to support bursty, periodic tender screening simulations locks capital into idle hardware.
   - **Spot Instances (AWS Spot / Azure Spot / GCP Spot VMs)**: Allow organizations to purchase unused cloud compute capacity at steep discounts of **60% to 90% off standard on-demand rates**. Because cloud providers retain the contractual right to reclaim Spot capacity with brief notice when on-demand demand rises, Spot compute is exceptionally cheap.

3. **The FinOps Conclusion**:
   - Running Monte Carlo simulations on full-price On-Demand instances is an operational anti-pattern.
   - By architecting the Rust risk engine (`risk_engine/`) to support stateless parallel batches with persistent checkpointing, organizations achieve massive 75% to 85% compute cost reductions while completing high-volume tender audits within minutes.

---

### <span id="q8"></span>🔹 **Q8: How does graceful interruption and state checkpointing work across AWS, Azure, and Google Cloud Spot instances?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: Because cloud providers can reclaim Spot instances when capacity is demanded elsewhere, enterprise production systems must implement automated interruption detection and state serialization. Cloud providers communicate impending preemptions through specialized Instance Metadata Services (IMDS) and ACPI hardware signals.

Here is the exact technical mechanics across all three cloud platforms:

1. **Amazon Web Services (AWS EC2 Spot)**:
   - **Warning Window**: Exactly **2 minutes** before termination.
   - **Detection Mechanism**: The local instance queries IMDSv2 at `http://169.254.169.254/latest/meta-data/spot/instance-action`. When reclamation begins, AWS returns an HTTP 200 containing a JSON payload with the exact termination time and action (`stop` or `terminate`). AWS also emits an EventBridge event: `EC2 Spot Instance Interruption Warning`.
   - **State Checkpointing**: A background watchdog daemon detects the HTTP 200 response and dispatches `kill -SIGTERM ${ENGINE_PID}` to the running Rust simulation process. The Rust process catches the signal via `tokio::signal::unix::SignalKind::terminate()`, completes the current discrete iteration batch, serializes the accumulated Value at Risk (VaR) distribution and completed iteration index to a local file, and executes:
     `aws s3 cp /app/checkpoint.json s3://${CHECKPOINT_BUCKET}/monte_carlo/state_${TENDER_ID}.json`

2. **Microsoft Azure (Azure Spot Virtual Machines)**:
   - **Warning Window**: Exactly **30 seconds** before termination.
   - **Detection Mechanism**: The virtual machine polls the Azure Scheduled Events service available via IMDS at `http://169.254.169.254/metadata/scheduledevents?api-version=2020-07-01` with the required HTTP header `Metadata: true`. When preemption is scheduled, the service returns an event with `"EventType": "Preempt"`.
   - **State Checkpointing**: Upon detecting the `Preempt` event, the watchdog script triggers the serialization flush and uploads the checkpoint payload to Azure Blob Storage using managed identity authentication:
     `az storage blob upload --account-name ${STORAGE_ACCOUNT} --container-name checkpoints --file /app/checkpoint.json --name state_${TENDER_ID}.json --auth-mode login`

3. **Google Cloud Platform (GCP Spot VMs / Preemptible VMs)**:
   - **Warning Window**: Exactly **30 seconds** before termination.
   - **Detection Mechanism**: The metadata server exposes a dedicated preemption endpoint at `http://metadata.google.internal/computeMetadata/v1/instance/preempted` with the header `Metadata-Flavor: Google`. When preemption occurs, this endpoint flips its return string from `FALSE` to `TRUE`. In addition, Google Cloud delivers an ACPI Power Button event to the guest operating system.
   - **State Checkpointing**: The preemption daemon catches the signal or ACPI interrupt, halts simulation draws, and flushes progress to Google Cloud Storage (GCS) using Application Default Credentials (ADC):
     `gcloud storage cp /app/checkpoint.json gs://${GCS_BUCKET}/monte_carlo/state_${TENDER_ID}.json`

4. **Resumption by the Replacement Instance**:
   - When the cloud Auto-Scaling Group (AWS), VM Scale Set (Azure), or Managed Instance Group (GCP) automatically spins up a replacement Spot instance in an alternate Availability Zone, the instance startup script downloads the latest checkpoint from cloud storage:
     - **AWS**: `aws s3 cp s3://${CHECKPOINT_BUCKET}/monte_carlo/state_${TENDER_ID}.json /app/checkpoint.json`
     - **Azure**: `az storage blob download --account-name ${STORAGE_ACCOUNT} --container-name checkpoints --name state_${TENDER_ID}.json --file /app/checkpoint.json --auth-mode login`
     - **GCP**: `gcloud storage cp gs://${GCS_BUCKET}/monte_carlo/state_${TENDER_ID}.json /app/checkpoint.json`
   - The Rust simulation binary ingests the checkpoint, reads that iterations 0 through 45,000 are already completed, seeds the Mersenne Twister PRNG at step 45,001, and continues without lost progress or duplicate spend.

---

### <span id="q9"></span>🔹 **Q9: What is the estimated Total Cost of Ownership (TCO) and operational budget for implementing this MCP Framework for a Quantity Surveying (QS) firm or Property Developer?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: For institutional developers (such as HDB, JTC, CapitaLand, CDL) or professional Quantity Surveying consultancies (such as Rider Levett Bucknall, Arcadis, Turner & Townsend), implementing this agentic MCP compliance audit framework provides clear fiscal transparency.

Here is an itemized operational budget across all three deployment tiers:

1. **Tier 1: Sovereign On-Premises Deployment (Option 1)**:
   - **Hardware Compute**: **S$0.00 / month** (Utilizes existing corporate developer laptops, engineering workstations, or on-premises servers).
   - **LLM Cognitive Reasoning**: **S$0.00 / month** (Runs local sovereign open-weight Llama 3.1 via Ollama with zero token subscription costs).
   - **Database & MCP IPC**: **S$0.00 / month** (Embedded SQLite database engine and local operating system stdio IPC).
   - **Total Monthly Operational Cost**: **S$0.00 (100% Free)**. Ideal for internal proof-of-concept evaluations, confidential audits, or air-gapped environments.

2. **Tier 2: Hybrid Local Application + Cloud LLM APIs (Option 2)**:
   - **Compute Infrastructure**: **S$0.00 / month** (Application web UI and FastMCP servers run on existing local workstations).
   - **LLM API Consumption**:
     - Average input tokens per comprehensive contractor screening: ~3,500 tokens (extracting BCA CRS workhead grade, 3-year balance sheets, MOM SDP safety logs, and draft subcontract clauses).
     - Average output tokens per audit report: ~800 tokens (forensic narrative, configurable PQM score breakdown, statutory debarment flags).
     - Blended API Cost per Evaluation:
       - **AWS Amazon Bedrock (Nova Pro)**: ~S$0.006 per contractor screening.
       - **Google Cloud Vertex AI (Gemini 2.5 Pro)**: ~S$0.012 per contractor screening.
       - **Azure OpenAI Service (GPT-4o)**: ~S$0.024 per contractor screening.
     - Assuming an active procurement department audits **100 contractor submissions per month**:
       - Total Monthly LLM Token Cost: **S$1.20 to S$2.40 / month**.

3. **Tier 3: Full Cloud-Native Serverless Production Deployment (Option 3)**:
   - **Serverless Container Compute (AWS ECS Fargate / Azure Container Apps / Google Cloud Run)**:
     - Configured with 0.5 vCPU and 1.0 GB RAM per container replica.
     - Utilizing automatic scale-to-zero during non-working hours (evenings and weekends), active compute runtime totals approximately 180 to 220 hours per month.
     - Estimated Compute Cost: **S$15.00 to S$28.00 / month**.
   - **Cloud Container Registry (ECR / ACR / Artifact Registry)**:
     - Hosting a 450 MB production container image: **S$0.50 to S$1.50 / month**.
   - **Ingress & Networking**:
     - Built-in HTTPS ingress on Azure Container Apps or Google Cloud Run: **S$0.00**.
     - AWS Application Load Balancer (ALB) if dedicated ingress is provisioned: ~**S$18.00 to S$22.00 / month**.
   - **Total Monthly Cloud Production Budget**: **S$35.00 to S$55.00 / month**.

4. **Return on Investment (ROI) & Cost-Benefit Analysis**:
   - **Traditional Manual Procurement Due Diligence**: Evaluating a multi-trade tender package across 5 to 10 main contractors requires 4 to 8 weeks of quantity surveyor time, amounting to **S$6,000 to S$15,000 in professional billable hours** per tender exercise.
   - **Agentic MCP Pipeline**: Delivers deterministic statutory scoring, financial ratio stress-testing, and SOPA clause analysis in **under 30 seconds**.
   - **Catastrophic Risk Avoidance**: In the September 2021 Greatearth Corporation liquidation (affecting 5 HDB BTO projects and 2,980 homeowners), the developer incurred tens of millions of dollars in delay remediation, replacement contractor premiums, and liquidated damages. Preventing a single unviable or safety-debarred contractor award yields immediate financial protection that vastly exceeds the nominal operational cost of this framework.

---

### <span id="q10"></span>🔹 **Q10: Why was Leptos WebAssembly chosen for the Quantity Surveyor frontend instead of traditional Python web frameworks like Streamlit?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: Streamlit operates on an execution paradigm of **full script re-execution**: whenever a user adjusts a UI widget (such as dragging a contingency or volatility slider), the Python interpreter executes the script from line 1 to the end. For high-frequency numerical updates:
1. **Network Round-Trip Serialization**: Streamlit converts every widget state change into Google Protobuf messages, sends them over a WebSocket connection to the Python server, re-evaluates the Python code, and re-renders React iframes. At update rates exceeding 5 Hz, this creates noticeable latency (150ms to 600ms) and UI stuttering.
2. **Iframe Re-creation & Memory Churn**: Plotly and Canvas elements in Streamlit are destroyed and re-mounted on reruns, causing screen flickering and heavy browser garbage collection sweeps.

In contrast, **Leptos (v0.6)** in `risk_dashboard_leptos/` compiles Rust source code into a native WebAssembly binary (`wasm32-unknown-unknown`) running inside the client browser V8/SpiderMonkey engine:
1. **Fine-Grained Reactive Graph**: Leptos uses SolidJS-inspired reactive signals (`create_signal`, `create_memo`). When a slider changes in `src/components/risk_slider.rs`, only the specific DOM attribute or Canvas SVG path element updates. The rest of the page remains untouched, with zero Virtual DOM diffing overhead.
2. **Hardware-Accelerated 60 to 120 FPS Rendering**: The SVG probability distribution curve in `src/components/monte_carlo_chart.rs` renders reactive probability density distribution curves with smooth 60 FPS feedback as sliders are dragged.
3. **Zero Schema Drift**: By using Rust on both the server (`risk_engine/src/main.rs`) and the client (`risk_dashboard_leptos/src/models.rs`), shared Serde data structures eliminate runtime JSON translation mismatches entirely.

---

### <span id="q11"></span>🔹 **Q11: Why does the AWS deployment URL require an explicit port (:8000), whereas the Azure and Google Cloud URLs are completely port-free over HTTPS?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: This behavioral difference stems from the architectural distinction between **Managed Serverless PaaS Edge Ingress** (Google Cloud Run and Microsoft Azure Container Apps) and **Infrastructure-as-a-Service (IaaS) Layer 7 Load Balancing** (AWS Application Load Balancer).

#### 1. Azure & GCP: Managed Edge Proxies with Automated TLS Termination (Port 443)
Both Azure Container Apps and Google Cloud Run are serverless container platforms featuring fully managed, multi-tenant edge reverse proxies:
- **Microsoft Azure Container Apps** (`terraform/azure/main.tf`):
  - Every Container App environment is fronted by an integrated Envoy edge proxy.
  - Microsoft automatically provisions and renews free, managed TLS certificates for all default `*.azurecontainerapps.io` endpoints.
  - The Envoy edge proxy listens on standard **HTTPS Port 443**. When an inbound request arrives, Envoy terminates the TLS handshake at the Microsoft edge and forwards internal layer 7 traffic to the container via `target_port = 8000` (lines 91-98 of `main.tf`).
- **Google Cloud Run** (`terraform/gcp/main.tf`):
  - Cloud Run services sit behind the global Google Front-End (GFE) edge network.
  - Google automatically issues and manages SSL/TLS certificates for all default `*.run.app` URLs.
  - The GFE edge listens on standard **HTTPS Port 443**, handles TLS termination, and routes the decrypted request across Google's internal software-defined network (Andromeda) to the container on `container_port = 8000` (lines 57-60 of `main.tf`).

Under RFC 7230 and RFC 3986 (URI Generic Syntax), **Port 443** is the globally standardized default port for the `https://` URI scheme. Consequently, all modern web browsers (Chrome, Safari, Edge, Firefox) automatically omit `:443` from the address bar, rendering a clean, port-free URL.

#### 2. AWS ALB: Turnkey Developer Zero-Friction Design vs. Custom Domain Constraints
In Amazon Web Services, an **Application Load Balancer (ALB)** is a dedicated, customer-managed IaaS resource provisioned inside your Virtual Private Cloud (VPC) across multiple public subnets:
- **AWS Certificate Manager (ACM) Limitation**: Unlike Azure and Google Cloud, AWS does **not** provide free, automated wildcard SSL certificates for default AWS-owned DNS hostnames (such as `*.elb.amazonaws.com`).
- **Prerequisites for Native HTTPS (Port 443) on AWS**: To serve HTTPS on Port 443 with a valid certificate, AWS strictly requires:
  1. A custom registered domain name (e.g. `pqq-compliance.com`).
  2. An Amazon Route 53 Public Hosted Zone.
  3. An ACM public certificate validated via DNS CNAME records.
- **Why Port 8000 was Configured in Terraform**:
  - To make this repository **100% turnkey, zero-cost, and instantly runnable** for any evaluator, student, or recruiter, the Terraform code must not demand ownership of a paid external domain name or Route 53 hosted zones.
  - In `terraform/aws/main.tf` (lines 102-111), the ALB Listener is provisioned as an unencrypted HTTP listener:
    ```hcl
    resource "aws_lb_listener" "listener" {
      load_balancer_arn = aws_lb.alb.arn
      port              = "8000"
      protocol          = "HTTP"

      default_action {
        type             = "forward"
        target_group_arn = aws_lb_target_group.target_group.arn
      }
    }
    ```
  - Port 8000 was selected because FastAPI defaults to port 8000 during local development (`agent_client/agent_api.py`), enabling direct port-to-port mapping across the ALB listener, target group, and ECS Fargate task container.
  - Because Port 8000 is non-standard (standard HTTP is Port 80; standard HTTPS is Port 443), browsers are required by the HTTP standard to explicitly append `:8000` to the address bar.

#### 3. How to Make AWS Port-Independent in Enterprise Production
In an enterprise production deployment on AWS:
1. Register a corporate domain or subdomain in Route 53 (e.g., `pqq.enterprise.gov.sg`).
2. Request a free public certificate from AWS Certificate Manager (ACM).
3. Update `terraform/aws/main.tf` to define an HTTPS listener on `port = 443` with `ssl_policy = "ELBSecurityPolicy-TLS13-1-2-2021-06"` and `certificate_arn = aws_acm_certificate.cert.arn`.
4. Add an HTTP listener on `port = 80` that issues a permanent `301 Moved Permanently` redirect to HTTPS.
5. Create a Route 53 `A-record` Alias pointing to `aws_lb.alb.dns_name`.
This aligns AWS with Azure and GCP, yielding a completely port-free `https://pqq.enterprise.gov.sg` URL.

---

### <span id="q12"></span>🔹 **Q12: What are the step-by-step mathematical formulas, statutory thresholds, and decision trees used in the What-If Stress Testing Cockpit?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: The What-If Stress Testing Cockpit implemented in `agent_client/agent_api.py` (FastAPI route `/what_if`, lines 2050 to 2145) executes a multi-dimensional statutory stress simulation combining Singapore public procurement mandates (BCA Price-Quality Method framework), occupational safety enforcement (MOM Workplace Safety and Health Act), contractual security standards (PSSCOC Performance Guarantee), and macroeconomic inflation shocks.

Below is the complete step-by-step mathematical derivation, statutory thresholds, and underlying decision logic:

#### Step 1: Tender Price Competitiveness & Abnormally Low Tender (ALT) Scoring Curve
The Price Competitiveness score evaluates the contractor submitted bid price against the Authority tender benchmark budget (`req.benchmark_sgd`).

Let:
- `B` = Submitted Bid Price in SGD (`req.bid_price_sgd`)
- `M` = Authority Tender Benchmark Budget in SGD (`req.benchmark_sgd`)

The tender price variance percentage `V` is computed as:
```text
V = ((B - M) / M) * 100.0
```

The Price Score (scale 0 to 100 points) is evaluated using a non-linear piecewise scoring function:
1. **Abnormally Low Tender (ALT) Regime (`V <= -20.0%`)**:
   Under BCA and Ministry of Finance (MOF) public procurement guidelines, tenders that undercut the government benchmark budget by more than 20% represent severe project abandonment, insolvency, or illegal subcontract exploitation risks. A steep penalty gradient is enforced:
   ```text
   Price_Score = max(0.0, 100.0 - abs(V + 20.0) * 4.0)
   ```
   For example, an aggressive bid at -25% discount receives:
   `100.0 - abs(-25.0 + 20.0) * 4.0 = 100.0 - (5.0 * 4.0) = 80.00 / 100`.

2. **Competitive Discount Regime (`-20.0% < V <= 0.0%`)**:
   Bids within 0% to 20% below the benchmark represent realistic market competition and earn near-maximum pricing marks:
   ```text
   Price_Score = 100.0 - abs(V) * 0.5
   ```
   For example, a standard tender bid of S$115,000,000 against a S$120,000,000 benchmark (`V = -4.17%`) receives:
   `100.0 - (4.1667 * 0.5) = 97.92 / 100`.

3. **Budget Overrun Regime (`V > 0.0%`)**:
   Bids that exceed the client benchmark budget are penalized at 3.0 points per 1% overrun:
   ```text
   Price_Score = max(0.0, 100.0 - V * 3.0)
   ```
   For example, a bid at +10% above budget receives:
   `100.0 - (10.0 * 3.0) = 70.00 / 100`.

#### Step 2: Multi-Attribute Quality Attributes Scoring
The Quality Score synthesizes audited historical contractor performance across four statutory pillars (scale 0 to 100 points):

1. **CONQUAS Quality Track Record (`q_conquas`, 40 points maximum)**:
   Extracts the audited Building and Construction Authority Construction Quality Assessment System (CONQUAS) score from the `track_record_conquas` table (defaults to 75.0 points if no prior public projects exist):
   ```text
   q_conquas = (CONQUAS_Score / 100.0) * 40.0
   ```

2. **On-Time Project Handover Track Record (`q_track`, 30 points maximum)**:
   Evaluates historical handover timeliness:
   ```text
   q_track = (On_Time_Completion_Pct / 100.0) * 30.0
   ```

3. **MOM Safety Demerits Deduction (`q_safety`, 20 points maximum)**:
   Penalizes accumulated safety infractions. Under the Singapore Workplace Safety and Health (WSH) Act, 25 Safety Demerit Points (SDP) is the statutory debarment ceiling:
   ```text
   SDP_Penalty = min(20.0, (Active_SDP / 25.0) * 20.0)
   q_safety = max(0.0, 20.0 - SDP_Penalty)
   ```
   - If a contractor has 0 SDP: `q_safety = 20.00`
   - If a contractor has 12.5 SDP: `q_safety = 10.00`
   - If a contractor has >= 25 SDP: `q_safety = 0.00`

4. **Design for Manufacturing and Assembly (DfMA) Innovation Pillar (`q_dfma`, 10 points maximum)**:
   Baseline statutory incentive for Prefabricated Prefinished Volumetric Construction (PPVC) and mass engineered timber adoption (`9.00` points).

**Total Quality Synthesis**:
```text
Quality_Score = q_conquas + q_track + q_safety + q_dfma
```

#### Step 3: Composite Price-Quality Method (PQM) Score
The final procurement ranking synthesizes Price and Quality using the parametric weight slider (`req.quality_weight`):

Let:
- `W_q` = Quality Weight (range 0.10 to 0.50, default 0.30)
- `W_p` = Price Weight = `1.0 - W_q` (default 0.70)

```text
Composite_PQM = (Price_Score * W_p) + (Quality_Score * W_q)
```

#### Step 4: MOM Safety Demerits & Debarment Decision Tree
Let `SDP_base` = Baseline SDP from `safety_compliance` table, and `Delta_SDP` = Injected Safety Demerit Shock:
```text
Active_SDP = SDP_base + Delta_SDP
```

**Decision Logic**:
- If `Active_SDP >= 25` OR `Debarred_Flag == 1`:
  - `Safety_Status = "DISQUALIFIED ({Active_SDP} SDP)"`
  - Legal Consequence: Immediate statutory block on hiring or renewing foreign work permits (Work Permit and S-Pass). Under BCA tender rules, the contractor is legally disqualified from public tender award.
- Else:
  - `Safety_Status = "Compliant ({Active_SDP} SDP)"`

#### Step 5: Macroeconomic Inflation Stress on Liquidity Current Ratio
Let:
- `CA` = Current Assets in SGD (from audited balance sheet)
- `CL` = Current Liabilities in SGD (from audited balance sheet)
- `Base_Current_Ratio = CA / CL`
- `CPI_Pct` = Injected Material Inflation / CPI Surge (%)

Inflation increases raw material procurement and labor overhead costs while receivables from progress claims remain locked in fixed-sum contracts, contracting liquid working capital:
```text
Adjusted_Current_Ratio = Base_Current_Ratio * (1.0 - (CPI_Pct / 100.0))
```
- **Statutory Threshold**: A Current Ratio below **1.20** triggers an alert for severe working capital insolvency. The card turns red/pink.

#### Step 6: 10% Performance Guarantee Bond Headroom & Bank Credit Facility Haircut
In Singapore construction procurement:
- **Why is the Bond Headroom standardized at 10%?**:
  Under **Clause 4.1 of the Singapore Public Sector Standard Conditions of Contract (PSSCOC)** for Construction Works, as well as the private sector **SIA Conditions of Building Contract** and **REDAS Design and Build Conditions**, the contractor is legally obligated to submit an on-demand Banker Guarantee / Performance Bond for exactly **10% of the Contract Sum** (or 5% for minor/maintenance tenders).
  ```text
  Required_Bond_SGD = Tender_Benchmark_SGD * 0.10
  ```
- **Can the Performance Bond percentage be 12% or other values?**:
  Yes. While 10% is the universal gold standard across Singapore public and private building tenders, certain specialized international EPC contracts (e.g. FIDIC Silver Book for power plants or mega petrochemical facilities) or higher-risk private developer agreements may specify **12%**, **15%**, or **20%** in the Particular Conditions of Contract.
- **Bank Credit Line Haircut**:
  During market downturns, commercial banks reduce credit facility headroom. Let `BG_Facility` = Approved bank credit line facility in SGD, and `Haircut_Pct` = Injected bank credit facility haircut (%):
  ```text
  Adjusted_Credit_Facility = BG_Facility * (1.0 - (Haircut_Pct / 100.0))
  ```
- **Bond Headroom Calculation**:
  ```text
  Bond_Headroom_SGD = Adjusted_Credit_Facility - Required_Bond_SGD
  ```
  - If `Bond_Headroom_SGD >= 0`: The contractor possesses sufficient uncommitted banking capacity to execute the required on-demand Performance Bond (Status: Compliant / Green).
  - If `Bond_Headroom_SGD < 0`: The contractor credit line is exhausted. The bank will refuse to issue the Performance Guarantee, leading to immediate contract termination and forfeiture of tender deposits (Status: Deficit / Red).

#### Step 7: Statutory SOPA Section 9 Clause Invalidation
When the Statutory SOPA Subcontract Clause is toggled:
- The engine injects a conditional Pay-When-Paid clause into the contract audit pipeline.
- Under **Section 9 of the Singapore Building and Construction Industry Security of Payment Act (SOPA)** and the landmark Court of Appeal judgment in Audi Construction Pte Ltd v Kian Hiap Construction Pte Ltd [2018] SGCA 4:
  - Any contractual provision making payment to a downstream subcontractor contingent upon the main contractor receiving payment from the Employer is rendered legally void ab initio.
  - The audit dossier immediately flags a `CRITICAL STATUTORY VIOLATION: SOPA SECTION 9 BREACH`, alerting the legal evaluation committee to excise the offending clause.

