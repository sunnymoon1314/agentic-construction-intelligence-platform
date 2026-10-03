use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[allow(dead_code)]
pub struct MonteCarloRequest {
    pub uen: String,
    pub tender_value_sgd: f64,
    pub iterations: usize,
    pub available_working_capital_sgd: f64,
    pub available_credit_line_sgd: f64,
    pub lad_daily_rate_sgd: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RiskFactor {
    pub name: String,
    pub impact_sgd: f64,
    pub probability: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MonteCarloResponse {
    pub uen: String,
    pub iterations: usize,
    pub mean_cost_sgd: f64,
    pub p50_sgd: f64,
    pub p90_sgd: f64,
    pub p99_sgd: f64,
    pub var_95_sgd: f64,
    pub probability_of_default: f64,
    pub execution_duration_ms: f64,
    pub top_risk_drivers: Vec<RiskFactor>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ContractorProfile {
    pub name: String,
    pub uen: String,
    pub bca_grade: String,
    pub conqas_score: f64,
    pub bizsafe_level: String,
    pub mom_demerit_points: u32,
    pub bid_amount_sgd: f64,
    pub working_capital_sgd: f64,
    pub credit_line_sgd: f64,
}
