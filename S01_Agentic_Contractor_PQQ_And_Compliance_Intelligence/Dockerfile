FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY mcp_server/requirements.txt ./mcp_server/
COPY agent_client/requirements.txt ./agent_client/

# Install requirements
RUN pip install --no-cache-dir -r mcp_server/requirements.txt
RUN pip install --no-cache-dir -r agent_client/requirements.txt

# Copy source code
COPY mcp_server/ ./mcp_server/
COPY agent_client/ ./agent_client/
COPY demo_audit.py ./

# Generate the mock SQLite database inside the container
RUN python mcp_server/mock_data.py

# When using Stdio MCP, the agent script launches the server script itself.
EXPOSE 8000
CMD ["uvicorn", "agent_client.agent_api:app", "--host", "0.0.0.0", "--port", "8000"]
