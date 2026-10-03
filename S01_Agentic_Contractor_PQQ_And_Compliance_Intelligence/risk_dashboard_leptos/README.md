# <span style="color:red">🦀 Quantity Surveyor Leptos WebAssembly (WASM) Dashboard</span> <span style="font-size: 14px; font-weight: normal;">[⬆️ Back to Project 01B Main README](../README.md#toc)</span>

This directory contains the client-side **WebAssembly (WASM)** application built using **Leptos (v0.6)** for Project 01B. It serves as the real-time analytical terminal for Quantity Surveyors, Tender Evaluation Panels, and Procurement Directors conducting high-speed financial risk modeling.

---

## ⚡ 1. Why Leptos WASM Over Traditional Dashboards (Streamlit / React)

Traditional Python dashboards (such as Streamlit) rely on a full script re-execution model that stutters, drops frames, and queues up WebSocket messages when rendering fast simulation data.

| Metric | Traditional Python Dashboard (Streamlit) | Leptos WASM Terminal (`risk_dashboard_leptos`) |
| :--- | :--- | :--- |
| **Execution Engine** | Python server + React frontend bridge | Native WebAssembly compiled directly from Rust |
| **Reactivity Model** | Full script rerun on every slider movement | Fine-grained reactive signals (`create_signal`) |
| **Frame Latency** | 150ms -> 600ms network round-trip | **< 1ms client-side hardware-accelerated render** |
| **Max Update Frequency** | 2 to 5 Hz (flickering & iframe drops) | **60 to 120 Hz (smooth monitor refresh rate)** |
| **Memory Management** | Python GC sweeps + V8 JavaScript GC | **Deterministic compile-time RAII (Zero GC)** |
| **Type Integrity** | Dynamic Python dictionaries / JSON | **Exact shared Rust structs with Axum backend** |

---

## 🏗️ 2. Architectural Structure

```text
risk_dashboard_leptos/
├── Cargo.toml            # Dependencies: Leptos 0.6, wasm-bindgen, web-sys, Serde
├── Dockerfile            # Multi-stage build (Rust -> Trunk -> Nginx Alpine <10MB)
├── README.md             # Operational documentation
├── Trunk.toml            # Trunk WebAssembly bundler and dev server configuration
├── index.html            # Glassmorphic dark-theme HTML5 shell with Google Fonts
└── src/
    ├── app.rs            # Main reactive application shell and two-column layout
    ├── main.rs           # WebAssembly entrypoint mounting Leptos to DOM
    ├── models.rs         # Shared Rust structs (MonteCarloRequest, Response, RiskFactor)
    └── components/
        ├── adversarial_challenge.rs # Multi-agent duel & statutory scenario interactive viewer
        ├── audit_card.rs            # PQQ compliance badge, CONQUAS score, demerit limits
        ├── mod.rs                   # Component module exports
        ├── monte_carlo_chart.rs     # Reactive SVG bell curve, P90 line, VaR 95% threshold
        └── risk_slider.rs           # Zero-lag reactive slider component
```

---

## 🚀 3. Step-by-Step Execution Guide

### Option A: Run via Docker (Recommended, Zero Local Rust Toolchain Needed)

The multi-stage Docker build compiles the Rust WebAssembly bundle inside a container and serves the production artifacts via a lightweight Nginx container:

```bash
# Ensure you are at the project root before starting
docker build -t risk-dashboard-leptos risk_dashboard_leptos/
docker run -d -p 3000:80 --name leptos-dashboard-app risk-dashboard-leptos
```

Open your browser and navigate to:
```text
http://localhost:3000
```

To stop the container:
```bash
# Ensure you are at the project root before starting
docker stop leptos-dashboard-app && docker rm leptos-dashboard-app
```

---

### Option B: Run Locally with Trunk and Cargo

If you have Rust and Cargo installed:

1. **Install WebAssembly Target and Trunk**:
   ```bash
   rustup target add wasm32-unknown-unknown
   cargo install --locked trunk
   ```

2. **Launch the Development Server**:
   ```bash
   # Ensure you are at the project root before starting
   cd risk_dashboard_leptos
   trunk serve --port 3000 --open
   ```

Trunk will automatically compile the Rust code to `.wasm`, generate the JavaScript glue bindings, and hot-reload your browser whenever files in `src/` change.

---

## 🔬 4. Live Verification Checklist

1. **Preset Switching**: Click **Preset: Heng Win**, **Preset: Straits Civil**, and **Preset: Titan Piling**. Notice the instantaneous updates to the BCA Grade, CONQUAS score, and solvency ratings.
2. **Real-Time Sliders**: Drag the **Steel & Rebar Price Volatility** and **Foreign Labor Levy Escalation** sliders. Notice how the bell curve shifts and the **VaR 95% Risk Limit** updates smoothly at 60 FPS without screen flicker or reload lag.
3. **Forensic Risk Decomposition**: Observe the live breakdown of top risk drivers showing monetary exposure in S$ millions.
