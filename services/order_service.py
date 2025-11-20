from typing import Dict, Optional
import uuid
import json
from pathlib import Path
from datetime import datetime

class OrderService:
    """Service layer for handling order operations"""
    
    def __init__(self, catalog_repository):
        self.catalog_repository = catalog_repository
        self.orders_dir = Path(__file__).parent.parent / "data" / "orders"
        self.orders_dir.mkdir(parents=True, exist_ok=True)
    
    def process_order(self, name: str, email_address: str, product: str, quantity: int) -> Dict:
        """Process a new order with validation and persistence"""
        if not all([name, email_address, product]):
            raise ValueError("Name, email, and product are required fields")
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer")
        
        # Get and validate product details
        laptop_details = self.catalog_repository.get_laptop_details(product)
        if not laptop_details:
            raise ValueError(f"Product '{product}' not found in catalog")
        
        # Calculate prices
        unit_price = laptop_details["price"]
        total_price = unit_price * quantity
        
        # Generate order
        order_number = str(uuid.uuid4()).replace('-', '')[:6]
        order_data = {
            "order_number": order_number,
            "timestamp": datetime.utcnow().isoformat(),
            "customer": {
                "name": name,
                "email": email_address
            },
            "product": {
                "model": product,
                "specs": laptop_details["specs"],
                "unit_price": unit_price,
                "quantity": quantity,
                "total_price": total_price
            }
        }
        
        # Save order
        file_name = f"order-{order_number}.json"
        order_file = self.orders_dir / file_name
        order_file.write_text(json.dumps(order_data, indent=2))
        
        return {
            "message": f"Order {order_number} placed for {quantity}× {product}. Total price: ${total_price:.2f}. The order file is saved as {file_name}",
            "order_number": order_number,
            "file_name": file_name,
            "total_price": total_price
        }