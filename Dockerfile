FROM python:3.11-slim

# Install Node.js for MongoDB MCP Server
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-install mongodb-mcp-server so npx doesn't need to download at runtime
RUN npx -y mongodb-mcp-server --version || true

COPY . .
EXPOSE 8080
CMD ["python", "app.py"]
