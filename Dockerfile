FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies without pip cache to minimize container size
RUN pip install --no-cache-dir fastapi uvicorn google-antigravity

# Copy application files
COPY . .

# Cloud Run default port
ENV PORT=8080

# Execute uvicorn server binding to 0.0.0.0 and dynamically resolving PORT
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
