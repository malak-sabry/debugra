"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8002";

interface OrderItem {
  id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
}

interface Order {
  id: string;
  total: number;
  status: string;
  shipping_address: string;
  discount_code: string | null;
  created_at: string;
  items: OrderItem[];
}

export default function OrdersPage() {
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("shop_token");
    if (!token) { router.push("/auth/login"); return; }

    fetch(`${BASE}/api/checkout/orders`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Failed to load orders: ${r.status}`);
        return r.json();
      })
      .then(setOrders)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [router]);

  const statusColor: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-700",
    paid: "bg-green-100 text-green-700",
    shipped: "bg-blue-100 text-blue-700",
    cancelled: "bg-red-100 text-red-700",
  };

  if (loading) return <div className="flex items-center justify-center min-h-screen text-gray-500">Loading…</div>;
  if (error) return <div className="flex items-center justify-center min-h-screen text-red-500">{error}</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <Link href="/" className="text-blue-600 font-semibold text-lg">← Shop</Link>
        <Link href="/cart" className="text-sm text-gray-600 hover:text-gray-900">Cart</Link>
      </nav>

      <main className="max-w-3xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">My Orders</h1>

        {orders.length === 0 ? (
          <div className="bg-white rounded-xl shadow p-10 text-center">
            <p className="text-gray-400 text-lg mb-4">No orders yet.</p>
            <Link href="/" className="text-blue-600 hover:underline">Browse products →</Link>
          </div>
        ) : (
          <div className="space-y-4">
            {orders.map((order) => (
              <div key={order.id} className="bg-white rounded-xl shadow overflow-hidden">
                <button
                  onClick={() => setExpanded(expanded === order.id ? null : order.id)}
                  className="w-full text-left px-6 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-mono text-gray-400">#{order.id.slice(0, 8)}</p>
                      <p className="font-semibold text-gray-900 mt-0.5">
                        ${(order.total / 100).toFixed(2)}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {new Date(order.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span
                        className={`text-xs px-2 py-1 rounded-full font-medium ${
                          statusColor[order.status] ?? "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {order.status}
                      </span>
                      <span className="text-gray-400">{expanded === order.id ? "▲" : "▼"}</span>
                    </div>
                  </div>
                </button>

                {expanded === order.id && (
                  <div className="border-t px-6 py-4 bg-gray-50">
                    <p className="text-sm text-gray-500 mb-3">
                      <span className="font-medium">Ship to:</span> {order.shipping_address}
                    </p>
                    {order.discount_code && (
                      <p className="text-sm text-green-600 mb-3">
                        Discount applied: <span className="font-mono">{order.discount_code}</span>
                      </p>
                    )}
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-gray-400 border-b">
                          <th className="pb-2 font-medium">Item</th>
                          <th className="pb-2 font-medium text-right">Qty</th>
                          <th className="pb-2 font-medium text-right">Price</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {(order.items ?? []).map((item) => (
                          <tr key={item.id}>
                            <td className="py-2 text-gray-800">{item.product_name}</td>
                            <td className="py-2 text-right text-gray-600">{item.quantity}</td>
                            <td className="py-2 text-right text-gray-800">
                              ${((item.unit_price * item.quantity) / 100).toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="border-t font-semibold">
                          <td className="pt-2" colSpan={2}>Total</td>
                          <td className="pt-2 text-right">${(order.total / 100).toFixed(2)}</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
