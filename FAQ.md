# <span style="color:red">❓ 5. Frequently Asked Questions (FAQ)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](README.md#toc)</span>

This document addresses common architectural, statutory, deployment, and operational questions regarding the **Agentic Construction Intelligence Platform (ACIP)**.

---

## <span id="faq-toc"></span>📑 Table Of Contents (TOC)

- [Q1: What is the core purpose of ACIP, and is it intended as a commercial product?](#q1)
- [Q2: Where can I find the implementation guides, source code, and technical runbooks for modules S01 through S07?](#q2)
- [Q3: Does ACIP seek to replace existing enterprise systems like Procore, Autodesk Construction Cloud, or SAP?](#q3)
- [Q4: Why compile a quantitative engine in Rust instead of running risk simulations in Python, Go, or C++?](#q4)
- [Q5: How can ACIP support deployment architectures requiring strict data isolation?](#q5)
- [Q6: Who bears legal and statutory liability if an agentic recommendation contains an oversight or incorrect assessment?](#q6)
- [Q7: How does ACIP prevent generative AI hallucinations when evaluating strict Singapore statutory regulations (such as SOPA, MOM SDP, and BCA CW01 limits)?](#q7)
- [Q8: How does ACIP handle fractional lags in construction scheduling engines (S04), and why does it reject ceiling rounding rules in favour of Fractional Day Offsets and fail-closed guardrails?](#q8)
- [Q9: What is the current implementation scope of each module, and how are module handshakes governed across the lakehouse boundary?](#q9)

---

### <span id="q1"></span>🔹 **Q1: What is the core purpose of ACIP, and is it intended as a commercial product?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: ACIP is an open reference architecture and research Proof of Concept (POC), not a commercial product or proprietary vendor solution. It was developed to explore, architect, and demonstrate how the open Model Context Protocol (MCP), multi-agent cognitive reasoning, and deterministic quantitative computing can be practically applied to complex built-environment challenges. Its design goal is to provide transparent, reproducible architectural patterns that augment appropriately qualified and authorised human professionals—including licensed Qualified Persons (QPs), Professional Engineers (PEs), and professional Quantity Surveyors (QS)—rather than replace them with autonomous black-box systems.

---

### <span id="q2"></span>🔹 **Q2: Where can I find the implementation guides, source code, and technical runbooks for modules S01 through S07?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: S01 (Agentic Contractor PQQ & Compliance Intelligence), S02 (Agentic Bid Evaluation & Tender Intelligence), S03 (Agentic Cost & Commercial Control Intelligence), and S04 (Agentic Progress & Delay Intelligence) serve as fully active, complete production reference implementations with full source code, synthetic registries (SQLite in S01, DuckDB and Parquet lakehouses in S02, S03, and S04), FastMCP tool servers, interactive visual cockpits, and automated test suites (including 78 automated tests across 6 suites in S04). Modules S05 through S07 are planned on the progressive ACIP architectural roadmap with contractually pinned lakehouse handshakes already emitted by S04.

---

### <span id="q3"></span>🔹 **Q3: Does ACIP seek to replace existing enterprise systems like Procore, Autodesk Construction Cloud, or SAP?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: No. ACIP is architected as an intelligent reasoning and audit layer, not a transactional system of record. It is architected to interface with existing Common Data Environments (CDEs) and enterprise resource planning systems via standardized REST/JSON APIs and open Model Context Protocol (MCP) servers. Rather than duplicating existing project management data stores, ACIP is designed to ingest structured metadata and unstructured project correspondence across siloed systems (e.g. Primavera P6 schedule baselines, Autodesk Construction Cloud openBIM models, and SAP ERP commit ledgers) to execute automated cross-domain audit rules and decision-support reasoning.

---

### <span id="q4"></span>🔹 **Q4: Why compile a quantitative engine in Rust instead of running risk simulations in Python, Go, or C++?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: While Python is ideal for agentic orchestration and MCP JSON-RPC routing, running high-throughput Monte Carlo risk simulation across complex multi-variable cost and schedule models can encounter CPU-bound throughput bottlenecks in standard CPython runtimes due to the Global Interpreter Lock (GIL) and dynamic memory allocation overhead.

When evaluating compiled systems languages:
- **Why not Go?** While Go provides straightforward concurrency primitives (goroutines), its runtime relies on background garbage collection (GC). In high-iteration Monte Carlo risk simulations, periodic GC sweeps can introduce latency jitter that affects predictable real-time financial modeling.
- **Why not C++?** While C++ delivers raw computational speed, manual memory management and shared-memory concurrency across multithreaded simulation graphs require careful defensive engineering to prevent data races, dangling pointers, and memory-safety issues.
- **Why Rust?** Rust's strict compile-time ownership model and borrow checker enforce zero-cost memory safety without a tracing garbage collector. This enables high-throughput parallel execution with Rayon and compiler-assisted vectorisation while eliminating entire classes of concurrency data races. Simulations are structured for controlled numerical reproducibility using fixed pseudorandom seeds and deterministic reduction ordering.

The selection of Rust is not an assertion that Go or C++ cannot be used; rather, it reflects ACIP's design priorities around compile-time memory safety, predictable execution latency, and deterministic reduction ordering.

For environments where deploying a compiled native Rust binary is not feasible, a vectorized NumPy fallback implementation is also provided within the codebase.

---

### <span id="q5"></span>🔹 **Q5: How can ACIP support deployment architectures requiring strict data isolation?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: S01 demonstrates a local, offline deployment pattern that operates without external model APIs or application-level cloud data egress, utilizing local open-weight models (such as Llama 3.1 via Ollama), schema-defined MCP stdio IPC, and embedded SQLite. This pattern provides an architectural reference for sensitive workflows requiring on-premises execution. Whether an actual enterprise implementation satisfies a particular public-sector security classification (such as Restricted or Confidential) depends on the deploying organisation's complete infrastructure perimeter, including host hardening, network segmentation, identity and access management (IAM), audit logging, and formal security accreditation.

---

### <span id="q6"></span>🔹 **Q6: Who bears legal and statutory liability if an agentic recommendation contains an oversight or incorrect assessment?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: ACIP does not determine legal liability. The platform is designed as an audit-assist decision-support system in which final operational, commercial, and statutory decisions strictly remain with appropriately authorised human decision-makers and, where applicable, the relevant registered or licensed professionals. Any allocation of legal, commercial, or professional liability depends entirely upon the applicable statutory law, contractual risk allocations, professional duties of care, and the specific facts of the project or dispute. ACIP outputs do not constitute formal legal counsel or statutory engineering certifications.

---

### <span id="q7"></span>🔹 **Q7: How does ACIP prevent generative AI hallucinations when evaluating strict Singapore statutory regulations (such as SOPA, MOM SDP, and BCA CW01 limits)?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: Generative Large Language Models (LLMs) are strictly decoupled from authoritative calculations and statutory compliance decisions. Under ACIP's Deterministic Execution Boundary (Section 2.2), LLMs act solely as semantic parsers and intent planners; all LLM extraction outputs are treated as candidate hypotheses subject to deterministic validation and human review. All statutory rule evaluations—including BCA CW01 financial grade caps, Ministry of Manpower (MOM) 25 Safety Demerit Point debarment triggers, and SOPA Section 9 pay-when-paid unenforceability checks—are executed exclusively by deterministic Python and Rust code via schema-defined Model Context Protocol (MCP) tool interfaces. The model cannot alter formulas, invent thresholds, or directly update databases. Every finding generates an append-only, tamper-evident audit record with traceable evidence references linking the conclusion directly to the underlying statutory regulation and primary project data.

---

### <span id="q8"></span>🔹 **Q8: How does ACIP handle fractional lags in construction scheduling engines (S04), and why does it reject ceiling rounding rules in favour of Fractional Day Offsets and fail-closed guardrails?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: In compliance-heavy built-environment domains (governed by Primavera P6, NEC4, FIDIC, and Singapore PSSCOC conditions of contract), relationship lags frequently represent precise physical or statutory intervals such as concrete curing (e.g., 36 hours = 1.5 workdays) or statutory notice delivery windows. Handling these values requires strict industrial best practice:

1. **Rejection of the Ceiling Rule (Rounding Up)**:
Unilaterally rounding up fractional lags via a ceiling rule introduces artificial slack, distorts Total Float and Free Float, and can artificially extend critical path durations. In contractual or statutory timelines (such as curing periods or notice windows), unauthorized padding alters legal completion milestones, shifts the critical path, and distorts liquidated damages liability. Consequently, the ceiling rule is strictly rejected across ACIP S04.

2. **Fractional Day Offsets (Recommended Baseline)**:
Modern enterprise scheduling engines (Primavera P6, MS Project) calculate activity durations and relationship lags down to fractional hours or decimals. In ACIP S04, the recalculation engine located at `S04_Agentic_Progress_And_Delay_Intelligence/engine/cpm_recalculation_service.py` implements **Fractional Day Offsets** as its default baseline (`enforce_discrete_guardrail=False`). During topological forward and backward passes, the engine tracks continuous workday offsets (`es_offset`, `ef_offset`, `ls_offset`, `lf_offset`). This preserves mathematical fidelity, ensures exact float calculations without rounding drift, and prevents cascading schedule compression or inflation errors across the Directed Acyclic Graph (DAG).

3. **Fail-Closed Rejection (Recommended Guardrail)**:
Where a downstream consumer, project specification, or discrete-day contractual regime legally mandates integer-only boundaries, the engine activates a fail-closed guardrail (`enforce_discrete_guardrail=True`). Rather than applying silent rounding or heuristic truncation, the engine immediately raises `FractionalLagUnsupportedError`. This fail-closed behavior forces explicit upstream normalization (such as explicitly converting hours to full calendar shifts or contractually re-baselining lag definitions), completely eliminating silent rounding bugs that undermine legal defensibility in forensic delay analysis.

---

### <span id="q9"></span>🔹 **Q9: What is the current implementation scope of each module, and how are module handshakes governed across the lakehouse boundary?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: Current implementation scope by module:
1. **S01 (Contractor PQQ & Compliance Intelligence)**: Reference implementation featuring FastMCP statutory tools, SQLite synthetic registries, Rust Monte Carlo risk engine, and tri-cloud Terraform.
2. **S02 (Bid Evaluation & Tender Intelligence)**: Reference implementation featuring DuckDB multi-project store, FastMCP rate-leveling tools, and single-page executive cockpit on Port 8085.
3. **S03 (Cost & Commercial Control Intelligence)**: Reference implementation featuring 7 ZSTD Parquet lakehouse tables, 6 FastMCP statutory tools, 5D openBIM takeoff, and single-page executive cockpit on Port 8086.
4. **S04 (Progress & Delay Intelligence)**: Reference implementation featuring native Primavera P6 XER tabular parsing, CPM forward and backward recalculation over Directed Acyclic Graphs, controlled TIA fragnet simulation with float erosion analysis, tri-agent adversarial delay deliberation theater, and single-page executive cockpit on Port 8087. Validated across 78 automated test methods across 6 suites (Gate 2, Increments 1A, 1B, 2, 3, and 4) and 4 progressive deployment tiers.

Across the lakehouse boundary, S04 establishes strict downstream cross-module handshakes located at:
- `S04_Agentic_Progress_And_Delay_Intelligence/data/parquet/quality_inspection_schedule_links.parquet`: Maps Primavera P6 WBS nodes and activities to S05 Quality Inspection defect clusters and CONQUAS audit lots, enforcing composite foreign keys (`project_id`, `schedule_revision_id`, `activity_id`).
- `S04_Agentic_Progress_And_Delay_Intelligence/data/parquet/formal_claims_delay_links.parquet`: Maps critical-path schedule variance records to S06 SOPA Claims Triage and formal Extension of Time (EOT) heads of claim.
- **Cryptographic Manifests**: The emitter service (`engine/handshake_emitters.py`) computes SHA-256 sidecar hashes (`.sha256`) and manifest envelopes for every published table, enforcing atomic lakehouse publishing and fail-closed preflight integrity checks (`check_manifest()`).
