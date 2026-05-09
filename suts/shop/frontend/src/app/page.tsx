"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { addToLocalCart, getLocalCartCount } from "@/lib/cart";

interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  stock: number;
  image_url: string;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8002";

export default function ShopPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  // DEBUGRA_BUG:SHOP-06 — cartCount reads from unscoped localStorage; persists after logout
  const [cartCount, setCartCount] = useState(0);

  const user = typeof window !== "undefined"
    ? JSON.parse(localStorage.getItem("shop_user") ?? "null")
    : null;

  useEffect(() => {
    // Seed local cart count from unscoped localStorage on mount
    setCartCount(getLocalCartCount());
  }, []);

  useEffect(() => {
    fetch(`${API}/api/products`)
      .then((r) => r.json())
      .then(setProducts)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const addToCart = async (productId: string) => {
    const token = localStorage.getItem("shop_token");
    if (!token) {
      window.location.href = "/auth/login";
      return;
    }
    const product = products.find((p) => p.id === productId);
    if (product) {
      addToLocalCart({ productId, name: product.name, price: product.price });
    }
    await fetch(`${API}/api/cart`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ product_id: productId, quantity: 1 }),
    });
    // DEBUGRA_BUG:SHOP-06 — count from unscoped localStorage, not user-scoped API
    setCartCount(getLocalCartCount());
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b px-6 py-3 flex items-center justify-between sticky top-0 z-10" data-testid="shop-nav">
        <span className="font-bold text-indigo-700 text-lg">TechShop</span>
        <div className="flex items-center gap-4">
          {user ? (
            <>
              <span className="text-sm text-gray-600" data-testid="user-name">{user.name}</span>
              <Link href="/cart" className="relative text-sm text-indigo-600" data-testid="cart-link">
                🛒 Cart
                {cartCount > 0 && (
                  <span className="ml-1 text-xs bg-red-500 text-white rounded-full px-1.5">{cartCount}</span>
                )}
              </Link>
              <Link href="/orders" className="text-sm text-indigo-600 hover:underline" data-testid="orders-link">
                Orders
              </Link>
              <button
                onClick={() => {
                  localStorage.removeItem("shop_token");
                  localStorage.removeItem("shop_user");
                  // DEBUGRA_BUG:SHOP-06 — shop_cart NOT cleared here; persists for next user
                  window.location.reload();
                }}
                className="text-sm text-red-500 hover:underline"
                data-testid="logout-button"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link href="/auth/login" className="text-sm text-indigo-600 hover:underline" data-testid="login-link">Sign In</Link>
              <Link href="/auth/register" className="text-sm px-3 py-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">Register</Link>
            </>
          )}
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold mb-6">Products</h1>
        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-64 bg-gray-200 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
            {products.map((p) => (
              <div key={p.id} className="bg-white rounded-xl border overflow-hidden" data-testid={`product-card-${p.id}`}>
                <div className="aspect-video bg-gray-100 flex items-center justify-center">
                  {/* DEBUGRA_BUG:SHOP-07 — image_url is broken, will 404 */}
                  <img
                    src={p.image_url}
                    alt={p.name}
                    className="w-full h-full object-cover"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    data-testid="product-image"
                  />
                </div>
                <div className="p-4 space-y-2">
                  <h3 className="font-semibold text-gray-900" data-testid="product-name">{p.name}</h3>
                  <p className="text-sm text-gray-500">{p.description}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-bold text-indigo-700" data-testid="product-price">${p.price.toFixed(2)}</span>
                    <button
                      onClick={() => addToCart(p.id)}
                      className="text-sm px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors"
                      data-testid="add-to-cart-button"
                    >
                      Add to Cart
                    </button>
                  </div>
                  <p className="text-xs text-gray-400">{p.stock} in stock</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
