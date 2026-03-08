import { useState } from "react";
import { generateBasket } from "../services/api";
import BasketResults from "../components/BasketResults";

const EXAMPLES = [
  "I have £50 for a week of protein breakfasts and dinners",
  "£80 budget, 2 people, high protein meals for 7 days",
  "£40 vegan meal plan for a week, breakfast and dinner",
  "£60 for 7 days of keto breakfasts and dinners",
];

export default function Planner() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await generateBasket(query);
      setResult(res.data);
    } catch (err) {
      console.error(err);
      setError("Could not connect to the backend. Make sure it's running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && e.metaKey) handleSubmit();
  };

  return (
    <div>
      <div className="planner-header">
        <h1>Smart Grocery <span>Planner</span></h1>
        <p>Tell us your budget and goals — we'll build the perfect weekly basket with meal-by-meal breakdown.</p>
      </div>

      <div className="card query-box" style={{ marginBottom: 28 }}>
        <div className="query-examples">
          {EXAMPLES.map((ex) => (
            <button key={ex} className="example-pill" onClick={() => setQuery(ex)}>
              {ex}
            </button>
          ))}
        </div>

        <div className="query-input-wrap">
          <textarea
            className="query-textarea"
            rows={3}
            placeholder="e.g. I have £50 for a week of protein breakfast and dinner..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            className="submit-btn"
            onClick={handleSubmit}
            disabled={loading || !query.trim()}
          >
            {loading ? "⏳" : "✨"} Generate
          </button>
        </div>
        <p style={{ fontSize: 12, color: "var(--text-3)", marginTop: 8 }}>
          Tip: Press ⌘+Enter to generate
        </p>
      </div>

      {error && (
        <div className="error-box">⚠ {error}</div>
      )}

      {loading && (
        <div className="loading-state">
          <div className="loading-spinner" />
          <p>Planning your meals and finding the best prices...</p>
        </div>
      )}

      {result && !loading && (
        <div className="fade-in">
          <BasketResults result={result} />
        </div>
      )}

      {!result && !loading && !error && (
        <div className="empty-state">
          <div className="icon">🥗</div>
          <h3>Your basket will appear here</h3>
          <p>Try one of the example prompts above or write your own</p>
        </div>
      )}
    </div>
  );
}