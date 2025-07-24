import json
from pathlib import Path
from typing import Dict, Optional

def load_starter_packs() -> Dict:
    """Load starter packs from JSON file"""
    packs_file = Path("static_data/starter_packs.json")
    with open(packs_file, "r") as f:
        return json.load(f)["packs"]  # Access the "packs" key

def get_pack_by_name(pack_name: str) -> Optional[Dict]:
    """Get a specific pack by name"""
    packs = load_starter_packs()
    return packs.get(pack_name)

def validate_pack_compatibility(pack_a: str, pack_b: str) -> bool:
    """Check if two packs can be blended"""
    pack_a_data = get_pack_by_name(pack_a)
    pack_b_data = get_pack_by_name(pack_b)
    
    if not pack_a_data or not pack_b_data:
        return False
        
    compatible_with_a = pack_a_data.get("compatible_with", [])
    compatible_with_b = pack_b_data.get("compatible_with", [])
    
    return (pack_b in compatible_with_a) or (pack_a in compatible_with_b)
