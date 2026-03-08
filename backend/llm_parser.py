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
HF_PARSER_MODEL = os.getenv(
    "HUGGINGFACE_PARSER_MODEL",
    "meta-llama/Llama-3.2-3B-Instruct",
)
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_PARSER_MODEL}"


def _call_hf_parser(prompt: str) -> str:
    """
    Call Hugging Face text-generation endpoint for fast, low-latency parsing.
    Falls back to raising so caller can use regex parser.
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
            "max_new_tokens": 256,
            "temperature": 0.1,
            "top_p": 0.9,
            "do_sample": False,
            "return_full_text": False,
        },
    }

    resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    # Handle both list and dict shapes
    if isinstance(data, list) and data and isinstance(data[0], dict):
        text = data[0].get("generated_text") or data[0].get("generated_token_ids") or ""
    elif isinstance(data, dict):
        text = data.get("generated_text") or ""
    else:
        text = ""

    if not text:
        text = json.dumps(data)

    return text


def parse_user_query(user_text: str) -> dict:
    prompt = f"""You are a grocery planning assistant. Analyze this request and extract structured data.

User request: "{user_text}"

Extract:
- budget: total budget in GBP (number only, e.g. 50)
- days: number of days (default 7 if not specified)
- meals: list of meal types requested from ["breakfast", "lunch", "dinner", "snack"]
- diet: diet focus from ["protein", "vegan", "vegetarian", "balanced", "keto", "budget"]
- people: number of people (default 1)
- preferences: any specific food preferences mentioned as a list

Return ONLY valid JSON, no explanation:
{{
  "budget": 50,
  "days": 7,
  "meals": ["breakfast", "dinner"],
  "diet": "protein",
  "people": 1,
  "preferences": ["high protein", "eggs", "chicken"]
}}"""

    try:
        result_text = _call_hf_parser(prompt)
        logger.info(f"LLM raw parse: {result_text}")

        # Extract JSON from response
        json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

    except Exception as e:
        logger.warning(f"LLM parse failed, falling back to regex parser: {e}")

    # Smart regex fallback
    return _regex_fallback(user_text)


def _regex_fallback(text: str) -> dict:
    text_lower = text.lower()

    # Budget
    budget_match = re.search(r'£(\d+(?:\.\d+)?)', text)
    if not budget_match:
        budget_match = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:pounds?|gbp)\b', text_lower)
    budget = float(budget_match.group(1)) if budget_match else 50.0

    # Days
    days_match = re.search(r'(\d+)\s*(?:days?|weeks?)', text_lower)
    if days_match:
        val = int(days_match.group(1))
        days = val * 7 if 'week' in text_lower[days_match.start():days_match.end()] else val
    else:
        days = 7

    # Meals
    meals = []
    if any(w in text_lower for w in ['breakfast', 'morning', 'brunch']):
        meals.append('breakfast')
    if any(w in text_lower for w in ['lunch', 'midday']):
        meals.append('lunch')
    if any(w in text_lower for w in ['dinner', 'evening', 'supper', 'tea']):
        meals.append('dinner')
    if not meals:
        meals = ['breakfast', 'dinner']

    # Diet
    if any(w in text_lower for w in ['protein', 'muscle', 'gym', 'gains', 'high protein']):
        diet = 'protein'
    elif any(w in text_lower for w in ['vegan', 'plant']):
        diet = 'vegan'
    elif any(w in text_lower for w in ['vegetarian', 'veggie', 'no meat']):
        diet = 'vegetarian'
    elif any(w in text_lower for w in ['keto', 'low carb']):
        diet = 'keto'
    else:
        diet = 'balanced'

    # People
    people_match = re.search(r'(?:for\s+)?(\d+)\s*(?:people|person|persons?)', text_lower)
    people = int(people_match.group(1)) if people_match else 1

    return {
        "budget": budget,
        "days": days,
        "meals": meals,
        "diet": diet,
        "people": people,
        "preferences": []
    }