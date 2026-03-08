# ShopQuick

This repository contains a simple backend and frontend for a meal planning application.

## Structure

```
backend/
│   ├─ app/
│   │   ├─ main.py              # FastAPI entry point
│   │   ├─ routes/
│   │   │   └─ planner.py       # API route for meal planning
│   │   ├─ models/
│   │   │   └─ products.py      # Product schema
│   │   ├─ services/
│   │   │   ├─ optimizer.py     # Optimization engine
│   │   │   └─ ollama_client.py # LLM chat wrapper
│   │   └─ data/
│   │       └─ products.json    # Sample product database
│   └─ requirements.txt
│
├─ frontend/
│   ├─ src/
│   │   ├─ App.jsx
│   │   ├─ index.jsx
│   │   └─ components/
│   │       └─ ChatInterface.jsx
│   └─ package.json
│
└─ README.md
```
