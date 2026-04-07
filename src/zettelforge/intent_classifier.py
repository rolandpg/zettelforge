"""
Intent Classifier - Adaptive Query Routing (MAGMA-style)
A-MEM Agentic Memory Architecture V1.0

Query Intent Types:
- factual: "What CVE was used?" - Entity lookup, direct
- temporal: "What changed since X?" - Timeline queries
- relational: "Who uses what?" - Graph traversal
- exploratory: "Tell me about X" - Full recall + synthesis
- causal: "Why did X happen?" - Causal edge traversal

Task 3: Lightweight intent classifier to weight traversal policy
"""

import re
import ollama
from enum import Enum
from typing import Dict, List, Optional, Tuple


class QueryIntent(Enum):
    FACTUAL = "factual"          # Entity lookup (CVE, actor, tool)
    TEMPORAL = "temporal"         # Time-based queries
    RELATIONAL = "relational"     # Graph traversal (who uses what)
    EXPLORATORY = "exploratory"   # General exploration
    CAUSAL = "causal"            # Causal chains
    UNKNOWN = "unknown"


# Keywords for fast classification (zero-shot)
INTENT_KEYWORDS = {
    QueryIntent.FACTUAL: [
        'cve-', 'cve ', 'vulnerability', 'exploit', 'malware', 'tool',
        'actor', 'apt', 'threat', 'what is', 'what was', 'which'
    ],
    QueryIntent.TEMPORAL: [
        'when', 'timeline', 'since', 'before', 'after', 'changed',
        'history', 'previously', 'earlier', 'latest', 'recent'
    ],
    QueryIntent.RELATIONAL: [
        'who uses', 'who targets', 'who conducts', 'related to',
        'connected to', 'associated with', 'linked to', 'uses tool'
    ],
    QueryIntent.CAUSAL: [
        'why', 'because', 'caused by', 'enables', 'leads to',
        'results in', 'due to', 'reason for'
    ],
    QueryIntent.EXPLORATORY: [
        'tell me about', 'explain', 'describe', 'overview',
        'information on', 'details about', 'context'
    ]
}


class IntentClassifier:
    """
    Lightweight intent classifier for query routing.
    Uses keyword matching + optional LLM for ambiguous cases.
    """
    
    def __init__(self, use_llm_fallback: bool = True):
        self.use_llm_fallback = use_llm_fallback
        self._llm_client = None
    
    def classify(self, query: str) -> Tuple[QueryIntent, Dict]:
        """
        Classify query intent.
        Returns (intent, metadata) where metadata includes confidence and reasoning.
        """
        query_lower = query.lower()
        
        # Fast keyword matching
        scores = {intent: 0 for intent in QueryIntent}
        
        for intent, keywords in INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    scores[intent] += 1
        
        # Get best intent
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        
        # Confidence threshold
        if best_score >= 2:
            confidence = min(1.0, best_score / 4)
            return best_intent, {
                'confidence': confidence,
                'method': 'keyword',
                'scores': scores
            }
        
        # Low confidence - use LLM fallback
        if self.use_llm_fallback:
            return self._classify_llm(query)
        
        return QueryIntent.EXPLORATORY, {
            'confidence': 0.3,
            'method': 'default',
            'scores': scores
        }
    
    def _classify_llm(self, query: str) -> Tuple[QueryIntent, Dict]:
        """Use LLM for ambiguous queries."""
        import ollama
        
        prompt = f"""Classify this query into one of these intents:
- factual: Entity lookup (CVE, actor, tool, malware)
- temporal: Time-based queries (when, since, history)
- relational: Graph traversal (who uses what, connections)
- exploratory: General exploration (tell me about)
- causal: Cause-effect (why, because)

Query: {query}

Respond with just the intent name (factual, temporal, relational, exploratory, or causal):"""

        try:
            response = ollama.generate(
                model="qwen2.5:3b",
                prompt=prompt,
                options={"temperature": 0.1, "num_predict": 20}
            )
            
            intent_name = response.get('response', '').strip().lower()
            
            for intent in QueryIntent:
                if intent.value == intent_name:
                    return intent, {
                        'confidence': 0.8,
                        'method': 'llm',
                        'llm_response': intent_name
                    }
        except Exception as e:
            print(f"LLM classification failed: {e}")
        
        return QueryIntent.EXPLORATORY, {
            'confidence': 0.5,
            'method': 'llm_fallback',
            'scores': {}
        }
    
    def get_traversal_policy(self, intent: QueryIntent) -> Dict:
        """
        Get traversal policy weights based on intent.
        Returns dict of (retriever_weight, graph_weight, temporal_weight)
        """
        policies = {
            QueryIntent.FACTUAL: {
                'vector': 0.3,
                'entity_index': 0.7,
                'graph': 0.0,
                'temporal': 0.0,
                'top_k': 3
            },
            QueryIntent.TEMPORAL: {
                'vector': 0.2,
                'entity_index': 0.1,
                'graph': 0.2,
                'temporal': 0.5,
                'top_k': 5
            },
            QueryIntent.RELATIONAL: {
                'vector': 0.2,
                'entity_index': 0.2,
                'graph': 0.5,
                'temporal': 0.1,
                'top_k': 10
            },
            QueryIntent.CAUSAL: {
                'vector': 0.1,
                'entity_index': 0.1,
                'graph': 0.6,
                'temporal': 0.2,
                'top_k': 10
            },
            QueryIntent.EXPLORATORY: {
                'vector': 0.5,
                'entity_index': 0.2,
                'graph': 0.2,
                'temporal': 0.1,
                'top_k': 10
            },
            QueryIntent.UNKNOWN: {
                'vector': 0.4,
                'entity_index': 0.2,
                'graph': 0.2,
                'temporal': 0.2,
                'top_k': 5
            }
        }
        
        return policies.get(intent, policies[QueryIntent.EXPLORATORY])


# Global instance
_classifier: Optional[IntentClassifier] = None


def get_intent_classifier() -> IntentClassifier:
    """Get global intent classifier."""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier