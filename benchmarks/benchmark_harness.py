"""
Benchmark harness for A-MEM vs Naive Vector Memory
"""
import sys
import json
import time
import os
from pathlib import Path

# Add amem to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zettelforge import MemoryManager
from naive_memory import NaiveVectorMemory

def run_benchmark():
    print("=== Agentic Memory Benchmark ===")
    print("Comparing A-MEM vs Naive Vector Memory")
    
    # Initialize
    print("\nInitializing systems...")
    
    # We use a temporary directory for A-MEM to avoid polluting the main instance
    import tempfile
    tmpdir = tempfile.mkdtemp()
    
    amem = MemoryManager(jsonl_path=f"{tmpdir}/notes.jsonl", lance_path=f"{tmpdir}/vectordb")
    naive = NaiveVectorMemory()
    
    # Load dataset
    with open(Path(__file__).parent / "dataset.json", "r") as f:
        dataset = json.load(f)
    
    # Ingestion Benchmark
    print("\n[1] INGESTION BENCHMARK")
    print("-" * 30)
    
    # A-MEM ingestion
    t0 = time.time()
    for item in dataset:
        amem.remember(item["content"], domain="security_ops")
    amem_ingest_time = time.time() - t0
    print(f"A-MEM ingestion time: {amem_ingest_time:.3f}s for {len(dataset)} items")
    
    # Naive ingestion
    t0 = time.time()
    for item in dataset:
        naive.remember(item["content"])
    naive_ingest_time = time.time() - t0
    print(f"Naive ingestion time: {naive_ingest_time:.3f}s for {len(dataset)} items")
    
    # Queries Benchmark
    queries = [
        {
            "name": "Alias Resolution & Multi-hop",
            "query": "What malware does APT28 use?",
            "expected_logic": "APT28 is Fancy Bear, Fancy Bear used DROPBEAR, but later APT28 stopped using it."
        },
        {
            "name": "Supersession & State Tracking",
            "query": "Is Server ALPHA currently secure or compromised?",
            "expected_logic": "It was compromised, but later patched and secured."
        },
        {
            "name": "Vulnerability Tracking",
            "query": "Is CVE-2024-1111 patched?",
            "expected_logic": "Detected on day 15, patched system-wide on day 16."
        }
    ]
    
    print("\n[2] QUERY RETRIEVAL BENCHMARK")
    print("-" * 30)
    
    results = []
    
    for q in queries:
        print(f"\nQuery: {q['query']}")
        print(f"Expected Logic: {q['expected_logic']}")
        
        # A-MEM Retrieval
        t0 = time.time()
        # In A-MEM, we use the synthesis layer to get the final answer
        amem_ans = amem.synthesize(q['query'], format="direct_answer", k=5)
        amem_q_time = time.time() - t0
        amem_text = amem_ans.get("synthesis", {}).get("answer", "No answer")
        
        # Naive Retrieval
        t0 = time.time()
        naive_notes = naive.recall(q['query'], k=3)
        naive_q_time = time.time() - t0
        naive_text = "\\n".join([f"- {n['text']}" for n in naive_notes])
        
        print(f"A-MEM Answer ({amem_q_time:.3f}s): {amem_text}")
        print(f"Naive Context ({naive_q_time:.3f}s): {naive_text}")
        
        results.append({
            "query": q["query"],
            "expected": q["expected_logic"],
            "amem": {"time": amem_q_time, "answer": amem_text},
            "naive": {"time": naive_q_time, "context": naive_text}
        })
        
    # Write report
    report_path = Path(__file__).parent / "results" / "benchmark_report.md"
    with open(report_path, "w") as f:
        f.write("# A-MEM Benchmark Report\\n\\n")
        f.write("## Ingestion Performance\\n")
        f.write(f"- A-MEM: {amem_ingest_time:.3f}s\\n")
        f.write(f"- Naive Vector Memory: {naive_ingest_time:.3f}s\\n\\n")
        
        f.write("## Query Performance\\n\\n")
        for res in results:
            f.write(f"### Query: {res['query']}\\n")
            f.write(f"**Expected Logic:** {res['expected']}\\n\\n")
            f.write(f"**A-MEM (Synthesis):** ({res['amem']['time']:.3f}s)\\n{res['amem']['answer']}\\n\\n")
            f.write(f"**Naive Vector Memory (Raw context):** ({res['naive']['time']:.3f}s)\\n{res['naive']['context']}\\n\\n")
            
    print(f"\nReport written to {report_path}")

if __name__ == "__main__":
    run_benchmark()
