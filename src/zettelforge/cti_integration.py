"""
CTI Platform Integration - ZettelForge ↔ Django CTI Database
ZettelForge v1.1.0

Bi-directional integration between ZettelForge memory and CTI platform:
- Import CTI platform entities into ZettelForge memory
- Export ZettelForge notes to CTI platform
- Unified threat recall across both systems
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Setup Django environment
CTI_WORKSPACE = os.path.expanduser("~/cti-workspace")
sys.path.insert(0, CTI_WORKSPACE)

# Configure Django settings before importing models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ctidb.settings")


class CTIPlatformConnector:
    """
    Connect ZettelForge to Django CTI platform.
    Enables unified threat recall across memory and CTI DB.
    """
    
    def __init__(self, cti_workspace: str = None):
        self.cti_workspace = Path(cti_workspace or os.path.expanduser("~/cti-workspace"))
        self.db_path = self.cti_workspace / "data/cti/cti.db"
        self._django_setup = False
        
        # Lazy Django setup
        self._threat_actors = None
        self._cves = None
        self._iocs = None
        self._campaigns = None
        self._malware = None
    
    def _ensure_django(self):
        """Setup Django once for model access."""
        if self._django_setup:
            return
        
        try:
            import django
            django.setup()
            from intel.models import ThreatActor, CVE, IOC, Sector, ThreatAlert, ATTACKTechnique
            self.ThreatActor = ThreatActor
            self.CVE = CVE
            self.IOC = IOC
            self.Sector = Sector
            self.ThreatAlert = ThreatAlert
            self.ATTACKTechnique = ATTACKTechnique
            self._django_setup = True
            print("[CTI] Django initialized")
        except Exception as e:
            print(f"[CTI] Django setup failed: {e}")
            raise
    
    def import_threat_actor(self, actor_name: str = None, actor_id: int = None) -> Dict:
        """Import threat actor from CTI platform into ZettelForge format."""
        self._ensure_django()
        
        if actor_id:
            actor = self.ThreatActor.objects.get(id=actor_id)
        elif actor_name:
            actor = self.ThreatActor.objects.filter(name__icontains=actor_name).first()
        else:
            return None
        
        if not actor:
            return None
        
        # Convert to ZettelForge note format
        note_data = {
            "content": f"# {actor.name} ({actor.country})\n\n"
                      f"**Type:** {actor.actor_type}\n"
                      f"**Risk Level:** {actor.risk_level}\n"
                      f"**Active:** {actor.is_active}\n\n"
                      f"## Description\n{actor.description}\n\n"
                      f"## Aliases\n{actor.aka}\n\n"
                      f"## Target Sectors\n{', '.join(s.name for s in actor.target_sectors.all())}",
            "domain": "cti",
            "metadata": {
                "cti_source": "threat_actor",
                "cti_id": actor.id,
                "actor_type": actor.actor_type,
                "country": actor.country,
                "risk_level": actor.risk_level,
                "is_active": actor.is_active,
                "aliases": actor.aka.split(",") if actor.aka else []
            }
        }
        
        return note_data
    
    def import_cve(self, cve_id: str) -> Dict:
        """Import CVE from CTI platform into ZettelForge format."""
        self._ensure_django()
        
        cve = self.CVE.objects.filter(cve_id=cve_id).first()
        if not cve:
            return None
        
        note_data = {
            "content": f"# {cve.cve_id}\n\n"
                      f"**CVSS:** {cve.cvss_score} ({cve.cvss_vector})\n"
                      f"**EPSS:** {cve.eps_score} ({cve.epss_percentile}%)\n"
                      f"**Published:** {cve.published}\n"
                      f"**In KEV:** {cve.is_in_kev}\n\n"
                      f"## Description\n{cve.description}\n\n"
                      f"## Product\n{cve.vendor} - {cve.product}",
            "domain": "cti",
            "metadata": {
                "cti_source": "cve",
                "cti_id": cve.id,
                "cve_id": cve.cve_id,
                "cvss_score": float(cve.cvss_score) if cve.cvss_score else None,
                "epss_score": float(cve.epss_score) if cve.epss_score else None,
                "is_in_kev": cve.is_in_kev,
                "published": str(cve.published) if cve.published else None
            }
        }
        
        return note_data
    
    def import_ioc(self, ioc_id: int = None, ioc_value: str = None) -> Dict:
        """Import IOC from CTI platform."""
        self._ensure_django()
        
        if ioc_id:
            ioc = self.IOC.objects.get(id=ioc_id)
        elif ioc_value:
            ioc = self.IOC.objects.filter(value__icontains=ioc_value).first()
        else:
            return None
        
        if not ioc:
            return None
        
        note_data = {
            "content": f"# IOC: {ioc.value}\n\n"
                      f"**Type:** {ioc.ioc_type}\n"
                      f"**Threat Actor:** {ioc.threat_actor.name if ioc.threat_actor else 'Unknown'}\n"
                      f"**Confidence:** {ioc.confidence}\n"
                      f"**First Seen:** {ioc.first_seen}\n\n"
                      f"## Context\n{ioc.context}",
            "domain": "cti",
            "metadata": {
                "cti_source": "ioc",
                "cti_id": ioc.id,
                "ioc_type": ioc.ioc_type,
                "value": ioc.value,
                "threat_actor_id": ioc.threat_actor.id if ioc.threat_actor else None,
                "campaign_id": ioc.campaign.id if ioc.campaign else None
            }
        }
        
        return note_data
    
    def search_cti(self, query: str, entity_type: str = None) -> List[Dict]:
        """
        Search CTI platform and return results.
        entity_type: 'actor', 'cve', 'ioc', 'campaign', 'malware'
        """
        self._ensure_django()
        results = []
        
        # Search threat actors
        if entity_type in [None, 'actor']:
            actors = self.ThreatActor.objects.filter(
                name__icontains=query
            ) | self.ThreatActor.objects.filter(
                aka__icontains=query
            )
            for a in actors[:10]:
                results.append({
                    "type": "threat_actor",
                    "id": a.id,
                    "name": a.name,
                    "country": a.country,
                    "actor_type": a.actor_type,
                    "risk_level": a.risk_level
                })
        
        # Search CVEs
        if entity_type in [None, 'cve']:
            cves = self.CVE.objects.filter(cve_id__icontains=query.upper())
            for c in cves[:10]:
                results.append({
                    "type": "cve",
                    "id": c.id,
                    "cve_id": c.cve_id,
                    "cvss_score": float(c.cvss_score) if c.cvss_score else None,
                    "is_in_kev": c.is_in_kev
                })
        
        # Search IOCs
        if entity_type in [None, 'ioc']:
            iocs = self.IOC.objects.filter(value__icontains=query)[:10]
            for i in iocs:
                results.append({
                    "type": "ioc",
                    "id": i.id,
                    "ioc_type": i.ioc_type,
                    "value": i.value[:100],  # Truncate for display
                    "threat_actor": i.threat_actor.name if i.threat_actor else None
                })
        
        return results
    
    def get_entity_summary(self, entity_type: str, entity_id: int) -> Dict:
        """Get summary of CTI entity for memory storage."""
        self._ensure_django()
        
        if entity_type == "actor":
            actor = self.ThreatActor.objects.get(id=entity_id)
            return {
                "name": actor.name,
                "type": "ThreatActor",
                "summary": f"{actor.actor_type} from {actor.country}. Risk: {actor.risk_level}. Active: {actor.is_active}",
                "metadata": {
                    "country": actor.country,
                    "actor_type": actor.actor_type,
                    "risk_level": actor.risk_level,
                    "is_active": actor.is_active
                }
            }
        
        elif entity_type == "cve":
            cve = self.CVE.objects.get(id=entity_id)
            return {
                "name": cve.cve_id,
                "type": "CVE",
                "summary": f"CVSS: {cve.cvss_score}, EPSS: {cve.epss_score}, KEV: {cve.is_in_kev}",
                "metadata": {
                    "cvss_score": float(cve.cvss_score) if cve.cvss_score else None,
                    "is_in_kev": cve.is_in_kev
                }
            }
        
        elif entity_type == "ioc":
            ioc = self.IOC.objects.get(id=entity_id)
            return {
                "name": ioc.value[:50],
                "type": "IOC",
                "summary": f"{ioc.ioc_type} - {ioc.threat_actor.name if ioc.threat_actor else 'Unknown'}",
                "metadata": {
                    "ioc_type": ioc.ioc_type
                }
            }
        
        return {}
    
    def get_all_active_actors(self) -> List[Dict]:
        """Get all active threat actors."""
        self._ensure_django()
        actors = self.ThreatActor.objects.filter(is_active=True).order_by('-risk_level', 'name')
        return [
            {
                "id": a.id,
                "name": a.name,
                "country": a.country,
                "actor_type": a.actor_type,
                "risk_level": a.risk_level
            }
            for a in actors
        ]
    
    def get_recent_kevs(self, days: int = 30) -> List[Dict]:
        """Get recent CVEs in CISA KEV."""
        self._ensure_django()
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        
        cves = self.CVE.objects.filter(
            is_in_kev=True
        ).filter(
            published__gte=cutoff.date()
        ).order_by('-published')[:20]
        
        return [
            {
                "cve_id": c.cve_id,
                "cvss_score": float(c.cvss_score) if c.cvss_score else None,
                "published": str(c.published)
            }
            for c in cves
        ]
    
    def get_stats(self) -> Dict:
        """Get CTI platform statistics."""
        self._ensure_django()
        return {
            "threat_actors": self.ThreatActor.objects.count(),
            "cves": self.CVE.objects.count(),
            "cves_in_kev": self.CVE.objects.filter(is_in_kev=True).count(),
            "iocs": self.IOC.objects.count(),
            "sectors": self.Sector.objects.count(),
            "threat_alerts": self.ThreatAlert.objects.count(),
            "attack_techniques": self.ATTACKTechnique.objects.count()
        }


# Global singleton
_cti_connector: Optional[CTIPlatformConnector] = None


def get_cti_connector() -> CTIPlatformConnector:
    """Get global CTI platform connector."""
    global _cti_connector
    if _cti_connector is None:
        _cti_connector = CTIPlatformConnector()
    return _cti_connector


# Convenience functions for memory integration
def import_cti_to_memory(memory_manager, query: str = None, entity_type: str = None) -> List[Any]:
    """
    Import CTI entities into ZettelForge memory.
    Usage: import_cti_to_memory(mm, query="APT28", entity_type="actor")
    """
    connector = get_cti_connector()
    
    if query:
        results = connector.search_cti(query, entity_type)
        imported = []
        for r in results:
            if r['type'] == 'actor':
                note_data = connector.import_threat_actor(actor_id=r['id'])
            elif r['type'] == 'cve':
                note_data = connector.import_cve(r['cve_id'])
            elif r['type'] == 'ioc':
                note_data = connector.import_ioc(ioc_id=r['id'])
            else:
                continue
            
            if note_data:
                note, _ = memory_manager.remember(note_data["content"], domain="cti")
                imported.append(note)
        return imported
    
    return []


def unified_recall(memory_manager, query: str, k: int = 10) -> Dict:
    """
    Unified recall across ZettelForge memory and CTI platform.
    Returns {"memory": [...], "cti": [...]}
    """
    # Recall from memory
    memory_results = memory_manager.recall(query, k=k)
    
    # Search CTI platform
    cti_connector = get_cti_connector()
    cti_results = cti_connector.search_cti(query)
    
    return {
        "memory": memory_results,
        "cti": cti_results
    }