#!/usr/bin/env python3
"""
SkillManager - Hermes-inspired procedural memory

Creates and manages skills that capture "how to do X" from experience.

Skill structure:
    workspace/skills/
    ├── SKILL.md (template)
    ├── category/
    │   └── skill-name/
    │       └── SKILL.md
    ├── references/
    ├── templates/
    ├── scripts/
    └── assets/

Usage:
    from memory.skill_manager import SkillManager, create_skill
    
    sm = SkillManager()
    
    # List skills
    skills = sm.list_skills()
    
    # Create from nudge
    result = sm.create_from_nudge(
        name="cti-collection",
        description="Run the CTI collection pipeline",
        procedure="Steps here...",
        examples=["Example usage..."]
    )
    
    # Get skill content
    skill = sm.get_skill("cti-collection")
"""

import logging
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Default skills directory
DEFAULT_SKILLS_DIR = "skills"

# Skill file name
SKILL_FILE = "SKILL.md"

# Character limits
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024

# Valid name pattern (filesystem-safe, URL-friendly)
VALID_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9._-]*$')

# Security patterns (same as memory scanning)
_INJECTION_PATTERNS = [
    (r'ignore previous', "prompt_injection"),
    (r'you are now', "role_hijack"),
    (r'curl.*KEY', "exfil_curl"),
    (r'wget.*KEY', "exfil_wget"),
    (r'authorized_keys', "ssh_backdoor"),
]

_INVISIBLE_CHARS = {'\u200b', '\u200c', '\u200d', '\ufeff'}


@dataclass
class SkillInfo:
    """Metadata about a skill."""
    name: str
    identifier: str  # category/name
    description: str
    category: str
    path: Path
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


def scan_content(content: str) -> Optional[str]:
    """Scan for injection patterns. Returns error or None."""
    for char in _INVISIBLE_CHARS:
        if char in content:
            return f"Invisible char U+{ord(char):04X}"
    for pattern, threat in _INJECTION_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return f"Threat: {threat}"
    return None


