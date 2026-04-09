"""
Auto RALPH Loop - Hyperparameter Optimization for A-MEM Retriever
Runs 15 optimization iterations to find the best entity_boost and exact_match_boost.
"""
import sys
from pathlib import Path
import json
import time

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from zettelforge import MemoryManager
from naive_memory import NaiveVectorMemory

def run_loop():
    print("=== Starting 15-Loop RALPH Optimization ===")
    
    with open(Path(__file__).parent / "dataset.json", "r") as f:
        dataset = json.load(f)
        
    queries = [
        {
            "query": "What malware does APT28 use?",
            "must_include": ["dropbear", "edge", "credentials"]
        },
        {
            "query": "Is Server ALPHA currently secure or compromised?",
            "must_include": ["secure", "patched"]
        },
        {
            "query": "Is CVE-2024-1111 patched?",
            "must_include": ["system-wide", "16", "patched"]
        }
    ]

    best_score = -1
    best_params = {}
    history = []

    # Search grid for parameters
    import itertools
    import random
    
    entity_boosts = np.linspace(1.0, 3.0, 5)
    exact_match_boosts = np.linspace(1.0, 3.0, 5)
    thresholds = [0.2, 0.25, 0.3]
    
    params = list(itertools.product(entity_boosts, exact_match_boosts, thresholds))
    random.seed(42)
    random.shuffle(params)
    
    import tempfile
    
    for i in range(15):
        eb, emb, thresh = params[i]
        print(f"\n[Loop {i+1}/15] Recon: Testing eb={eb:.2f}, emb={emb:.2f}, thresh={thresh:.2f}")
        
        tmpdir = tempfile.mkdtemp()
        mm = MemoryManager(jsonl_path=f"{tmpdir}/notes.jsonl", lance_path=f"{tmpdir}/vectordb")
        mm.retriever.entity_boost = eb
        mm.retriever.exact_match_boost = emb
        mm.retriever.similarity_threshold = thresh
        
        # Ingest
        for item in dataset:
            mm.remember(item["content"], domain="security_ops")
            
        score = 0
        for q in queries:
            ans = mm.synthesize(q['query'], format="direct_answer", k=3)
            text = ans.get("synthesis", {}).get("answer", "").lower()
            
            for keyword in q["must_include"]:
                if keyword.lower() in text:
                    score += 1
                    
        print(f"Analyze & Link: Score = {score}/{len(queries) * 3}")
        history.append({"loop": i+1, "eb": eb, "emb": emb, "thresh": thresh, "score": score})
        
        if score > best_score:
            best_score = score
            best_params = {"entity_boost": eb, "exact_match_boost": emb, "similarity_threshold": thresh}
            print(f"Prioritize: New best found! (Score {score})")
            
    print("\n=== Handoff: Optimization Complete ===")
    print(f"Best Score: {best_score}")
    print(f"Best Parameters: {json.dumps(best_params, indent=2)}")
    
    # Save the history
    with open(Path(__file__).parent / "results" / "ralph_optimization_log.json", "w") as f:
        json.dump({"best": best_params, "history": history}, f, indent=2)

if __name__ == "__main__":
    import numpy as np
    run_loop()