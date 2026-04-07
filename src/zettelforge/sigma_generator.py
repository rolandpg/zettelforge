"""
Sigma Rule Generator - IOC to Detection Rules
ZettelForge v1.3.0

Generates Sigma YAML rules from CTI IOCs and causal edges.
Compatible with Sigma CLI and Microsoft Sentinel conversion.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path


# Sigma rule templates by IOC type
SIGMA_TEMPLATES = {
    "ip": {
        "title": "Malicious IP - {indicator}",
        "id": "zf-ip-{hash_id}",
        "status": "stable",
        "description": "Detection for known malicious IP address associated with {actor}",
        "references": ["{source}"],
        "tags": ["attack.initial_access", "mitre.impact"],
        "logsource": {
            "category": "network_connection"
        },
        "selection": {
            "DestinationIP": ["{indicator}"]
        },
        "condition": "selection"
    },
    "domain": {
        "title": "Malicious Domain - {indicator}",
        "id": "zf-domain-{hash_id}",
        "status": "stable",
        "description": "Detection for known malicious domain associated with {actor}",
        "references": ["{source}"],
        "tags": ["attack.initial_access", "mitre.impact"],
        "logsource": {
            "category": "dns"
        },
        "selection": {
            "query": ["{indicator}"]
        },
        "condition": "selection"
    },
    "hash_md5": {
        "title": "Malicious File Hash - {indicator}",
        "id": "zf-hash-md5-{hash_id}",
        "status": "stable",
        "description": "Detection for known malicious file hash associated with {actor}",
        "references": ["{source}"],
        "tags": ["attack.execution", "mitre.impact"],
        "logsource": {
            "category": "file_event"
        },
        "selection": {
            "HashMD5": ["{indicator}"]
        },
        "condition": "selection"
    },
    "hash_sha256": {
        "title": "Malicious File Hash - {indicator}",
        "id": "zf-hash-sha256-{hash_id}",
        "status": "stable",
        "description": "Detection for known malicious file hash associated with {actor}",
        "references": ["{source}"],
        "tags": ["attack.execution", "mitre.impact"],
        "logsource": {
            "category": "file_event"
        },
        "selection": {
            "HashSHA256": ["{indicator}"]
        },
        "condition": "selection"
    },
    "url": {
        "title": "Malicious URL - {indicator}",
        "id": "zf-url-{hash_id}",
        "status": "stable",
        "description": "Detection for known malicious URL associated with {actor}",
        "references": ["{source}"],
        "tags": ["attack.initial_access", "mitre.impact"],
        "logsource": {
            "category": "network_connection"
        },
        "selection": {
            "Url": ["{indicator}"]
        },
        "condition": "selection"
    }
}


# MITRE ATT&CK mapping by relation
RELATION_TO_MITRE = {
    "exploits": "attack.initial_access",
    "uses": "attack.execution",
    "targets": "attack.impact",
    "enables": "attack.persistence",
    "causes": "attack.impact"
}


class SigmaGenerator:
    """
    Generate Sigma rules from IOCs and causal relationships.
    """
    
    def __init__(self, cti_connector=None, knowledge_graph=None):
        self.cti_connector = cti_connector
        self.knowledge_graph = knowledge_graph
        self._rules_cache: Dict[str, Dict] = {}
    
    def generate_from_ioc(
        self,
        ioc_value: str,
        ioc_type: str,
        actor: str = None,
        source: str = "ZettelForge",
        tags: List[str] = None
    ) -> Dict:
        """
        Generate Sigma rule from single IOC.
        
        Args:
            ioc_value: The indicator value (IP, domain, hash, URL)
            ioc_type: Type (ip, domain, hash_md5, hash_sha256, url)
            actor: Associated threat actor
            source: Source of intelligence
            tags: Additional MITRE tags
            
        Returns:
            Dict with Sigma rule fields
        """
        # Normalize IOC type
        ioc_type = ioc_type.lower().replace("hash_", "hash_")
        
        if ioc_type not in SIGMA_TEMPLATES:
            raise ValueError(f"Unsupported IOC type: {ioc_type}")
        
        template = SIGMA_TEMPLATES[ioc_type].copy()
        
        # Generate ID
        hash_id = str(abs(hash(ioc_value)))[:8]
        template["id"] = template["id"].format(hash_id=hash_id)
        
        # Fill placeholders
        template["title"] = template["title"].format(indicator=ioc_value[:50])
        template["description"] = template["description"].format(
            actor=actor or "unknown threat actor"
        )
        template["references"] = [s.format(source=source) for s in template["references"]]
        
        # Add tags
        if tags:
            template["tags"].extend(tags)
        if actor:
            template["tags"].append(f"threat.actor.{actor.lower().replace(' ', '_')}")
        
        # Set selection
        template["selection"] = {
            k: [v] for k, v in template["selection"].items()
        }
        template["selection"][list(template["selection"].keys())[0]] = [ioc_value]
        
        # Add metadata
        template["metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "zettelforge_version": "1.3.0",
            "source_ioc": ioc_value,
            "source_type": ioc_type
        }
        
        return template
    
    def generate_from_actor(
        self,
        actor_name: str,
        min_confidence: str = "MEDIUM"
    ) -> List[Dict]:
        """
        Generate Sigma rules for all IOCs associated with an actor.
        
        Args:
            actor_name: Threat actor name
            min_confidence: Minimum confidence level (LOW, MEDIUM, HIGH)
            
        Returns:
            List of Sigma rules
        """
        if not self.cti_connector:
            return []
        
        rules = []
        
        # Search IOCs for actor
        iocs = self.cti_connector.search_cti(actor_name, entity_type="ioc")
        
        # IOC type to Sigma type mapping
        sigma_type_map = {
            "IP": "ip",
            "DOMAIN": "domain",
            "HASH_MD5": "hash_md5",
            "HASH_SHA1": "hash_sha1", 
            "HASH_SHA256": "hash_sha256",
            "URL": "url",
            "EMAIL": "email"
        }
        
        for ioc in iocs:
            confidence = ioc.get("confidence", "MEDIUM")
            if confidence in ["MEDIUM", "HIGH"] or min_confidence == "LOW":
                try:
                    # Get IOC value and type directly from search result
                    ioc_type_raw = ioc.get("ioc_type", "")
                    ioc_value = ioc.get("value", "")
                    
                    if not ioc_value or not ioc_type_raw:
                        continue
                    
                    sigma_type = sigma_type_map.get(ioc_type_raw, None)
                    if not sigma_type:
                        continue
                    
                    rule = self.generate_from_ioc(
                        ioc_value=ioc_value,
                        ioc_type=sigma_type,
                        actor=actor_name,
                        source=ioc.get("source", "CTI Platform")
                    )
                    rules.append(rule)
                except Exception as e:
                    print(f"[Sigma] Error generating rule for IOC {ioc.get('id')}: {e}")
        
        return rules
    
    def generate_from_causal_edges(
        self,
        relation_types: List[str] = None,
        actor_filter: str = None
    ) -> List[Dict]:
        """
        Generate Sigma rules leveraging causal graph edges.
        Uses knowledge graph to find actor → tool → target relationships.
        
        Args:
            relation_types: Filter by relation (uses, exploits, targets)
            actor_filter: Filter by specific actor
            
        Returns:
            List of Sigma rules with enriched context
        """
        if not self.knowledge_graph:
            return []
        
        rules = []
        
        # Get causal edges
        edges = self.knowledge_graph.get_edges_by_type(
            relation_types or ["uses", "exploits", "targets"]
        )
        
        for edge in edges:
            # Extract from edge
            subject = edge.get("subject", "")
            relation = edge.get("relation", "")
            obj = edge.get("object", "")
            
            # Filter by actor if specified
            if actor_filter and actor_filter.lower() not in subject.lower():
                continue
            
            # Determine IOC type from object
            ioc_type, ioc_value = self._parse_object_to_ioc(obj)
            
            if not ioc_value:
                continue
            
            # Get MITRE tags from relation
            mitre_tag = RELATION_TO_MITRE.get(relation, "attack.impact")
            
            try:
                rule = self.generate_from_ioc(
                    ioc_value=ioc_value,
                    ioc_type=ioc_type,
                    actor=subject,
                    tags=[mitre_tag]
                )
                rule["metadata"]["causal_relation"] = relation
                rule["metadata"]["target"] = obj
                rules.append(rule)
            except ValueError:
                continue
        
        return rules
    
    def _parse_object_to_ioc(self, obj: str) -> Tuple[str, str]:
        """Parse knowledge graph object to IOC type/value."""
        obj = obj.strip()
        
        # IP pattern
        ip_match = re.match(r'^(\d{1,3}\.){3}\d{1,3}$', obj)
        if ip_match:
            return "ip", obj
        
        # Domain pattern
        if re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}', obj):
            return "domain", obj
        
        # URL pattern
        if obj.startswith(("http://", "https://", "ftp://")):
            return "url", obj
        
        # Hash patterns
        if re.match(r'^[a-fA-F0-9]{32}$', obj):
            return "hash_md5", obj
        if re.match(r'^[a-fA-F0-9]{64}$', obj):
            return "hash_sha256", obj
        
        return None, None
    
    def export_yaml(
        self,
        rules: List[Dict],
        output_dir: str = None
    ) -> str:
        """
        Export rules as Sigma YAML format.
        
        Args:
            rules: List of Sigma rule dicts
            output_dir: Optional directory to write files
            
        Returns:
            YAML-formatted string
        """
        import yaml
        
        # Custom YAML representer for multiline strings
        def str_representer(dumper, data):
            if '\n' in data:
                return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
            return dumper.represent_scalar('tag:yaml.org,2002:str', data)
        
        yaml.add_representer(str, str_representer)
        
        output = []
        
        for rule in rules:
            # Remove metadata for clean export
            export_rule = {k: v for k, v in rule.items() if k != "metadata"}
            yaml_str = yaml.dump(export_rule, default_flow_style=False, sort_keys=False)
            output.append(yaml_str)
            output.append("---\n")
        
        result = "\n".join(output)
        
        # Write to files if directory specified
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            for rule in rules:
                filename = f"{rule['id']}.yaml"
                filepath = output_path / filename
                
                export_rule = {k: v for k, v in rule.items() if k != "metadata"}
                with open(filepath, 'w') as f:
                    yaml.dump(export_rule, f, default_flow_style=False, sort_keys=False)
        
        return result
    
    def export_sentinel(
        self,
        rules: List[Dict],
        output_dir: str = None
    ) -> Dict:
        """
        Export rules in Microsoft Sentinel KQL format.
        
        Args:
            rules: List of Sigma rule dicts
            output_dir: Optional directory to write files
            
        Returns:
            Dict with KQL queries per rule
        """
        kql_queries = {}
        
        for rule in rules:
            rule_id = rule["id"]
            title = rule["title"]
            selection = rule.get("selection", {})
            
            # Build KQL query
            conditions = []
            for field, values in selection.items():
                if isinstance(values, list):
                    value_list = ", ".join(f'"{v}"' for v in values)
                    conditions.append(f"{field} in ({value_list})")
            
            kql = " or ".join(conditions) if conditions else ""
            
            kql_queries[rule_id] = {
                "title": title,
                "query": kql,
                "description": rule.get("description", ""),
                "tags": rule.get("tags", [])
            }
        
        # Write to files if directory specified
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            for rule_id, kql_data in kql_queries.items():
                filename = f"{rule_id}.kql"
                filepath = output_path / filename
                
                with open(filepath, 'w') as f:
                    f.write(f"// {kql_data['title']}\n")
                    f.write(f"// Tags: {', '.join(kql_data['tags'])}\n")
                    f.write(kql_data["query"])
        
        return kql_queries


# Global singleton
_sigma_generator: Optional[SigmaGenerator] = None


def get_sigma_generator(
    cti_connector=None,
    knowledge_graph=None
) -> SigmaGenerator:
    """Get global Sigma generator."""
    global _sigma_generator
    
    if _sigma_generator is None:
        _sigma_generator = SigmaGenerator(cti_connector, knowledge_graph)
    
    return _sigma_generator


def generate_actor_rules(
    actor_name: str,
    cti_connector=None
) -> List[Dict]:
    """Convenience: Generate rules for a threat actor."""
    generator = get_sigma_generator(cti_connector)
    return generator.generate_from_actor(actor_name)


def generate_sentinel_rules(
    actor_name: str,
    cti_connector=None,
    output_dir: str = None
) -> Dict:
    """Convenience: Generate Sentinel KQL for a threat actor."""
    generator = get_sigma_generator(cti_connector)
    rules = generator.generate_from_actor(actor_name)
    return generator.export_sentinel(rules, output_dir)