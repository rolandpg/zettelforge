"""
ZettelForge Integrations — Framework wrappers for popular AI/agent libraries.

Available integrations:
    - langchain: ZettelForgeRetriever (LangChain BaseRetriever)
"""

from zettelforge.integrations.langchain_retriever import ZettelForgeRetriever

__all__ = ["ZettelForgeRetriever"]
