#!/usr/bin/env python3
"""
Embedding Engine Comparison Test
Compares: Ollama (cold load) vs llama-server (hot)

Patrick Roland — Roland Fleet
"""
import time
import ollama
import requests
import statistics

MODEL = "nomic-embed-text-v2-moe"
LLAMA_SERVER_URL = "http://localhost:8080/embedding"
OLLAMA_EMBED_BATCH_SIZE = 5
LLAMA_SERVER_BATCH_SIZE = 5

TEST_TEXTS = [
    "APT28 using Cobalt Strike beacon against DIB network",
    "CVE-2025-32711 EchoLeak Microsoft SharePoint vulnerability",
    "CMMC 2.0 compliance requirements for DoD contractors",
    "MSSP market consolidation PE acquisition strategy",
    "Ransomware attack via exposed backup infrastructure",
]


def get_embedding_ollama(text: str) -> float:
    """Time a single Ollama embedding call (cold load each time)"""
    start = time.perf_counter()
    try:
        resp = ollama.embeddings(model=MODEL, prompt=text)
        elapsed = time.perf_counter() - start
        return elapsed, len(resp.get("embedding", []))
    except Exception as e:
        elapsed = time.perf_counter() - start
        return elapsed, str(e)


def get_embedding_llama_server(text: str) -> float:
    """Time a single llama-server embedding call (always hot)"""
    start = time.perf_counter()
    try:
        resp = requests.post(
            LLAMA_SERVER_URL,
            json={"content": text},
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        # llama-server returns [{"index": 0, "embedding": [[[...]], [[...]], ...]}]
        # Outer list is batch dimension, inner list per embedding, then actual vector
        emb_list = data[0]["embedding"] if isinstance(data, list) else data.get("embedding", [])
        # Each item is the actual vector — flatten if nested
        if emb_list and isinstance(emb_list[0], list):
            embedding = emb_list[0]  # first embedding, already a list of floats
        else:
            embedding = emb_list
        elapsed = time.perf_counter() - start
        return elapsed, len(embedding)
    except Exception as e:
        elapsed = time.perf_counter() - start
        return elapsed, str(e)


def run_test(name: str, func, texts: list, runs: int = 3):
    """Run a comparison test"""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(f"Texts: {len(texts)} | Runs per text: {runs}")
    print("-" * 60)
    
    all_times = []
    dims = None
    
    for run in range(runs):
        run_times = []
        for text in texts:
            elapsed, result = func(text)
            run_times.append(elapsed)
            if isinstance(result, int):
                dims = result
            if run == 0:  # Log first run detail
                status = f"{elapsed*1000:.1f}ms" if isinstance(result, int) else f"ERR: {result}"
                print(f"  Run {run+1}: {elapsed*1000:.1f}ms | dims={dims}")
        all_times.extend(run_times)
    
    print("-" * 60)
    print(f"  Count:     {len(all_times)} calls")
    print(f"  Mean:      {statistics.mean(all_times)*1000:.1f}ms")
    print(f"  Median:    {statistics.median(all_times)*1000:.1f}ms")
    print(f"  Stdev:     {statistics.stdev(all_times)*1000:.1f}ms" if len(all_times) > 1 else f"  Stdev:     N/A")
    print(f"  Min:       {min(all_times)*1000:.1f}ms")
    print(f"  Max:       {max(all_times)*1000:.1f}ms")
    
    return {
        "mean_ms": statistics.mean(all_times) * 1000,
        "median_ms": statistics.median(all_times) * 1000,
        "min_ms": min(all_times) * 1000,
        "max_ms": max(all_times) * 1000,
        "dims": dims,
    }


def main():
    print("="*60)
    print("  EMBEDDING ENGINE COMPARISON TEST")
    print("  llama-server (hot GPU) vs Ollama (cold load)")
    print("="*60)
    
    # Check llama-server is running
    try:
        resp = requests.get("http://localhost:8080/health", timeout=5)
        print(f"\nllama-server: OK ({resp.status_code})")
    except:
        try:
            resp = requests.post(LLAMA_SERVER_URL, json={"content": "test"}, timeout=5)
            print(f"\nllama-server: OK (responding)")
        except Exception as e:
            print(f"\nllama-server: NOT REACHABLE ({e})")
            print("Start with: nohup ~/llama.cpp/build/bin/llama-server -m ~/models/nomic-embed-text-v2-moe.gguf --embedding -c 8192 -ngl 99 --host 0.0.0.0 --port 8080 -t 16 > /tmp/llama-server.log 2>&1 &")
            return
    
    # Test llama-server (always hot — GPU-accelerated)
    ll_results = run_test(
        "llama-server (hot, GPU-accelerated)",
        get_embedding_llama_server,
        TEST_TEXTS,
        runs=3
    )
    
    # Test Ollama (cold load — model loads from disk each call)
    # Note: Each ollama.embeddings() call loads the model from scratch
    print("\n  [Note: Ollama cold-load benchmark — model loads from disk each call]")
    ollama_results = run_test(
        "Ollama (cold load per call)",
        get_embedding_ollama,
        TEST_TEXTS,
        runs=1  # Only 1 run since it's slow
    )
    
    # Summary
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    speedup = ollama_results["mean_ms"] / ll_results["mean_ms"]
    print(f"  llama-server (hot):  {ll_results['mean_ms']:.1f}ms avg")
    print(f"  Ollama (cold):      {ollama_results['mean_ms']:.1f}ms avg")
    print(f"  Speedup:             {speedup:.0f}x faster with llama-server")
    print(f"  Dimensions:          {ll_results.get('dims', 'N/A')}")
    print("="*60)
    
    return speedup


if __name__ == "__main__":
    main()
