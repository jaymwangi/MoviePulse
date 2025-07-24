import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

class DateSessionLogger:
    """Handles logging and retrieval of date night sessions"""
    
    def __init__(self):
        self.sessions_dir = Path("logs/date_sessions")
        self.file_path = self.sessions_dir / "date_sessions.json"
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self):
        """Create directory if it doesn't exist"""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def save_session(self, pack_a: str, pack_b: str, blended_prefs: Dict) -> str:
        """
        Save a new date night session
        
        Args:
            pack_a: Name of first starter pack
            pack_b: Name of second starter pack
            blended_prefs: Dictionary of blended preferences
            
        Returns:
            Generated session ID
        """
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "packs": [pack_a, pack_b],
            "blended_prefs": blended_prefs
        }
        
        existing_data = self._load_existing_sessions()
        existing_data[session_id] = session_data
        
        with open(self.file_path, 'w') as f:
            json.dump(existing_data, f, indent=2)
            
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Retrieve a specific session by ID"""
        sessions = self._load_existing_sessions()
        return sessions.get(session_id)
    
    def get_all_sessions(self) -> Dict:
        """Retrieve all logged sessions"""
        return self._load_existing_sessions()
    
    def _load_existing_sessions(self) -> Dict:
        """Load existing sessions or return empty dict"""
        if not self.file_path.exists():
            return {}
            
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
