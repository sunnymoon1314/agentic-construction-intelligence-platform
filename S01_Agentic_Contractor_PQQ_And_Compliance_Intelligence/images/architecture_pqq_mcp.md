# Enterprise Contractor Pre-Qualification and Compliance MCP Framework Architecture

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
