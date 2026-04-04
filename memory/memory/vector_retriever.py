"""
Vector Retriever Shim — Re-export from parent directory

This module re-exports VectorRetriever from the parent memory directory
to maintain proper package structure for synthesis submodules.
"""
import sys
from pathlib import Path

# Add parent directory to path for direct import
_parent = Path(__file__).parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from vector_retriever import VectorRetriever

__all__ = ['VectorRetriever']
