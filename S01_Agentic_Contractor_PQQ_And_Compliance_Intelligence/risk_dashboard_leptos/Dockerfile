# Stage 1: Build the Leptos WASM application with Trunk
FROM rust:bookworm AS builder

# Install WebAssembly target and Trunk build tool
RUN rustup target add wasm32-unknown-unknown && \
    cargo install --locked trunk

WORKDIR /app
COPY Cargo.toml Trunk.toml index.html ./
COPY src/ ./src/

# Compile the release WASM bundle
RUN trunk build --release

# Stage 2: Serve the compiled WebAssembly bundle with Nginx Alpine
FROM nginx:alpine

# Copy custom Nginx configuration with proper WASM MIME type support
RUN printf 'server {\n\
    listen 80;\n\
    server_name localhost;\n\
    location / {\n\
        root /usr/share/nginx/html;\n\
        index index.html;\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
    types {\n\
        application/wasm wasm;\n\
        text/html html;\n\
        text/css css;\n\
        application/javascript js;\n\
        application/json json;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
