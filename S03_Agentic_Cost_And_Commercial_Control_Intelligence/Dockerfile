FROM python:3.11-slim

WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and data assets
COPY mcp_server/ ./mcp_server/
COPY agent_client/ ./agent_client/
COPY dashboard/ ./dashboard/
COPY data/ ./data/

# Default User-Defined Port (UDP)
ENV PORT=8086
EXPOSE 8086

# Healthcheck to verify dashboard server availability
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8086}/api/health || exit 1

# Start the Interactive Commercial Cockpit Server
CMD ["sh", "-c", "python3 dashboard/server.py --port ${PORT:-8086}"]
