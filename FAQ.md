# <span style="color:red">❓ 4. Frequently Asked Questions (FAQ)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](README.md#toc)</span>

This document addresses common architectural, statutory, deployment, and operational questions regarding the **Agentic Construction Intelligence Platform (ACIP)**.

---

🔹 **Q1: What is the core purpose of ACIP, and is it intended as a commercial product?**

Answer: ACIP is an open reference architecture and research Proof of Concept (POC), not a commercial product or proprietary vendor solution. It was developed to explore, architect, and demonstrate how the open Model Context Protocol (MCP), multi-agent cognitive reasoning, and deterministic quantitative computing can be practically applied to complex built-environment challenges. Its design goal is to provide transparent, reproducible architectural patterns that augment appropriately qualified and authorised human professionals—including licensed Qualified Persons (QPs), Professional Engineers (PEs), and professional Quantity Surveyors (QS)—rather than replace them with autonomous black-box systems.

---

🔹 **Q2: Where can I find the implementation guides, source code, and technical runbooks for modules S03 through S07?**

Answer: Modules S03 through S07 are planned on the progressive ACIP architectural roadmap. At present, S01 (Agentic Contractor PQQ & Compliance Intelligence) and S02 (Agentic Bid Evaluation & Tender Intelligence) serve as active, working reference implementations with complete source code, synthetic registries (SQLite in S01, DuckDB in S02), FastMCP tool servers, interactive visual cockpits, and automated test suites. The high-level architectural specifications and core problem statements for S03 through S07 are summarized in Section 3 of the Master README, while their underlying codebases, synthetic datasets, and technical runbooks will be developed, verified, and released sequentially.

---

🔹 **Q3: Does ACIP seek to replace existing enterprise systems like Procore, Autodesk Construction Cloud, or SAP?**

Answer: No. ACIP is architected as an intelligent reasoning and audit layer, not a transactional system of record. It is architected to interface with existing Common Data Environments (CDEs) and enterprise resource planning systems via standardized REST/JSON APIs and open Model Context Protocol (MCP) servers. Rather than duplicating existing project management data stores, ACIP is designed to ingest structured metadata and unstructured project correspondence across siloed systems (e.g. Primavera P6 schedule baselines, Autodesk Construction Cloud openBIM models, and SAP ERP commit ledgers) to execute automated cross-domain audit rules and decision-support reasoning.

---

🔹 **Q4: Why compile a quantitative engine in Rust instead of running risk simulations in Python, Go, or C++?**

Answer: While Python is ideal for agentic orchestration and MCP JSON-RPC routing, running high-throughput Monte Carlo risk simulation across complex multi-variable cost and schedule models can encounter CPU-bound throughput bottlenecks in standard CPython runtimes due to the Global Interpreter Lock (GIL) and dynamic memory allocation overhead.

When evaluating compiled systems languages:
- **Why not Go?** While Go provides straightforward concurrency primitives (goroutines), its runtime relies on background garbage collection (GC). In high-iteration Monte Carlo risk simulations, periodic GC sweeps can introduce latency jitter that affects predictable real-time financial modeling.
- **Why not C++?** While C++ delivers raw computational speed, manual memory management and shared-memory concurrency across multithreaded simulation graphs require careful defensive engineering to prevent data races, dangling pointers, and memory-safety issues.
- **Why Rust?** Rust's strict compile-time ownership model and borrow checker enforce zero-cost memory safety without a tracing garbage collector. This enables high-throughput parallel execution with Rayon and compiler-assisted vectorisation while eliminating entire classes of concurrency data races. Simulations are structured for controlled numerical reproducibility using fixed pseudorandom seeds and deterministic reduction ordering.

The selection of Rust is not an assertion that Go or C++ cannot be used; rather, it reflects ACIP's design priorities around compile-time memory safety, predictable execution latency, and deterministic reduction ordering.

For environments where deploying a compiled native Rust binary is not feasible, a vectorized NumPy fallback implementation is also provided within the codebase.

---

🔹 **Q5: How can ACIP support deployment architectures requiring strict data isolation?**

Answer: S01 demonstrates a local, offline deployment pattern that operates without external model APIs or application-level cloud data egress, utilizing local open-weight models (such as Llama 3.1 via Ollama), schema-defined MCP stdio IPC, and embedded SQLite. This pattern provides an architectural reference for sensitive workflows requiring on-premises execution. Whether an actual enterprise implementation satisfies a particular public-sector security classification (such as Restricted or Confidential) depends on the deploying organisation's complete infrastructure perimeter, including host hardening, network segmentation, identity and access management (IAM), audit logging, and formal security accreditation.

---

🔹 **Q6: Who bears legal and statutory liability if an agentic recommendation contains an oversight or incorrect assessment?**

Answer: ACIP does not determine legal liability. The platform is designed as an audit-assist decision-support system in which final operational, commercial, and statutory decisions strictly remain with appropriately authorised human decision-makers and, where applicable, the relevant registered or licensed professionals. Any allocation of legal, commercial, or professional liability depends entirely upon the applicable statutory law, contractual risk allocations, professional duties of care, and the specific facts of the project or dispute. ACIP outputs do not constitute formal legal counsel or statutory engineering certifications.

---

🔹 **Q7: How does ACIP prevent generative AI hallucinations when evaluating strict Singapore statutory regulations (such as SOPA, MOM SDP, and BCA CW01 limits)?**

Answer: Generative Large Language Models (LLMs) are strictly decoupled from authoritative calculations and statutory compliance decisions. Under ACIP's Deterministic Execution Boundary (Section 2.2), LLMs act solely as semantic parsers and intent planners; all LLM extraction outputs are treated as candidate hypotheses subject to deterministic validation and human review. All statutory rule evaluations—including BCA CW01 financial grade caps, Ministry of Manpower (MOM) 25 Safety Demerit Point debarment triggers, and SOPA Section 9 pay-when-paid unenforceability checks—are executed exclusively by deterministic Python and Rust code via schema-defined Model Context Protocol (MCP) tool interfaces. The model cannot alter formulas, invent thresholds, or directly update databases. Every finding generates an append-only, tamper-evident audit record with traceable evidence references linking the conclusion directly to the underlying statutory regulation and primary project data.
