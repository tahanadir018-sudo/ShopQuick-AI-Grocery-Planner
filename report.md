# ShopQuick – AI Grocery Basket Planner (Technical Report)

> Act as a Senior Software Engineer. This document explains the ShopQuick system end‑to‑end: architecture, feature set, LLM strategy (why hosted Llama 3 instead of purely local models), and how the frontend and backend collaborate to generate fast, budget‑aware grocery plans.

---

## 1. Project Title & High‑Level Overview

**Project name:** ShopQuick — AI Grocery Basket Planner  
**Goal:** Help users turn a natural‑language budget and diet description into a concrete, store‑aware grocery basket for the week.

### 1.1 Rationale

Modern shoppers often think in goals, not line‑items:

- “I have **£50** for a **week of high‑protein breakfasts and dinners** for **two people**.”
- “I want a **vegan week**, keep it **cheap**, and don’t overcomplicate the cooking.”

Traditional grocery apps and price comparators require manual search, list building, and mental math. ShopQuick reverses this: the user describes their intent once, and the system:

1. **Parses the intent** (budget, days, meals, diet, people).
2. **Scores products** against that intent and the weekly meal slots.
3. **Optimizes per‑meal basket composition** within the budget.
4. **Picks the cheapest store per item**, including user‑reported in‑store prices.
5. **Explains the plan back** in clear language (summary, per‑meal notes, practical tips).

The result is a lightweight, “smart nutritionist + price hunter” experience that runs as a simple web app.

---

## 2. System Architecture

### 2.1 High‑Level Diagram (Conceptual)

- **Frontend (React / Vite)**
  - Pages:
    - **Planner**: prompt entry, basket results, AI summary, budget bar.
    - **Products & Prices**: product catalog, per‑store price comparison, inline price editing.
  - Communicates with backend via **HTTP (Axios)**.

- **Backend (Python / FastAPI)**
  - `main.py`: FastAPI app & HTTP endpoints.
  - `database.py`: SQLite schema, seeding, queries.
  - `basket_engine.py`: scoring & meal‑aware basket construction.
  - `llm_parser.py`: parses user text → structured plan using Hugging Face Llama 3.
  - `llm_basket.py`: generates natural‑language reasoning/summary using Hugging Face Llama 3.

- **Database (SQLite)**
  - `products`: base catalog of ~25 items with categories, diet tags, meal types, default prices.
  - `stores`: Aldi, Tesco, Asda, Sainsbury’s.
  - `store_prices`: per‑product, per‑store price overrides.

- **LLM Provider (Hugging Face Inference API)**
  - Hosted **Llama 3.2 Instruct** models.
  - Used for both:
    - Request parsing (`parse_user_query`).
    - Basket reasoning (`generate_basket_reasoning`).
  - Accessed via HTTPS using `HUGGINGFACE_API_KEY`.

All user state is ephemeral (no accounts yet). The only persistent data is the product catalog and store prices, which are small and live in a single SQLite file (`groceries.db`).

### 2.2 Data Model

**Products**

- `id` (PK)
- `name` – e.g. “Eggs”.
- `category` – e.g. “Dairy”, “Meat”, “Grain”.
- `default_price` – fallback when store price not present.
- `meal_type` – `breakfast`, `dinner`, `lunch`, `snack`, or `both`.
- `diet_tags` – CSV of tags like `protein`, `vegan`, `carb`, `fat`, `fiber`.
- `unit` – human‑readable quantity (e.g. “pack of 12”).

**Stores**

- `id` (PK)
- `name` – `Aldi`, `Tesco`, `Asda`, `Sainsbury's`.

**Store Prices**

- Composite primary key: `(product_id, store_id)`.
- `price` – floating‑point value in GBP.
- On insert, we use `INSERT OR IGNORE` (for seeds) and then an **upsert** pattern (`ON CONFLICT (...) DO UPDATE`) for user overrides.

### 2.3 Backend Modules & Responsibilities

1. **`database.py`**
   - Creates tables (`products`, `stores`, `store_prices`).
   - Seeds a curated product list and initial prices for four major UK chains.
   - Provides data access helpers:
     - `get_all_products_with_prices()`:
       - Returns each product with:
         - `cheapest_price`: minimum per‑store price, using a correlated sub‑select.
         - `cheapest_store`: store name corresponding to that minimum price.
       - This guarantees that “cheapest store” and “cheapest price” never drift apart.
     - `get_store_prices_for_product(product_id)`:
       - Returns all `(store, price)` rows sorted ascending by price for item cards and comparison tables.

