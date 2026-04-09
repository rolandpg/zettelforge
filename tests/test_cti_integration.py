#!/usr/bin/env python3
"""
Test CTI Platform Integration with ZettelForge.
Validates bi-directional sync between memory and CTI DB.

These tests require a live local CTI Django workspace/database.
They are skipped by default unless the ZETTELFORGE_CTI_INTEGRATION_TESTS
environment variable is set to "1".
"""
import os
import sys
import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("ZETTELFORGE_CTI_INTEGRATION_TESTS") != "1",
    reason="CTI integration tests require a live CTI workspace. "
           "Set ZETTELFORGE_CTI_INTEGRATION_TESTS=1 to enable.",
)


from zettelforge.cti_integration import get_cti_connector, CTIPlatformConnector


def test_cti_connection():
    connector = get_cti_connector()
    
    # Test 1: Get stats
    stats = connector.get_stats()
    assert 'threat_actors' in stats
    assert 'cves' in stats
    
    # Test 2: Search threat actors
    actors = connector.search_cti("APT28", entity_type="actor")
    assert isinstance(actors, list)
    
    # Test 3: Search CVEs
    cves = connector.search_cti("CVE-2024", entity_type="cve")
    assert isinstance(cves, list)
    
    # Test 4: Get active actors
    active = connector.get_all_active_actors()
    assert isinstance(active, list)
    
    # Test 5: Recent KEVs
    kevs = connector.get_recent_kevs(days=30)
    assert isinstance(kevs, list)