import json
from pathlib import Path
from typing import Dict, Any, Optional

STATE_FILE = Path.home() / ".config" / "shipmybox" / "state.json"

def load_state() -> Optional[Dict[str, Any]]:
    """Load the last saved parcel state.
    
    Returns:
        Dict containing the state of the last parcel, or None if no state exists.
    """
    if not STATE_FILE.exists():
        return None
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        # If the state file is corrupted or unreadable, treat it as non-existent
        return None

def save_state(state: Dict[str, Any]) -> None:
    """Save the parcel state.
    
    Args:
        state: Dict containing the parcel details to persist.
    """
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