2. **`basket_engine.py`**
   - Defines meal‑specific rules (`MEAL_RULES`), diet tags, and exclusions.
   - Scores products with `score_product()` using:
     - Diet tag matches (e.g. `protein` tag for protein‑focused diets).
     - Meal type compatibility (e.g. `breakfast` vs `dinner` vs `both`).
     - Category preference per meal (e.g. oats & bread for breakfast).
     - Value heuristic (`5 / price`) for cheap protein.
   - `build_meal_basket(parsed: dict) -> dict`:
     - Takes parsed user query fields:
       - `budget`, `days`, `meals`, `diet`, `people`.
     - Loads all products with their cheapest store prices.
     - Applies diet exclusions (e.g. vegans exclude Meat/Fish/Dairy).
     - Computes a per‑meal budget slice and then, per meal:
       - Picks high‑score products compatible with that meal.
       - Computes quantities per week:
         - Mains (Meat/Fish) ≈ 1 per day.
         - Sides/others ≈ `max(1, days // 2)`.
         - Multiplies by people.
       - Guards against blowing the per‑meal and overall budget with a 1.3× per‑meal and 1.05× total tolerance cap.
     - Returns:
       - `basket` – list of items with meal, qty, unit, diet tags, unit price, total price, cheapest store, and full store_prices list.
       - `total`, `budget`, `remaining`, `days`, `meals`, `diet`, `people`.

3. **`llm_parser.py`**
   - Uses Hugging Face hosted **Llama 3.2 Instruct** to parse free text into:
     - `budget` (GBP).
     - `days`.
     - `meals` (`breakfast`, `lunch`, `dinner`, `snack`).
     - `diet` (`protein`, `vegan`, `vegetarian`, `balanced`, `keto`, `budget`).
     - `people`.
     - `preferences` (strings extracted from user text).
   - If the LLM call fails or the response is malformed, it falls back to a **regex‑based parser**, ensuring the app continues functioning even if the LLM is down or misconfigured.

4. **`llm_basket.py`**
   - Uses the same Llama 3.2 Instruct family to:
     - Read the structured basket output (items, quantities, prices, diet).
     - Produce:
       - A short **summary** paragraph explaining the basket.
       - Per‑meal **usage notes** (e.g. what to cook for breakfast vs dinner).
       - A list of **tips** (batch cooking, leftovers, how to use remaining budget).
       - Optionally an estimated **protein per day**.
   - If the HF reasoning call fails, `_fallback_reasoning` synthesizes a deterministic but less personalised explanation based purely on basket metadata.

5. **`main.py`**
   - Creates the FastAPI app with CORS for `http://localhost:5173` and `http://localhost:3000`.
   - Ensures DB initialization and seeding at startup.
   - Exposes HTTP endpoints:
     - `POST /basket` – prompt → structured basket + reasoning.
     - `GET /products` – all products with their store prices.
     - `POST /price` – user overrides store price for a product.
     - `GET /health` – simple health check.

---

## 3. Frontend Architecture

### 3.1 Tech Stack

- **React 18+** (functional components, hooks).
- **Vite** for fast dev/build tooling.
- **Axios** for HTTP.
- Custom dark theme with **Syne** (display) and **DM Sans** (body) via Google Fonts.

### 3.2 Components & Pages

1. `App.jsx` – top‑level layout & navigation:
   - Local state for active page: `"planner"` vs `"products"`.
   - Sticky top navigation bar: brand icon, app name “ShopQuick”, tagline “AI Grocery Planner”.

2. `Planner.jsx` – main AI planner:
   - State:
     - `query`, `loading`, `result`, `error`.
   - Renders:
     - Prompt examples as “pills”.
     - Textarea for natural language request.
     - Generate button (disabled when empty or loading).
     - Loading spinner & message.
     - Either:
       - Empty state (“Your basket will appear here”).
       - Or `<BasketResults result={result} />`.

3. `BasketResults.jsx` – basket visualisation:
   - Renders:
     - AI summary banner with optional estimated protein per day and tips list.
     - Budget bar (spent vs remaining vs budget).
     - Per‑meal sections (Breakfast, Dinner, etc.) with cards for each product via `<ItemCard>`.

4. `ItemCard.jsx` – individual grocery item:
   - Shows:
     - Item name, category, unit.
     - Quantity & total price.
     - Best price store badge.
     - Diet tags as coloured labels.
     - Expandable list of all store prices sorted by cheapest.

