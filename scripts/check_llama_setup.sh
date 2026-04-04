#!/bin/bash
# llama-server setup check for DGX OS (GB10 Superchip)
# Checks for existing installs before downloading/building

set -e

echo "=== Checking existing installs ==="
echo ""

# Check if llama-server is already built
if [ -f "/tmp/llama.cpp/build/bin/llama-server" ]; then
    echo "llama-server: FOUND at /tmp/llama.cpp/build/bin/llama-server"
    LLAMA_SERVER="/tmp/llama.cpp/build/bin/llama-server"
elif [ -f "/usr/local/bin/llama-server" ]; then
    echo "llama-server: FOUND at /usr/local/bin/llama-server"
    LLAMA_SERVER="/usr/local/bin/llama-server"
elif command -v llama-server &> /dev/null; then
    echo "llama-server: FOUND in PATH"
    LLAMA_SERVER=$(which llama-server)
else
    echo "llama-server: NOT FOUND"
    BUILD_LLAMA=1
fi

# Check if llama.cpp source exists
if [ -d "/tmp/llama.cpp" ]; then
    echo "llama.cpp source: FOUND at /tmp/llama.cpp"
    LLAMA_SRC="/tmp/llama.cpp"
elif [ -d "$HOME/llama.cpp" ]; then
    echo "llama.cpp source: FOUND at $HOME/llama.cpp"
    LLAMA_SRC="$HOME/llama.cpp"
else
    echo "llama.cpp source: NOT FOUND"
    CLONE_LLAMA=1
fi

# Check for existing nomic model files
echo ""
echo "=== Checking for nomic-embed-text-v2-moe ==="

# Ollama blobs directory
OLLAMA_MODELS="$HOME/.ollama/models"
if [ -d "$OLLAMA_MODELS/blobs" ]; then
    echo "Ollama blobs: $OLLAMA_MODELS/blobs"
    OLLAMA_BLOB=$(ls "$OLLAMA_MODELS/blobs" | grep -i nomic || echo "")
    if [ -n "$OLLAMA_BLOB" ]; then
        echo "  Found nomic blob: $OLLAMA_BLOB"
    else
        echo "  No nomic blob found in Ollama"
    fi
fi

# Check for any existing GGUF files
echo ""
echo "=== Checking for existing GGUF files ==="
GGUF_COUNT=$(find ~ -name "*.gguf" -type f 2>/dev/null | wc -l)
if [ "$GGUF_COUNT" -gt 0 ]; then
    echo "Found $GGUF_COUNT GGUF file(s):"
    find ~ -name "*.gguf" -type f 2>/dev/null | head -5
else
    echo "  No GGUF files found"
fi

# Check for HuggingFace cache
HF_CACHE="$HOME/.cache/huggingface/hub"
if [ -d "$HF_CACHE" ]; then
    echo ""
    echo "=== HuggingFace cache ==="
    HF_MODELS=$(ls -d "$HF_CACHE"/models--* 2>/dev/null | wc -l)
    echo "Cached models: $HF_MODELS"
    ls -d "$HF_CACHE"/models--* 2>/dev/null | head -5 || echo "  (empty)"
fi

# Check GPU availability
echo ""
echo "=== GPU check ==="
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null || echo "nvidia-smi available but query failed"
    nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null || echo "  (compute cap not available)"
else
    echo "No NVIDIA GPU detected"
fi

# Check CUDA availability
echo ""
echo "=== CUDA check ==="
if [ -d "/usr/local/cuda" ]; then
    echo "CUDA: FOUND at /usr/local/cuda"
    nvcc --version 2>/dev/null || echo "  nvcc not in PATH"
elif [ -d "/usr/lib/cuda" ]; then
    echo "CUDA: FOUND at /usr/lib/cuda"
else
    echo "CUDA: NOT FOUND in standard locations"
fi

# Check system resources
echo ""
echo "=== System resources ==="
echo "CPU cores: $(nproc)"
echo "RAM total: $(free -h | awk '/^Mem:/ {print $2}')"
echo "RAM free:  $(free -h | awk '/^Mem:/ {print $7}')"
echo "Disk:      $(df -h ~ | awk 'NR==2 {print $4 " available"}')"

# Summary
echo ""
echo "=== Summary ==="
if [ -z "$BUILD_LLAMA" ] && [ -n "$LLAMA_SERVER" ]; then
    echo "llama-server: READY to use"
else
    echo "llama-server: needs to be built"
fi

if [ -n "$CLONE_LLAMA" ]; then
    echo "llama.cpp source: needs to be cloned"
else
    echo "llama.cpp source: ready"
fi

echo ""
echo "=== Next steps ==="
if [ -n "$BUILD_LLAMA" ] || [ -n "$CLONE_LLAMA" ]; then
    echo "Run: bash ~/scripts/build_llama_server.sh"
else
    echo "llama-server is ready. Run ~/scripts/start_llama_server.sh to start."
fi
