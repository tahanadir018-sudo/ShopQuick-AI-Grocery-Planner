import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000",
});

export const generateBasket = (query) =>
  API.post("/basket", { query });

export const fetchProducts = () =>
  API.get("/products");

export const updatePrice = (product, store, price) =>
  API.post("/price", { product, store, price });