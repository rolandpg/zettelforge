import sys
import json
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from zettelforge import MemoryManager
from zettelforge.knowledge_graph import get_knowledge_graph

def run_graph_test():
    print("=== Phase 6: Knowledge Graph Benchmark ===")
    
    tmpdir = tempfile.mkdtemp()
    amem = MemoryManager(jsonl_path=f"{tmpdir}/notes.jsonl", lance_path=f"{tmpdir}/vectordb")
    kg = get_knowledge_graph()
    
    with open(Path(__file__).parent / "dataset.json", "r") as f:
        dataset = json.load(f)
        
    print("Ingesting dataset and building Knowledge Graph...")
    for item in dataset:
        amem.remember(item["content"], domain="security_ops")
        
    print("\n--- Testing Graph Neighbors ---")
    print("Querying neighbors for 'Fancy Bear' (Alias for APT28)...\n")
    
    neighbors = amem.get_entity_relationships("actor", "Fancy Bear")
    
    if not neighbors:
        print("No neighbors found. Let's dump all graph nodes to debug:")
        print(kg._node_index)
        return
        
    for neighbor in neighbors:
        node = neighbor['node']
        rel = neighbor['relationship']
        print(f"APT28 -[{rel}]-> {node['entity_value'].upper()} ({node['entity_type']})")
        
    print("\n--- Multi-hop Graph Traversal ---")
    print("Traversing up to depth 2 from APT28...")
    paths = amem.traverse_graph("actor", "APT28", max_depth=2)
    
    for path in paths:
        path_str = "APT28"
        for step in path:
            path_str += f" -[{step['relationship']}]-> {step['to_value'].upper()} ({step['to_type']})"
        print(path_str)

if __name__ == "__main__":
    run_graph_test()
