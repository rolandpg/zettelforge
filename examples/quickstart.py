"""ZettelForge quickstart — 10 lines to CTI memory."""
from zettelforge import MemoryManager

mm = MemoryManager()

# Store threat intelligence — entities extracted automatically
note, status = mm.remember(
    "APT28 uses Cobalt Strike and XAgent for lateral movement. "
    "They exploit CVE-2024-3094 for initial access via T1021.",
    domain="security_ops",
)
print(f"Stored: {note.id} ({status})")
print(f"Entities: {note.semantic.entities}")

# Recall with alias resolution (APT28 = Fancy Bear)
results = mm.recall("What tools does Fancy Bear use?")
for r in results:
    print(f"Found: {r.content.raw[:80]}...")
