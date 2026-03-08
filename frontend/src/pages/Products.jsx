import { useEffect, useState } from "react";
import { fetchProducts, updatePrice } from "../services/api";

const MEAL_FILTERS = ["All", "breakfast", "dinner", "both", "snack"];
const DIET_FILTERS = ["All", "protein", "vegan", "carb", "fat", "fiber"];

export default function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mealFilter, setMealFilter] = useState("All");
  const [dietFilter, setDietFilter] = useState("All");
   const [editingProductId, setEditingProductId] = useState(null);
   const [editStore, setEditStore] = useState("Aldi");
   const [editPrice, setEditPrice] = useState("");
   const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchProducts()
      .then((res) => setProducts(res.data.products))
      .catch(() => setError("Could not load products. Make sure the backend is running."))
      .finally(() => setLoading(false));
  }, []);

  const filtered = products.filter((p) => {
    const mealOk = mealFilter === "All" || p.meal_type === mealFilter;
    const dietOk = dietFilter === "All" || (p.diet_tags || "").includes(dietFilter);
    return mealOk && dietOk;
  });

  const getCheapestStore = (prices) => {
    if (!prices || prices.length === 0) return null;
    return prices.reduce((a, b) => (a.price < b.price ? a : b));
  };

  const handleStartEdit = (product) => {
    setEditingProductId(product.id);
    const currentPrices = product.store_prices || [];
    const firstStore = currentPrices[0]?.store || "Aldi";
    setEditStore(firstStore);
    const firstPrice = currentPrices.find((sp) => sp.store === firstStore)?.price
      ?? product.default_price
      ?? "";
    setEditPrice(firstPrice !== undefined && firstPrice !== null ? String(firstPrice) : "");
  };

  const handleCancelEdit = () => {
    setEditingProductId(null);
    setEditStore("Aldi");
    setEditPrice("");
  };

  const handleSavePrice = async (productId, productName) => {
    const priceNum = parseFloat(editPrice);
    if (Number.isNaN(priceNum) || priceNum <= 0) return;
    try {
      setSaving(true);
      await updatePrice(productName, editStore, priceNum);
      const res = await fetchProducts();
      setProducts(res.data.products);
      handleCancelEdit();
    } catch (e) {
      console.error(e);
      setError("Could not update price. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="products-header">
        <h1>Products & Prices</h1>
        <p>All available products with store-by-store price comparison.</p>
      </div>

      <div className="filters-bar">
        <span style={{ color: "var(--text-3)", fontSize: 13, alignSelf: "center" }}>Meal:</span>
        {MEAL_FILTERS.map((f) => (
          <button
            key={f}
            className={`filter-btn ${mealFilter === f ? "active" : ""}`}
            onClick={() => setMealFilter(f)}
          >
            {f}
          </button>
        ))}
        <span style={{ color: "var(--text-3)", fontSize: 13, alignSelf: "center", marginLeft: 12 }}>Diet:</span>
        {DIET_FILTERS.map((f) => (
          <button
            key={f}
            className={`filter-btn ${dietFilter === f ? "active" : ""}`}
            onClick={() => setDietFilter(f)}
          >
            {f}
          </button>
        ))}
      </div>

      {loading && (
        <div className="loading-state">
          <div className="loading-spinner" />
          <p>Loading products...</p>
        </div>
      )}

      {error && <div className="error-box">⚠ {error}</div>}

      {!loading && !error && (
        <div className="products-grid fade-in">
          {filtered.map((p) => {
            const cheapest = getCheapestStore(p.store_prices);
            return (
              <div key={p.id} className="product-card">
                <div className="product-card-top">
                  <span className="product-name">{p.name}</span>
                  <span className="product-category">{p.category}</span>
                </div>
                <div className="product-unit">{p.unit}</div>

                <span className={`product-meal-type meal-type-${p.meal_type}`}>
                  {p.meal_type === "both" ? "🌅 Any meal" :
                   p.meal_type === "breakfast" ? "☀️ Breakfast" :
                   p.meal_type === "dinner" ? "🌙 Dinner" : "🍎 Snack"}
                </span>

                {p.diet_tags && (
                  <div className="item-tags" style={{ marginBottom: 12 }}>
                    {p.diet_tags.split(",").map((t) => (
                      <span key={t} className={`tag tag-${t.trim()} tag-default`}>
                        {t.trim()}
                      </span>
                    ))}
                  </div>
                )}

                <table className="store-prices-table">
                  <tbody>
                    {(p.store_prices || []).sort((a, b) => a.price - b.price).map((sp) => {
                      const isChp = cheapest && sp.store === cheapest.store;
                      return (
                        <tr key={sp.store}>
                          <td style={{ color: "var(--text-2)" }}>
                            {sp.store}
                            {isChp && <span className="cheapest-badge">Cheapest</span>}
                          </td>
                          <td className="price-col" style={{ color: isChp ? "var(--accent)" : "var(--text)" }}>
                            £{sp.price.toFixed(2)}
                          </td>
                        </tr>
                      );
                    })}
                    {(!p.store_prices || p.store_prices.length === 0) && (
                      <tr>
                        <td colSpan={2} style={{ color: "var(--text-3)", fontSize: 13 }}>
                          Default: £{p.default_price?.toFixed(2)}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>

                <div style={{ marginTop: 10 }}>
                  {editingProductId === p.id ? (
                    <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4 }}>
                      <select
                        value={editStore}
                        onChange={(e) => setEditStore(e.target.value)}
                        style={{
                          background: "var(--surface-2)",
                          border: "1px solid var(--border)",
                          color: "var(--text)",
                          borderRadius: 6,
                          padding: "4px 8px",
                          fontSize: 12,
                        }}
                      >
                        <option value="Aldi">Aldi</option>
                        <option value="Tesco">Tesco</option>
                        <option value="Asda">Asda</option>
                        <option value="Sainsbury's">Sainsbury&apos;s</option>
                      </select>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={editPrice}
                        onChange={(e) => setEditPrice(e.target.value)}
                        placeholder="New price"
                        style={{
                          background: "var(--surface-2)",
                          border: "1px solid var(--border)",
                          color: "var(--text)",
                          borderRadius: 6,
                          padding: "4px 8px",
                          fontSize: 12,
                          width: 90,
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => handleSavePrice(p.id, p.name)}
                        disabled={saving}
                        style={{
                          background: "var(--accent)",
                          color: "#000",
                          border: "none",
                          borderRadius: 6,
                          padding: "4px 10px",
                          fontSize: 12,
                          cursor: "pointer",
                        }}
                      >
                        {saving ? "Saving..." : "Save"}
                      </button>
                      <button
                        type="button"
                        onClick={handleCancelEdit}
                        style={{
                          background: "transparent",
                          color: "var(--text-3)",
                          border: "none",
                          fontSize: 12,
                          cursor: "pointer",
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleStartEdit(p)}
                      style={{
                        marginTop: 6,
                        background: "transparent",
                        border: "none",
                        color: "var(--text-3)",
                        fontSize: 12,
                        cursor: "pointer",
                        textDecoration: "underline",
                      }}
                    >
                      Update price at a store
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div className="empty-state">
          <div className="icon">🔍</div>
          <h3>No products match these filters</h3>
        </div>
      )}
    </div>
  );
}