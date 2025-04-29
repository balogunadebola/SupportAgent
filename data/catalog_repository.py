from typing import Dict, Optional, List
import json
from pathlib import Path

class CatalogRepository:
    """Repository pattern implementation for laptop catalog data"""
    
    def __init__(self, data_file: str = "catalog.json"):
        self.data_file = Path(__file__).parent / data_file
        self._ensure_data_file_exists()
    
    def _ensure_data_file_exists(self) -> None:
        """Ensure the catalog file exists with initial data if needed"""
        if not self.data_file.exists():
            initial_catalog = {
                "gaming": {
                    "ROG Strix G15": {"price": 1499.99, "specs": "AMD Ryzen 9, RTX 3070, 32GB RAM, 1TB SSD"},
                    "Alienware m17": {"price": 1999.99, "specs": "Intel i9, RTX 3080, 32GB RAM, 2TB SSD"},
                    "Razer Blade 15": {"price": 1799.99, "specs": "Intel i7, RTX 3070, 16GB RAM, 1TB SSD"}
                },
                "business": {
                    "ThinkPad X1 Carbon": {"price": 1399.99, "specs": "Intel i7, 16GB RAM, 512GB SSD"},
                    "Dell XPS 13": {"price": 1299.99, "specs": "Intel i5, 16GB RAM, 512GB SSD"},
                    "HP Elite Dragonfly": {"price": 1599.99, "specs": "Intel i7, 32GB RAM, 1TB SSD"}
                },
                "budget": {
                    "Acer Aspire 5": {"price": 649.99, "specs": "AMD Ryzen 5, 8GB RAM, 256GB SSD"},
                    "Lenovo IdeaPad 3": {"price": 549.99, "specs": "Intel i3, 8GB RAM, 256GB SSD"},
                    "HP Pavilion": {"price": 699.99, "specs": "AMD Ryzen 7, 16GB RAM, 512GB SSD"}
                }
            }
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            self.data_file.write_text(json.dumps(initial_catalog, indent=2))
    
    def get_categories(self) -> List[str]:
        """Get all available laptop categories"""
        catalog = json.loads(self.data_file.read_text())
        return list(catalog.keys())
    
    def get_laptops_in_category(self, category: str) -> Dict:
        """Get all laptops in a specific category"""
        catalog = json.loads(self.data_file.read_text())
        return catalog.get(category, {})
    
    def get_laptop_details(self, model: str) -> Optional[Dict]:
        """Get details for a specific laptop model"""
        catalog = json.loads(self.data_file.read_text())
        for category in catalog.values():
            if model in category:
                return category[model]
        return None
    
    def update_laptop_details(self, category: str, model: str, details: Dict) -> bool:
        """Update details for a specific laptop model"""
        catalog = json.loads(self.data_file.read_text())
        if category not in catalog:
            return False
        
        catalog[category][model] = details
        self.data_file.write_text(json.dumps(catalog, indent=2))
        return True