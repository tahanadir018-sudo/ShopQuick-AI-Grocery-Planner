import logging

# Allow use both as part of the 'backend' package and as a standalone module
try:  # pragma: no cover - import compat
    from .database import get_all_products_with_prices, get_store_prices_for_product
except ImportError:
    from database import get_all_products_with_prices, get_store_prices_for_product

logger = logging.getLogger(__name__)

# Meal plan templates: which product categories matter per meal
MEAL_RULES = {
    "breakfast": {
        "must_have": [],
        "preferred_categories": ["Dairy", "Meat", "Bakery", "Fruit", "Grain"],
        "preferred_meal_types": ["breakfast", "both"],
    },
    "lunch": {
        "must_have": [],
        "preferred_categories": ["Grain", "Legumes", "Vegetables", "Fish", "Meat"],
        "preferred_meal_types": ["lunch", "both"],
    },
    "dinner": {
        "must_have": [],
        "preferred_categories": ["Meat", "Fish", "Grain", "Vegetables", "Legumes"],
        "preferred_meal_types": ["dinner", "both"],
    },
    "snack": {
        "must_have": [],
        "preferred_categories": ["Snack", "Fruit", "Dairy"],
        "preferred_meal_types": ["snack", "both"],
    },
}

# Diet-specific scoring boosts
DIET_TAGS = {
    "protein":     ["protein", "lowfat"],
    "vegan":       ["vegan", "fiber"],
    "vegetarian":  ["fiber", "protein", "calcium"],
    "keto":        ["fat", "protein"],
    "balanced":    ["protein", "carb", "fiber", "fat"],
    "budget":      [],  # just cheapest
}

# Items that don't make sense for certain diets
DIET_EXCLUSIONS = {
    "vegan":       ["Meat", "Fish", "Dairy"],
    "vegetarian":  ["Meat", "Fish"],
    "keto":        [],  # we handle by boosting fat/protein
}


def score_product(product: dict, diet: str, meals: list) -> float:
    """Score a product based on how well it fits the diet and meal plan"""
    score = 0.0

    # Diet tag match
    preferred_tags = DIET_TAGS.get(diet, [])
    product_tags = product.get("diet_tags", "").split(",")
    for tag in preferred_tags:
        if tag in product_tags:
            score += 10

    # Meal type match
    product_meal = product.get("meal_type", "both")
    for meal in meals:
        meal_types = MEAL_RULES.get(meal, {}).get("preferred_meal_types", [])
        if product_meal in meal_types:
            score += 8
        preferred_cats = MEAL_RULES.get(meal, {}).get("preferred_categories", [])
        if product.get("category") in preferred_cats:
            score += 5

    # Bonus for versatile "both" items
    if product_meal == "both":
        score += 3

    # Value score: high protein per penny
    price = product.get("cheapest_price") or product.get("default_price") or 1
    if price > 0 and "protein" in product_tags:
        score += (5 / price)  # cheap protein is valued higher

    return score


def build_meal_basket(parsed: dict) -> dict:
    """
    Build a smart, meal-aware grocery basket.
    Returns basket items grouped by meal, plus store comparison.
    """
    budget = parsed.get("budget", 50.0)
    days = parsed.get("days", 7)
    meals = parsed.get("meals", ["breakfast", "dinner"])
    diet = parsed.get("diet", "balanced")
    people = parsed.get("people", 1)

    effective_budget = budget  # per person already or total
    logger.info(f"Building basket: budget=£{effective_budget}, days={days}, meals={meals}, diet={diet}, people={people}")

    all_products = get_all_products_with_prices()

    # Filter out diet exclusions
    excluded_categories = DIET_EXCLUSIONS.get(diet, [])
    eligible = [p for p in all_products if p["category"] not in excluded_categories]

    # Score and sort
    for p in eligible:
        p["score"] = score_product(p, diet, meals)
    eligible.sort(key=lambda x: x["score"], reverse=True)

    # Build basket meal by meal
    basket = []
    total_spent = 0.0
    used_ids = set()

    # Budget split: reserve roughly equal per meal
    meal_budget = effective_budget / max(len(meals), 1)

    for meal in meals:
        meal_spent = 0.0
        meal_rules = MEAL_RULES.get(meal, {})
        preferred_types = meal_rules.get("preferred_meal_types", ["both"])
        preferred_cats = meal_rules.get("preferred_categories", [])

        # Get candidates for this meal
        candidates = [
            p for p in eligible
            if p["id"] not in used_ids
            and (p["meal_type"] in preferred_types or p["meal_type"] == "both")
        ]

        # Sort candidates: prefer items matching this meal's categories
        candidates.sort(
            key=lambda x: (
                x["category"] in preferred_cats,
                x["score"]
            ),
            reverse=True
        )

        # Pick items for this meal until meal budget is ~used
        for product in candidates:
            price = product.get("cheapest_price") or product.get("default_price") or 0
            if price == 0:
                continue

            # How many units needed for the week?
            # Use a sensible quantity: protein mains = 1 per day, sides = 0.5 per day
            is_main = product["category"] in ["Meat", "Fish"]
            qty = days if is_main else max(1, days // 2)
            qty = qty * people

            item_total = round(price * qty, 2)

            if meal_spent + item_total > meal_budget * 1.3:
                # Try with smaller qty
                qty = max(1, qty // 2)
                item_total = round(price * qty, 2)

            if total_spent + item_total > effective_budget * 1.05:
                continue

            # Get store prices for this product
            store_prices = get_store_prices_for_product(product["id"])

            basket.append({
                "id": product["id"],
                "name": product["name"],
                "category": product["category"],
                "meal": meal,
                "qty": qty,
                "unit": product.get("unit", ""),
                "diet_tags": product.get("diet_tags", ""),
                "unit_price": round(price, 2),
                "total_price": item_total,
                "cheapest_store": product.get("cheapest_store", ""),
                "store_prices": store_prices,
            })

            used_ids.add(product["id"])
            meal_spent += item_total
            total_spent += item_total

            # Stop when we have enough variety per meal
            meal_items = [b for b in basket if b["meal"] == meal]
            max_items_per_meal = 4 if meal == "dinner" else 3
            if len(meal_items) >= max_items_per_meal:
                break

    total = round(total_spent, 2)
    remaining = round(effective_budget - total, 2)

    logger.info(f"Basket built: {len(basket)} items, total=£{total}, remaining=£{remaining}")

    return {
        "basket": basket,
        "total": total,
        "budget": effective_budget,
        "remaining": remaining,
        "days": days,
        "meals": meals,
        "diet": diet,
        "people": people,
    }