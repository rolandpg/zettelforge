"""
Proactive Context Injection - Memory Pre-loading for Agents
ZettelForge v1.2.0

Automatically recalls relevant context before agent tasks.
Integrates with ZettelForge memory + CTI platform for unified context.
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path


# Context injection triggers
CONTEXT_TRIGGERS = {
    # Security/CTI tasks
    "cve_analysis": ["cve", "vulnerability", "exploit", "patch"],
    "threat_actor_research": ["apt", "actor", "threat", "attribution"],
    "incident_response": ["incident", "breach", "compromised", "investigation"],
    "malware_analysis": ["malware", "sample", "payload", "detection"],
    
    # Memory/knowledge tasks  
    "project_context": ["project", "task", "goal", "deadline"],
    "person_lookup": ["person", "contact", "who is"],
    "entity_lookup": ["what is", "explain", "tell me about"],
    
    # Planning tasks
    "planning": ["plan", "schedule", "roadmap", "strategy"],
    "research": ["research", "investigate", "find information"],
}


# Priority sources for each domain
CONTEXT_PRIORITY = {
    "cti": {
        "cve": ["cve", "vulnerability", "exploit"],
        "actor": ["threat actor", "apt", "attribution"],
        "ioc": ["indicator", "ioc", "hash", "ip", "domain"]
    },
    "security": {
        "incident": ["incident", "breach", "compromised"],
        "vulnerability": ["cve", "vulnerability", "patch"],
        "threat": ["threat", "attack", "campaign"]
    },
    "general": {
        "project": ["project", "task", "deadline"],
        "person": ["person", "contact"],
        "entity": ["entity", "organization"]
    }
}


class ContextInjector:
    """
    Proactively injects relevant context into agent tasks.
    Monitors task context and pre-loads relevant memories.
    """
    
    def __init__(
        self,
        memory_manager=None,
        cti_connector=None,
        min_relevance: float = 0.3
    ):
        self.memory_manager = memory_manager
        self.cti_connector = cti_connector
        self.min_relevance = min_relevance
        
        # Context cache
        self._context_cache: Dict[str, Any] = {}
        self._last_inject: Dict[str, datetime] = {}
        
        # Injection callbacks
        self._injection_handlers: List[Callable] = []
    
    def classify_task_context(self, task_description: str) -> List[str]:
        """
        Classify task into context domains.
        Returns list of matching context types.
        """
        task_lower = task_description.lower()
        matched = []
        
        for context_type, keywords in CONTEXT_TRIGGERS.items():
            for kw in keywords:
                if kw in task_lower:
                    matched.append(context_type)
                    break
        
        return matched if matched else ["general"]
    
    def inject_context(
        self,
        task_description: str,
        domain: Optional[str] = None,
        k: int = 5,
        force_refresh: bool = False
    ) -> Dict[str, List[Any]]:
        """
        Inject relevant context for a task.
        Returns {"memory": [...], "cti": [...], "summary": "..."}
        """
        context_types = self.classify_task_context(task_description)
        
        # Generate cache key
        cache_key = f"{task_description[:50]}:{':'.join(context_types)}"
        
        # Return cached if valid
        if not force_refresh and cache_key in self._context_cache:
            if (datetime.now() - self._last_inject.get(cache_key, datetime.min)).seconds < 300:
                return self._context_cache[cache_key]
        
        results = {
            "memory": [],
            "cti": [],
            "task_types": context_types,
            "injected_at": datetime.now().isoformat()
        }
        
        # Query memory
        if self.memory_manager:
            memory_results = self.memory_manager.recall(
                task_description,
                k=k,
                domain=domain
            )
            results["memory"] = [
                {
                    "id": note.id,
                    "content": note.content[:200],
                    "domain": note.domain,
                    "timestamp": note.created.isoformat() if note.created else None
                }
                for note in memory_results
            ]
        
        # Query CTI platform
        if self.cti_connector:
            cti_results = self.cti_connector.search_cti(task_description)
            results["cti"] = cti_results[:k]
        
        # Generate summary
        results["summary"] = self._generate_context_summary(results, context_types)
        
        # Cache results
        self._context_cache[cache_key] = results
        self._last_inject[cache_key] = datetime.now()
        
        # Trigger injection handlers
        for handler in self._injection_handlers:
            try:
                handler(results)
            except Exception as e:
                print(f"[ContextInjector] Handler error: {e}")
        
        return results
    
    def _generate_context_summary(self, context: Dict, task_types: List[str]) -> str:
        """Generate human-readable context summary."""
        parts = []
        
        if context.get("memory"):
            parts.append(f"Memory: {len(context['memory'])} relevant notes")
        
        if context.get("cti"):
            cti_by_type = {}
            for item in context["cti"]:
                t = item.get("type", "unknown")
                cti_by_type[t] = cti_by_type.get(t, 0) + 1
            type_str = ", ".join(f"{v} {k}" for k, v in cti_by_type.items())
            parts.append(f"CTI: {type_str}")
        
        if not parts:
            return "No relevant context found."
        
        return " | ".join(parts)
    
    def register_injection_handler(self, handler: Callable):
        """Register callback for context injection events."""
        self._injection_handlers.append(handler)
    
    def clear_cache(self):
        """Clear context cache."""
        self._context_cache.clear()
        self._last_inject.clear()
    
    def get_hot_context(self, domain: str = None) -> List[Dict]:
        """
        Get frequently accessed/contextual notes.
        Based on recent activity and domain.
        """
        if not self.memory_manager:
            return []
        
        # Get recent notes
        all_notes = self.memory_manager.store.get_all_notes()
        
        if domain:
            all_notes = [n for n in all_notes if n.domain == domain]
        
        # Sort by recency
        all_notes.sort(key=lambda n: n.created or datetime.min, reverse=True)
        
        return [
            {
                "id": note.id,
                "content": note.content[:150],
                "domain": note.domain
            }
            for note in all_notes[:10]
        ]


class ProactiveAgentMixin:
    """
    Mixin for agents to enable proactive context injection.
    Use: class MyAgent(ProactiveAgentMixin, SomeBaseAgent): ...
    """
    
    def __init__(self, *args, **kwargs):
        self._context_injector = None
        super().__init__(*args, **kwargs)
    
    def init_context_injection(
        self,
        memory_manager=None,
        cti_connector=None,
        auto_inject: bool = True
    ):
        """Initialize context injection system."""
        self._context_injector = ContextInjector(
            memory_manager=memory_manager,
            cti_connector=cti_connector
        )
        self._auto_inject = auto_inject
    
    def before_task(self, task_description: str) -> Dict:
        """
        Call before agent task to pre-load context.
        Returns injected context dict.
        """
        if not self._context_injector:
            return {}
        
        return self._context_injector.inject_context(task_description)
    
    def get_context_summary(self, task_description: str) -> str:
        """Get just the summary string for a task."""
        if not self._context_injector:
            return ""
        
        result = self._context_injector.inject_context(task_description)
        return result.get("summary", "")
    
    def inject_into_prompt(self, task_description: str, base_prompt: str) -> str:
        """
        Inject context into a prompt for LLM consumption.
        Returns modified prompt with context.
        """
        context = self.before_task(task_description)
        
        if not context.get("memory") and not context.get("cti"):
            return base_prompt
        
        # Build context section
        context_parts = ["## Relevant Context\n"]
        
        if context.get("memory"):
            context_parts.append("### From Memory:")
            for i, note in enumerate(context["memory"][:3], 1):
                context_parts.append(f"{i}. {note['content']}")
        
        if context.get("cti"):
            context_parts.append("\n### From CTI Platform:")
            for item in context["cti"][:3]:
                context_parts.append(f"- {item.get('name', item.get('cve_id', item.get('value', 'Unknown')))}")
        
        context_section = "\n".join(context_parts)
        
        return f"{base_prompt}\n\n{context_section}"


# Global singleton
_context_injector: Optional[ContextInjector] = None


def get_context_injector(
    memory_manager=None,
    cti_connector=None
) -> ContextInjector:
    """Get global context injector."""
    global _context_injector
    
    if _context_injector is None:
        _context_injector = ContextInjector(
            memory_manager=memory_manager,
            cti_connector=cti_connector
        )
    
    return _context_injector


def inject_for_task(
    task_description: str,
    memory_manager=None,
    cti_connector=None,
    k: int = 5
) -> Dict:
    """Convenience function for context injection."""
    injector = get_context_injector(memory_manager, cti_connector)
    return injector.inject_context(task_description, k=k)