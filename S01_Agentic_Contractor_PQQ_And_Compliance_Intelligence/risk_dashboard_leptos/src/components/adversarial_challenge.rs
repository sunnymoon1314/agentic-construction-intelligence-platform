use leptos::*;

#[component]
pub fn AdversarialChallenge() -> impl IntoView {
    // 0: Adversarial Duel, 1: Heng Win, 2: Titan Piling, 3: Starlight Urban, 4: SOPA Section 9
    let (active_tab, set_active_tab) = create_signal(0usize);

    view! {
        <div class="glass-panel" style="padding: 24px; margin-top: 24px;">
            // Section Header
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border-glass);">
                <div>
                    <h3 style="font-size: 1.25rem; font-weight: 700; color: var(--text-title); display: flex; align-items: center; gap: 10px;">
                        <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #7c3aed; box-shadow: 0 0 10px #7c3aed;"></span>
                        "Multi-Agent Adversarial Challenge & Statutory Scenario Audits"
                    </h3>
                    <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">
                        "LangGraph Multi-Agent Duel (Evaluator vs Devil's Advocate) & Singapore Statutory Challenge Scenarios"
                    </p>
                </div>
                <span style="font-size: 0.75rem; font-weight: 600; padding: 4px 10px; border-radius: 6px; background: rgba(124, 58, 237, 0.12); color: #7c3aed; border: 1px solid rgba(124, 58, 237, 0.25);">
                    "Unified MCP + Rust UI"
                </span>
            </div>

            // Interactive Tab Navigation Bar
            <div style="display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap;">
                <button
                    on:click=move |_| set_active_tab.set(0)
                    style=move || {
                        if active_tab.get() == 0 {
                            "background: #2563eb; color: #ffffff; border: 1px solid #3b82f6; padding: 8px 16px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; cursor: pointer; box-shadow: 0 2px 6px rgba(37,99,235,0.2);"
                        } else {
                            "background: var(--tab-unselected-bg); color: var(--tab-unselected-text); border: 1px solid var(--tab-unselected-border); padding: 8px 16px; border-radius: 8px; font-size: 0.8rem; font-weight: 500; cursor: pointer;"
                        }
                    }
                >
                    "⚔️ Multi-Agent Adversarial Duel"
                </button>

                <button
                    on:click=move |_| set_active_tab.set(1)
                    style=move || {
                        if active_tab.get() == 1 {
                            "background: #059669; color: #ffffff; border: 1px solid #10b981; padding: 8px 16px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; cursor: pointer; box-shadow: 0 2px 6px rgba(5,150,105,0.2);"
                        } else {
                            "background: var(--tab-unselected-bg); color: var(--tab-unselected-text); border: 1px solid var(--tab-unselected-border); padding: 8px 16px; border-radius: 8px; font-size: 0.8rem; font-weight: 500; cursor: pointer;"
                        }
                    }
                >
                    "🏢 Scenario 1: Heng Win (Benchmark)"
                </button>

                <button
                    on:click=move |_| set_active_tab.set(2)
                    style=move || {
                        if active_tab.get() == 2 {
                            "background: #e11d48; color: #ffffff; border: 1px solid #f43f5e; padding: 8px 16px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; cursor: pointer; box-shadow: 0 2px 6px rgba(225,29,72,0.2);"
                        } else {
                            "background: var(--tab-unselected-bg); color: var(--tab-unselected-text); border: 1px solid var(--tab-unselected-border); padding: 8px 16px; border-radius: 8px; font-size: 0.8rem; font-weight: 500; cursor: pointer;"
                        }
                    }
                >
                    "⚠️ Scenario 2: Titan Piling (MOM Bar)"
                </button>

                <button
                    on:click=move |_| set_active_tab.set(3)
                    style=move || {
                        if active_tab.get() == 3 {
                            "background: #d97706; color: #ffffff; border: 1px solid #f59e0b; padding: 8px 16px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; cursor: pointer; box-shadow: 0 2px 6px rgba(217,119,6,0.2);"
                        } else {
                            "background: var(--tab-unselected-bg); color: var(--tab-unselected-text); border: 1px solid var(--tab-unselected-border); padding: 8px 16px; border-radius: 8px; font-size: 0.8rem; font-weight: 500; cursor: pointer;"
                        }
                    }
                >
                    "📉 Scenario 3: Starlight (Greatearth Collapse)"
                </button>

                <button
                    on:click=move |_| set_active_tab.set(4)
                    style=move || {
                        if active_tab.get() == 4 {
                            "background: #7c3aed; color: #ffffff; border: 1px solid #8b5cf6; padding: 8px 16px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; cursor: pointer; box-shadow: 0 2px 6px rgba(124,58,237,0.2);"
                        } else {
                            "background: var(--tab-unselected-bg); color: var(--tab-unselected-text); border: 1px solid var(--tab-unselected-border); padding: 8px 16px; border-radius: 8px; font-size: 0.8rem; font-weight: 500; cursor: pointer;"
                        }
                    }
                >
                    "⚖️ Scenario 4: SOPA Sec 9 (Void Clause)"
                </button>
            </div>

            // Dynamic Content Rendering Based on Active Tab
            {move || match active_tab.get() {
                // Tab 0: Adversarial Duel Transcript
                0 => view! {
                    <div style="display: flex; flex-direction: column; gap: 16px;">
                        // Step 1: Evaluator Agent
                        <div style="background: var(--bg-inner); border-left: 4px solid #2563eb; padding: 16px; border-radius: 0 10px 10px 0; border: 1px solid var(--bg-inner-border); border-left-width: 4px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-size: 0.8rem; font-weight: 700; color: #2563eb; text-transform: uppercase;">
                                    "🔷 [TENDER EVALUATOR AGENT] (LangGraph / Frontier LLM)"
                                </span>
                                <span style="font-size: 0.7rem; color: var(--text-muted);">"Step 1: Preliminary Review"</span>
                            </div>
                            <p style="font-size: 0.85rem; color: var(--text-main); line-height: 1.5;">
                                "Straits Civil Engineering Pte Ltd submits a highly competitive bid of S$85,000,000 for the Commercial Superstructure Package. Holds active BCA CW01 Grade A1 with unlimited tendering limits. Historical CONQUAS average score is outstanding at 88.2. Total audited net worth stands at S$22,450,000 against a paid-up capital of S$18,000,000. bizSAFE STAR certification is active. Preliminary Verdict: RECOMMEND AWARD with a total PQM score of 84.5 / 100."
                            </p>
                        </div>

                        // Step 2: Devil's Advocate Agent
                        <div style="background: var(--bg-inner); border-left: 4px solid #e11d48; padding: 16px; border-radius: 0 10px 10px 0; border: 1px solid var(--bg-inner-border); border-left-width: 4px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-size: 0.8rem; font-weight: 700; color: #e11d48; text-transform: uppercase;">
                                    "🔺 [DEVIL'S ADVOCATE RISK AGENT - FORENSIC OBJECTION]"
                                </span>
                                <span style="font-size: 0.7rem; color: var(--text-muted);">"Step 2: Statutory Cross-Reference"</span>
                            </div>
                            <p style="font-size: 0.85rem; color: var(--text-main); line-height: 1.5;">
                                "Objection raised. The Evaluator Agent is relying on lagging historical metrics. A granular audit of current balance sheets and statutory records reveals critical warning flags: (1) MOM Safety Risk: Contractor accumulated 14 Safety Demerit Points within the last 9 months, only 11 points away from the 25-point threshold that triggers a mandatory foreign manpower freeze. (2) Working Capital Deterioration: Current Assets include S$14.2M in disputed trade receivables. Quick Ratio is 0.94 (below the 1.0 statutory solvency cutoff). (3) Concurrent Over-Commitment: Contractor is executing two active LTA rail packages totaling S$180M."
                            </p>
                        </div>

                        // Step 3: Rust Risk Sidecar Execution
                        <div style="background: var(--bg-inner); border-left: 4px solid #7c3aed; padding: 16px; border-radius: 0 10px 10px 0; border: 1px solid var(--bg-inner-border); border-left-width: 4px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-size: 0.8rem; font-weight: 700; color: #7c3aed; text-transform: uppercase;">
                                    "🦀 [RUST RISK SIDECAR - AXUM + RAYON SIMD MONTE CARLO]"
                                </span>
                                <span style="font-size: 0.7rem; color: #059669; font-family: 'JetBrains Mono', monospace; font-weight: 600;">
                                    "Completed 100,000 Iterations in 11.84ms"
                                </span>
                            </div>
                            <p style="font-size: 0.85rem; color: var(--text-main); line-height: 1.5;">
                                "Cash-Flow Stress Test Shock Parameters: Starting cash S$12.5M, Material escalation +15%, Subcontractor payment delay 60-90 days. Simulation Output: Insolvency Probability = 27.84%. Value-at-Risk (95% confidence) indicates cash-flow deficit of -S$4.12M by Month 7."
                            </p>
                        </div>

                        // Step 4: Revised Arbitration Verdict
                        <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); padding: 16px; border-radius: 10px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-size: 0.85rem; font-weight: 700; color: #059669; text-transform: uppercase;">
                                    "⚖️ [ARBITRATION BOARD VERDICT: CONDITIONAL SHORTLIST]"
                                </span>
                                <span style="font-size: 0.75rem; color: #059669; font-weight: 600;">"Defensible Committee Decision"</span>
                            </div>
                            <p style="font-size: 0.85rem; color: var(--text-main); line-height: 1.5;">
                                "Challenge accepted. In light of the Rust sidecar liquidity findings and the 14 active MOM demerit points, the contractor cannot be recommended for unconditional award. Revised Verdict: CONDITIONAL SHORTLIST with mandatory statutory protections: (1) S$4.5M supplementary cash escrow deposit before award letter signing, (2) Bi-weekly MOM safety officer site audits, and (3) Direct employer disbursements to key structural subcontractors."
                            </p>
                        </div>
                    </div>
                }.into_view(),

                // Tab 1: Heng Win Benchmark
                1 => view! {
                    <div style="background: var(--bg-inner); padding: 20px; border-radius: 10px; border: 1px solid rgba(16, 185, 129, 0.3);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <h4 style="font-size: 1.05rem; font-weight: 700; color: #059669;">
                                "Scenario 1: Heng Win (Private) Limited — PQQ Benchmark"
                            </h4>
                            <span style="background: rgba(16, 185, 129, 0.15); color: #059669; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(16, 185, 129, 0.3);">
                                "VERDICT: RECOMMEND AWARD"
                            </span>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; font-size: 0.8rem;">
                            <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 10px; border-radius: 6px;">
                                <div style="color: var(--text-muted);">"BCA Registration"</div>
                                <div style="color: var(--text-title); font-weight: 600; margin-top: 2px;">"CW01 - Grade A1 (Unlimited)"</div>
                            </div>
                            <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 10px; border-radius: 6px;">
                                <div style="color: var(--text-muted);">"MOM Demerits"</div>
                                <div style="color: #059669; font-weight: 600; margin-top: 2px;">"0 Points (Clean Record)"</div>
                            </div>
                            <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 10px; border-radius: 6px;">
                                <div style="color: var(--text-muted);">"CONQUAS Quality"</div>
                                <div style="color: #0284c7; font-weight: 600; margin-top: 2px;">"92.4 / 100 (Tier 1 Top 5%)"</div>
                            </div>
                        </div>
                        <p style="font-size: 0.85rem; color: var(--text-main); line-height: 1.5;">
                            "Autonomous MCP statutory verification confirms zero safety violations under the MOM Workplace Safety and Health Act. Dual-envelope evaluation yields a Singapore Price-Quality Method (PQM) score of 88.5/100 against the S$120M benchmark. All financial liquidity ratios exceed statutory minimums (Current Ratio: 1.45, Quick Ratio: 1.20)."
                        </p>
                    </div>
                }.into_view(),

                // Tab 2: Titan Piling Safety Bar
                2 => view! {
                    <div style="background: var(--bg-inner); padding: 20px; border-radius: 10px; border: 1px solid rgba(244, 63, 94, 0.3);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <h4 style="font-size: 1.05rem; font-weight: 700; color: #e11d48;">
                                "Scenario 2: Titan Piling & Civil Engineering — MOM Safety Demerit Trap"
                            </h4>
                            <span style="background: rgba(244, 63, 94, 0.15); color: #e11d48; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(244, 63, 94, 0.3);">
                                "VERDICT: STATUTORY DISQUALIFICATION"
                            </span>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; font-size: 0.8rem;">
                            <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 10px; border-radius: 6px;">
                                <div style="color: var(--text-muted);">"MOM Safety Demerits"</div>
                                <div style="color: #e11d48; font-weight: 700; margin-top: 2px;">"28 Points (Debarment Threshold: 25)"</div>
                            </div>
                            <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 10px; border-radius: 6px;">
                                <div style="color: var(--text-muted);">"Statutory Consequence"</div>
                                <div style="color: #e11d48; font-weight: 600; margin-top: 2px;">"Mandatory Foreign Manpower Ban"</div>
                            </div>
                            <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 10px; border-radius: 6px;">
                                <div style="color: var(--text-muted);">"Project Impact"</div>
                                <div style="color: #d97706; font-weight: 600; margin-top: 2px;">"Immediate S$30,000/day LAD Delay"</div>
                            </div>
                        </div>
                        <p style="font-size: 0.85rem; color: var(--text-main); line-height: 1.5;">
                            "The contractor holds 28 active demerit points, breaching the statutory 25-point threshold under the Singapore MOM Demerit Points System. Under WSH regulations, the contractor is barred from applying for or renewing foreign worker work permits for 3 months. Awarding this tender would immediately trigger site paralysis and Liquidated Damages."
                        </p>
                    </div>
                }.into_view(),

                // Tab 3: Starlight Urban Greatearth Collapse
                3 => view! {
                    <div style="background: var(--bg-inner); padding: 20px; border-radius: 10px; border: 1px solid rgba(245, 158, 11, 0.3);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <h4 style="font-size: 1.05rem; font-weight: 700; color: #d97706;">
                                "Scenario 3: Starlight Urban Infrastructure — Greatearth Insolvency Precedent"
                            </h4>
                            <span style="background: rgba(245, 158, 11, 0.15); color: #d97706; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(245, 158, 11, 0.3);">
                                "VERDICT: FINANCIAL INSOLVENCY (FAIL)"
                            </span>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; font-size: 0.8rem;">
                            <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 10px; border-radius: 6px;">
                                <div style="color: var(--text-muted);">"Current Ratio"</div>
                                <div style="color: #e11d48; font-weight: 700; margin-top: 2px;">"0.88 (< 1.20 Minimum Cutoff)"</div>
                            </div>
                            <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 10px; border-radius: 6px;">
                                <div style="color: var(--text-muted);">"Quick Ratio (Acid-Test)"</div>
                                <div style="color: #e11d48; font-weight: 700; margin-top: 2px;">"0.62 (< 1.00 Severe Cash Drain)"</div>
                            </div>
                            <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 10px; border-radius: 6px;">
                                <div style="color: var(--text-muted);">"10% Performance Bond"</div>
                                <div style="color: #d97706; font-weight: 700; margin-top: 2px;">"S$1.50M Bank Line Deficit"</div>
                            </div>
                        </div>
                        <p style="font-size: 0.85rem; color: var(--text-main); line-height: 1.5;">
                            "Audited financial stress testing reveals symptoms identical to the September 2021 Greatearth Corporation 5-BTO default: acute working capital deficit, excessive gearing (Debt-to-Equity: 2.85), and uncommitted bank bonding capacity falling S$1.5M short of the mandatory 10% Banker's Guarantee required by BCA."
                        </p>
                    </div>
                }.into_view(),

                // Tab 4: SOPA Section 9
                4 => view! {
                    <div style="background: var(--bg-inner); padding: 20px; border-radius: 10px; border: 1px solid rgba(139, 92, 246, 0.3);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <h4 style="font-size: 1.05rem; font-weight: 700; color: #7c3aed;">
                                "Scenario 4: Trade Subcontract Clause 14 — SOPA Section 9 Pay-When-Paid Ambush"
                            </h4>
                            <span style="background: rgba(139, 92, 246, 0.15); color: #7c3aed; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(139, 92, 246, 0.3);">
                                "VERDICT: STATUTORILY VOID BY LAW"
                            </span>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; font-size: 0.8rem;">
                            <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 10px; border-radius: 6px;">
                                <div style="color: var(--text-muted);">"Audited Contract Clause"</div>
                                <div style="color: var(--text-title); font-weight: 600; margin-top: 2px;">"Subcontractor paid 14 days AFTER Main Contractor is paid"</div>
                            </div>
                            <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 10px; border-radius: 6px;">
                                <div style="color: var(--text-muted);">"Governing Singapore Law"</div>
                                <div style="color: #7c3aed; font-weight: 600; margin-top: 2px;">"SOPA 2004 Section 9(1)"</div>
                            </div>
                            <div style="background: var(--bg-card); border: 1px solid var(--border-glass); padding: 10px; border-radius: 6px;">
                                <div style="color: var(--text-muted);">"Judicial Precedent"</div>
                                <div style="color: #0284c7; font-weight: 600; margin-top: 2px;">"Audi Construction v Kian Hiap [2018] SGCA 4"</div>
                            </div>
                        </div>
                        <p style="font-size: 0.85rem; color: var(--text-main); line-height: 1.5;">
                            "Section 9(1) of the Building and Construction Industry Security of Payment Act explicitly renders every Pay-When-Paid provision unenforceable, void, and of no legal effect. Relying on this clause in Singapore courts or statutory adjudication will result in immediate summary enforcement by unpaid subcontractors."
                        </p>
                    </div>
                }.into_view(),

                _ => view! { <div></div> }.into_view(),
            }}
        </div>
    }
}