5. `Products.jsx` – product & price catalogue:
   - State:
     - Loaded products, filters, error/loading, plus inline edit state (`editingProductId`, `editStore`, `editPrice`, `saving`).
   - Renders:
     - Filters for meal type and diet tags.
     - Card grid of all products with:
       - Unit info, meal type chip, diet tags.
       - Store price table (highlighting cheapest).
       - **Inline price edit widget** for quickly posting new in‑store prices back to the backend.

6. `services/api.js` – HTTP abstraction:
   - `generateBasket(query)` → `POST /basket`.
   - `fetchProducts()` → `GET /products`.
   - `updatePrice(product, store, price)` → `POST /price`.

---

## 4. Detailed Page Descriptions & Image Prompts

> Note: The sections below mirror the structure of a README for a UI‑heavy app. For each page, we include an “Image Generation Prompt (for Gemini Nano Banana)” you can use to synthesize high‑fidelity UI mockups that match the current implementation.

### 4.1 Planner Page

#### Functionality

- Serves as the main **entry point** for the app.
- The user:
  - Enters a natural language query (e.g. “I have £50 for a week of protein breakfasts and dinners for 2 people”).
  - Or clicks one of several curated example prompts.
  - Hits “Generate” (or presses `⌘+Enter`) to submit.
- The frontend calls `POST /basket` and:
  - Shows a progress spinner while waiting.
  - Renders:
    - AI **analysis banner** with summary and tips.
    - **Budget bar** showing spent vs remaining.
    - **Per‑meal sections** with grocery item cards.

The design adheres to the app’s dark theme with lime accents, large hero heading, and subtle animation on load (`.fade-in`).

#### Image Generation Prompt (for Gemini Nano Banana)

> Generate a high‑fidelity UI screenshot of a dark‑themed web application called **“ShopQuick – AI Grocery Planner”**.  
> The screen is the **Planner page**. At the top, show a minimal sticky navigation bar with a cart icon, the title “ShopQuick”, and a subtitle “AI Grocery Planner” on a dark charcoal background. Below, center a hero heading “Smart Grocery Planner” with a highlighted lime‑green word “Planner”, and a short subtitle about generating weekly baskets from a budget and diet goal.  
> Under the heading, include a large card containing:  
> – A row of rounded “example prompt” pills with short sentences like “£50 for a week of protein breakfasts and dinners”.  
> – A multi‑line textarea with placeholder text “I have £50 for a week of protein breakfast and dinner…”, styled with subtle borders and rounded corners.  
> – On the right side of the textarea, a bright lime‑green “✨ Generate” button with a small loading state indicator.  
> Below this, show an AI “Analysis” banner card with a lime border, a short explanatory paragraph about the basket, bullet‑style tips with lightbulb icons, and a small note about estimated protein per day.  
> Under that, render a horizontal budget bar labeled with “Spent”, “Remaining”, and “Budget” amounts, filling partially with a lime progress track.  
> Finally, show two sections labeled “Breakfast” and “Dinner”, each containing several product cards (e.g. Eggs, Oats, Chicken Breast) with unit, quantity, price, diet tags, and a small “Best price: Aldi” badge. Use a clean, modern typography (Syne for headings, DM Sans for body), a dark gray/black background, and lime‑green accent color. The style should be professional, modern, and responsive, with soft shadows and subtle hover states.

---

### 4.2 Products & Prices Page

#### Functionality

- Provides a **catalog view** of all products and their store prices.
- Features:
  - **Meal filter** (All, breakfast, dinner, both, snack).
  - **Diet filter** (All, protein, vegan, carb, fat, fiber).
  - Product cards that display:
    - Product name and category badge.
    - Unit (e.g. “500g”, “pack of 12”).
    - Meal type chip indicating Breakfast / Dinner / Any / Snack.
    - Diet tags as chips, reusing the same colours as the planner item cards.
    - A store price table with one row per store, highlighting the **cheapest** entry.
  - An inline **“Update price at a store”** control:
    - Clicking this reveals a:
      - Store dropdown (`Aldi`, `Tesco`, `Asda`, `Sainsbury’s`).
      - Numeric input for price.
      - “Save” and “Cancel” buttons.
    - On save:
      - The frontend posts to `/price`.
      - Then refetches `/products` to keep the view consistent with backend data.
      - The cheapest store badges update automatically.

This page is the core of the “crowd‑sourced in‑store price” feature: users can capture observed discounts in real stores, and the system seamlessly incorporates them into future basket planning.

