import sqlite3

DB_FILE = "groceries.db"


def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        category TEXT,
        default_price REAL,
        meal_type TEXT,       -- 'breakfast', 'dinner', 'both', 'snack'
        diet_tags TEXT,       -- comma-separated: 'protein','vegan','carb','fat'
        unit TEXT             -- 'each', 'kg', 'litre', 'pack'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS store_prices (
        product_id INTEGER,
        store_id INTEGER,
        price REAL,
        PRIMARY KEY(product_id, store_id),
        FOREIGN KEY(product_id) REFERENCES products(id),
        FOREIGN KEY(store_id) REFERENCES stores(id)
    )
    """)

    conn.commit()
    conn.close()


def seed_db():
    conn = get_connection()
    cursor = conn.cursor()

    products = [
        # name, category, default_price, meal_type, diet_tags, unit
        ("Eggs",           "Dairy",      1.89,  "both",      "protein",           "pack of 12"),
        ("Oats",           "Grain",      1.20,  "breakfast", "carb,fiber",        "500g"),
        ("Milk",           "Dairy",      1.10,  "both",      "protein,calcium",   "2L"),
        ("Chicken Breast", "Meat",       5.50,  "dinner",    "protein,lowfat",    "500g"),
        ("Ground Beef",    "Meat",       4.80,  "dinner",    "protein,fat",       "500g"),
        ("Salmon Fillet",  "Fish",       6.00,  "dinner",    "protein,omega3",    "300g"),
        ("Tuna Can",       "Fish",       1.20,  "both",      "protein",           "each"),
        ("Rice",           "Grain",      1.50,  "dinner",    "carb",              "1kg"),
        ("Pasta",          "Grain",      1.00,  "dinner",    "carb",              "500g"),
        ("Bread",          "Bakery",     1.10,  "breakfast", "carb",              "800g loaf"),
        ("Bacon",          "Meat",       3.00,  "breakfast", "protein,fat",       "250g"),
        ("Sausages",       "Meat",       2.50,  "both",      "protein,fat",       "6 pack"),
        ("Greek Yogurt",   "Dairy",      2.20,  "breakfast", "protein,probiotic", "500g"),
        ("Cottage Cheese", "Dairy",      1.80,  "both",      "protein,lowfat",    "300g"),
        ("Beans",          "Legumes",    0.85,  "both",      "protein,fiber,vegan","400g can"),
        ("Lentils",        "Legumes",    1.10,  "dinner",    "protein,fiber,vegan","500g"),
        ("Broccoli",       "Vegetables", 0.89,  "dinner",    "fiber,vegan",       "400g"),
        ("Spinach",        "Vegetables", 1.00,  "both",      "iron,vegan",        "200g"),
        ("Peanut Butter",  "Pantry",     2.50,  "breakfast", "protein,fat",       "340g"),
        ("Protein Powder", "Supplement", 18.00, "both",      "protein",           "1kg"),
        ("Cheddar Cheese", "Dairy",      2.80,  "both",      "protein,fat",       "400g"),
        ("Sweet Potato",   "Vegetables", 1.20,  "dinner",    "carb,fiber,vegan",  "750g"),
        ("Olive Oil",      "Pantry",     4.50,  "both",      "fat",               "500ml"),
        ("Banana",         "Fruit",      0.90,  "breakfast", "carb,fiber,vegan",  "5 pack"),
        ("Whey Protein Bar","Snack",     3.50,  "both",      "protein",           "4 pack"),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO products (name, category, default_price, meal_type, diet_tags, unit)
        VALUES (?,?,?,?,?,?)
    """, products)

    stores = [("Aldi",), ("Tesco",), ("Asda",), ("Sainsbury's",)]
    cursor.executemany("INSERT OR IGNORE INTO stores (name) VALUES (?)", stores)

    # Store price variations (product_id, store_id, price)
    # Product IDs follow insertion order starting at 1
    prices = [
        # Eggs
        (1,1,1.59),(1,2,1.89),(1,3,1.79),(1,4,1.99),
        # Oats
        (2,1,0.99),(2,2,1.20),(2,3,1.10),(2,4,1.25),
        # Milk
        (3,1,0.99),(3,2,1.10),(3,3,1.05),(3,4,1.15),
        # Chicken Breast
        (4,1,4.99),(4,2,5.50),(4,3,5.25),(4,4,5.75),
        # Ground Beef
        (5,1,4.50),(5,2,4.80),(5,3,4.65),(5,4,5.00),
        # Salmon
        (6,1,5.50),(6,2,6.00),(6,3,5.75),(6,4,6.25),
        # Tuna
        (7,1,0.99),(7,2,1.20),(7,3,1.10),(7,4,1.30),
        # Rice
        (8,1,1.20),(8,2,1.50),(8,3,1.35),(8,4,1.60),
        # Pasta
        (9,1,0.85),(9,2,1.00),(9,3,0.90),(9,4,1.05),
        # Bread
        (10,1,0.89),(10,2,1.10),(10,3,0.99),(10,4,1.15),
        # Bacon
        (11,1,2.75),(11,2,3.00),(11,3,2.90),(11,4,3.10),
        # Sausages
        (12,1,2.20),(12,2,2.50),(12,3,2.35),(12,4,2.65),
        # Greek Yogurt
        (13,1,1.89),(13,2,2.20),(13,3,2.00),(13,4,2.35),
        # Cottage Cheese
        (14,1,1.55),(14,2,1.80),(14,3,1.65),(14,4,1.90),
        # Beans
        (15,1,0.69),(15,2,0.85),(15,3,0.79),(15,4,0.89),
        # Lentils
        (16,1,0.90),(16,2,1.10),(16,3,0.99),(16,4,1.15),
        # Broccoli
        (17,1,0.75),(17,2,0.89),(17,3,0.82),(17,4,0.95),
        # Spinach
        (18,1,0.85),(18,2,1.00),(18,3,0.90),(18,4,1.05),
        # Peanut Butter
        (19,1,2.20),(19,2,2.50),(19,3,2.35),(19,4,2.65),
        # Protein Powder
        (20,1,15.99),(20,2,18.00),(20,3,16.99),(20,4,19.00),
        # Cheddar
        (21,1,2.50),(21,2,2.80),(21,3,2.65),(21,4,2.95),
        # Sweet Potato
        (22,1,0.99),(22,2,1.20),(22,3,1.10),(22,4,1.25),
        # Olive Oil
        (23,1,3.99),(23,2,4.50),(23,3,4.25),(23,4,4.75),
        # Banana
        (24,1,0.75),(24,2,0.90),(24,3,0.85),(24,4,0.95),
        # Protein Bar
        (25,1,3.00),(25,2,3.50),(25,3,3.25),(25,4,3.75),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO store_prices (product_id, store_id, price)
        VALUES (?,?,?)
    """, prices)

    conn.commit()
    conn.close()


def get_all_products_with_prices():
    """Return all products with their cheapest store price"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            p.id,
            p.name,
            p.category,
            p.default_price,
            p.meal_type,
            p.diet_tags,
            p.unit,
            (
                SELECT MIN(sp2.price)
                FROM store_prices sp2
                WHERE sp2.product_id = p.id
            ) AS cheapest_price,
            (
                SELECT s2.name
                FROM store_prices sp3
                JOIN stores s2 ON s2.id = sp3.store_id
                WHERE sp3.product_id = p.id
                ORDER BY sp3.price ASC
                LIMIT 1
            ) AS cheapest_store
        FROM products p
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_store_prices_for_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.name as store, sp.price
        FROM store_prices sp
        JOIN stores s ON s.id = sp.store_id
        WHERE sp.product_id = ?
        ORDER BY sp.price ASC
    """, (product_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]