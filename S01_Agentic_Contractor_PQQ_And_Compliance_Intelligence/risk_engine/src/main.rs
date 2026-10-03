use axum::{
    routing::{get, post},
    Json, Router,
};
use rand::prelude::*;
use rand_distr::{LogNormal, Normal};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use std::time::Instant;

#[derive(Debug, Deserialize)]
pub struct SimulationRequest {
    pub uen: String,
    pub tender_value_sgd: f64,
    #[serde(default = "default_iterations")]
    pub iterations: usize,
    #[serde(default = "default_working_capital")]
    pub available_working_capital_sgd: f64,
    #[serde(default = "default_credit_line")]
    pub available_credit_line_sgd: f64,
    #[serde(default = "default_lad_daily_rate")]
    pub lad_daily_rate_sgd: f64,
}

fn default_iterations() -> usize { 500_000 }
fn default_working_capital() -> f64 { 15_000_000.0 }
fn default_credit_line() -> f64 { 25_000_000.0 }
fn default_lad_daily_rate() -> f64 { 30_000.0 }

#[derive(Debug, Serialize)]
pub struct SimulationResponse {
    pub uen: String,
    pub iterations: usize,
    pub execution_time_ms: f64,
    pub tender_value_sgd: f64,
    pub var_95_sgd: f64,
    pub cvar_95_sgd: f64,
    pub max_loss_sgd: f64,
    pub default_probability_pct: f64,
    pub liquidity_cushion_sgd: f64,
    pub risk_rating: String,
    pub recommendation: String,
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let app = Router::new()
        .route("/health", get(health_check))
        .route("/simulate", post(handle_simulation));

    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    println!("🦀 Rust Axum Quantitative Risk Engine listening on http://{}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn health_check() -> &'static str {
    "OK: Axum Quantitative Risk Sidecar Active"
}

async fn handle_simulation(
    Json(payload): Json<SimulationRequest>,
) -> Json<SimulationResponse> {
    let start = Instant::now();
    let n = payload.iterations.clamp(1_000, 2_000_000);
    
    // Parameters for Singapore AEC context
    // Material cost baseline: ~40% of total contract (concrete ~18%, steel ~14%, finishes ~8%)
    let material_cost_baseline = payload.tender_value_sgd * 0.40;
    let total_liquidity_buffer = payload.available_working_capital_sgd + payload.available_credit_line_sgd;

    // Parallel Monte Carlo execution using Rayon
    let losses: Vec<f64> = (0..n)
        .into_par_iter()
        .map_init(rand::thread_rng, |rng, _| {
            // 1. Material price shock (Log-Normal: mu=0, sigma=0.09 ~ 9% annual volatility)
            let log_norm = LogNormal::new(0.0, 0.09).unwrap();
            let mat_shock: f64 = rng.sample(log_norm) - 1.0;
            let material_overrun = (material_cost_baseline * mat_shock).max(0.0);

            // 2. Weather & Monsoon delay shock (Normal: mean=18 days, std=8 days)
            let norm_delay = Normal::new(18.0, 8.0).unwrap();
            let sample_delay: f64 = rng.sample(norm_delay);
            let delay_days: f64 = sample_delay.max(0.0);
            let delay_overrun = delay_days * payload.lad_daily_rate_sgd;

            // 3. Subcontractor default supply chain friction (Bernoulli p=0.04)
            let sub_shock: f64 = if rng.gen_bool(0.04) {
                payload.tender_value_sgd * rng.gen_range(0.02..0.05)
            } else {
                0.0
            };

            material_overrun + delay_overrun + sub_shock
        })
        .collect();

    // Parallel Sort to compute percentiles using Rayon
    let mut sorted_losses = losses;
    sorted_losses.par_sort_unstable_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    let idx_95 = (n as f64 * 0.95) as usize;
    let var_95 = sorted_losses[idx_95];
    
    let tail_losses = &sorted_losses[idx_95..];
    let cvar_95 = tail_losses.iter().sum::<f64>() / (tail_losses.len() as f64);
    let max_loss = *sorted_losses.last().unwrap_or(&0.0);

    // Compute probability of liquidity exhaustion
    let default_count = sorted_losses.iter().filter(|&&l| l > total_liquidity_buffer).count();
    let default_prob_pct = (default_count as f64 / n as f64) * 100.0;
    let liquidity_cushion = total_liquidity_buffer - var_95;

    let elapsed = start.elapsed().as_secs_f64() * 1000.0;

    let (risk_rating, recommendation) = if default_prob_pct > 5.0 || liquidity_cushion < 0.0 {
        ("CRITICAL DEFAULT RISK", "Disqualify or mandate 15% cash-backed retention escrow")
    } else if default_prob_pct > 1.0 || liquidity_cushion < payload.tender_value_sgd * 0.05 {
        ("MODERATE VOLATILITY RISK", "Approved conditional on 10% On-Demand Performance Bond")
    } else {
        ("PRUDENT & LOW RISK", "Unconditional clearance for tender award")
    };

    Json(SimulationResponse {
        uen: payload.uen,
        iterations: n,
        execution_time_ms: (elapsed * 100.0).round() / 100.0,
        tender_value_sgd: payload.tender_value_sgd,
        var_95_sgd: (var_95 * 100.0).round() / 100.0,
        cvar_95_sgd: (cvar_95 * 100.0).round() / 100.0,
        max_loss_sgd: (max_loss * 100.0).round() / 100.0,
        default_probability_pct: (default_prob_pct * 100.0).round() / 100.0,
        liquidity_cushion_sgd: (liquidity_cushion * 100.0).round() / 100.0,
        risk_rating: risk_rating.to_string(),
        recommendation: recommendation.to_string(),
    })
}
