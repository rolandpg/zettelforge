"""
ThreatRecall Enterprise by Threatengram

Licensed under the Business Source License 1.1 (BSL-1.1).
See LICENSE-ENTERPRISE for terms.

Enterprise features:
  - STIX 2.1 TypeDB ontology with inference rules
  - Blended retrieval (vector + graph hybrid)
  - Graph traversal (BFS multi-hop)
  - TypeDB-backed alias resolution
  - OpenCTI platform integration
  - Sigma rule generation
  - Advanced RAG synthesis (all 4 output formats)
  - Proactive context injection
  - Report ingestion with auto-chunking
  - Cross-encoder reranking
  - Multi-tenant OAuth/JWT authentication
"""

import os
from typing import Optional

_LICENSE_VALIDATED: Optional[bool] = None


def is_licensed() -> bool:
    """Check whether a valid enterprise license is present.

    Checks THREATENGRAM_LICENSE_KEY env var or a license file at
    ~/.threatengram/license.key
    """
    global _LICENSE_VALIDATED
    if _LICENSE_VALIDATED is not None:
        return _LICENSE_VALIDATED

    # Check env var
    key = os.environ.get("THREATENGRAM_LICENSE_KEY", "").strip()
    if key:
        from zettelforge.edition import _validate_license_key
        _LICENSE_VALIDATED = _validate_license_key(key)
        if _LICENSE_VALIDATED:
            return True

    # Check license file
    license_file = os.path.expanduser("~/.threatengram/license.key")
    if os.path.isfile(license_file):
        with open(license_file) as f:
            key = f.read().strip()
        from zettelforge.edition import _validate_license_key
        _LICENSE_VALIDATED = _validate_license_key(key)
        return _LICENSE_VALIDATED

    _LICENSE_VALIDATED = False
    return False


# Expose enterprise feature availability flags
FEATURES = {
    "typedb_ontology": True,
    "blended_retrieval": True,
    "graph_traversal": True,
    "alias_resolution_typedb": True,
    "opencti_integration": True,
    "sigma_generation": True,
    "advanced_synthesis": True,
    "context_injection": True,
    "report_ingestion": True,
    "cross_encoder_reranking": True,
    "multi_tenant_auth": True,
}
