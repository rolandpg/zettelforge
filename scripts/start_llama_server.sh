#!/bin/bash
# Start llama-server with nomic-embed-text-v2-moe on DGX OS (GB10)
# Set model path manually or it will look for a default

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LLAMA_SERVER="$HOME/llama.cpp/build/bin/llama-server"
MODEL_PATH="${1:-$HOME/.ollama/models/nomic-embed-text-v2-moe.gguf}"
PORT="${2:-8080}"
LOG_FILE="/tmp/llama-server-$PORT.log"
PID_FILE="/tmp/llama-server-$PORT.pid"

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "llama-server already running on PID $OLD_PID (port $PORT)"
        echo "PID file: $PID_FILE"
        exit 0
    else
        echo "Stale PID file found, removing..."
        rm -f "$PID_FILE"
    fi
fi

# Check for model
if [ ! -f "$MODEL_PATH" ]; then
    echo "ERROR: Model not found at $MODEL_PATH"
    echo ""
    echo "Options:"
    echo "  1. Download GGUF from HuggingFace:"
    echo "     https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe/tree/main"
    echo ""
    echo "  2. Or convert from Ollama (after running check script):"
    echo "     cp ~/.ollama/models/blobs/sha256:<hash> $MODEL_PATH"
    echo ""
    echo "  3. Or pass model path as argument:"
    echo "     bash $0 /path/to/model.gguf"
    exit 1
fi

# Check GPU
echo "=== GPU check ==="
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null || echo "Warning: nvidia-smi not available"

echo ""
echo "=== Starting llama-server ==="
echo "Model:     $MODEL_PATH"
echo "Port:      $PORT"
echo "Log:       $LOG_FILE"
echo ""

# Start llama-server
$LLAMA_SERVER \
    -m "$MODEL_PATH" \
    --embedding \
    -c 8192 \
    -ngl 99 \
    -fa on \
    --host 0.0.0.0 \
    --port "$PORT" \
    -t 16 \
    --log-disable \
    > "$LOG_FILE" 2>&1 &

SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"
echo "Started on PID $SERVER_PID"

# Wait for startup
sleep 3

# Check if running
if kill -0 "$SERVER_PID" 2>/dev/null; then
    echo ""
    echo "=== Server is running ==="
    echo "PID file:  $PID_FILE"
    echo "Log file:  $LOG_FILE"
    echo ""
    echo "Test with:"
    echo "  curl http://localhost:$PORT/embedding -d '{\"content\": \"test\"}'"
    echo ""
    echo "Stop with:"
    echo "  kill \$(cat $PID_FILE)"
else
    echo "ERROR: Server failed to start"
    echo ""
    echo "=== Log output ==="
    cat "$LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
