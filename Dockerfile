FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Install git, curl, and GitHub CLI (gh) for automated repository creation
RUN apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates && \
    mkdir -p -m 755 /etc/apt/keyrings && \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /etc/apt/keyrings/githubcli-archive-keyring.gpg && \
    chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list && \
    apt-get update && apt-get install -y --no-install-recommends gh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install dependencies without pip cache to minimize container size
RUN pip install --no-cache-dir fastapi uvicorn google-antigravity

# Copy application files
COPY . .

# Install package
RUN pip install --no-cache-dir -e .

# Cloud Run default port
ENV PORT=8080

# Execute uvicorn server binding to 0.0.0.0 and dynamically resolving PORT
CMD exec uvicorn remote_code_agent.server:app --host 0.0.0.0 --port ${PORT:-8080}
