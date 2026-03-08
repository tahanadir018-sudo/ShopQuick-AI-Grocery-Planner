import os
import requests
import json
import re
import logging

logger = logging.getLogger(__name__)

# -----------------------------
# Hugging Face configuration
# -----------------------------
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HF_REASONING_MODEL = os.getenv(
    "HUGGINGFACE_REASONING_MODEL",
    "meta-llama/Llama-3.2-3B-Instruct",
)
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_REASONING_MODEL}"


def _call_hf_reasoner(prompt: str) -> str:
    """
    Call Hugging Face text-generation endpoint for basket reasoning.
    If anything goes wrong, caller will fall back to deterministic reasoning.
    """
    if not HF_API_KEY:
        raise RuntimeError("HUGGINGFACE_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Accept": "application/json",
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 512,
            "temperature": 0.4,
            "top_p": 0.9,
            "do_sample": True,
            "return_full_text": False,
        },
    }

    resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=25)
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, list) and data and isinstance(data[0], dict):
        text = data[0].get("generated_text") or ""
    elif isinstance(data, dict):
        text = data.get("generated_text") or ""
    else:
        text = ""

    if not text:
        text = json.dumps(data)

    return text


def generate_basket_reasoning(query: str, basket_result: dict) -> dict:
    """
    Uses LLM to:
    1. Review the engine-generated basket
    2. Add smart reasoning / meal plan commentary
    3. Suggest any missing items
    4. Return a short summary and per-meal notes
    """
    basket = basket_result.get("basket", [])
    budget = basket_result.get("budget")
    total = basket_result.get("total")
    meals = basket_result.get("meals", [])
    diet = basket_result.get("diet")
    days = basket_result.get("days", 7)

    basket_summary = []
    for item in basket:
        basket_summary.append(
            f"- {item['name']} x{item['qty']} ({item['unit']}) for {item['meal']} @ £{item['unit_price']} each = £{item['total_price']}"
        )

    basket_text = "\n".join(basket_summary)

    prompt = f"""You are a smart grocery planning assistant helping a UK shopper.

User's request: "{query}"

Plan details:
- Budget: £{budget}
- Days: {days}
- Meals: {', '.join(meals)}
- Diet focus: {diet}

Generated basket:
{basket_text}

Total cost: £{total}

Your job:
1. Write a SHORT overall summary (2-3 sentences) explaining why this basket is good value and fits the user's goals.
2. For each meal ({', '.join(meals)}), write 1-2 sentences explaining the meal choices and how to use these ingredients.
3. Give 1-2 smart tips (e.g. meal prep advice, budget tip, protein calculation).

Return ONLY valid JSON:
{{
  "summary": "Your overall basket summary here...",
  "meal_notes": {{
    "breakfast": "How to use breakfast items...",
    "dinner": "How to use dinner items..."
  }},
  "tips": [
    "Tip 1 here",
    "Tip 2 here"
  ],
  "estimated_protein_per_day": 120
}}"""

    try:
        result_text = _call_hf_reasoner(prompt)
        logger.info(f"LLM reasoning raw: {result_text[:200]}")

        json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

    except Exception as e:
        logger.warning(f"LLM reasoning failed, using fallback reasoning: {e}")

    # Fallback: generate basic reasoning
    return _fallback_reasoning(basket_result)


def _fallback_reasoning(basket_result: dict) -> dict:
    diet = basket_result.get("diet", "balanced")
    meals = basket_result.get("meals", [])
    total = basket_result.get("total", 0)
    budget = basket_result.get("budget", 50)
    remaining = basket_result.get("remaining", 0)

    meal_notes = {}
    for meal in meals:
        items = [b for b in basket_result.get("basket", []) if b["meal"] == meal]
        names = [i["name"] for i in items]
        if names:
            meal_notes[meal] = f"Your {meal} includes {', '.join(names)}. Great choices for a {diet} diet."

    return {
        "summary": f"This basket covers your {diet} plan for {basket_result.get('days', 7)} days across {', '.join(meals)}. "
                   f"Total spend: £{total} out of £{budget} budget — saving £{remaining}.",
        "meal_notes": meal_notes,
        "tips": [
            "Batch cook your protein sources on Sunday to save time during the week.",
            f"You have £{remaining} remaining — consider adding vegetables or healthy fats."
        ],
        "estimated_protein_per_day": None
    }