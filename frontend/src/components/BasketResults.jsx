import ItemCard from "./ItemCard";

const MEAL_META = {
  breakfast: { icon: "☀️", label: "Breakfast", color: "var(--orange)" },
  lunch:     { icon: "🌤️", label: "Lunch",     color: "var(--accent)" },
  dinner:    { icon: "🌙", label: "Dinner",    color: "var(--blue)" },
  snack:     { icon: "🍎", label: "Snacks",    color: "var(--red)" },
};

export default function BasketResults({ result }) {
  const {
    basket = [],
    total = 0,
    budget = 0,
    remaining = 0,
    meals = [],
    diet,
    days,
    people,
    summary,
    meal_notes = {},
    tips = [],
    estimated_protein_per_day,
  } = result;

  const pct = budget > 0 ? Math.min((total / budget) * 100, 100) : 0;

  const groupedByMeal = {};
  for (const item of basket) {
    if (!groupedByMeal[item.meal]) groupedByMeal[item.meal] = [];
    groupedByMeal[item.meal].push(item);
  }

  return (
    <div>
      {/* Summary Banner */}
      {summary && (
        <div className="summary-banner">
          <h3>✦ AI Analysis</h3>
          <p className="summary-text">{summary}</p>
          {estimated_protein_per_day && (
            <p style={{ fontSize: 13, color: "var(--accent)", marginBottom: 12 }}>
              💪 Est. protein: ~{estimated_protein_per_day}g/day
            </p>
          )}
          {tips.length > 0 && (
            <div className="tips-list">
              {tips.map((tip, i) => (
                <div key={i} className="tip-item">
                  <span className="tip-icon">💡</span>
                  <span>{tip}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Budget Bar */}
      <div className="card budget-bar-wrap">
        <div className="budget-meta">
          <span className="budget-label">
            Budget for {days} days · {people > 1 ? `${people} people` : "1 person"} · {diet} plan
          </span>
          <div className="budget-numbers">
            <div className="budget-stat spent">
              <div className="val">£{total.toFixed(2)}</div>
              <div className="lbl">Spent</div>
            </div>
            <div className="budget-stat remaining">
              <div className="val">£{remaining.toFixed(2)}</div>
              <div className="lbl">Remaining</div>
            </div>
            <div className="budget-stat">
              <div className="val" style={{ color: "var(--text-2)" }}>£{budget.toFixed(2)}</div>
              <div className="lbl">Budget</div>
            </div>
          </div>
        </div>
        <div className="budget-bar">
          <div className="budget-fill" style={{ width: `${pct}%` }} />
        </div>
      </div>

      {/* Meal sections */}
      {meals.map((meal) => {
        const items = groupedByMeal[meal] || [];
        if (items.length === 0) return null;
        const meta = MEAL_META[meal] || { icon: "🍽️", label: meal, color: "var(--text-2)" };
        const note = meal_notes[meal];

        return (
          <div key={meal} className="meal-section">
            <div className="meal-header">
              <span className="meal-icon">{meta.icon}</span>
              <span className="meal-title" style={{ color: meta.color }}>{meta.label}</span>
              <span className="meal-count" style={{ fontSize: 13, color: "var(--text-3)", marginLeft: 6 }}>
                {items.length} items · £{items.reduce((s, i) => s + i.total_price, 0).toFixed(2)}
              </span>
              {note && <span className="meal-note">{note}</span>}
            </div>

            <div className="items-grid">
              {items.map((item) => (
                <ItemCard key={item.id} item={item} meal={meal} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}