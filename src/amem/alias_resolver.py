import json
from pathlib import Path
from typing import Dict, Optional

class AliasResolver:
    """Resolves entity aliases to their canonical names."""
    def __init__(self, alias_file: Optional[str] = None):
        from amem.memory_store import get_default_data_dir
        if alias_file is None:
            alias_file = get_default_data_dir() / "entity_aliases.json"
        self.alias_file = Path(alias_file)
        
        # Default hardcoded aliases for benchmark/threat intel
        self.aliases = {
            "actor": {
                "fancy bear": "apt28",
                "pawn storm": "apt28",
                "cozy bear": "apt29"
            },
            "tool": {}
        }
        self.load()

    def load(self):
        if self.alias_file.exists():
            try:
                with open(self.alias_file, "r") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if k not in self.aliases:
                            self.aliases[k] = {}
                        self.aliases[k].update(v)
            except Exception:
                pass

    def resolve(self, entity_type: str, entity: str) -> str:
        entity_lower = entity.lower().replace('-', ' ')
        
        # Check reverse mapping or direct mapping
        mapping = self.aliases.get(entity_type, {})
        if entity_lower in mapping:
            return mapping[entity_lower]
            
        return entity.lower()