#### Image Generation Prompt (for Gemini Nano Banana)

> Generate a high‑fidelity UI screenshot of the **“Products & Prices”** page in the ShopQuick web app. Use a dark background with lime‑green accents, consistent with a modern grocery planner. At the top, show a section title “Products & Prices” and a short description explaining that this is a store comparison view.  
> Beneath the title, include a horizontal filter bar: on the left a “Meal” label followed by pill‑style buttons for “All”, “breakfast”, “dinner”, “both”, “snack”; then a “Diet” label and pill buttons for “All”, “protein”, “vegan”, “carb”, “fat”, “fiber”. Highlight one active filter with a lime border and soft background glow.  
> Below the filters, render a responsive grid of product cards. Each card should show: the product name (e.g. “Eggs”), a small category pill (e.g. “Dairy”), the unit (e.g. “pack of 12”), and a meal‑type chip such as “☀️ Breakfast” or “🌙 Dinner” styled with soft colored backgrounds. Include a row of colored diet tags (e.g. “protein”, “vegan”) as small capsules.  
> At the bottom of each card, show a table with four rows for Aldi, Tesco, Asda, and Sainsbury’s, each with a price and the cheapest row highlighted with a “Cheapest” badge and lime text color. Below the table, add an inline editor area: a subtle “Update price at a store” link that, when expanded, reveals a dropdown for store selection, a small numeric input for the new price, and a compact lime “Save” button beside a grey “Cancel” text button.  
> Keep the overall style clean and professional with modern typography, rounded corners, soft shadows, and a consistent dark theme with neon‑lime accent elements.

---

### 4.3 (Optional) Basket Results View (as a Distinct Page/State)

Even though the results appear on the Planner page, they form a distinct visual mode worth documenting.

#### Functionality

- Displays the **AI reasoning banner**, **budget bar**, and **per‑meal item cards**.
- Uses consistent card styling and tags across the application.
- Aggregates:
  - Total cost per meal.
  - Total cost overall.
  - Remaining budget.

#### Image Generation Prompt (for Gemini Nano Banana)

> Generate a detailed UI screenshot of the **basket results** state in the ShopQuick Planner. The top portion should feature a prominent banner titled “✦ AI Analysis” with a lime border, containing a short paragraph about how the chosen items fit a high‑protein weekly plan, a small line about estimated protein per day (e.g. “Est. protein: ~120g/day”), and two bullet‑style tips with lightbulb icons.  
> Below the banner, draw a horizontal budget card showing “Spent”, “Remaining”, and “Budget” values with numeric amounts and a progress bar filled in lime‑green to indicate the spending level.  
> Under the budget card, create two meal sections — one labeled “Breakfast” with a small sun icon, and one labeled “Dinner” with a moon icon. Each section should have a horizontal rule and a row of product cards arranged in a grid. Each card shows product name, category tag, quantity (e.g. “×7 units”), per‑unit price, total price in bold lime text, diet tags, and a “Best price: [Store]” badge with a small store icon.  
> Use a dark theme with neon lime highlights, smooth cards, subtle entrance animation hints, and clean modern typography emphasizing clarity and readability.

---

## 5. Backend API Endpoints

### 5.1 `POST /basket`

**Purpose:** Convert a natural language grocery planning request into a structured basket and explanation.

**Request:**

- Body: `{ "query": "<user natural language text>" }`.

**Flow:**

1. `parse_user_query(query)`:
   - Hits Hugging Face Llama 3.2 Instruct with a tightly scoped prompt and small token budget.
   - Extracts JSON with `budget`, `days`, `meals`, `diet`, `people`, `preferences`.
   - If HF fails, uses regex heuristics:
     - Regex for `£amount` or `NN pounds`.
     - Regex for “N days” or “N weeks” (weeks × 7).
     - Keyword matches for meal types and diets.

2. `build_meal_basket(parsed)`:
   - Fetches all products with `cheapest_price` and `cheapest_store`.
   - Filters incompatible categories (e.g. meat for vegans).
   - Scores and selects products per meal and budget strategy.

3. `generate_basket_reasoning(query, basket_result)`:
   - Calls HF Llama 3.2 Instruct to produce human‑readable explanations.
   - On failure, falls back to deterministic reasoning.

**Response:**

- JSON object containing:
  - `basket` – array of product entries with:
    - `id`, `name`, `category`, `meal`, `qty`, `unit`, `diet_tags`, `unit_price`, `total_price`, `cheapest_store`, `store_prices`.
  - `total`, `budget`, `remaining`, `days`, `meals`, `diet`, `people`.
  - `parsed_query` – the structured fields from parser.
  - `summary`, `meal_notes`, `tips`, `estimated_protein_per_day`.

