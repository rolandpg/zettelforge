#!/bin/bash
# Build llama-server for DGX OS (GB10 Superchip / ARM64 Linux + NVIDIA CUDA)
set -e

# Use existing llama.cpp source if present, otherwise clone
if [ -d "$HOME/llama.cpp" ]; then
    LLAMA_SRC="$HOME/llama.cpp"
    echo "Using existing llama.cpp at $LLAMA_SRC"
    cd "$LLAMA_SRC"
    echo "Pulling latest..."
    git checkout master
    git pull
elif [ -d "/home/rolandpg/llama.cpp" ]; then
    LLAMA_SRC="/home/rolandpg/llama.cpp"
    echo "Using existing llama.cpp at $LLAMA_SRC"
    cd "$LLAMA_SRC"
    git checkout master
    git pull
else
    echo "Cloning llama.cpp..."
    git clone https://github.com/ggerganov/llama.cpp.git /tmp/llama.cpp
    LLAMA_SRC="/tmp/llama.cpp"
fi

# Build directory alongside source, not in /tmp
LLAMA_BUILD="$LLAMA_SRC/build"

cd "$LLAMA_SRC"

# Create build directory
mkdir -p "$LLAMA_BUILD"
cd "$LLAMA_BUILD"

# Configure with CUDA for NVIDIA GPU support
echo ""
echo "=== Configuring cmake with CUDA ==="
echo "Source: $LLAMA_SRC"
echo "Build:  $LLAMA_BUILD"
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLAMA_CUDA=ON \
    -DLLAMA_FASTMath=ON \
    -DLLAMA_NATIVE=ON \
    -DCMAKE_C_COMPILER=gcc \
    -DCMAKE_CXX_COMPILER=g++

# Build
echo ""
echo "=== Building llama-server ==="
cmake --build . --target llama-server -j$(nproc)

# Verify
if [ -f "$LLAMA_BUILD/bin/llama-server" ]; then
    echo ""
    echo "=== Build successful ==="
    echo "Binary: $LLAMA_BUILD/bin/llama-server"
    ls -lh "$LLAMA_BUILD/bin/llama-server"
else
    echo "ERROR: llama-server not found after build"
    exit 1
fi

echo ""
echo "=== Done ==="
echo "Next: bash ~/.openclaw/workspace/scripts/start_llama_server.sh"
