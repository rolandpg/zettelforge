"""
Seed TypeDB with known CTI entity aliases.

Inserts alias-of relations so TypeDB can resolve:
  "Fancy Bear" -> APT28
  "Cozy Bear" -> APT29
  "Pawn Storm" -> APT28
  etc.

Run: python -m zettelforge.schema.seed_aliases
"""
from zettelforge.typedb_client import TypeDBKnowledgeGraph

# Known threat actor aliases: {canonical: [aliases]}
ACTOR_ALIASES = {
    "apt28": ["fancy bear", "fancy-bear", "pawn storm", "pawn-storm", "sofacy", "sednit", "strontium", "forest blizzard"],
    "apt29": ["cozy bear", "cozy-bear", "the dukes", "nobelium", "midnight blizzard"],
    "apt31": ["zirconium", "judgment panda"],
    "lazarus": ["lazarus group", "hidden cobra", "zinc", "diamond sleet"],
    "sandworm": ["voodoo bear", "iridium", "seashell blizzard"],
    "volt typhoon": ["volt-typhoon", "bronze silhouette", "vanguard panda"],
    "kimsuky": ["velvet chollima", "thallium", "emerald sleet"],
    "turla": ["venomous bear", "snake", "waterbug", "krypton", "secret blizzard"],
    "muddywater": ["muddy-water", "mercury", "mango sandstorm"],
}

# Known tool aliases
TOOL_ALIASES = {
    "cobalt strike": ["cobalt-strike", "cobaltstrike", "cs beacon"],
    "metasploit": ["msf", "metasploit framework"],
    "mimikatz": ["mimi"],
}


def seed_aliases(kg: TypeDBKnowledgeGraph = None):
    """Seed alias relations into TypeDB."""
    if kg is None:
        kg = TypeDBKnowledgeGraph()

    count = 0

    # Actor aliases
    for canonical, aliases in ACTOR_ALIASES.items():
        kg.add_node("actor", canonical)
        for alias_name in aliases:
            kg.add_node("actor", alias_name)
            # Use add_edge with ALIAS_OF relationship
            # This doesn't map to a standard STIX relation in RELATION_MAP,
            # so we insert directly via TypeDB
            try:
                from typedb.driver import TransactionType
                canonical_stix = kg._stix_id("actor", canonical)
                alias_stix = kg._stix_id("actor", alias_name)
                tx = kg._driver.transaction(kg.database, TransactionType.WRITE)
                tx.query(
                    f'match $c isa threat-actor, has stix-id "{canonical_stix}"; '
                    f'$a isa threat-actor, has stix-id "{alias_stix}"; '
                    f'insert (canonical: $c, aliased: $a) isa alias-of, has confidence 1.0;'
                ).resolve()
                tx.commit()
                count += 1
            except Exception:
                pass  # May already exist

    # Tool aliases
    for canonical, aliases in TOOL_ALIASES.items():
        kg.add_node("tool", canonical)
        for alias_name in aliases:
            kg.add_node("tool", alias_name)
            try:
                from typedb.driver import TransactionType
                canonical_stix = kg._stix_id("tool", canonical)
                alias_stix = kg._stix_id("tool", alias_name)
                tx = kg._driver.transaction(kg.database, TransactionType.WRITE)
                tx.query(
                    f'match $c isa tool, has stix-id "{canonical_stix}"; '
                    f'$a isa tool, has stix-id "{alias_stix}"; '
                    f'insert (canonical: $c, aliased: $a) isa alias-of, has confidence 1.0;'
                ).resolve()
                tx.commit()
                count += 1
            except Exception:
                pass

    return count


if __name__ == "__main__":
    count = seed_aliases()
    print(f"Seeded {count} alias relations into TypeDB.")
