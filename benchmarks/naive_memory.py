"""
A naive vector-only memory system to simulate basic RAG architectures
like LangChain VectorStore or older versions of Mem0/Zep.
"""
import numpy as np
from typing import List, Dict
import time

def get_embedding(text: str, model: str = "nomic-embed-text") -> List[float]:
    try:
        import ollama
        resp = ollama.embeddings(model=model, prompt=text)
        return resp.get("embedding", [0.0] * 768)
    except Exception as e:
        import hashlib
        # Deterministic mock embedding based on string hash if ollama fails
        # This allows naive memory to at least have stable vectors for cosine sim
        h = int(hashlib.md5(text.encode()).hexdigest(), 16)
        np.random.seed(h % (2**32))
        return np.random.rand(768).tolist()

def cosine_similarity(a: List[float], b: List[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    norm_a, norm_b = np.linalg.norm(a_arr), np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0: return 0.0
    return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))

class NaiveVectorMemory:
    def __init__(self):
        self.store = []
        self.id_counter = 0

    def remember(self, text: str):
        emb = get_embedding(text)
        self.store.append({
            "id": self.id_counter,
            "text": text,
            "vector": emb,
            "timestamp": time.time()
        })
        self.id_counter += 1
        return self.id_counter - 1

    def recall(self, query: str, k: int = 3) -> List[Dict]:
        q_emb = get_embedding(query)
        scored = []
        for item in self.store:
            sim = cosine_similarity(q_emb, item["vector"])
            scored.append((item, sim))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [item for item, sim in scored[:k]]
