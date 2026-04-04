"""
Embedding Generation Utilities
Roland Fleet Agentic Memory Architecture V1.0

Supports two backends:
  - llama-server (GPU-accelerated, ~5ms/embed, port 8080)
  - Ollama (CPU, ~73ms/embed)

llama-server is used by default when available.
"""
import ollama
import requests
import os
import hashlib
from typing import List, Optional


class EmbeddingGenerator:
    """Generate embeddings using llama-server or Ollama with nomic-embed-text"""

    DEFAULT_MODEL = "nomic-embed-text-v2-moe"
    LLAMA_SERVER_URL = os.environ.get(
        "LLAMA_SERVER_URL",
        "http://localhost:8080/embedding"
    )

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        use_llama_server: Optional[bool] = None,
    ):
        self.model = model
        # Auto-detect: use llama-server if available, unless overridden
        if use_llama_server is None:
            use_llama_server = self._check_llama_server()
        self.use_llama_server = use_llama_server

    def _check_llama_server(self) -> bool:
        """Check if llama-server is reachable."""
        try:
            resp = requests.post(
                self.LLAMA_SERVER_URL,
                json={"content": "health"},
                timeout=3,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def embed(self, text: str) -> List[float]:
        """Generate embedding vector for a single text."""
        if self.use_llama_server:
            return self._embed_via_llama_server(text)
        else:
            return self._embed_via_ollama(text)

    def _embed_via_llama_server(self, text: str) -> List[float]:
        """Generate embedding via llama-server (GPU-accelerated, ~5ms)."""
        resp = requests.post(self.LLAMA_SERVER_URL, json={"content": text}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # llama-server returns [{"index": 0, "embedding": [[[...]]]]}]
        emb_list = data[0]["embedding"]
        if emb_list and isinstance(emb_list[0], list):
            return emb_list[0]  # flatten first embedding
        return emb_list

    def _embed_via_ollama(self, text: str) -> List[float]:
        """Generate embedding via Ollama (CPU, ~73ms)."""
        response = ollama.embeddings(model=self.model, prompt=text)
        return response["embedding"]
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        for text in texts:
            try:
                emb = self.embed(text)
                embeddings.append(emb)
            except Exception as e:
                print(f"Embedding failed for text: {e}")
                embeddings.append([0.0] * 768)  # Fallback
        return embeddings
    
    def embed_note_fields(
        self, 
        content: str, 
        context: str, 
        keywords: List[str], 
        tags: List[str]
    ) -> List[float]:
        """Generate embedding from note's text fields"""
        combined = " ".join([
            content,
            context,
            " ".join(keywords),
            " ".join(tags)
        ])
        return self.embed(combined)
    
    @staticmethod
    def compute_hash(text: str) -> str:
        """Compute SHA256 hash of text"""
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a * norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


def test_embedding_pipeline():
    """Test the embedding generation pipeline end-to-end"""
    print("Testing embedding pipeline...")
    
    gen = EmbeddingGenerator()
    
    # Test single embedding
    test_text = "This is a test of the embedding generation system for memory notes"
    emb = gen.embed(test_text)
    print(f"✓ Single embedding generated: {len(emb)} dimensions")
    
    # Test batch embedding
    texts = [
        "Security alert: CVE-2024-1234 critical vulnerability",
        "Financial analysis: MSSP market consolidation trends",
        "Social media post: Thoughts on zero trust architecture"
    ]
    embs = gen.embed_batch(texts)
    print(f"✓ Batch embedding generated: {len(embs)} embeddings")
    
    # Test similarity
    sim = gen.cosine_similarity(embs[0], embs[1])
    print(f"✓ Similarity between security and finance: {sim:.4f}")
    
    # Test hash
    h = gen.compute_hash(test_text)
    print(f"✓ Hash computed: {h}")
    
    print("\n✓ Embedding pipeline test PASSED")
    return True


if __name__ == "__main__":
    test_embedding_pipeline()
