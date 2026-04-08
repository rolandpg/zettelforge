# ThreatRecall API Dockerfile
# Multi-stage build for production deployment

FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r threatrecall && useradd -r -g threatrecall threatrecall

# Copy installed packages from builder
COPY --from=builder /root/.local /home/threatrecall/.local
ENV PATH=/home/threatrecall/.local/bin:$PATH

# Copy application code
COPY src/ ./src/
COPY zettelforge/src/ ./zettelforge/src/
COPY run_dev.py .

# Set environment variables
ENV PYTHONPATH=/app/src:/app/zettelforge/src
ENV TR_DATA_DIR=/data/threatrecall
ENV TR_SECRETS_BACKEND=env
ENV TR_LOG_LEVEL=INFO

# Create data directory
RUN mkdir -p /data/threatrecall && chown -R threatrecall:threatrecall /data

# Switch to non-root user
USER threatrecall

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "threatrecall_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
