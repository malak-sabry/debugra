"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8002";

interface CartItem {
  id: string;
  product_id: string;
  product_name: string;
  unit_price: number;
  quantity: number;
  subtotal: number;
}

export default function CartPage() {
  const [items, setItems] = useState<CartItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const token = typeof window !== "undefined" ? localStorage.getItem("shop_token") ?? "" : "";

  const fetchCart = async () => {
    if (!token) { window.location.href = "/auth/login"; return; }
    try {
      const res = await fetch(`${API}/api/cart`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCart(); }, []);

  const removeItem = async (itemId: string) => {
    await fetch(`${API}/api/cart/${itemId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    fetchCart();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <Link href="/" className="font-bold text-indigo-700">← TechShop</Link>
        <h1 className="font-semibold">Your Cart</h1>
      </nav>

      <main className="max-w-3xl mx-auto px-6 py-8">
        {loading ? (
          <div className="space-y-3">
            {[1, 2].map((i) => <div key={i} className="h-16 bg-gray-200 rounded-xl animate-pulse" />)}
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-16 space-y-4">
            <p className="text-gray-500" data-testid="empty-cart">Your cart is empty</p>
            <Link href="/" className="text-indigo-600 hover:underline text-sm">Browse products</Link>
          </div>
        ) : (
          <div className="space-y-4">
            {items.map((item) => (
              <div key={item.id} className="bg-white rounded-xl border px-5 py-4 flex items-center justify-between" data-testid={`cart-item-${item.id}`}>
                <div>
                  <p className="font-medium text-gray-900" data-testid="item-name">{item.product_name}</p>
                  <p className="text-sm text-gray-500">Qty: {item.quantity} × ${item.unit_price.toFixed(2)}</p>
                </div>
                <div className="flex items-center gap-4">
                  <span className="font-semibold" data-testid="item-subtotal">${item.subtotal.toFixed(2)}</span>
                  <button
                    onClick={() => removeItem(item.id)}
                    className="text-xs text-red-500 hover:underline"
                    data-testid="remove-item-button"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}

            <div className="bg-white rounded-xl border px-5 py-4 flex items-center justify-between">
              <span className="font-semibold text-lg">Total</span>
              <span className="font-bold text-xl text-indigo-700" data-testid="cart-total">${total.toFixed(2)}</span>
            </div>

            <Link
              href="/checkout"
              className="block w-full text-center bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-medium transition-colors"
              data-testid="checkout-button"
            >
              Proceed to Checkout
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
