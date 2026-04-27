"""
ZettelForge Integrations — Framework wrappers for popular AI/agent libraries.

Available integrations:
    - langchain: ZettelForgeRetriever (LangChain BaseRetriever)
    - crewai:    ZettelForgeRecallTool / RememberTool / SynthesizeTool
                 (CrewAI BaseTool subclasses, optional dep —
                 ``pip install zettelforge[crewai]``)

The CrewAI module is intentionally NOT imported here so the integrations
package never hard-requires the crewai dependency. Import it explicitly:
    ``from zettelforge.integrations.crewai import ZettelForgeRecallTool``
"""

from zettelforge.integrations.langchain_retriever import ZettelForgeRetriever

__all__ = ["ZettelForgeRetriever"]
