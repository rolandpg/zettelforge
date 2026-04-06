FROM python:3.10-slim-buster

# System dependencies for LanceDB / Numpy / PyArrow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy dependencies
# (We assume requirements.txt will be generated or we just install amem)
COPY requirements.txt .
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Install fastapi and uvicorn directly for the API layer
RUN pip install --no-cache-dir fastapi uvicorn pydantic numpy lancedb pyarrow requests ollama

# Copy the amem core and the API
COPY . /app

# We expect AMEM_DATA_DIR to be mounted as a volume
ENV AMEM_DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=1

# Expose the API port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
