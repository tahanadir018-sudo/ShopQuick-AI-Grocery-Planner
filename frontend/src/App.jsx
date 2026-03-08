import { useState } from "react";
import Planner from "./pages/Planner";
import Products from "./pages/Products";
import "./index.css";

export default function App() {
  const [page, setPage] = useState("planner");

  return (
    <div className="app-root">
      <nav className="topnav">
        <div className="nav-brand">
          <span className="brand-icon">🛒</span>
          <span className="brand-name">ShopQuick</span>
          <span className="brand-tag">AI Grocery Planner</span>
        </div>
        <div className="nav-links">
          <button
            className={`nav-btn ${page === "planner" ? "active" : ""}`}
            onClick={() => setPage("planner")}
          >
            Planner
          </button>
          <button
            className={`nav-btn ${page === "products" ? "active" : ""}`}
            onClick={() => setPage("products")}
          >
            Products & Prices
          </button>
        </div>
      </nav>

      <main className="main-content">
        {page === "planner" ? <Planner /> : <Products />}
      </main>
    </div>
  );
}