class SkillManager:
    """
    Manages procedural memories (skills).
    
    Skills capture HOW to do something, not WHAT something is.
    Created autonomously after successful complex tasks.
    """
    
    def __init__(self, skills_dir: Optional[Path] = None):
        if skills_dir is None:
            workspace = Path(__file__).parent.parent
            skills_dir = workspace / DEFAULT_SKILLS_DIR
        
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
    
    def list_skills(self) -> List[SkillInfo]:
        """List all available skills."""
        skills = []
        
        if not self.skills_dir.exists():
            return skills
        
        for category_dir in self.skills_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            category = category_dir.name
            
            for skill_dir in category_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                
                skill_path = skill_dir / SKILL_FILE
                if not skill_path.exists():
                    continue
                
                # Parse frontmatter
                name = skill_dir.name
                identifier = f"{category}/{name}"
                description, created, updated = self._parse_skill_header(skill_path)
                
                skills.append(SkillInfo(
                    name=name,
                    identifier=identifier,
                    description=description or "",
                    category=category,
                    path=skill_path,
                    created_at=created,
                    updated_at=updated,
                ))
        
        return sorted(skills, key=lambda s: s.identifier)
    
    def _parse_skill_header(self, path: Path) -> tuple:
        """Parse skill frontmatter for description and timestamps."""
        try:
            content = path.read_text()
            
            # Check for YAML frontmatter
            if not content.startswith('---'):
                return None, None, None
            
            end_match = re.search(r'\n---\s*\n', content[3:])
            if not end_match:
                return None, None, None
            
            yaml_content = content[3:end_match.start()]
            
            # Simple parse (name: value)
            desc_match = re.search(r'description:\s*(.+)', yaml_content)
            desc = desc_match.group(1).strip() if desc_match else None
            
            created_match = re.search(r'created:\s*(.+)', yaml_content)
            created = created_match.group(1).strip() if created_match else None
            
            updated_match = re.search(r'updated:\s*(.+)', yaml_content)
            updated = updated_match.group(1).strip() if updated_match else None
            
            return desc, created, updated
            
        except Exception as e:
            logger.warning(f"Failed to parse skill header: {e}")
            return None, None, None
    
    def get_skill(self, identifier: str) -> Optional[Dict]:
        """
        Get skill by identifier (category/name).
        
        Returns:
            Dict with name, description, content, category, path or None
        """
        parts = identifier.split('/')
        if len(parts) != 2:
            # Try to find by name only
            for skill in self.list_skills():
                if skill.name == identifier:
                    parts = [skill.category, skill.name]
                    break
            else:
                return None
        
        category, name = parts
        skill_path = self.skills_dir / category / name / SKILL_FILE
        
        if not skill_path.exists():
            return None
        
        content = skill_path.read_text()
        desc, created, updated = self._parse_skill_header(skill_path)
        
        return {
            "name": name,
            "identifier": identifier,
            "description": desc or "",
            "category": category,
            "content": content,
            "path": skill_path,
            "created_at": created,
            "updated_at": updated,
        }
    
    def create(
        self,
        name: str,
        description: str,
        procedure: str,
        category: str = "general",
        examples: Optional[List[str]] = None,
        references: Optional[List[str]] = None,
    ) -> Dict[str, any]:
        """
        Create a new skill.
        
        Args:
            name: Skill name (filesystem-safe)
            description: One-line description
            procedure: How-to steps
            category: Category for organization
            examples: Usage examples
            references: Reference links
            
        Returns:
            {"success": bool, "error": str or None, "skill": SkillInfo or None}
        """
        # Validate name
        if not name:
            return {"success": False, "error": "Name required", "skill": None}
        
        if len(name) > MAX_NAME_LENGTH:
            return {"success": False, "error": f"Name exceeds {MAX_NAME_LENGTH}", "skill": None}
        
        if not VALID_NAME_RE.match(name):
            return {
                "success": False,
                "error": "Invalid name. Use lowercase, numbers, hyphens, dots, underscores. Start with letter/number.",
                "skill": None
            }
        
        # Validate description
        if len(description) > MAX_DESCRIPTION_LENGTH:
            return {"success": False, "error": f"Description exceeds {MAX_DESCRIPTION_LENGTH}", "skill": None}
        
        # Scan content
        for item in [description, procedure]:
            scan_result = scan_content(item)
            if scan_result:
                return {"success": False, "error": f"Blocked: {scan_result}", "skill": None}
        
        # Create directory
        skill_dir = self.skills_dir / category / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        # Build content
        from datetime import datetime
        now = datetime.now().isoformat()
        
        content_lines = [
            "---",
            f"name: {name}",
            f"description: {description}",
            f"category: {category}",
            f"created: {now}",
            f"updated: {now}",
            "---",
            "",
            f"# {name}",
            "",
            "## When to Use",
            f"{description}",
            "",
            "## Procedure",
            procedure,
        ]
        
        if examples:
            content_lines.extend([
                "",
                "## Examples",
            ])
            for ex in examples:
                content_lines.append(f"- {ex}")
        
        if references:
            content_lines.extend([
                "",
                "## References",
            ])
            for ref in references:
                content_lines.append(f"- {ref}")
        
        content_lines.append("")
        
        # Write
        skill_path = skill_dir / SKILL_FILE
        skill_path.write_text("\n".join(content_lines))
        
        logger.info(f"Created skill: {category}/{name}")
        
        return {
            "success": True,
            "error": None,
            "skill": SkillInfo(
                name=name,
                identifier=f"{category}/{name}",
                description=description,
                category=category,
                path=skill_path,
                created_at=now,
                updated_at=now,
            )
        }
    
    def update(self, identifier: str, updates: Dict) -> Dict[str, any]:
        """
        Update skill fields.
        
        Args:
            identifier: category/name
            updates: Dict with description, procedure, examples, etc.
            
        Returns:
            {"success": bool, "error": str or None}
        """
        skill = self.get_skill(identifier)
        if not skill:
            return {"success": False, "error": f"Skill not found: {identifier}"}
        
        # Scan updates
        for key in ['description', 'procedure']:
            if key in updates:
                scan_result = scan_content(updates[key])
                if scan_result:
                    return {"success": False, "error": f"Blocked: {scan_result}"}
        
        # Read current content
        content = skill['path'].read_text()
        
        # Update frontmatter
        from datetime import datetime
        now = datetime.now().isoformat()
        
        for key, value in updates.items():
            if key in ['description', 'category']:
                # Update in frontmatter
                pattern = re.compile(rf'{key}:\s*.+')
                if pattern.search(content):
                    content = pattern.sub(f'{key}: {value}', content)
                else:
                    # Add it
                    content = content.replace('---', f'---\n{key}: {value}', 1)
        
        # Always update updated timestamp
        pattern = re.compile(r'updated:\s*.+')
        content = pattern.sub(f'updated: {now}', content)
        
        # Update procedure if provided
        if 'procedure' in updates:
            # Find ## Procedure section and replace
            lines = content.split('\n')
            new_lines = []
            in_procedure = False
            for line in lines:
                if line == '## Procedure':
                    in_procedure = True
                    new_lines.append(line)
                elif in_procedure and line.startswith('## '):
                    in_procedure = False
                    new_lines.append(updates['procedure'])
                    new_lines.append('')
                    new_lines.append(line)
                elif not in_procedure:
                    new_lines.append(line)
            
            # If procedure wasn't found, add it
            if '## Procedure' not in content:
                insert_idx = content.find('\n---\n')
                if insert_idx > 0:
                    new_content = content[:insert_idx] + '\n---\n\n## Procedure\n' + updates['procedure'] + content[insert_idx:]
                    content = new_content
            
            content = '\n'.join(new_lines)
        
        # Write
        skill['path'].write_text(content)
        
        return {"success": True, "error": None}
    
    def delete(self, identifier: str) -> Dict[str, any]:
        """
        Delete a skill.
        
        Returns:
            {"success": bool, "error": str or None}
        """
        skill = self.get_skill(identifier)
        if not skill:
            return {"success": False, "error": f"Skill not found: {identifier}"}
        
        # Remove directory
        skill_dir = skill['path'].parent
        shutil.rmtree(skill_dir)
        
        logger.info(f"Deleted skill: {identifier}")
        return {"success": True, "error": None}
    
    def search(self, query: str) -> List[SkillInfo]:
        """
        Search skills by name/description.
        
        Returns:
            List of matching SkillInfo
        """
        query_lower = query.lower()
        results = []
        
        for skill in self.list_skills():
            if (query_lower in skill.name.lower() or 
                query_lower in skill.description.lower()):
                results.append(skill)
        
        return results


