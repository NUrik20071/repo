"""
prices.py - MLBB Shop Pricing System
Manages product prices for multiple currencies and regions
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# ============================================================================
# PRICE DATA STRUCTURE
# ============================================================================

PRICE_DATA = {
    "KZ": {
        "currency": "₸",
        "currency_name": "KZT",
        "region": "🇰🇿 Kazakhstan",
        "products": {
            "passes": [
                {"id": "diamond_pass", "name": "🎫 Алмазный Пропуск", "price": 850},
                {"id": "twilight_pass", "name": "🌆 Сумеречный Пропуск", "price": 4125},
            ],
            "bundles": [
                {"id": "weekly_elite", "name": "🎁 Недельный Элитный Набор", "price": 450},
                {"id": "monthly_epic", "name": "🎁 Месячный Эпический Набор", "price": 2350},
            ],
            "diamonds": [
                {"id": "d50", "name": "💎 50+5 (Бонус 50+50)", "price": 450, "bonus": True},
                {"id": "d150", "name": "💎 150+15", "price": 1370, "bonus": True},
                {"id": "d250", "name": "💎 250+25", "price": 2200, "bonus": True},
                {"id": "d500", "name": "💎 500+65", "price": 4350, "bonus": True},
                {"id": "d78", "name": "💎 78+8", "price": 710},
                {"id": "d156", "name": "💎 156+16", "price": 1400},
                {"id": "d234", "name": "💎 234+23", "price": 2060},
                {"id": "d625", "name": "💎 625+81", "price": 5450},
                {"id": "d1860", "name": "💎 1860+335", "price": 16200},
                {"id": "d3099", "name": "💎 3099+589", "price": 27070},
                {"id": "d4649", "name": "💎 4649+883", "price": 40500},
                {"id": "d7740", "name": "💎 7740+1548", "price": 66600},
            ],
            "stars": [
                {"id": "s50", "name": "⭐ 50 Stars", "price": 500},
                {"id": "s75", "name": "⭐ 75 Stars", "price": 740},
                {"id": "s100", "name": "⭐ 100 Stars", "price": 950},
                {"id": "s150", "name": "⭐ 150 Stars", "price": 1400},
                {"id": "s250", "name": "⭐ 250 Stars", "price": 2300},
                {"id": "s350", "name": "⭐ 350 Stars", "price": 3200},
                {"id": "s500", "name": "⭐ 500 Stars", "price": 4500},
                {"id": "s750", "name": "⭐ 750 Stars", "price": 6700},
                {"id": "s1000", "name": "⭐ 1000 Stars", "price": 8900},
                {"id": "s1500", "name": "⭐ 1500 Stars", "price": 13300},
                {"id": "s2500", "name": "⭐ 2500 Stars", "price": 22000},
                {"id": "s5000", "name": "⭐ 5000 Stars", "price": 43500},
                {"id": "s10000", "name": "⭐ 10000 Stars", "price": 86500},
            ],
        }
    },
    "RU": {
        "currency": "₽",
        "currency_name": "RUB",
        "region": "🇷🇺 Russia",
        "products": {
            "passes": [
                {"id": "diamond_pass", "name": "🎫 Алмазный Пропуск", "price": 175},
                {"id": "twilight_pass", "name": "🌆 Сумеречный Пропуск", "price": 920},
            ],
            "bundles": [
                {"id": "weekly_elite", "name": "🎁 Недельный Элитный Набор", "price": 90},
                {"id": "monthly_epic", "name": "🎁 Месячный Эпический Набор", "price": 450},
            ],
            "diamonds": [
                {"id": "d50", "name": "💎 50+5 (Бонус 50+50)", "price": 90, "bonus": True},
                {"id": "d150", "name": "💎 150+15", "price": 265, "bonus": True},
                {"id": "d250", "name": "💎 250+25", "price": 430, "bonus": True},
                {"id": "d500", "name": "💎 500+65", "price": 880, "bonus": True},
                {"id": "d78", "name": "💎 78+8", "price": 145},
                {"id": "d156", "name": "💎 156+16", "price": 280},
                {"id": "d234", "name": "💎 234+23", "price": 405},
                {"id": "d625", "name": "💎 625+81", "price": 1095},
                {"id": "d1860", "name": "💎 1860+335", "price": 3315},
                {"id": "d3099", "name": "💎 3099+589", "price": 5530},
                {"id": "d4649", "name": "💎 4649+883", "price": 8350},
                {"id": "d7740", "name": "💎 7740+1548", "price": 13860},
            ],
            "stars": [
                {"id": "s50", "name": "⭐ 50 Stars", "price": 65},
                {"id": "s75", "name": "⭐ 75 Stars", "price": 97},
                {"id": "s100", "name": "⭐ 100 Stars", "price": 129},
                {"id": "s150", "name": "⭐ 150 Stars", "price": 189},
                {"id": "s250", "name": "⭐ 250 Stars", "price": 329},
                {"id": "s350", "name": "⭐ 350 Stars", "price": 459},
                {"id": "s500", "name": "⭐ 500 Stars", "price": 659},
                {"id": "s750", "name": "⭐ 750 Stars", "price": 989},
                {"id": "s1000", "name": "⭐ 1000 Stars", "price": 1349},
                {"id": "s1500", "name": "⭐ 1500 Stars", "price": 1999},
                {"id": "s2500", "name": "⭐ 2500 Stars", "price": 3399},
                {"id": "s5000", "name": "⭐ 5000 Stars", "price": 6799},
                {"id": "s10000", "name": "⭐ 10000 Stars", "price": 13699},
            ],
        }
    }
}

# ============================================================================
# DATABASE INITIALIZATION & MANAGEMENT
# ============================================================================

class PriceDatabase:
    """Manages SQLite database for product prices and pricing history"""
    
    def __init__(self, db_path: str = "shop.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize all database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Regions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regions (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                currency TEXT NOT NULL,
                currency_symbol TEXT NOT NULL
            )
        """)
        
        # Product categories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        """)
        
        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                category_id TEXT NOT NULL,
                name TEXT NOT NULL,
                has_bonus BOOLEAN DEFAULT 0,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)
        
        # Current prices
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                region_id TEXT NOT NULL,
                price INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(product_id, region_id),
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (region_id) REFERENCES regions(id)
            )
        """)
        
        # Price history for tracking changes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                region_id TEXT NOT NULL,
                old_price INTEGER,
                new_price INTEGER NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (region_id) REFERENCES regions(id)
            )
        """)
        
        # User ratings/stars (existing functionality)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_ratings (
                user_id INTEGER PRIMARY KEY,
                game_id TEXT,
                star_id TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stars_ru (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stars_kz (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def populate_initial_data(self):
        """Populate database with initial pricing data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Clear existing data (optional)
        # cursor.execute("DELETE FROM prices")
        # cursor.execute("DELETE FROM products")
        # cursor.execute("DELETE FROM categories")
        # cursor.execute("DELETE FROM regions")
        
        # Insert regions
        for region_code, region_data in PRICE_DATA.items():
            cursor.execute("""
                INSERT OR IGNORE INTO regions (id, name, currency, currency_symbol)
                VALUES (?, ?, ?, ?)
            """, (region_code, region_data["region"], region_data["currency_name"], region_data["currency"]))
        
        # Insert categories
        categories = ["passes", "bundles", "diamonds", "stars"]
        for category in categories:
            cursor.execute("""
                INSERT OR IGNORE INTO categories (id, name)
                VALUES (?, ?)
            """, (category, category.upper()))
        
        # Insert products and prices
        for region_code, region_data in PRICE_DATA.items():
            for category, products in region_data["products"].items():
                for product in products:
                    product_id = product["id"]
                    product_name = product["name"]
                    has_bonus = product.get("bonus", False)
                    price = product["price"]
                    
                    # Insert product if not exists
                    cursor.execute("""
                        INSERT OR IGNORE INTO products (id, category_id, name, has_bonus)
                        VALUES (?, ?, ?, ?)
                    """, (product_id, category, product_name, has_bonus))
                    
                    # Insert price
                    cursor.execute("""
                        INSERT OR IGNORE INTO prices (product_id, region_id, price)
                        VALUES (?, ?, ?)
                    """, (product_id, region_code, price))
        
        conn.commit()
        conn.close()
    
    def get_product_price(self, product_id: str, region_id: str) -> Optional[int]:
        """Get price for a product in a specific region"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT price FROM prices
            WHERE product_id = ? AND region_id = ?
        """, (product_id, region_id))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def update_price(self, product_id: str, region_id: str, new_price: int):
        """Update product price and track history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get old price
        old_price = self.get_product_price(product_id, region_id)
        
        # Update price
        cursor.execute("""
            INSERT OR REPLACE INTO prices (product_id, region_id, price, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (product_id, region_id, new_price))
        
        # Record in history
        cursor.execute("""
            INSERT INTO price_history (product_id, region_id, old_price, new_price)
            VALUES (?, ?, ?, ?)
        """, (product_id, region_id, old_price, new_price))
        
        conn.commit()
        conn.close()
    
    def get_all_prices(self, region_id: str) -> Dict[str, Dict]:
        """Get all prices for a region, organized by category"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.id, pr.name, c.id as category, p.price
            FROM prices p
            JOIN products pr ON p.product_id = pr.id
            JOIN categories c ON pr.category_id = c.id
            WHERE p.region_id = ?
            ORDER BY c.id, pr.name
        """, (region_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        # Organize by category
        organized = {}
        for row in results:
            category = row[2]
            if category not in organized:
                organized[category] = []
            organized[category].append({
                "id": row[0],
                "name": row[1],
                "price": row[3]
            })
        
        return organized
    
    def get_price_history(self, product_id: str, limit: int = 10) -> List[Dict]:
        """Get price change history for a product"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT product_id, region_id, old_price, new_price, changed_at
            FROM price_history
            WHERE product_id = ?
            ORDER BY changed_at DESC
            LIMIT ?
        """, (product_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]


# ============================================================================
# PRICE FORMATTING & DISPLAY
# ============================================================================

def format_price(price: int, currency_symbol: str) -> str:
    """Format price with currency symbol"""
    return f"{price} {currency_symbol}"


def get_formatted_prices(region_id: str, db: PriceDatabase) -> str:
    """Get formatted price list for a region"""
    region_data = PRICE_DATA[region_id]
    currency = region_data["currency"]
    region_name = region_data["region"]
    
    output = f"📊 ПРАЙС {region_name}:\n\n"
    
    prices = db.get_all_prices(region_id)
    
    for category, products in prices.items():
        output += f"**{category.upper()}**\n"
        for product in products:
            output += f"• {product['name']} — {format_price(product['price'], currency)}\n"
        output += "\n"
    
    return output


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Initialize database
    db = PriceDatabase("shop.db")
    db.populate_initial_data()
    
    # Print formatted prices
    print(get_formatted_prices("RU", db))
    print(get_formatted_prices("KZ", db))
    
    # Example: Update a price
    print("\n--- Updating 💎 50+5 price for KZ from 450 to 500 ---")
    db.update_price("d50", "KZ", 500)
    
    # Check price history
    history = db.get_price_history("d50")
    print("\nPrice History for d50:")
    for record in history:
        print(record)
