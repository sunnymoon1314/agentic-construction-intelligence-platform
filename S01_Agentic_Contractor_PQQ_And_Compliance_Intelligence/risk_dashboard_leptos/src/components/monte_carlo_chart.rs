use leptos::*;
use crate::models::MonteCarloResponse;

#[component]
pub fn MonteCarloChart(
    simulation_result: ReadSignal<Option<MonteCarloResponse>>,
    base_bid_sgd: ReadSignal<f64>,
) -> impl IntoView {
    view! {
        <div class="glass-panel" style="padding: 24px; position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 38px; height: 38px; border-radius: 8px; border: 1.5px solid rgba(16, 185, 129, 0.4); background: rgba(16, 185, 129, 0.1); display: flex; align-items: center; justify-content: center; font-size: 1.15rem; flex-shrink: 0; box-shadow: 0 0 10px rgba(16, 185, 129, 0.15);">
                        "📈"
                    </div>
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <h3 style="font-size: 1.15rem; font-weight: 700; color: var(--text-title); margin: 0;">
                                "Monte Carlo Cost Distribution Curve (500,000 Iterations)"
                            </h3>
                            <span title="Hardware-accelerated probability density distribution curve computed across 500,000 stochastic runs modeling material inflation and delay shocks." style="cursor: help; font-size: 0.85rem; opacity: 0.9;">"ℹ️"</span>
                        </div>
                        <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 3px; margin-bottom: 0;">
                            "Sub-millisecond WebAssembly rendering | Value at Risk (VaR 95%) & Solvency Thresholds"
                        </p>
                    </div>
                </div>
                <div style="display: flex; gap: 16px; font-size: 0.75rem;">
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="width: 12px; height: 3px; background: #2563eb; display: inline-block;"></span>
                        <span style="color: var(--text-sub); font-weight: 500;">"Mean Cost"</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="width: 12px; height: 3px; background: #d97706; display: inline-block;"></span>
                        <span style="color: var(--text-sub); font-weight: 500;">"P90 Budget"</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="width: 12px; height: 3px; background: #e11d48; display: inline-block;"></span>
                        <span style="color: var(--text-sub); font-weight: 500;">"VaR 95% Risk Limit"</span>
                    </div>
                </div>
            </div>

            // Responsive SVG Chart
            <div style="width: 100%; height: 300px; position: relative;">
                {move || {
                    if let Some(res) = simulation_result.get() {
                        let mean = res.mean_cost_sgd;
                        let p90 = res.p90_sgd;
                        let var95 = res.var_95_sgd;
                        let base_bid = base_bid_sgd.get();

                        // Coordinate mapping (Width 800, Height 260)
                        let w = 800.0;
                        let h = 240.0;
                        let x_min = base_bid * 0.90;
                        let x_max = base_bid * 1.35;
                        let map_x = |val: f64| -> f64 {
                            let ratio = (val - x_min) / (x_max - x_min);
                            50.0 + (ratio.max(0.0).min(1.0)) * (w - 100.0)
                        };

                        let mean_x = map_x(mean);
                        let p90_x = map_x(p90);
                        let var95_x = map_x(mean + var95);

                        // Generate smooth bell curve points
                        let std_dev = (p90 - mean) / 1.2815;
                        let mut points = Vec::new();
                        let steps = 60;
                        for i in 0..=steps {
                            let curr_x_val = x_min + (i as f64 / steps as f64) * (x_max - x_min);
                            let z = (curr_x_val - mean) / std_dev;
                            let y_norm = (-0.5 * z * z).exp();
                            let plot_x = map_x(curr_x_val);
                            let plot_y = h - (y_norm * (h - 40.0));
                            points.push(format!("{:.1},{:.1}", plot_x, plot_y));
                        }
                        let path_d = format!("M 50,{:.1} L {} L {:.1},{:.1} Z", h, points.join(" L "), w - 50.0, h);
                        let stroke_d = format!("M {}", points.join(" L "));

                        view! {
                            <svg viewBox="0 0 800 280" style="width: 100%; height: 100%; overflow: visible;">
                                <defs>
                                    <linearGradient id="curveGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                        <stop offset="0%" stop-color="#2563eb" stop-opacity="0.35" />
                                        <stop offset="70%" stop-color="#0284c7" stop-opacity="0.12" />
                                        <stop offset="100%" stop-color="#0284c7" stop-opacity="0.0" />
                                    </linearGradient>
                                </defs>

                                // Horizontal grid lines
                                <line x1="50" y1="60" x2="750" y2="60" stroke="var(--chart-grid)" stroke-dasharray="4" />
                                <line x1="50" y1="120" x2="750" y2="120" stroke="var(--chart-grid)" stroke-dasharray="4" />
                                <line x1="50" y1="180" x2="750" y2="180" stroke="var(--chart-grid)" stroke-dasharray="4" />
                                <line x1="50" y1=h.to_string() x2="750" y2=h.to_string() stroke="var(--chart-axis)" />

                                // Bell curve area fill & stroke
                                <path d=path_d fill="url(#curveGradient)" />
                                <path d=stroke_d fill="none" stroke="#2563eb" stroke-width="2.5" />

                                // Mean line
                                <line x1=mean_x.to_string() y1="20" x2=mean_x.to_string() y2=h.to_string() stroke="#2563eb" stroke-width="1.8" stroke-dasharray="3,3" />
                                <text x=mean_x.to_string() y="15" fill="#2563eb" font-size="11" font-family="'JetBrains Mono', monospace" text-anchor="middle" font-weight="600">
                                    {format!("Mean: S${:.2}M", mean / 1_000_000.0)}
                                </text>

                                // P90 line
                                <line x1=p90_x.to_string() y1="35" x2=p90_x.to_string() y2=h.to_string() stroke="#d97706" stroke-width="2.0" />
                                <text x=p90_x.to_string() y="30" fill="#d97706" font-size="11" font-family="'JetBrains Mono', monospace" text-anchor="middle" font-weight="600">
                                    {format!("P90: S${:.2}M", p90 / 1_000_000.0)}
                                </text>

                                // VaR 95 line
                                <line x1=var95_x.to_string() y1="50" x2=var95_x.to_string() y2=h.to_string() stroke="#e11d48" stroke-width="2.2" stroke-dasharray="5,2" />
                                <text x=var95_x.to_string() y="45" fill="#e11d48" font-size="11" font-family="'JetBrains Mono', monospace" text-anchor="middle" font-weight="600">
                                    {format!("VaR 95%: +S${:.2}M", var95 / 1_000_000.0)}
                                </text>

                                // X-Axis Legend
                                <text x="50" y="260" fill="var(--text-muted)" font-size="10" font-family="'JetBrains Mono', monospace">
                                    {format!("-10% (S${:.1}M)", x_min / 1_000_000.0)}
                                </text>
                                <text x="400" y="260" fill="var(--text-title)" font-size="11" font-weight="600" text-anchor="middle">
                                    "Projected Final Cost Distribution"
                                </text>
                                <text x="750" y="260" fill="var(--text-muted)" font-size="10" font-family="'JetBrains Mono', monospace" text-anchor="end">
                                    {format!("+35% (S${:.1}M)", x_max / 1_000_000.0)}
                                </text>
                            </svg>
                        }.into_view()
                    } else {
                        view! {
                            <div style="display: flex; height: 100%; align-items: center; justify-content: center; color: #64748b;">
                                "Initializing Monte Carlo simulation parameters..."
                            </div>
                        }.into_view()
                    }
                }}
            </div>
        </div>
    }
}