# ============================================================================
# CLI for testing
# ============================================================================

if __name__ == "__main__":
    import sys
    
    sm = SkillManager()
    
    print("=== SkillManager Test ===\n")
    
    # List existing skills
    skills = sm.list_skills()
    print(f"Existing skills: {len(skills)}")
    for s in skills:
        print(f"  - {s.identifier}: {s.description[:50]}...")
    
    # Create a test skill
    print("\n--- Creating test skill ---")
    result = sm.create(
        name="test-cti-collect",
        description="Run CTI collection pipeline",
        category="security",
        procedure="1. cd ~/cti-workspace\n2. python3 collect_cisa_kev.py\n3. python3 collect_nvd.py\n4. python3 threat_alert.py",
        examples=["python3 collect_cisa_kev.py"],
    )
    
    if result['success']:
        print(f"Created: {result['skill'].identifier}")
    else:
        print(f"Error: {result['error']}")
    
    # List again
    print("\n--- After creation ---")
    skills = sm.list_skills()
    print(f"Total skills: {len(skills)}")
    
    # Search
    print("\n--- Search for 'cti' ---")
    results = sm.search("cti")
    for r in results:
        print(f"  - {r.identifier}")
    
    # Get skill
    print("\n--- Get skill content ---")
    skill = sm.get_skill("security/test-cti-collect")
    if skill:
        print(f"Name: {skill['name']}")
        print(f"Description: {skill['description']}")
        print(f"\nContent preview:\n{skill['content'][:300]}...")
    
    # Cleanup
    print("\n--- Cleanup ---")
    result = sm.delete("security/test-cti-collect")
    print(f"Delete: {result}")
