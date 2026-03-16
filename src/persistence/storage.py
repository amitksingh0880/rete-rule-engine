import json
import os
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class StorageManager:
    """Handles persistence of rules and categories to local JSON files."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.rules_file = os.path.join(data_dir, "rules.json")
        self.categories_file = os.path.join(data_dir, "categories.json")
        
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        self._ensure_file(self.rules_file, {})
        self._ensure_file(self.categories_file, [])

    def _ensure_file(self, path: str, default: Any):
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump(default, f, indent=2)

    def save_rules(self, rules: Dict[str, str]):
        """Save a dictionary of rule_id -> dsl_source."""
        try:
            with open(self.rules_file, "w") as f:
                json.dump(rules, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save rules: {e}")

    def load_rules(self) -> Dict[str, str]:
        """Load the rules dictionary."""
        try:
            with open(self.rules_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            return {}

    def save_categories(self, categories: List[Dict[str, Any]]):
        """Save the list of categories."""
        try:
            with open(self.categories_file, "w") as f:
                json.dump(categories, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save categories: {e}")

    def load_categories(self) -> List[Dict[str, Any]]:
        """Load the categories list."""
        try:
            with open(self.categories_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load categories: {e}")
            return []
