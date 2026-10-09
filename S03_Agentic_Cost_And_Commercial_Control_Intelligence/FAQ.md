# <span style="color:red">❓ 9. Frequently Asked Questions (FAQ)</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to TOC](README.md#toc)</span>

---

## <span id="faq-toc"></span>📑 Table Of Contents (TOC)

- [Q1: How does DuckDB's Dual-Mode Storage Adapter toggle between local storage and cloud object storage (s3://, gs://, azure://) via the httpfs extension?](#q1)
- [Q2: What is the statutory legal foundation and condition precedent mechanism of the PSSCOC Clause 19.1 28-day notice timebar?](#q2)
- [Q3: How does the Forensic VO Audit Engine detect Star Rate duplication fraud against the baseline Schedule of Rates (SOR)?](#q3)
- [Q4: How does openBIM IFC 5D quantity takeoff reconciliation detect physical over-certification under Singapore SOPA Section 15?](#q4)
- [Q5: What is the exact mathematical formulation for calculating Singapore SOPA Section 11 statutory payment response withholdings and MOM safety backcharges?](#q5)
- [Q6: How does the Statutory Deadline Clock compute SOPA Section 11 response deadlines omitting Sundays and Singapore gazetted public holidays?](#q6)
- [Q7: What is the mathematical formulation behind the Predictive EVM engine and the Risk-Adjusted Estimate at Completion (EAC) velocity radar?](#q7)
- [Q8: How does the multi-agent deliberation pipeline synthesize qualitative dispute narratives and executive briefing memos without hallucinating financial metrics?](#q8)

---

### <span id="q1"></span>🔹 **Q1: How does DuckDB's Dual-Mode Storage Adapter toggle between local storage and cloud object storage (s3://, gs://, azure://) via the httpfs extension?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: The storage decoupling engine implemented in `mcp_server/server.py` evaluates the `COMMERCIAL_LAKE_BUCKET` environment variable on every analytical query. When `COMMERCIAL_LAKE_BUCKET` is empty or unset, the system operates in Local Mode, reading from pre-partitioned Apache Parquet files in `data/parquet/*.parquet` or fallback local DuckDB tables in `data/commercial_control.duckdb`.

When `COMMERCIAL_LAKE_BUCKET` is configured with a cloud URI (such as `s3://acip-s03-commercial-lake-prod`, `gs://acip-s03-commercial-lake-prod`, or `azure://storageaccount.blob.core.windows.net/commercial-lake`), `get_connection()` dynamically executes `INSTALL httpfs; LOAD httpfs;` within the DuckDB C++ memory space. In Cloud Mode:
1. DuckDB's vectorized query engine executes byte-range HTTP GET requests directly against remote object storage blobs.
2. DuckDB fetches only the required column chunks and footer metadata without downloading whole files. For example, when querying `cost_forecast_eac.parquet`, only the 12 EVM metric columns are transferred into container memory.
3. This decouples the compute containers (AWS ECS Fargate, Azure Container Apps, Google Cloud Run) from persistent local storage. If a container crashes, the container restarts instantly without data loss, because the immutable analytical state is stored in cloud object storage.

---

### <span id="q2"></span>🔹 **Q2: What is the statutory legal foundation and condition precedent mechanism of the PSSCOC Clause 19.1 28-day notice timebar?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: Under the Public Sector Standard Conditions of Contract (PSSCOC 2020/2025 Edition), Clause 19.1 establishes that if the contractor intends to claim additional payment, a variation, or an extension of time resulting from an instruction of the Superintending Officer (SO), written notice of the claim must be served within **28 calendar days** of the date of the instruction.

In Singapore construction law, as affirmed in landmark Appellate Division jurisprudence, compliance with Clause 19.1 operates as a strict **condition precedent** to liability. In `mcp_server/server.py` inside `audit_variation_order`:
1. The engine computes `days_elapsed = (claim_notice_date - instruction_date).days`.
2. If `days_elapsed > 28`, the claim is classified as `TIMEBAR_EXPIRED_CLAIM_WAIVED`.
3. The valuation waterfall tier is overridden to `DISALLOWED_TIMEBAR`, the certified amount is set to S$0.00, and 100% of the claimed sum is deducted.
4. Itemizing this contractual timebar defense in the Section 11 Payment Response preserves the Employer's legal rights and prevents statutory waiver during subsequent adjudication before the Singapore Mediation Centre (SMC).

---

### <span id="q3"></span>🔹 **Q3: How does the Forensic VO Audit Engine detect Star Rate duplication fraud against the baseline Schedule of Rates (SOR)?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: In commercial contracting, contractors frequently attempt to claim baseline contract works under Tier 3 (Star Rates) or Tier 4 (Dayworks) at inflated ad-hoc rates (e.g. S$380/m3) instead of billing under the contract Schedule of Rates (SOR) baseline rate (e.g. S$240/m3).

To eliminate this pricing leakage, `audit_variation_order` executes an automated anti-fraud query against `schedule_of_rates.parquet`:
1. The tool searches for any existing baseline item code matching `claimed_item_code` within the project.
2. If a match is detected and the contractor has proposed a Tier 3 Star Rate or Tier 4 Daywork, the engine flags `RATE_DUPLICATION_DETECTED`.
3. The engine automatically rejects the contractor's proposed rate and enforces a mandatory fallback to `TIER_1_SOR`.
4. The deduction disallowed is computed as:
   `deduction_disallowed = contractor_claimed_amount - (quantity * contract_sor_rate)`
   For example, in VO-WHC-001, the contractor claimed S$380.00/m3 for concrete columns. The engine caught the duplication against baseline code `STR-02-004` (S$240.00/m3), enforced Tier 1 fallback, certified S$84,000.00, and disallowed S$49,000.00.

---

### <span id="q4"></span>🔹 **Q4: How does openBIM IFC 5D quantity takeoff reconciliation detect physical over-certification under Singapore SOPA Section 15?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: Section 15 of the Building and Construction Industry Security of Payment Act (SOPA) stipulates that the value of construction work carried out under a construction contract shall be determined by reference to the actual progress of the works. Contractors often engage in front-ramping by submitting percentage claims that exceed actual physical installation on site.

The `reconcile_progress_valuation` tool in `mcp_server/server.py` evaluates contractor claimed quantities against `ifc_openbim_verified_qty` derived from openBIM IFC 5D reality-capture models:
1. `discrepancy_qty = max(0.0, contractor_claimed_qty - ifc_openbim_verified_qty)`
2. `variance_pct = (discrepancy_qty / ifc_openbim_verified_qty) * 100.0`
3. If `variance_pct > 2.0%`, the item is flagged as `FLAGGED_OVER_CERTIFICATION` and `audit_action` is assigned `DISALLOW_UNINSTALLED_PORTION`.
4. The uninstalled volume is immediately deducted from the progress certificate:
   `disallowed_amount = discrepancy_qty * contract_unit_rate`
   For Claim No. 08 on Woodlands Health Campus, this physical takeoff reconciliation disallowed S$312,000.00 on concrete columns, S$226,300.00 on medical gas piping, and S$185,000.00 on centrifugal chillers, withholding a total of S$730,125.00 in uninstalled works.

---

### <span id="q5"></span>🔹 **Q5: What is the exact mathematical formulation for calculating Singapore SOPA Section 11 statutory payment response withholdings and MOM safety backcharges?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: The statutory response calculation executed by `generate_sopa_response` in `mcp_server/server.py` follows strict cumulative netting principles:

1. **Gross Valuation Netting**:
   `Verified_Gross_Cumulative = SUM(ifc_openbim_verified_amount)`
   `openBIM_Disallowance = SUM(contractor_claimed_amount) - Verified_Gross_Cumulative`

2. **Retention Cap Enforcement**:
   Under PSSCOC Clause 32, retention is withheld at 5% of certified gross until reaching the statutory retention ceiling (e.g. S$1,000,000.00 for WHC). Once accumulated retention reaches `retention_limit_sgd`, period retention deduction becomes S$0.00:
   `Period_Retention = 0.00 if Cumulative_Retention >= Retention_Limit else MIN(0.05 * Period_Gross, Remaining_Cap)`

3. **Ministry of Manpower (MOM) Safety Infractions Set-Off**:
   Indemnification set-offs are computed using three contractual formula tiers:
   - Stop-Work Order (SWO) Idle Charges: `swo_deduction = swo_idle_days * S$12,500.00/day`
   - Safety Demerit Points (SDP) Tier Charge: `sdp_deduction = demerit_points * S$1,500.00/point`
   - Unremediated Fines Markup: `fines_deduction = unremediated_fines * 1.15` (15% administrative markup)
   - Total Safety Set-Off: `total_safety_set_off = swo_deduction + sdp_deduction + fines_deduction`

4. **Net Certified Amount Payable**:
   `Net_Payable = Verified_Gross_Cumulative - Total_Safety_Set_Off - Period_Retention`

---

### <span id="q6"></span>🔹 **Q6: How does the Statutory Deadline Clock compute SOPA Section 11 response deadlines omitting Sundays and Singapore gazetted public holidays?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: Under Section 11(1) of the Building and Construction Industry Security of Payment Act (SOPA), the respondent must serve a payment response within the time specified by contract or within **14 calendar days** after the payment claim is served, whichever is earlier. Section 2 of the SOPA Act explicitly excludes Sundays and public holidays from the statutory day count.

The `serve_sopa_deadline_clock` tool in `mcp_server/server.py` interfaces with `data/calendar_engine.py` and `data/statutory_calendars.json`:
1. It parses `date_claim_served` (e.g. `2026-10-01`).
2. It increments day-by-day. For each day, if the day is a Sunday (weekday == 6) or matches a gazetted public holiday in `statutory_calendars.json` (such as Deepavali, Hari Raya Puasa, Christmas Day, or Chinese New Year), it is omitted from the statutory day count.
3. Once the statutory threshold (e.g. 14 business days) is reached, that exact calendar date is fixed as the statutory deadline (e.g. `2026-10-17`).
4. Real-time traffic-light scoring is assigned based on business days remaining:
   - Green (`LOW_STATUTORY_RISK`): > 7 business days remaining.
   - Amber (`MODERATE_STATUTORY_RISK`): 4 to 7 business days remaining.
   - Red (`CRITICAL_STATUTORY_RISK`): <= 3 business days remaining.

---

### <span id="q7"></span>🔹 **Q7: What is the mathematical formulation behind the Predictive EVM engine and the Risk-Adjusted Estimate at Completion (EAC) velocity radar?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: The predictive cost engine implemented in `get_predictive_eac` combines traditional Earned Value Management (EVM) with a monthly burn velocity risk scalar:

1. **EVM Performance Index**:
   `Cost_Performance_Index (CPI) = BCWP / ACWP`
   Where BCWP is Budgeted Cost of Work Performed (Earned Value) and ACWP is Actual Cost of Work Performed.

2. **Base Estimate at Completion (EAC)**:
   `Base_EAC = Budget_at_Completion (BAC) / CPI`

3. **Velocity-Sensitive Risk Multiplier**:
   If the monthly contingency burn velocity exceeds the healthy threshold of S$200,000.00/month, a velocity risk multiplier is applied:
   `risk_multiplier = 1.0 + (monthly_velocity / 1,000,000.00) * 0.10`
   `Risk_Adjusted_EAC = Base_EAC * risk_multiplier`

4. **Contingency Depletion and Breach Month Index**:
   `Months_Left = Remaining_Contingency / Monthly_Burn_Velocity`
   `Forecasted_Breach_Month = Current_Month_Index + ROUND(Months_Left)`
   For WHC Annex, with BAC of S$52.38M, BCWP of S$28.45M, and ACWP of S$30.15M (CPI = 0.9436), Base EAC is S$55.51M. Applying velocity scaling for S$231,250/mo burn results in Risk-Adjusted EAC of S$56.80M, projecting contingency exhaustion at Month 10 and a total budget overrun of S$1.80M.

---

### <span id="q8"></span>🔹 **Q8: How does the multi-agent deliberation pipeline synthesize qualitative dispute narratives and executive briefing memos without hallucinating financial metrics?** <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to FAQ TOC](#faq-toc)</span>

Answer: The multi-agent commercial pipeline in `agent_client/evaluator.py` establishes strict programmatic separation between mathematical computation and qualitative narrative generation:

1. **Deterministic Computation Precedence**:
   Neither LLMs nor probabilistic models compute financial balances, retention sums, or timebar day counts. All financial metrics are computed strictly by the FastMCP server tools (`reconcile_progress_valuation`, `audit_variation_order`, `generate_sopa_response`, `get_predictive_eac`).
2. **Context-Constrained Prompting**:
   The computed deterministic outputs (disallowed sums, expired timebars, CPI values, and statutory deadlines) are injected as immutable context variables into the deliberation roles:
   - **Forensic QS Auditor Agent**: Formulates technical reasons for disallowing uninstalled openBIM volumes.
   - **Contracts & Claims Counsel Agent**: Drafts formal legal objections under PSSCOC Clause 19.1 timebars and Clause 14 rate defense.
   - **Statutory Commercial Director Agent**: Synthesizes the formal Section 11 Payment Response dossier and executive briefing memo.
3. **Audit-Proof Reproducibility**:
   Every figure cited in the generated dispute narratives matches the exact penny of the Parquet lakehouse ledgers, ensuring the legal dossiers are admissible and defensible before adjudication tribunals.
