# Multi-stage Docker build for high-performance Rust Axum risk sidecar
FROM rust:1.85-alpine AS builder

WORKDIR /app
RUN apk add --no-cache musl-dev

COPY Cargo.toml Cargo.lock* ./
# Create dummy src to cache dependencies
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release || true

# Copy real source code
COPY src/ src/
RUN touch src/main.rs && cargo build --release

# Production minimal container
FROM alpine:3.20

WORKDIR /app
COPY --from=builder /app/target/release/risk_engine /app/risk_engine

EXPOSE 8080
CMD ["/app/risk_engine"]
