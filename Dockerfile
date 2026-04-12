FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml MANIFEST.in README.md LICENSE ./
COPY src/ src/

RUN pip install --no-cache-dir build \
    && python -m build --wheel \
    && pip install --no-cache-dir dist/*.whl

# ---------------------------------------------------------------------------
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app
COPY config.default.yaml ./

RUN useradd --create-home zettelforge
USER zettelforge

ENV ZETTELFORGE_BACKEND=jsonl \
    AMEM_DATA_DIR=/app/data

VOLUME ["/app/data"]

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "zettelforge.web:app", "--host", "0.0.0.0", "--port", "8000"]
