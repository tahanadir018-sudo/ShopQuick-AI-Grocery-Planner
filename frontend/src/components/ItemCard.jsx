import { useState } from "react";

const TAG_CLASS = {
  protein: "tag-protein",
  vegan:   "tag-vegan",
  carb:    "tag-carb",
  fat:     "tag-fat",
  fiber:   "tag-fiber",
};

export default function ItemCard({ item, meal }) {
  const [showPrices, setShowPrices] = useState(false);

  const tags = (item.diet_tags || "").split(",").filter(Boolean);
  const cheapest = item.store_prices?.length
    ? item.store_prices.reduce((a, b) => (a.price < b.price ? a : b))
    : null;

  return (
    <div className={`item-card ${meal}`}>
      <div className="item-top">
        <span className="item-name">{item.name}</span>
        <span className="item-cat">{item.category}</span>
      </div>

      <div className="item-unit-label">{item.unit}</div>

      <div className="item-pricing">
        <div>
          <div className="item-qty">× {item.qty} units</div>
          <div className="item-per-unit">£{item.unit_price}/unit</div>
        </div>
        <div className="item-total">£{item.total_price.toFixed(2)}</div>
      </div>

      {cheapest && (
        <div className="item-store-badge">
          🏪 Best price: <strong>{cheapest.store}</strong>
        </div>
      )}

      {tags.length > 0 && (
        <div className="item-tags" style={{ marginBottom: 8 }}>
          {tags.map((t) => (
            <span key={t} className={`tag ${TAG_CLASS[t.trim()] || "tag-default"}`}>
              {t.trim()}
            </span>
          ))}
        </div>
      )}

      {item.store_prices?.length > 0 && (
        <>
          <button
            className="store-prices-toggle"
            onClick={() => setShowPrices((v) => !v)}
          >
            {showPrices ? "▲" : "▼"} Store prices
          </button>
          {showPrices && (
            <div className="store-prices-list">
              {[...item.store_prices].sort((a, b) => a.price - b.price).map((sp) => (
                <div key={sp.store} className="store-price-row">
                  <span className="store-name">{sp.store}</span>
                  <span className={`store-price ${sp.store === cheapest?.store ? "cheapest" : ""}`}>
                    £{sp.price.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}