### 5.2 `GET /products`

**Purpose:** Return a flattened view of the catalog for the frontend Products page.

**Response:**

- `{ "products": [ { id, name, category, default_price, meal_type, diet_tags, unit, store_prices: [{ store, price }, ...] }, ... ] }`.

Data is shaped such that each product includes a list of store prices; the frontend can derive cheapest store client‑side even though the backend also provides global cheapest info for the engine.

### 5.3 `POST /price`

**Purpose:** Allow **users to override store prices** when they see different prices in real stores.

**Request:**

- Body:
  - `product` – product name (string, e.g. `"Eggs"`).
  - `store` – store name (e.g. `"Aldi"`).
  - `price` – new price (float).

**Flow:**

1. Looks up product by `name` and store by `name`.
2. Uses an **upsert** on `store_prices`:
   - If `(product_id, store_id)` doesn’t exist → insert.
   - Else → update price with new value.
3. Commits and returns `{"status": "success", ...}`.

**Effect:**

- Future calls to `/products` and `/basket` will use:
  - The updated price when computing cheapest store.
  - The updated price when computing totals in the basket.

### 5.4 `GET /health`

Simple health endpoint returning `{"status": "ok"}`.

---

## 6. LLM Strategy: Why Hosted Llama 3 vs Local Models

The project initially assumed a **locally hosted Ollama + Phi‑3** stack. While that can work in some environments, we explicitly switched to **Hugging Face–hosted Llama 3.2 Instruct** for the following reasons.

### 6.1 Performance & Latency

- **Local models** (Ollama/Phi‑3) require:
  - Good CPU/GPU on the user’s machine.
  - Proper model downloads, disk space, and background service.
  - Extra network hop to `localhost:11434`.
  - Depending on hardware, latency can easily be 5–15 seconds for multi‑step prompts.

- **Hosted Llama 3.2 on Hugging Face:**
  - Runs on dedicated inference hardware with optimized kernels.
  - We use:
    - Small `max_new_tokens` and low `temperature` for parsing.
    - Moderate token range and temperature for reasoning.
  - End‑to‑end latency is **dramatically lower**, as you’ve observed (“speed is very fast”), typically in the 1–3 second range.

For a UX‑heavy app like ShopQuick, **fast feedback** is crucial: users will iterate on different budgets and diets quickly, so >5 seconds per request feels sluggish, while ~1–2 seconds feels interactive.

### 6.2 Operational Complexity

- **Local hosting:**
  - Requires each developer or deployment target to:
    - Install and keep Ollama/models up to date.
    - Ensure the right ports and GPU drivers are configured.
    - Troubleshoot network/firewall issues for `localhost:11434`.
  - Harder to reproduce bugs (different local environments, hardware, model versions).

- **Hosted Hugging Face Llama 3:**
  - Centralised configuration:
    - The repo just needs `HUGGINGFACE_API_KEY` and model name(s).
  - Model versioning can be pinned and changed in one place.
  - Easier to scale out or migrate to a different HF model in the same family if needed.

For a small project, reducing **“it works on my machine”** friction is a major win.

### 6.3 Resource Usage & Cost

- **Local**:
  - Heavy models consume RAM/VRAM and CPU/GPU cycles on the user’s device, which may not be acceptable/possible (e.g., older laptops).
  - Could also degrade other apps when running inference.

- **Cloud (HF)**:
  - Offloads compute to remote hardware.
  - Obvious flip side: API usage has a cost.
  - However, we:
    - Minimize tokens.
    - Keep prompts tight and results JSON‑like.
  - For a prototype or early‑stage app, this is often cheaper than investing in local GPU hosting or dedicated servers.

### 6.4 Reliability & Fallbacks

- HF API includes standard HTTP semantics: you can inspect status codes, apply retries or degrade gracefully.
- Our implementation:
  - **Parser:** On failure → robust regex fallback; user still gets a reasonable basket.
  - **Reasoner:** On failure → deterministic summary; user still sees budget and per‑meal notes, just without LLM nuance.

This layered design means **LLM is an enhancement, not a single point of failure**.

### 6.5 Future Flexibility

- Because we talk to HF via a thin wrapper, we can:
  - Swap `HUGGINGFACE_PARSER_MODEL` and `HUGGINGFACE_REASONING_MODEL` independently.
  - Move parsing to a lighter model and reasoning to a slightly larger one.
  - Experiment with other Llama 3.x variants or even different model families without touching business logic or frontend code.

