# <span style="color:red">🦀 Quantitative Monte Carlo Risk Sidecar (Rust & Axum)</span>

High-performance quantitative risk microservice built in **Rust** using the **Axum** asynchronous web framework and **Rayon** data parallelism.

This sidecar provides the FastMCP server with sub-15 millisecond stochastic stress-testing capabilities, simulating 100,000 distinct project lifecycle iterations across material price spikes, Singapore monsoon weather extensions, and Liquidated Ascertained Damages (LAD) exposure.

## 📐 Mathematical Model & Stochastic Shocks

The quantitative engine models project cost overrun via three stochastic risk components:

```text
Total Loss = Material Overrun + Weather LAD Overrun + Subcontractor Default Loss
```

1. **Material Cost Escalation (Log-Normal Distribution)**:
   - Baseline Material Exposure: 40% of total contract value (Concrete ~18%, Steel ~14%, Architectural Finishes ~8%).
   - Stochastic Shock: `Shock ~ LogNormal(mu=0.0, sigma=0.09) - 1.0`.
   - `Material Overrun = max(0.0, Material Baseline * Shock)`.

2. **Weather Delay & Monsoon LAD Exposure (Normal Distribution)**:
   - Singapore Meteorological Service historical variance during Northeast and Southwest monsoon seasons.
   - Delay Days: `Delay ~ Normal(mean=18.0 days, std=8.0 days)`.
   - `LAD Overrun = Delay Days * Daily LAD Rate` (Benchmark: S$30,000/day on S$120M tender).

3. **Subcontractor Supply Chain Default (Bernoulli Jump Process)**:
   - Probability of critical trade subcontractor liquidation: `p = 0.04` (4% annual probability).
   - Impact Magnitude: Uniform random loss between 2% and 5% of total contract value for emergency re-mobilization.

4. **Risk Metrics Computed**:
   - **Value-at-Risk (VaR 95%)**: 95th percentile worst-case cost shock.
   - **Conditional VaR (CVaR 95%)**: Expected shortfall in the catastrophic 5% tail.
   - **Default Probability**: Percentage of 100,000 iterations where total losses exceed the contractor's combined working capital and uncommitted bank facilities.

## 🚀 Execution & Benchmarking

### Local Compilation (Native Cargo)
```bash
# Ensure you are at the project root before starting
cd risk_engine
cargo build --release
./target/release/risk_engine
```

### Dockerized Microservice
```bash
# Ensure you are at the project root before starting
docker build -t aec-risk-sidecar:latest risk_engine/
docker run -p 8080:8080 aec-risk-sidecar:latest
```

### API Endpoint Specification

- **Method**: `POST`
- **Path**: `/simulate`
- **Payload**:
```json
{
  "uen": "197600888B",
  "tender_value_sgd": 120000000.0,
  "iterations": 100000,
  "available_working_capital_sgd": 18500000.0,
  "available_credit_line_sgd": 28000000.0,
  "lad_daily_rate_sgd": 30000.0
}
```

- **Response (Sample Execution in 11.4 ms)**:
```json
{
  "uen": "197600888B",
  "iterations": 100000,
  "execution_time_ms": 11.42,
  "tender_value_sgd": 120000000.0,
  "var_95_sgd": 7241850.25,
  "cvar_95_sgd": 9812400.10,
  "max_loss_sgd": 16420500.00,
  "default_probability_pct": 0.02,
  "liquidity_cushion_sgd": 39258149.75,
  "risk_rating": "PRUDENT & LOW RISK",
  "recommendation": "Unconditional clearance for tender award"
}
```
