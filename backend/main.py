import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Support both package-style imports (uvicorn backend.main:app)
# and running this file directly (python backend/main.py)
try:  # pragma: no cover - simple import shim
    from .database import init_db, seed_db, get_connection
    from .llm_parser import parse_user_query
    from .basket_engine import build_meal_basket
    from .llm_basket import generate_basket_reasoning
except ImportError:  # Fallback when executed as a script
    from database import init_db, seed_db, get_connection
    from llm_parser import parse_user_query
    from basket_engine import build_meal_basket
    from llm_basket import generate_basket_reasoning

# -------------------------
# Logging
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# -------------------------
# App Init
# -------------------------
app = FastAPI(title="ShopQuick Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("Initializing database...")
init_db()
seed_db()
logger.info("Database ready.")


# -------------------------
# Models
# -------------------------
class BasketRequest(BaseModel):
    query: str


class PriceUpdateRequest(BaseModel):
    product: str
    store: str
    price: float


# -------------------------
# Routes
# -------------------------
@app.post("/basket")
def get_basket(req: BasketRequest):
    logger.info(f"===== NEW REQUEST: {req.query} =====")

    # 1. Parse query
    parsed = parse_user_query(req.query)
    logger.info(f"Parsed: {parsed}")

    # 2. Build smart basket
    basket_result = build_meal_basket(parsed)
    logger.info(f"Basket: {len(basket_result['basket'])} items, £{basket_result['total']}")

    # 3. LLM reasoning layer
    reasoning = generate_basket_reasoning(req.query, basket_result)
    logger.info(f"Reasoning: {reasoning.get('summary', '')[:100]}")

    return {
        "basket": basket_result["basket"],
        "total": basket_result["total"],
        "budget": basket_result["budget"],
        "remaining": basket_result["remaining"],
        "days": basket_result["days"],
        "meals": basket_result["meals"],
        "diet": basket_result["diet"],
        "people": basket_result["people"],
        "parsed_query": parsed,
        "summary": reasoning.get("summary", ""),
        "meal_notes": reasoning.get("meal_notes", {}),
        "tips": reasoning.get("tips", []),
        "estimated_protein_per_day": reasoning.get("estimated_protein_per_day"),
    }


@app.get("/products")
def list_products():
    """Return all products with store prices"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.name, p.category, p.default_price, p.meal_type, p.diet_tags, p.unit,
               s.name as store, sp.price as store_price
        FROM products p
        LEFT JOIN store_prices sp ON sp.product_id = p.id
        LEFT JOIN stores s ON s.id = sp.store_id
        ORDER BY p.name, sp.price ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    products = {}
    for r in rows:
        pid = r["id"]
        if pid not in products:
            products[pid] = {
                "id": pid,
                "name": r["name"],
                "category": r["category"],
                "default_price": r["default_price"],
                "meal_type": r["meal_type"],
                "diet_tags": r["diet_tags"],
                "unit": r["unit"],
                "store_prices": []
            }
        if r["store"]:
            products[pid]["store_prices"].append({
                "store": r["store"],
                "price": r["store_price"]
            })

    return {"products": list(products.values())}


@app.post("/price")
def update_price(req: PriceUpdateRequest):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM products WHERE name = ?", (req.product,))
    product_row = cursor.fetchone()
    if not product_row:
        return {"error": "Product not found"}

    cursor.execute("SELECT id FROM stores WHERE name = ?", (req.store,))
    store_row = cursor.fetchone()
    if not store_row:
        return {"error": "Store not found"}

    cursor.execute("""
        INSERT INTO store_prices (product_id, store_id, price)
        VALUES (?, ?, ?)
        ON CONFLICT(product_id, store_id)
        DO UPDATE SET price = excluded.price
    """, (product_row["id"], store_row["id"], req.price))

    conn.commit()
    conn.close()

    logger.info(f"Price updated: {req.product} @ {req.store} = £{req.price}")
    return {"status": "success", "product": req.product, "store": req.store, "new_price": req.price}


@app.get("/health")
def health():
    return {"status": "ok"}