If the project grows large enough to justify dedicated local inference (e.g. via vLLM or a custom containerized Llama server), the HF client layer can be swapped for an internal HTTP endpoint with similar semantics.

---

## 7. Running, Configuration, and Tooling

### 7.1 Environment Variables

Set the following before running the backend:

- `HUGGINGFACE_API_KEY` – required.
- `HUGGINGFACE_PARSER_MODEL` – optional, defaults to `meta-llama/Llama-3.2-3B-Instruct`.
- `HUGGINGFACE_REASONING_MODEL` – optional, defaults to `meta-llama/Llama-3.2-3B-Instruct`.

On Windows PowerShell:

```powershell
$env:HUGGINGFACE_API_KEY = "<your_hf_api_key>"
$env:HUGGINGFACE_PARSER_MODEL = "meta-llama/Llama-3.2-3B-Instruct"
$env:HUGGINGFACE_REASONING_MODEL = "meta-llama/Llama-3.2-3B-Instruct"
```

### 7.2 Backend

From the project root (after activating your venv):

```powershell
uvicorn backend.main:app --reload
```

This will:

- Initialize/seed `groceries.db` if necessary.
- Serve:
  - `http://localhost:8000/basket`
  - `http://localhost:8000/products`
  - `http://localhost:8000/price`
  - `http://localhost:8000/health`

### 7.3 Frontend

From `frontend/`:

```bash
npm run dev
```

Then open `http://localhost:5173` in your browser.

To check code health:

- **Lint:** `npm run lint`
- **Build:** `npm run build`

### 7.4 Backend Sanity Checks

To ensure Python source compiles:

```bash
python -m compileall backend
```

---

## 8. Future Enhancements (“What more can we add?”)

Below are concrete, backward‑compatible enhancements that fit naturally into the current architecture.

### 8.1 User Accounts & Saved Plans

- Add lightweight authentication (JWT or session) so users can:
  - Save favorite prompts.
  - Save / rename baskets per week.
  - Re‑generate a previous plan when prices change.
- Data model impact:
  - `users` table.
  - `baskets` table with JSON snapshot and timestamp.

### 8.2 Nutrition & Macro Breakdown

- Extend `products` with **approximate nutrition info** (protein, carbs, fats, calories per unit).
- Compute totals per day from selected foods and present as:
  - Graphs in the Planner results (per‑day macros).
  - Additional reasoning for Llama (e.g., “You’re slightly low on fiber; consider adding beans or oats.”).

### 8.3 Streaming UI / Partial Results

- Convert the LLM calls to use streaming (if/when the model/provider supports it for the chosen endpoints).
- Show:
  - Basket immediately when the engine finishes.
  - Stream in the AI summary paragraph and tips afterward.

### 8.4 More Controls on Basket Generation

- Frontend sliders/toggles for:
  - “Variety vs repetition” (how many distinct items per meal).
  - “Aggressive savings” vs “premium ingredients”.
  - Hard excludes (e.g. “no fish”, “no dairy”) in addition to diet.

### 8.5 Price History & Trend Insights

- Extend `store_prices` with timestamps and track history:
  - Time‑series views of price changes per product and store.
  - LLM reasoning can highlight: “Eggs are currently cheaper than their 30‑day average”.

### 8.6 Multi‑Region Support

- Abstract currencies and units:
  - Add `currency` and `region` metadata.
  - Localize budget parsing (e.g. `$50` instead of `£50`).
  - Region‑specific product catalogs.

### 8.7 Better Error Feedback

- Frontend:
  - Distinguish between network issues, HF errors, and input validation.
  - Provide inline hints if the query looks underspecified (“Please mention at least one meal type or we’ll assume breakfast and dinner.”).

---

## 9. Summary

ShopQuick combines:

- A **deterministic, diet‑aware basket engine** (SQLite + FastAPI + scoring logic) with
- A **cloud‑hosted Llama 3.2 Instruct integration** (via Hugging Face) and
- A **polished React frontend** for prompt‑driven planning and price exploration.

Moving from local models (Ollama/Phi‑3) to hosted Llama 3 yields a significantly faster, more consistent user experience while still preserving resilience through regex and deterministic fallbacks. The architecture is intentionally simple and modular, making it straightforward to evolve the system with user accounts, nutrition analytics, richer price histories, and more advanced personalization over time.

