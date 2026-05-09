"use client";

import { useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8002";

export default function CheckoutPage() {
  const [address, setAddress] = useState("");
  const [discountCode, setDiscountCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [orderId, setOrderId] = useState<string | null>(null);

  const token = typeof window !== "undefined" ? localStorage.getItem("shop_token") ?? "" : "";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/api/checkout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          shipping_address: address,
          discount_code: discountCode || null,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setOrderId(data.order_id);
        // DEBUGRA_BUG:SHOP-08 — Missing history.replaceState; back button returns here
      } else {
        setError(data.detail ?? "Checkout failed");
      }
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  };

  if (orderId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white rounded-xl shadow p-8 w-full max-w-md text-center space-y-4">
          <div className="text-5xl">✅</div>
          <h2 className="text-xl font-bold text-gray-900">Order Confirmed!</h2>
          <p className="text-gray-500 text-sm" data-testid="order-id">Order ID: {orderId}</p>
          <Link href="/" className="block text-indigo-600 hover:underline text-sm" data-testid="continue-shopping">
            Continue Shopping
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b px-6 py-3 flex items-center">
        <Link href="/cart" className="font-bold text-indigo-700">← Cart</Link>
        <h1 className="font-semibold ml-4">Checkout</h1>
      </nav>

      <main className="max-w-lg mx-auto px-6 py-8">
        <div className="bg-white rounded-xl shadow p-6 space-y-5">
          <form onSubmit={handleSubmit} className="space-y-4" data-testid="checkout-form">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Shipping Address</label>
              {/* DEBUGRA_BUG:SHOP-04 — No client-side validation; empty address allowed */}
              <textarea
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                rows={3}
                placeholder="123 Main St, City, State 12345"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                data-testid="address-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Discount Code (optional)</label>
              <input
                type="text"
                value={discountCode}
                onChange={(e) => setDiscountCode(e.target.value)}
                placeholder="SAVE10 or SAVE20"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                data-testid="discount-code-input"
              />
            </div>
            {error && <p className="text-red-500 text-sm" data-testid="error-message">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-medium transition-colors disabled:opacity-60"
              data-testid="place-order-button"
            >
              {loading ? "Processing…" : "Place Order"}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
